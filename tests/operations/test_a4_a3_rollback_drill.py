from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "a4_a3_rollback_drill.ps1"


def test_a4_a3_drill_uses_pinned_source_and_restores_a4() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "PINNED_ROLLBACK_SOURCE_OK" in source
    assert "Write-Host $proofLine" in source
    assert "$proof.manifest_sha256 -ne $a3ManifestSha256" in source
    assert "$proof.revision_id -ne $a3Revision" in source
    assert "research_core_rp_a3_manifest.sha256" in source
    assert "ab62e07483dfea07c992b950b9c05c74fa0e3767fa0b3bce64b20193a1860333" in source
    assert "46d4fea8c1c5cd92e2fd5cb71a7a3ca232d872b1c6d56ce6cd100971250bde45" in source
    assert "67e8f2c5435ab70af951e94daab814cf524cb09853b2ab0008d9f32499bfa2b1" in source
    assert "SELECT COUNT(*) FROM team_members WHERE is_borrowed IS NULL" in source
    assert 'borrowedNulls -ne 0' in source
    assert "downgrade v0004_unknown_operation_mode" in source
    assert "A4_A3_ROLLBACK_READY_OK" in source
    assert "alembic -c database/alembic.ini upgrade head" in source
    assert "A4_RESTORED_OK" in source
    assert "A4_A3_ROLLBACK_DRILL_OK" in source
    assert "$LeaveAtA3" in source
    assert "A3_SERVICES_QUIESCED_OK" in source
    assert "A4_A3_ROLLBACK_COMPLETE_OK" in source


def test_a4_a3_drill_arms_recovery_before_side_effects() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    stop_call = source.index("Invoke-Compose stop web api scheduler")
    restart_guard = source.index("$servicesStopped = $true")
    importer_call = source.index("$rollbackOutput = & docker")
    restore_guard = source.index("$needsA4Restore = $true")

    assert restart_guard < stop_call
    assert restore_guard < importer_call


def test_a4_a3_drill_restarts_only_after_verified_a4_health() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    restart_gate = source.index("if ($servicesStopped -and -not $needsA4Restore)")
    database_guard = source.index("Assert-A4DatabaseState", restart_gate)
    compose_wait = source.index(
        "Invoke-Compose up --detach --no-build --wait --wait-timeout 60",
        database_guard,
    )
    readiness = source.index('/health/ready"', compose_wait)
    success = source.index("A4_SERVICES_READY_OK", readiness)

    assert restart_gate < database_guard < compose_wait < readiness < success
    assert "SERVICES_LEFT_QUIESCED" in source
    assert "Invoke-Compose stop web api scheduler" in source[compose_wait:]


def test_permanent_a3_boundary_is_after_exact_identity_and_downgrade_checks() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    precheck = source.index("$activeMaterialization -ne $a3Materialization")
    downgrade = source.index("downgrade v0004_unknown_operation_mode", precheck)
    post_revision = source.index(
        '$downgradedRevision -ne "v0004_unknown_operation_mode"', downgrade
    )
    post_identity = source.index(
        "$downgradedMaterialization -ne $a3Materialization", post_revision
    )
    permanent_boundary = source.index("$leaveAtA3Completed = $true", post_identity)

    assert precheck < downgrade < post_revision < post_identity < permanent_boundary


def test_scheduler_safety_flags_are_checked_before_quiesce_or_mutation() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    scheduler_guard = source.index("SCHEDULER_ENABLED must remain false")
    shadow_guard = source.index("SHADOW_MODE must remain true")
    publisher_guard = source.index("AUTO_PUBLISH must remain false")
    first_side_effect = source.index("Invoke-Compose stop web api scheduler")

    assert scheduler_guard < first_side_effect
    assert shadow_guard < first_side_effect
    assert publisher_guard < first_side_effect
