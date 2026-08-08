"""Lease and idempotency storage for the shadow scheduler.

Alembic in ``apps/api`` is the sole migration owner.  This module consumes the
``scheduler_leases`` and ``scheduler_runs`` contract; it never creates schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any, Callable, Protocol
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class RunClaim:
    idempotency_key: str
    claimed: bool


class SchedulerStore(Protocol):
    def acquire_lease(self, name: str, owner_id: str, ttl_seconds: int) -> bool: ...

    def claim_run(
        self,
        *,
        idempotency_key: str,
        job_name: str,
        scheduled_for: datetime,
        source_fingerprint: str,
        owner_id: str,
        shadow_mode: bool,
    ) -> RunClaim: ...

    def finish_run(
        self, idempotency_key: str, status: str, detail: dict[str, Any]
    ) -> None: ...

    def close(self) -> None: ...


class MemorySchedulerStore:
    """Deterministic implementation used only by unit tests."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._leases: dict[str, tuple[str, datetime]] = {}
        self._runs: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def acquire_lease(self, name: str, owner_id: str, ttl_seconds: int) -> bool:
        with self._lock:
            now = self._clock()
            current = self._leases.get(name)
            if current and current[0] != owner_id and current[1] > now:
                return False
            self._leases[name] = (owner_id, now + timedelta(seconds=ttl_seconds))
            return True

    def claim_run(
        self,
        *,
        idempotency_key: str,
        job_name: str,
        scheduled_for: datetime,
        source_fingerprint: str,
        owner_id: str,
        shadow_mode: bool,
    ) -> RunClaim:
        with self._lock:
            if idempotency_key in self._runs:
                return RunClaim(idempotency_key, False)
            self._runs[idempotency_key] = {
                "job_name": job_name,
                "scheduled_for": scheduled_for,
                "source_fingerprint": source_fingerprint,
                "owner_id": owner_id,
                "shadow_mode": shadow_mode,
                "status": "STARTED",
            }
            return RunClaim(idempotency_key, True)

    def finish_run(
        self, idempotency_key: str, status: str, detail: dict[str, Any]
    ) -> None:
        with self._lock:
            self._runs[idempotency_key]["status"] = status
            self._runs[idempotency_key]["detail"] = detail

    def close(self) -> None:
        return


class PostgresSchedulerStore:
    """PostgreSQL-backed atomic lease and run claim implementation."""

    def __init__(self, database_url: str) -> None:
        import psycopg

        self._connection = psycopg.connect(database_url, autocommit=False)

    def acquire_lease(self, name: str, owner_id: str, ttl_seconds: int) -> bool:
        statement = """
            INSERT INTO scheduler_leases
                (name, owner_id, acquired_at, expires_at, updated_at)
            VALUES
                (%s, %s, CURRENT_TIMESTAMP,
                 CURRENT_TIMESTAMP + (%s * INTERVAL '1 second'), CURRENT_TIMESTAMP)
            ON CONFLICT (name) DO UPDATE SET
                owner_id = EXCLUDED.owner_id,
                acquired_at = CASE
                    WHEN scheduler_leases.owner_id = EXCLUDED.owner_id
                    THEN scheduler_leases.acquired_at
                    ELSE EXCLUDED.acquired_at
                END,
                expires_at = EXCLUDED.expires_at,
                updated_at = CURRENT_TIMESTAMP
            WHERE scheduler_leases.expires_at <= CURRENT_TIMESTAMP
               OR scheduler_leases.owner_id = EXCLUDED.owner_id
            RETURNING owner_id
        """
        with self._connection.transaction():
            with self._connection.cursor() as cursor:
                cursor.execute(statement, (name, owner_id, ttl_seconds))
                row = cursor.fetchone()
        return bool(row and row[0] == owner_id)

    def claim_run(
        self,
        *,
        idempotency_key: str,
        job_name: str,
        scheduled_for: datetime,
        source_fingerprint: str,
        owner_id: str,
        shadow_mode: bool,
    ) -> RunClaim:
        statement = """
            INSERT INTO scheduler_runs
                (id, idempotency_key, job_name, scheduled_for, source_fingerprint,
                 status, shadow_mode, owner_id, started_at, detail)
            VALUES (%s, %s, %s, %s, %s, 'STARTED', %s, %s, CURRENT_TIMESTAMP, '{}'::jsonb)
            ON CONFLICT DO NOTHING
            RETURNING idempotency_key
        """
        with self._connection.transaction():
            with self._connection.cursor() as cursor:
                cursor.execute(
                    statement,
                    (
                        str(uuid4()),
                        idempotency_key,
                        job_name,
                        scheduled_for,
                        source_fingerprint,
                        shadow_mode,
                        owner_id,
                    ),
                )
                row = cursor.fetchone()
        return RunClaim(idempotency_key, bool(row))

    def finish_run(
        self, idempotency_key: str, status: str, detail: dict[str, Any]
    ) -> None:
        from psycopg.types.json import Jsonb

        database_status = "SKIPPED" if status == "SHADOW_NOOP" else status
        persisted_detail = {**detail, "scheduler_result": status}
        with self._connection.transaction():
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE scheduler_runs
                    SET status = %s, detail = %s, finished_at = CURRENT_TIMESTAMP
                    WHERE idempotency_key = %s
                    """,
                    (database_status, Jsonb(persisted_detail), idempotency_key),
                )

    def close(self) -> None:
        self._connection.close()
