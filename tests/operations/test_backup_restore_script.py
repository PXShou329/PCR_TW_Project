from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKUP_RESTORE_SCRIPT = REPOSITORY_ROOT / "scripts" / "backup_restore_smoke.ps1"


def test_alembic_downgrade_uses_installed_psycopg3_driver() -> None:
    source = BACKUP_RESTORE_SCRIPT.read_text(encoding="utf-8")
    rollback = source[source.index("# The restored clone now contains") :]

    assert '$ownerRestoreMigrationUrl = "postgresql+psycopg://' in source
    assert '--env "PCR_DATABASE_URL=$ownerRestoreMigrationUrl"' in rollback
    assert '--env "PCR_DATABASE_URL=$ownerRestoreUrl"' not in rollback
