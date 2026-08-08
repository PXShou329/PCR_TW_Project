from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import shutil
import stat
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from pcr_database.models import Base, CoreCsvRow, CoreFile, CoreRevision, ImportRun
from pcr_pipeline.research_core_snapshot import (
    EXPECTED_MANIFEST_SHA256,
    ExportSafetyError,
    SnapshotDriftError,
    SnapshotValidationError,
    canonical_json_bytes,
    canonical_manifest_sha256,
    core_materialization_manifest,
    csv_aggregate_semantic_sha256,
    export_materialized_revision,
    finalize_materialized_snapshot,
    json_semantic_sha256,
    load_pinned_manifest,
    load_research_core_snapshot,
    materialize_snapshot,
    materialized_drift_reason,
    materialized_report,
    raw_tree_aggregate_sha256,
)
from pcr_pipeline.verify_round_trip import run_round_trip_smoke


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_CORE = ROOT / "research_core" / "pcr_tw_project"
MANIFEST = ROOT / "scripts" / "research_core_rp_a2_manifest.sha256"
RAW_TREE_SHA256 = "fd3f1a0a102873ad4a0f0248e24f52cfc0e4e2e7f371e3abe35fd6848ba00900"


def sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


def write_tree_manifest(root: Path, destination: Path) -> str:
    lines = []
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix()
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return canonical_manifest_sha256(lines)


def copied_core(tmp_path: Path) -> Path:
    destination = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, destination)
    return destination


def add_import_run(session: Session, run_id: str, fixture_sha256: str) -> None:
    run = ImportRun(
        id=run_id,
        fixture_sha256=fixture_sha256,
        canonical_source="research_core_rp_a2",
        research_core_version="1.5",
        application_version="3.0.0-b1",
        imported_at=datetime.now(timezone.utc),
        status="RUNNING",
        manifest={"materialization": {"sha256": "a" * 64}},
        row_counts={},
    )
    session.add(run)
    session.flush()
    run.status = "SUCCEEDED"
    session.flush()


def test_manifest_pinned_loader_preserves_exact_rows_and_directed_edges() -> None:
    snapshot = load_research_core_snapshot(RESEARCH_CORE, MANIFEST)
    report = snapshot.report()

    assert snapshot.manifest_sha256 == EXPECTED_MANIFEST_SHA256
    assert snapshot.raw_tree_sha256 == RAW_TREE_SHA256
    assert report.file_count == 48
    assert report.csv_file_count == 13
    assert report.csv_row_count == 215
    assert report.csv_row_counts == {
        "17_TEST_EXECUTION_LOG.csv": 0,
        "18_TW_CHARACTER_AVAILABILITY.csv": 15,
        "24_PVE_GUIDE_REGISTRY.csv": 2,
        "25_PVE_TEAM_REGISTRY.csv": 3,
        "26_PVE_OPERATION_TIMELINES.csv": 8,
        "27_PVE_TIMELINE_STEPS.csv": 14,
        "39_ARENA_COUNTER_REGISTRY.csv": 0,
        "41_GACHA_TIMELINE.csv": 3,
        "45_GACHA_COMMUNITY_SOURCE_INDEX.csv": 4,
        "46_ARENA_SOURCE_REGISTRY.csv": 5,
        "47_PRINCESS_ARENA_CASE_REGISTRY.csv": 0,
        "92_EVIDENCE_LEDGER.csv": 75,
        "93_CLAIM_REGISTER.csv": 86,
    }
    guide = snapshot.csv_file("24_PVE_GUIDE_REGISTRY.csv").row_by_key(
        "TW_DEEP_FIRE_08_10_20260802"
    )
    assert guide.natural_key == "TW_DEEP_FIRE_08_10_20260802"
    assert guide.as_mapping(snapshot.csv_file("24_PVE_GUIDE_REGISTRY.csv").header)[
        "team_count"
    ] == "3"
    assert all(isinstance(value, str) for value in guide.values)

    assert report.evidence_to_claim_count == 75
    assert report.claim_to_evidence_count == 162
    assert ("ev053", "CLM-PVE-F810-STD") in snapshot.evidence_to_claim_edges
    assert ("CLM-PVE-F810-STD", "ev053") not in snapshot.claim_to_evidence_edges
    assert report.ev053_asymmetry_preserved is True

    assert Counter(file.file_role for file in snapshot.files) == {
        "STRUCTURED_DATA": 13,
        "VALIDATOR_GENERATED": 4,
        "VALIDATOR_TOOL": 2,
        "VERSIONED_STATIC_ASSET": 29,
    }
    readme = snapshot.file("README.md")
    assert (readme.semantic_kind, readme.encoding_profile, readme.newline_profile) == (
        "raw",
        "UTF-8",
        "LF",
    )
    stats = snapshot.file("tools/stats.json")
    assert (stats.file_role, stats.semantic_kind, stats.newline_profile) == (
        "VALIDATOR_GENERATED",
        "json",
        "CRLF",
    )
    assert (
        snapshot.file("tools/validation_config.json").file_role
        == "VERSIONED_STATIC_ASSET"
    )
    assert snapshot.file("tools/validate_project.py").file_role == "VALIDATOR_TOOL"
    assert snapshot.file("92_EVIDENCE_LEDGER.csv").file_role == "STRUCTURED_DATA"

    manifest_files = core_materialization_manifest(snapshot)["files"]
    for file in snapshot.files:
        manifest_file = manifest_files[file.relative_path]
        assert manifest_file["semantic_kind"] == file.semantic_kind
        assert manifest_file["semantic_sha256"] == file.semantic_sha256
        assert manifest_file["file_role"] == file.file_role
        assert manifest_file["encoding_profile"] == file.encoding_profile
        assert manifest_file["newline_profile"] == file.newline_profile


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda core: (core / "README.md").unlink(), "missing="),
        (lambda core: (core / "EXTRA.md").write_text("extra", encoding="utf-8"), "extra="),
    ],
)
def test_loader_rejects_missing_and_extra_files(tmp_path: Path, mutation, message: str) -> None:
    core = copied_core(tmp_path)
    mutation(core)
    with pytest.raises(SnapshotValidationError, match=message):
        load_research_core_snapshot(core, MANIFEST)


