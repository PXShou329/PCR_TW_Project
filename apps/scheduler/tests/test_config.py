from __future__ import annotations

import pytest

from pcr_scheduler.config import ConfigurationError, SchedulerConfig


def test_safe_defaults_are_disabled_shadow_only() -> None:
    config = SchedulerConfig.from_env({})
    assert config.enabled is False
    assert config.shadow_mode is True
    assert config.auto_publish is False
    assert "database_url" not in config.public_view()


@pytest.mark.parametrize(
    "settings",
    [
        {"AUTO_PUBLISH": "true"},
        {"SHADOW_MODE": "false"},
        {"SCHEDULER_ENABLED": "true"},
        {"SCHEDULER_ENABLED": "perhaps"},
        {"SCHEDULER_POLL_SECONDS": "60", "SCHEDULER_LEASE_TTL_SECONDS": "60"},
    ],
)
def test_unsafe_or_ambiguous_configuration_fails_closed(
    settings: dict[str, str],
) -> None:
    with pytest.raises(ConfigurationError):
        SchedulerConfig.from_env(settings)


def test_enabled_mode_requires_database_but_remains_shadow() -> None:
    config = SchedulerConfig.from_env(
        {
            "SCHEDULER_ENABLED": "true",
            "DATABASE_URL": "postgresql://example.invalid/local",
        }
    )
    assert config.enabled is True
    assert config.shadow_mode is True
    assert config.auto_publish is False
