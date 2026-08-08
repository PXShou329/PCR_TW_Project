from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import pcr_pipeline.import_pve as import_cli
from pcr_pipeline.research_core_snapshot import (
    EXPECTED_MANIFEST_SHA256,
    RP_A3_MANIFEST_SHA256,
)


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


def test_approved_rollback_source_uses_exact_snapshot_contract(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    calls = []
    report = SimpleNamespace(file_count=48, csv_row_count=239)
    snapshot = SimpleNamespace(
        manifest_sha256=RP_A3_MANIFEST_SHA256,
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
        lambda *_args: pytest.fail("A4 baseline must not judge immutable A3"),
    )
    core = tmp_path / "core"
    manifest = tmp_path / "manifest.sha256"
    import_cli._verify_import_source(
        core,
        manifest,
        RP_A3_MANIFEST_SHA256,
        tmp_path / "checker.py",
    )

    assert calls == [
        (
            core,
            manifest,
            {"expected_manifest_sha256": RP_A3_MANIFEST_SHA256},
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
