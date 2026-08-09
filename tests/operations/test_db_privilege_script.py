from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_db_privilege_runtime_matrix_covers_all_table_privileges() -> None:
    source = (ROOT / "scripts" / "check_db_privileges.ps1").read_text(
        encoding="utf-8"
    )

    for privilege in (
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "TRUNCATE",
        "REFERENCES",
        "TRIGGER",
    ):
        assert f'"{privilege}"' in source
    assert source.count("foreach ($privilege in $tablePrivileges)") == 2
    assert 'Assert-SqlDenied "api-gacha-truncate"' in source
    assert 'TRUNCATE TABLE gacha_timeline_claims' in source
    assert '"permission denied for table gacha_timeline_claims"' in source
    assert '$privilege -in @("SELECT", "INSERT", "UPDATE", "DELETE")' in source
    assert '$privilege -in @("SELECT", "INSERT", "UPDATE")' in source
    assert "$matrixChecks -ne 651" in source
    assert "$actualDenials -ne 23" in source
    assert "$allowedSmokes -ne 10" in source
