from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import pcr_pipeline.import_pve as import_cli
from pcr_pipeline.research_core_snapshot import (
    EXPECTED_MANIFEST_SHA256,
    RP_A3_MANIFEST_SHA256,
    RP_A4_MANIFEST_SHA256,
    RP_A5_MANIFEST_SHA256,
    RP_A6_0_MANIFEST_SHA256,
    RP_B5_1_MANIFEST_SHA256,
)


ROOT = Path(__file__).resolve().parents[2]
BASELINE_CHECKER = ROOT / "scripts" / "check_research_baseline.py"
VALIDATOR = ROOT / "research_core" / "pcr_tw_project" / "tools" / "validate_project.py"


def test_active_import_source_runs_the_live_baseline(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[Path, Path]] = []
    monkeypatch.setattr(
        import_cli,
        "_verify_research_baseline",
        lambda research_core, checker: calls.append((research_core, checker)),
    )

    core = tmp_path / "core"
    checker = tmp_path / "checker.py"
    import_cli._verify_import_source(
        core,
        tmp_path / "manifest.sha256",
        EXPECTED_MANIFEST_SHA256,
        checker,
    )

    assert calls == [(core, checker)]


@pytest.mark.parametrize(
    ("manifest_sha256", "csv_row_count"),
    [
        (RP_A3_MANIFEST_SHA256, 239),
        (RP_A4_MANIFEST_SHA256, 325),
        (RP_A5_MANIFEST_SHA256, 356),
        (RP_B5_1_MANIFEST_SHA256, 376),
        (RP_A6_0_MANIFEST_SHA256, 376),
    ],
)
def test_approved_rollback_source_uses_exact_snapshot_contract(
    monkeypatch,
    tmp_path: Path,
    capsys,
    manifest_sha256: str,
    csv_row_count: int,
) -> None:
    calls = []
    report = SimpleNamespace(file_count=48, csv_row_count=csv_row_count)
    snapshot = SimpleNamespace(
        manifest_sha256=manifest_sha256,
        revision_id="a" * 64,
        report=lambda: report,
    )

    def load_snapshot(research_core, manifest_path, **kwargs):
        calls.append((research_core, manifest_path, kwargs))
        return snapshot

    monkeypatch.setattr(import_cli, "load_research_core_snapshot", load_snapshot)
    monkeypatch.setattr(
        import_cli,
        "_verify_research_baseline",
        lambda *_args: pytest.fail("B4-0 baseline must not judge historical pins"),
    )
    core = tmp_path / "core"
    manifest = tmp_path / "manifest.sha256"
    import_cli._verify_import_source(
        core,
        manifest,
        manifest_sha256,
        tmp_path / "checker.py",
    )

    assert calls == [
        (
            core,
            manifest,
            {"expected_manifest_sha256": manifest_sha256},
        )
    ]
    assert "PINNED_ROLLBACK_SOURCE_OK" in capsys.readouterr().out


def test_unapproved_historical_manifest_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="approved rollback pin"):
        import_cli._verify_import_source(
            tmp_path / "core",
            tmp_path / "manifest.sha256",
            "f" * 64,
            tmp_path / "checker.py",
        )


def test_validator_uses_taipei_civil_date_in_every_runtime() -> None:
    source = VALIDATOR.read_text(encoding="utf-8")

    assert "date.today()" not in source
    assert 'timezone(timedelta(hours=8), name="Asia/Taipei")' in source
    assert "datetime.now(TAIPEI_TIMEZONE).date().isoformat()" in source


def test_baseline_reverifies_pinned_tree_after_canonical_write_and_mutation() -> None:
    source = BASELINE_CHECKER.read_text(encoding="utf-8")

    validator_run = source.index("errors.extend(run(project, expected))")
    post_write = source.index('f"post-write tree: {error}"', validator_run)
    mutation_run = source.index("errors.extend(run(project, mutation))", post_write)
    post_mutation = source.index('f"post-mutation tree: {error}"', mutation_run)

    assert validator_run < post_write < mutation_run < post_mutation
