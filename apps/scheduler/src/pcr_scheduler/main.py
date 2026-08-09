"""Scheduler service entry point."""

from __future__ import annotations

import logging
import signal
from threading import Event

from .config import ConfigurationError, SchedulerConfig
from .health import HealthServer
from .runner import ShadowScheduler
from .state import HeartbeatState
from .store import PostgresSchedulerStore
from .structured_log import configure_logging


LOG = logging.getLogger(__name__)


def main() -> int:
    configure_logging()
    try:
        config = SchedulerConfig.from_env()
    except ConfigurationError:
        LOG.exception("scheduler_configuration_invalid")
        return 2

    state = HeartbeatState(enabled=config.enabled, shadow_mode=config.shadow_mode)
    health = HealthServer(config.health_host, config.health_port, state)
    stop = Event()

    def request_stop(*_args: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    health.start()

    if not config.enabled:
        state.update(status="disabled", ready=True)
        LOG.info("scheduler_disabled", extra=config.public_view())
        while not stop.wait(config.poll_interval_seconds):
            state.update(status="disabled", ready=True)
        health.close()
        return 0

    store = PostgresSchedulerStore(config.database_url or "")
    scheduler = ShadowScheduler(config, store, state)
    LOG.info("scheduler_started", extra=config.public_view())
    try:
        scheduler.run(stop)
    finally:
        store.close()
        health.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
