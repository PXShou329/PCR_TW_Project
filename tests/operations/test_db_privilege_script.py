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
    assert "($servingTables.Count + $controlTables.Count)" in source
    assert "$tablePrivileges.Count" in source
    assert "$serviceRoles.Count" in source
    assert "$expectedMatrixChecks -ne 777" in source
    assert "$matrixChecks -ne $expectedMatrixChecks" in source
    assert "$actualDenials -ne 26" in source
    assert "$allowedSmokes -ne 12" in source
    assert 'Assert-SqlDenied "api-parena-update"' in source
    assert 'Assert-SqlDenied "api-parena-truncate"' in source
    assert 'Assert-SqlDenied "scheduler-parena-update"' in source
