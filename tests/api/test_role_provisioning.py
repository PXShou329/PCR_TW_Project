from __future__ import annotations

import pytest

from pcr_database.provision_roles import (
    APPEND_ONLY_TABLES,
    CORE_MIRROR_TABLES,
    MUTABLE_MIRROR_TABLES,
    SERVING_TABLES,
    _required_secret,
)


@pytest.mark.parametrize("value", ["", "short", "replace-me-now-please", "placeholder-secret-value"])
def test_service_role_passwords_fail_closed(monkeypatch, value: str) -> None:
    monkeypatch.setenv("PCR_API_DB_PASSWORD", value)
    with pytest.raises(RuntimeError, match="non-placeholder secret"):
        _required_secret("PCR_API_DB_PASSWORD")


def test_service_role_password_accepts_non_placeholder_secret(monkeypatch) -> None:
    monkeypatch.setenv("PCR_API_DB_PASSWORD", "test-only-strong-value-123")
    assert _required_secret("PCR_API_DB_PASSWORD") == "test-only-strong-value-123"


def test_timeline_tables_are_inside_the_least_privilege_serving_closure() -> None:
    assert len(SERVING_TABLES) == 24
    assert "operation_timelines" in SERVING_TABLES
    assert "timeline_steps" in SERVING_TABLES
    assert set(CORE_MIRROR_TABLES) == {
        "core_revisions",
        "core_files",
        "core_csv_rows",
        "materialization_state",
    }
    assert APPEND_ONLY_TABLES == ("revision_activations",)
    assert "revision_activations" in SERVING_TABLES
    assert "revision_activations" not in MUTABLE_MIRROR_TABLES
    assert {
        "arena_defenses",
        "arena_defense_members",
        "arena_counters",
        "arena_counter_members",
        "arena_counter_evidence",
        "arena_counter_claims",
    } <= set(MUTABLE_MIRROR_TABLES)
