from __future__ import annotations

from pathlib import Path

import pytest

from pcr_database.provision_roles import (
    APPEND_ONLY_TABLES,
    CORE_MIRROR_TABLES,
    MUTABLE_MIRROR_TABLES,
    SERVING_TABLES,
    TYPED_SERVING_TABLES,
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
    assert len(TYPED_SERVING_TABLES) == 24
    assert len(MUTABLE_MIRROR_TABLES) == 28
    assert len(SERVING_TABLES) == 29
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
    assert {
        "gacha_timeline_events",
        "gacha_timeline_evidence",
        "gacha_timeline_claims",
        "gacha_community_sources",
        "gacha_timeline_community_sources",
    } <= set(TYPED_SERVING_TABLES)


def test_runtime_privilege_verifier_covers_gacha_allow_and_deny_probes() -> None:
    verifier_path = (
        Path(__file__).resolve().parents[2] / "scripts" / "check_db_privileges.ps1"
    )
    verifier = verifier_path.read_text(encoding="utf-8")

    for table in {
        "gacha_timeline_events",
        "gacha_timeline_evidence",
        "gacha_timeline_claims",
        "gacha_community_sources",
        "gacha_timeline_community_sources",
    }:
        assert f'"{table}"' in verifier
    assert 'Assert-SqlDenied "api-gacha-update"' in verifier
    assert 'Assert-SqlDenied "api-gacha-truncate"' in verifier
    assert '"permission denied for table gacha_timeline_claims"' in verifier
    assert 'Assert-SqlDenied "scheduler-gacha-update"' in verifier
    assert "SET LOCAL ROLE pcr_api; SELECT 1 FROM gacha_timeline_events" in verifier
    assert "SET LOCAL ROLE pcr_importer; UPDATE gacha_timeline_events" in verifier
    for privilege in ("TRUNCATE", "REFERENCES", "TRIGGER"):
        assert f'"{privilege}"' in verifier
    assert "$matrixChecks -ne 651 -or $actualDenials -ne 23 -or $allowedSmokes -ne 10" in verifier