def test_loader_rejects_any_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    core = copied_core(tmp_path)
    target = core / "README.md"
    original_lstat = Path.lstat

    def fake_lstat(path: Path):
        result = original_lstat(path)
        if path == target:
            values = list(result)
            values[0] = stat.S_IFLNK | 0o777
            return os.stat_result(values)
        return result

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(SnapshotValidationError, match="symlink"):
        load_research_core_snapshot(core, MANIFEST)


@pytest.mark.parametrize(
    "target_kind",
    (
        "root",
        "root_ancestor",
        "manifest",
        "manifest_ancestor",
        "walk_directory",
        "walk_file",
    ),
)
def test_loader_rejects_mocked_windows_reparse_points(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_kind: str,
) -> None:
    core = copied_core(tmp_path)
    targets = {
        "root": core,
        "root_ancestor": core.parent,
        "manifest": MANIFEST,
        "manifest_ancestor": MANIFEST.parent,
        "walk_directory": core / "tools",
        "walk_file": core / "README.md",
    }
    target = targets[target_kind]
    original_lstat = Path.lstat
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)

    def fake_lstat(path: Path):
        result = original_lstat(path)
        if path == target:
            return SimpleNamespace(
                st_mode=result.st_mode,
                st_file_attributes=reparse_flag,
            )
        return result

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(SnapshotValidationError, match="symlink or reparse point"):
        load_research_core_snapshot(core, MANIFEST)


def test_manifest_rejects_case_and_unicode_collisions_and_unsafe_paths(
    tmp_path: Path,
) -> None:
    collision_lines = [f"{'0' * 64}  A.md", f"{'1' * 64}  a.md"]
    collision_manifest = tmp_path / "collision.sha256"
    collision_manifest.write_text("\n".join(collision_lines) + "\n", encoding="utf-8")
    with pytest.raises(SnapshotValidationError, match="case/Unicode collision"):
        load_pinned_manifest(
            collision_manifest,
            expected_manifest_sha256=canonical_manifest_sha256(collision_lines),
            expected_file_count=2,
        )

    for index, unsafe in enumerate(("../escape.md", "bad\\path.md", "e\u0301.md")):
        lines = [f"{'0' * 64}  {unsafe}"]
        manifest = tmp_path / f"unsafe-{index}.sha256"
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with pytest.raises(SnapshotValidationError, match="path"):
            load_pinned_manifest(
                manifest,
                expected_manifest_sha256=canonical_manifest_sha256(lines),
                expected_file_count=1,
            )


