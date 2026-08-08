"""One-process verification of PostgreSQL lease and idempotency wiring."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from .config import SchedulerConfig
from .runner import ShadowScheduler
from .state import HeartbeatState
from .store import PostgresSchedulerStore
from .structured_log import configure_logging


def main() -> int:
    configure_logging()
    config = SchedulerConfig.from_env()
    if not config.enabled:
        raise RuntimeError("scheduler smoke requires SCHEDULER_ENABLED=true")
    state = HeartbeatState(enabled=True, shadow_mode=True)
    store = PostgresSchedulerStore(config.database_url or "")
    try:
        scheduler = ShadowScheduler(config, store, state, owner_id="b0-smoke")
        now = datetime.now(UTC)
        first = scheduler.tick(now)
        second = scheduler.tick(now)
    finally:
        store.close()
    acceptable_first = {"SHADOW_NOOP", "DUPLICATE_SKIPPED"}
    if first not in acceptable_first or second != "DUPLICATE_SKIPPED":
        raise RuntimeError(f"unexpected scheduler results: first={first} second={second}")
    print(
        json.dumps(
            {
                "status": "SCHEDULER_SHADOW_SMOKE_OK",
                "first": first,
                "second": second,
                "canonical_write_capable": False,
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
