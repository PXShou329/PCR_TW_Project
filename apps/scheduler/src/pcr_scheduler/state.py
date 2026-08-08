"""Thread-safe heartbeat shared by the worker and health server."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class HeartbeatState:
    enabled: bool
    shadow_mode: bool
    status: str = "starting"
    ready: bool = False
    started_at: str = field(default_factory=_now)
    last_heartbeat_at: str | None = None
    last_run_key: str | None = None
    last_run_status: str | None = None
    last_error: str | None = None
    _lock: Lock = field(default_factory=Lock, repr=False)

    def update(self, **changes: Any) -> None:
        with self._lock:
            for name, value in changes.items():
                if not hasattr(self, name) or name == "_lock":
                    raise AttributeError(name)
                setattr(self, name, value)
            self.last_heartbeat_at = _now()

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "service": "scheduler",
                "status": self.status,
                "ready": self.ready,
                "enabled": self.enabled,
                "shadow_mode": self.shadow_mode,
                "canonical_write_capable": False,
                "started_at": self.started_at,
                "last_heartbeat_at": self.last_heartbeat_at,
                "last_run_key": self.last_run_key,
                "last_run_status": self.last_run_status,
                "last_error": self.last_error,
            }
