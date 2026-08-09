"""B0 scheduler loop: lease + idempotent shadow no-op, without network I/O."""

from __future__ import annotations

import hashlib
import logging
import socket
import uuid
from datetime import UTC, datetime
from threading import Event

from .config import SchedulerConfig
from .state import HeartbeatState
from .store import SchedulerStore


LOG = logging.getLogger(__name__)


def schedule_bucket(now: datetime, interval_seconds: int) -> datetime:
    """Floor an aware timestamp to the configured UTC polling bucket."""

    if now.tzinfo is None:
        raise ValueError("schedule_bucket requires an aware datetime")
    seconds = int(now.timestamp())
    return datetime.fromtimestamp(
        seconds - (seconds % interval_seconds),
        tz=UTC,
    )


def idempotency_key(job_name: str, scheduled_for: datetime, fingerprint: str) -> str:
    material = f"{job_name}\n{scheduled_for.astimezone(UTC).isoformat()}\n{fingerprint}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class ShadowScheduler:
    def __init__(
        self,
        config: SchedulerConfig,
        store: SchedulerStore,
        state: HeartbeatState,
        *,
        owner_id: str | None = None,
    ) -> None:
        self._config = config
        self._store = store
        self._state = state
        self._owner_id = owner_id or f"{socket.gethostname()}:{uuid.uuid4()}"

    def tick(self, now: datetime | None = None) -> str:
        current = now or datetime.now(UTC)
        bucket = schedule_bucket(current, self._config.poll_interval_seconds)
        run_key = idempotency_key(
            self._config.job_name,
            bucket,
            self._config.source_fingerprint,
        )
        lease_name = f"scheduler:{self._config.job_name}"
        if not self._store.acquire_lease(
            lease_name, self._owner_id, self._config.lease_ttl_seconds
        ):
            self._state.update(status="standby", ready=True, last_run_status="LEASE_HELD")
            LOG.info("scheduler_lease_held", extra={"job_name": self._config.job_name})
            return "LEASE_HELD"

        claim = self._store.claim_run(
            idempotency_key=run_key,
            job_name=self._config.job_name,
            scheduled_for=bucket,
            source_fingerprint=self._config.source_fingerprint,
            owner_id=self._owner_id,
            shadow_mode=True,
        )
        if not claim.claimed:
            self._state.update(
                status="idle",
                ready=True,
                last_run_key=run_key,
                last_run_status="DUPLICATE_SKIPPED",
            )
            LOG.info("scheduler_duplicate_skipped", extra={"run_key": run_key})
            return "DUPLICATE_SKIPPED"

        # B0 safety boundary: there is intentionally no fetch and no canonical
        # write call here.  The persisted run proves lease/idempotency wiring.
        detail = {
            "action": "none",
            "reason": "B0 shadow scheduler has no source adapter or publisher",
            "canonical_writes": 0,
            "network_requests": 0,
        }
        self._store.finish_run(run_key, "SHADOW_NOOP", detail)
        self._state.update(
            status="idle",
            ready=True,
            last_run_key=run_key,
            last_run_status="SHADOW_NOOP",
            last_error=None,
        )
        LOG.info(
            "scheduler_shadow_noop",
            extra={"run_key": run_key, "job_name": self._config.job_name},
        )
        return "SHADOW_NOOP"

    def run(self, stop: Event) -> None:
        self._state.update(status="idle", ready=True)
        while not stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # boundary: keep health visible for operators
                self._state.update(
                    status="degraded", ready=False, last_error=type(exc).__name__
                )
                LOG.exception("scheduler_tick_failed")
            stop.wait(self._config.poll_interval_seconds)