def test_tree_framing_and_csv_semantics_preserve_boundaries_and_row_order() -> None:
    assert raw_tree_aggregate_sha256({"a": b"bc"}) != raw_tree_aggregate_sha256(
        {"ab": b"c"}
    )
    with pytest.raises(SnapshotValidationError, match="collision"):
        raw_tree_aggregate_sha256({"A": b"one", "a": b"two"})

    header = ("id", "value")
    first = csv_aggregate_semantic_sha256(
        "fixture.csv", "id", header, (("a", ("a", "1")), ("b", ("b", "2")))
    )
    reordered = csv_aggregate_semantic_sha256(
        "fixture.csv", "id", header, (("b", ("b", "2")), ("a", ("a", "1")))
    )
    assert first != reordered


def test_json_semantics_ignore_key_order_and_invalid_json_fails_closed(tmp_path: Path) -> None:
    assert json_semantic_sha256("fixture.json", b'{"a":1,"b":2}') == json_semantic_sha256(
        "fixture.json", b'{"b":2,"a":1}'
    )
    with pytest.raises(SnapshotValidationError, match="non-finite JSON number"):
        json_semantic_sha256("overflow.json", b'{"nested":[1e400]}')
    with pytest.raises(ValueError, match="Out of range float values"):
        canonical_json_bytes({"nested": [math.inf]})

    first_parent = tmp_path / "first"
    second_parent = tmp_path / "second"
    first_parent.mkdir()
    second_parent.mkdir()
    first_core = copied_core(first_parent)
    second_core = copied_core(second_parent)
    config_path = "tools/validation_config.json"
    value = json.loads((first_core / config_path).read_text(encoding="utf-8"))
    ascending = dict(sorted(value.items()))
    descending = dict(reversed(sorted(value.items())))
    (first_core / config_path).write_bytes(
        json.dumps(ascending, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    (second_core / config_path).write_bytes(
        json.dumps(descending, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    first_manifest = tmp_path / "first.sha256"
    second_manifest = tmp_path / "second.sha256"
    first_manifest_sha = write_tree_manifest(first_core, first_manifest)
    second_manifest_sha = write_tree_manifest(second_core, second_manifest)
    first = load_research_core_snapshot(
        first_core,
        first_manifest,
        expected_manifest_sha256=first_manifest_sha,
    )
    second = load_research_core_snapshot(
        second_core,
        second_manifest,
        expected_manifest_sha256=second_manifest_sha,
    )
    assert first.raw_tree_sha256 != second.raw_tree_sha256
    assert first.file(config_path).semantic_kind == "json"
    assert first.file(config_path).semantic_sha256 == second.file(config_path).semantic_sha256
    assert first.semantic_tree_sha256 == second.semantic_tree_sha256

    invalid_parent = tmp_path / "invalid-parent"
    invalid_parent.mkdir()
    invalid_core = copied_core(invalid_parent)
    (invalid_core / config_path).write_bytes(b'{"broken":')
    invalid_manifest = tmp_path / "invalid.sha256"
    invalid_manifest_sha = write_tree_manifest(invalid_core, invalid_manifest)
    with pytest.raises(SnapshotValidationError, match="invalid UTF-8 JSON"):
        load_research_core_snapshot(
            invalid_core,
            invalid_manifest,
            expected_manifest_sha256=invalid_manifest_sha,
        )


def test_materialization_is_staged_idempotent_and_finalized_only_with_typed_hash() -> None:
    snapshot = load_research_core_snapshot(RESEARCH_CORE, MANIFEST)
    engine = sqlite_engine()
    with Session(engine) as session, session.begin():
        add_import_run(session, "run-b1", "b" * 64)
        assert materialize_snapshot(session, snapshot, import_run_id="run-b1") is True
        assert materialize_snapshot(session, snapshot, import_run_id="run-b1") is False
        revision = session.get(CoreRevision, snapshot.revision_id)
        assert revision is not None
        assert revision.status == "STAGING"
        assert revision.materialization_sha256 is None
        assert materialized_report(
            session, snapshot.revision_id, require_succeeded=False
        ).as_dict() == snapshot.report().as_dict()

        finalize_materialized_snapshot(
            session,
            snapshot,
            import_run_id="run-b1",
            typed_materialization_sha256="a" * 64,
        )
        assert revision.status == "SUCCEEDED"
        assert revision.materialization_sha256 == "a" * 64
        assert materialized_report(session, snapshot.revision_id).as_dict() == snapshot.report().as_dict()


def test_materialization_allows_multiple_immutable_revisions(tmp_path: Path) -> None:
    first = load_research_core_snapshot(RESEARCH_CORE, MANIFEST)
    second_core = copied_core(tmp_path)
    readme = second_core / "README.md"
    readme.write_bytes(readme.read_bytes() + b"\n")
    second_manifest = tmp_path / "second.sha256"
    second_manifest_sha = write_tree_manifest(second_core, second_manifest)
    second = load_research_core_snapshot(
        second_core,
        second_manifest,
        expected_manifest_sha256=second_manifest_sha,
    )
    assert second.revision_id != first.revision_id

    engine = sqlite_engine()
    with Session(engine) as session, session.begin():
        assert materialize_snapshot(session, first) is True
        assert materialize_snapshot(session, second) is True
        revisions = set(session.scalars(select(CoreRevision.revision_id)).all())
        assert revisions == {first.revision_id, second.revision_id}


def test_materialized_report_recomputes_file_and_csv_row_hashes() -> None:
    snapshot = load_research_core_snapshot(RESEARCH_CORE, MANIFEST)

    file_engine = sqlite_engine()
    with Session(file_engine) as session, session.begin():
        materialize_snapshot(session, snapshot)
        file = session.get(CoreFile, (snapshot.revision_id, "README.md"))
        assert file is not None
        file.content = file.content + b"tamper"
        session.flush()
        assert materialized_drift_reason(
            session,
            snapshot.revision_id,
            require_succeeded=False,
        ) == "core_files_drift"

    row_engine = sqlite_engine()
    with Session(row_engine) as session, session.begin():
        materialize_snapshot(session, snapshot)
        row = session.scalar(
            select(CoreCsvRow).where(
                CoreCsvRow.revision_id == snapshot.revision_id,
                CoreCsvRow.relative_path == "18_TW_CHARACTER_AVAILABILITY.csv",
            )
        )
        assert row is not None
        row.values = [*row.values[:-1], row.values[-1] + "tamper"]
        session.flush()
        assert materialized_drift_reason(
            session,
            snapshot.revision_id,
            require_succeeded=False,
        ) == "core_csv_rows_drift"


def test_materialized_reconstruction_recomputes_profiles_and_rejects_invalid_json() -> None:
    snapshot = load_research_core_snapshot(RESEARCH_CORE, MANIFEST)

    manifest_engine = sqlite_engine()
    with Session(manifest_engine) as session, session.begin():
        materialize_snapshot(session, snapshot)
        revision = session.get(CoreRevision, snapshot.revision_id)
        assert revision is not None
        tampered_manifest = copy.deepcopy(revision.manifest)
        tampered_manifest["files"]["README.md"]["newline_profile"] = "CRLF"
        revision.manifest = tampered_manifest
        session.flush()
        assert materialized_drift_reason(
            session,
            snapshot.revision_id,
            require_succeeded=False,
        ) == "revision_manifest_mismatch"

    invalid_json_engine = sqlite_engine()
    with Session(invalid_json_engine) as session, session.begin():
        materialize_snapshot(session, snapshot)
        file = session.get(
            CoreFile,
            (snapshot.revision_id, "tools/validation_config.json"),
        )
        assert file is not None
        invalid_content = b'{"broken":'
        invalid_sha256 = hashlib.sha256(invalid_content).hexdigest()
        file.content = invalid_content
        file.size_bytes = len(invalid_content)
        file.sha256 = invalid_sha256
        file.semantic_sha256 = invalid_sha256
        session.flush()
        assert materialized_drift_reason(
            session,
            snapshot.revision_id,
            require_succeeded=False,
        ) == "core_files_drift"


def test_exact_byte_export_is_atomic_external_and_deterministic(tmp_path: Path) -> None:
    snapshot = load_research_core_snapshot(RESEARCH_CORE, MANIFEST)
    engine = sqlite_engine()
    first = tmp_path / "export-one"
    second = tmp_path / "export-two"
    with Session(engine) as session, session.begin():
        materialize_snapshot(session, snapshot)
        first_report = export_materialized_revision(
            session,
            snapshot.revision_id,
            first,
            require_succeeded=False,
        )
        second_report = export_materialized_revision(
            session,
            snapshot.revision_id,
            second,
            require_succeeded=False,
        )
    assert first_report.as_dict() == second_report.as_dict() == snapshot.report().as_dict()
    for file in snapshot.files:
        assert (first / file.relative_path).read_bytes() == file.content
        assert (second / file.relative_path).read_bytes() == file.content
    assert not list(tmp_path.glob(".export-*.tmp-*"))


def test_export_rejects_canonical_or_existing_destination(tmp_path: Path) -> None:
    snapshot = load_research_core_snapshot(RESEARCH_CORE, MANIFEST)
    engine = sqlite_engine()
    empty = tmp_path / "empty"
    empty.mkdir()
    nonempty = tmp_path / "nonempty"
    nonempty.mkdir()
    (nonempty / "keep.txt").write_text("keep", encoding="utf-8")
    with Session(engine) as session, session.begin():
        materialize_snapshot(session, snapshot)
        for destination in (RESEARCH_CORE / "export", empty, nonempty):
            with pytest.raises(ExportSafetyError):
                export_materialized_revision(
                    session,
                    snapshot.revision_id,
                    destination,
                    require_succeeded=False,
                )


def test_export_rejects_dangling_symlink_and_reparse_ancestors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = load_research_core_snapshot(RESEARCH_CORE, MANIFEST)
    engine = sqlite_engine()
    dangling_destination = tmp_path / "dangling-export"
    symlink_parent = tmp_path / "symlink-parent"
    reparse_parent = tmp_path / "junction-parent"
    original_lexists = os.path.lexists
    original_lstat = Path.lstat
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    fake_metadata = {
        dangling_destination: SimpleNamespace(
            st_mode=stat.S_IFLNK | 0o777,
            st_file_attributes=0,
        ),
        symlink_parent: SimpleNamespace(
            st_mode=stat.S_IFLNK | 0o777,
            st_file_attributes=0,
        ),
        reparse_parent: SimpleNamespace(
            st_mode=stat.S_IFDIR | 0o777,
            st_file_attributes=reparse_flag,
        ),
    }

    def fake_lexists(path) -> bool:
        candidate = Path(path)
        return candidate in fake_metadata or original_lexists(path)

    def fake_lstat(path: Path):
        if path in fake_metadata:
            return fake_metadata[path]
        return original_lstat(path)

    monkeypatch.setattr(os.path, "lexists", fake_lexists)
    monkeypatch.setattr(Path, "lstat", fake_lstat)

    with Session(engine) as session, session.begin():
        materialize_snapshot(session, snapshot)
        for destination in (
            dangling_destination,
            symlink_parent / "export",
            reparse_parent / "export",
        ):
            with pytest.raises(ExportSafetyError, match="symlink or reparse point"):
                export_materialized_revision(
                    session,
                    snapshot.revision_id,
                    destination,
                    require_succeeded=False,
                )


def test_cli_round_trip_smoke_uses_disposable_staging() -> None:
    result = run_round_trip_smoke(research_core=RESEARCH_CORE, manifest_path=MANIFEST)
    assert result["status"] == "ROUND_TRIP_OK"
    assert result["created"] is True
    assert result["deterministic_exports"] is True
    assert result["report"]["raw_tree_sha256"] == RAW_TREE_SHA256
    assert result["baseline"] is None
