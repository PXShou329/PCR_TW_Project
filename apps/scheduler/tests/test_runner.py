from __future__ import annotations

from datetime import UTC, datetime

from pcr_scheduler.config import SchedulerConfig
from pcr_scheduler.runner import ShadowScheduler, idempotency_key, schedule_bucket
from pcr_scheduler.state import HeartbeatState
from pcr_scheduler.store import MemorySchedulerStore


def config() -> SchedulerConfig:
    return SchedulerConfig(
        enabled=True,
        database_url="postgresql://unused",
        poll_interval_seconds=60,
        lease_ttl_seconds=180,
    )


def test_schedule_bucket_and_key_are_deterministic() -> None:
    now = datetime(2026, 8, 8, 3, 4, 59, tzinfo=UTC)
    bucket = schedule_bucket(now, 60)
    assert bucket == datetime(2026, 8, 8, 3, 4, tzinfo=UTC)
    assert idempotency_key("job", bucket, "v1") == idempotency_key(
        "job", bucket, "v1"
    )
    assert idempotency_key("job", bucket, "v1") != idempotency_key(
        "job", bucket, "v2"
    )


def test_same_bucket_is_claimed_once_and_never_publishes() -> None:
    store = MemorySchedulerStore()
    state = HeartbeatState(enabled=True, shadow_mode=True)
    scheduler = ShadowScheduler(config(), store, state, owner_id="worker-a")
    now = datetime(2026, 8, 8, 3, 4, 20, tzinfo=UTC)

    assert scheduler.tick(now) == "SHADOW_NOOP"
    assert scheduler.tick(now) == "DUPLICATE_SKIPPED"
    snapshot = state.snapshot()
    assert snapshot["canonical_write_capable"] is False
    assert snapshot["last_run_status"] == "DUPLICATE_SKIPPED"


def test_only_one_owner_holds_unexpired_lease() -> None:
    now = datetime(2026, 8, 8, 3, 4, 20, tzinfo=UTC)
    store = MemorySchedulerStore(clock=lambda: now)
    first = ShadowScheduler(
        config(), store, HeartbeatState(enabled=True, shadow_mode=True), owner_id="a"
    )
    second = ShadowScheduler(
        config(), store, HeartbeatState(enabled=True, shadow_mode=True), owner_id="b"
    )

    assert first.tick(now) == "SHADOW_NOOP"
    assert second.tick(now) == "LEASE_HELD"
