from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKUP_RESTORE_SCRIPT = REPOSITORY_ROOT / "scripts" / "backup_restore_smoke.ps1"
API_DOCKERFILE = REPOSITORY_ROOT / "infra" / "docker" / "api.Dockerfile"


def test_lossy_borrowed_state_downgrade_uses_psycopg3_and_must_fail_closed() -> None:
    source = BACKUP_RESTORE_SCRIPT.read_text(encoding="utf-8")
    downgrade_probe = source[source.index("# NULL is canonical source truth") :]

    assert '$ownerRestoreMigrationUrl = "postgresql+psycopg://' in source
    assert '--env "PCR_DATABASE_URL=$ownerRestoreMigrationUrl"' in downgrade_probe
    assert '--env "PCR_DATABASE_URL=$ownerRestoreUrl"' not in downgrade_probe
    assert "downgrade v0004_unknown_operation_mode" in downgrade_probe
    assert "$downgradeExit -eq 0" in downgrade_probe
    assert '$postDowngradeRevision -ne "v0005_borrowed_tristate"' in downgrade_probe
    assert "$borrowedNullBefore -lt 1" in downgrade_probe
    assert "$borrowedNullAfter -ne $borrowedNullBefore" in downgrade_probe
    assert "$unknownTimelineCount -lt 1" in downgrade_probe
    assert "BORROWED_TRISTATE_DOWNGRADE_BLOCKED_OK" in downgrade_probe


def test_api_image_contains_current_and_rollback_manifests() -> None:
    source = API_DOCKERFILE.read_text(encoding="utf-8")

    assert "scripts/research_core_rp_a4_manifest.sha256" in source
    assert "scripts/research_core_rp_a3_manifest.sha256" in source
    assert "scripts/research_core_rp_a2_manifest.sha256" in source
