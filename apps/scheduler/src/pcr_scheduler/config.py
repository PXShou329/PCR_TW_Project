"""Environment configuration with fail-closed B0 safety rules."""

from __future__ import annotations

from dataclasses import dataclass
from os import environ
from typing import Mapping


TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
FALSE_VALUES = frozenset({"0", "false", "no", "off"})


class ConfigurationError(ValueError):
    """Raised when scheduler settings would violate the B0 safety boundary."""


def _boolean(values: Mapping[str, str], key: str, default: bool) -> bool:
    raw = values.get(key)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ConfigurationError(
        f"{key} must be one of {sorted(TRUE_VALUES | FALSE_VALUES)}; got {raw!r}"
    )


def _integer(
    values: Mapping[str, str], key: str, default: int, *, minimum: int, maximum: int
) -> int:
    raw = values.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{key} must be an integer; got {raw!r}") from exc
    if not minimum <= parsed <= maximum:
        raise ConfigurationError(
            f"{key} must be between {minimum} and {maximum}; got {parsed}"
        )
    return parsed


@dataclass(frozen=True, slots=True)
class SchedulerConfig:
    """Runtime configuration.

    B0 deliberately has no publishing implementation.  ``AUTO_PUBLISH=true`` is
    rejected even when shadow mode is disabled, so a deployment cannot turn the
    walking skeleton into a canonical writer through configuration alone.
    """

    enabled: bool = False
    shadow_mode: bool = True
    auto_publish: bool = False
    database_url: str | None = None
    health_host: str = "0.0.0.0"
    health_port: int = 8081
    poll_interval_seconds: int = 60
    lease_ttl_seconds: int = 180
    job_name: str = "shadow_source_scan"
    source_fingerprint: str = "b0-no-fetch-v1"

    @classmethod
    def from_env(cls, values: Mapping[str, str] | None = None) -> "SchedulerConfig":
        source = environ if values is None else values
        config = cls(
            enabled=_boolean(source, "SCHEDULER_ENABLED", False),
            shadow_mode=_boolean(source, "SHADOW_MODE", True),
            auto_publish=_boolean(source, "AUTO_PUBLISH", False),
            database_url=source.get("DATABASE_URL") or None,
            health_host=source.get("SCHEDULER_HEALTH_HOST", "0.0.0.0"),
            health_port=_integer(
                source, "SCHEDULER_HEALTH_PORT", 8081, minimum=1, maximum=65535
            ),
            poll_interval_seconds=_integer(
                source, "SCHEDULER_POLL_SECONDS", 60, minimum=5, maximum=3600
            ),
            lease_ttl_seconds=_integer(
                source, "SCHEDULER_LEASE_TTL_SECONDS", 180, minimum=30, maximum=3600
            ),
            job_name=source.get("SCHEDULER_JOB_NAME", "shadow_source_scan").strip(),
            source_fingerprint=source.get(
                "SCHEDULER_SOURCE_FINGERPRINT", "b0-no-fetch-v1"
            ).strip(),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.auto_publish:
            raise ConfigurationError(
                "AUTO_PUBLISH=true is unavailable in B0; canonical writes are not implemented"
            )
        if not self.shadow_mode:
            raise ConfigurationError("SHADOW_MODE must remain true in B0")
        if self.enabled and not self.database_url:
            raise ConfigurationError("DATABASE_URL is required when SCHEDULER_ENABLED=true")
        if not self.job_name:
            raise ConfigurationError("SCHEDULER_JOB_NAME cannot be blank")
        if not self.source_fingerprint:
            raise ConfigurationError("SCHEDULER_SOURCE_FINGERPRINT cannot be blank")
        if self.lease_ttl_seconds <= self.poll_interval_seconds:
            raise ConfigurationError(
                "SCHEDULER_LEASE_TTL_SECONDS must be greater than SCHEDULER_POLL_SECONDS"
            )

    def public_view(self) -> dict[str, object]:
        """Return a health-safe view which never includes DATABASE_URL."""

        return {
            "enabled": self.enabled,
            "shadow_mode": self.shadow_mode,
            "auto_publish": self.auto_publish,
            "poll_interval_seconds": self.poll_interval_seconds,
            "lease_ttl_seconds": self.lease_ttl_seconds,
            "job_name": self.job_name,
            "source_fingerprint": self.source_fingerprint,
        }
