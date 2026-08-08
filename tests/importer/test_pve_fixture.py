from __future__ import annotations

import csv
import hashlib
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, func, select, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import pcr_pipeline.pve_fixture as fixture_module
from pcr_database.models import (
    Base,
    Character,
    Claim,
    CoreRevision,
    Evidence,
    ImportRun,
    MaterializationState,
    OperationTimeline,
    RevisionActivation,
    Stage,
    Team,
    TeamMember,
    TimelineStep,
)
from pcr_pipeline.pve_fixture import (
    TARGET_GUIDE_ID,
    FixtureValidationError,
    MirrorDriftError,
    import_fire_8_10,
    import_pve_projection,
    load_fire_8_10_closure,
    load_pve_closure,
)
from pcr_pipeline.research_core_snapshot import (
    EXPECTED_CSV_ROW_COUNT,
    EXPECTED_MANIFEST_SHA256,
    RP_A2_MANIFEST_SHA256,
    RP_A2_SNAPSHOT_CONTRACT,
    SnapshotValidationError,
    VALIDATOR_RUNTIME_PATHS,
    snapshot_contract_for_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_CORE = ROOT / "research_core" / "pcr_tw_project"
A3_MANIFEST = ROOT / "scripts" / "research_core_rp_a3_manifest.sha256"
RP_A2_MANIFEST = ROOT / "scripts" / "research_core_rp_a2_manifest.sha256"
SYNTHETIC_GUIDE_ID = "TW_DEEP_FIRE_09_10_SYNTHETIC"
SYNTHETIC_TEAM_ID = "TM-F910-SYNTHETIC"
SYNTHETIC_AXIS_ID = "AX-F910-SYNTHETIC-EV051"


def sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


def rewrite_csv(path: Path, mutate) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    mutate(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_tree_manifest(core: Path, destination: Path) -> str:
    lines = []
    for path in sorted(candidate for candidate in core.rglob("*") if candidate.is_file()):
        relative = path.relative_to(core).as_posix()
        if relative in VALIDATOR_RUNTIME_PATHS:
            continue
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
    canonical = ("\n".join(lines) + "\n").encode("utf-8")
    destination.write_bytes(canonical)
    return hashlib.sha256(canonical).hexdigest()


def build_manifested_core(
    tmp_path: Path,
    *,
    name: str,
) -> tuple[Path, Path, str]:
    core = tmp_path / name / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    manifest = tmp_path / f"{name}.sha256"
    return core, manifest, write_tree_manifest(core, manifest)


def export_checkpoint_core(tmp_path: Path, ref: str = "rp-b1-1") -> Path:
    """Export the immutable B1 research core without touching the worktree."""

    archive = tmp_path / "rp-b1-1.tar"
    subprocess.run(
        [
            "git",
            "archive",
            "--format=tar",
            f"--output={archive}",
            ref,
            "research_core/pcr_tw_project",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    destination = tmp_path / "rp-b1-1"
    destination.mkdir()
    with tarfile.open(archive, mode="r:") as bundle:
        bundle.extractall(destination, filter="data")
    return destination / "research_core" / "pcr_tw_project"


def build_synthetic_multi_stage_core(
    tmp_path: Path,
    *,
    name: str = "synthetic",
    source_core: Path = RESEARCH_CORE,
) -> tuple[Path, Path, str]:
    core = tmp_path / name / "pcr_tw_project"
    shutil.copytree(source_core, core)

    def add_guide(rows):
        source = next(row for row in rows if row["guide_id"] == TARGET_GUIDE_ID)
        guide = dict(source)
        guide.update(
            {
                "guide_id": SYNTHETIC_GUIDE_ID,
                "stage": "9-10",
                "status": "PROVISIONAL",
                "team_count": "0",
                "notes": "synthetic provisional stage for importer closure tests",
            }
        )
        rows.append(guide)

    def add_team(rows):
        source = next(row for row in rows if row["team_id"] == "TM-F810-03")
        requirements = fixture_module.json.loads(source["requirements"])
        requirements["timeline_ref"] = SYNTHETIC_AXIS_ID
        team = dict(source)
        team.update(
            {
                "team_id": SYNTHETIC_TEAM_ID,
                "guide_id": SYNTHETIC_GUIDE_ID,
                "stage": "紅焰9-10",
                "requirements": fixture_module.json.dumps(
                    requirements,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "clear_status": "PROVISIONAL",
                "notes": "synthetic non-effective team retained by typed projection",
            }
        )
        rows.append(team)

    def add_timeline(rows):
        source = next(
            row for row in rows if row["source_axis_id"] == "AX-F810-03-EV051"
        )
        timeline = dict(source)
        timeline.update(
            {
                "source_axis_id": SYNTHETIC_AXIS_ID,
                "team_id": SYNTHETIC_TEAM_ID,
                "timeline_variant_name": "synthetic source gap",
                "notes": "synthetic timeline closure row",
            }
        )
        rows.append(timeline)

    rewrite_csv(core / "24_PVE_GUIDE_REGISTRY.csv", add_guide)
    rewrite_csv(core / "25_PVE_TEAM_REGISTRY.csv", add_team)
    rewrite_csv(core / "26_PVE_OPERATION_TIMELINES.csv", add_timeline)
    manifest = tmp_path / f"{name}.sha256"
    return core, manifest, write_tree_manifest(core, manifest)


def allow_synthetic_snapshot_row_count(
    monkeypatch: pytest.MonkeyPatch,
    synthetic_core: Path,
) -> None:
    original_loader = fixture_module.load_research_core_snapshot
    synthetic_root = synthetic_core.resolve()

    def load_with_synthetic_row_count(research_core, *args, **kwargs):
        if Path(research_core).resolve() == synthetic_root:
            kwargs["expected_csv_row_count"] = EXPECTED_CSV_ROW_COUNT + 3
        return original_loader(research_core, *args, **kwargs)

    monkeypatch.setattr(
        fixture_module,
        "load_research_core_snapshot",
        load_with_synthetic_row_count,
    )


def test_loader_builds_all_pve_closure_without_strengthening_unknowns() -> None:
    closure = load_pve_closure(RESEARCH_CORE)

    assert closure.guide["status"] == "VERIFIED"
    assert closure.guide["team_count"] == "5"
    assert [guide["guide_id"] for guide in closure.guides] == [
        TARGET_GUIDE_ID,
        "TW_DEEP_FIRE_10_10_20260802",
    ]
    assert [team["team_id"] for team in closure.teams] == [
        "TM-F810-01",
        "TM-F810-02",
        "TM-F810-03",
        "TM-F810-04",
        "TM-F810-05",
    ]
    assert len(closure.characters) == 17
    assert len(closure.evidence) == 34
    assert len(closure.claims) == 27
    assert len(closure.timelines) == 10
    assert len(closure.timeline_steps) == 19
    assert closure.dangling_claim_ids == ()

    first = closure.teams[0]
    assert first["operation_mode"] == "SOURCE_CONFLICT"
    requirements = fixture_module._validate_requirements(first)
    assert {item["mode"] for item in requirements["operation_mode_claims"]} == {
        "AUTO",
        "SEMI_AUTO",
    }
    assert all(
        value == "UNKNOWN"
        for slot in requirements["slots"].values()
        for value in slot.values()
    )
    fourth = next(team for team in closure.teams if team["team_id"] == "TM-F810-04")
    assert fourth["operation_mode"] == "UNKNOWN"
    fourth_requirements = fixture_module._validate_requirements(fourth)
    assert fourth_requirements["operation_mode_claims"] == [
        {"mode": "UNKNOWN", "source_id": "yt_p95ZoBCWuYE"}
    ]
    fifth_steps = [
        step
        for step in closure.timeline_steps
        if step["timeline_id"] == "TL-F810-05-EV083"
    ]
    assert len(fifth_steps) == 5
    assert all(step["trigger_type"] == "SOURCE_TEXT_ONLY" for step in fifth_steps)
    assert all(step["action_type"] == "NO_ACTION" for step in fifth_steps)


def test_zero_team_guide_and_compatibility_loader_are_preserved() -> None:
    closure = load_pve_closure(RESEARCH_CORE)
    compatibility = load_fire_8_10_closure(RESEARCH_CORE)
    zero_team_guide = next(
        guide
        for guide in closure.guides
        if guide["guide_id"] == "TW_DEEP_FIRE_10_10_20260802"
    )

    assert compatibility.fingerprint == closure.fingerprint
    assert zero_team_guide["team_count"] == "0"
    assert not any(
        team["guide_id"] == zero_team_guide["guide_id"] for team in closure.teams
    )
    assert closure.stage_evidence_ids_by_guide[zero_team_guide["guide_id"]]
    assert closure.stage_claim_ids_by_guide[zero_team_guide["guide_id"]]


def test_closure_captures_each_source_file_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    source_paths = {
        (core / relative).resolve(): relative for relative in fixture_module.SOURCE_FILES
    }
    read_counts = {relative: 0 for relative in fixture_module.SOURCE_FILES}
    original_read_bytes = Path.read_bytes

    def counted_read_bytes(path: Path) -> bytes:
        relative = source_paths.get(path.resolve())
        if relative is not None:
            read_counts[relative] += 1
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", counted_read_bytes)
    closure = load_pve_closure(core)

    assert set(closure.file_hashes) == set(fixture_module.SOURCE_FILES)
    assert set(read_counts.values()) == {1}


def test_import_is_atomic_idempotent_and_preserves_fk_closure(tmp_path: Path) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="atomic",
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        first = import_pve_projection(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
        second = import_fire_8_10(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )

        assert first.created is True
        assert first.activated is True
        assert second.created is False
        assert second.activated is False
        assert first.import_run_id == second.import_run_id
        assert first.fixture_sha256 == second.fixture_sha256
        assert first.revision_id == first.raw_tree_sha256
        assert first.file_count == 48
        assert first.csv_file_count == 13
        assert first.csv_row_count == 239
        assert first.row_counts == {
            "stages": 2,
            "teams": 5,
            "team_members": 25,
            "characters": 17,
            "evidence": 34,
            "claims": 27,
            "operation_timelines": 10,
            "timeline_steps": 19,
        }
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 1
        assert session.scalar(select(func.count()).select_from(Stage)) == 2
        assert session.scalar(select(func.count()).select_from(Team)) == 5
        assert session.scalar(select(func.count()).select_from(TeamMember)) == 25
        assert session.scalar(select(func.count()).select_from(Character)) == 17
        assert session.scalar(select(func.count()).select_from(OperationTimeline)) == 10
        assert session.scalar(select(func.count()).select_from(TimelineStep)) == 19
        stage = session.get(Stage, TARGET_GUIDE_ID)
        assert stage is not None
        assert stage.team_count == 5
        zero_team_stage = session.get(Stage, "TW_DEEP_FIRE_10_10_20260802")
        assert zero_team_stage is not None
        assert zero_team_stage.team_count == 0
        state = session.get(MaterializationState, 1)
        revision = session.get(CoreRevision, first.revision_id)
        assert state is not None
        assert revision is not None
        assert revision.status == "SUCCEEDED"
        assert revision.import_run_id == first.import_run_id
        assert state.active_revision_id == first.revision_id
        assert state.active_import_run_id == first.import_run_id
        assert state.materialization_sha256 == revision.materialization_sha256
        assert session.scalar(select(func.count()).select_from(RevisionActivation)) == 1

        imported_claim_ids = set(session.scalars(select(Claim.claim_id)).all())
        for evidence in session.scalars(select(Evidence)).all():
            if evidence.linked_claim_id is not None:
                assert evidence.linked_claim_id in imported_claim_ids
            assert evidence.linked_claim_id == evidence.declared_claim_id

        team = session.get(Team, "TM-F810-01")
        assert team is not None
        assert team.requirements_raw == fixture_module.json.dumps(
            team.requirements, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

        timeline = session.get(OperationTimeline, "AX-F810-02-EV073")
        assert timeline is not None
        assert timeline.timeline_id == "TL-F810-02-EV073"
        assert timeline.battle_duration_ms is None
        assert timeline.reproducibility == "UNVERIFIED_ON_TW"
        steps = session.scalars(
            select(TimelineStep)
            .where(TimelineStep.timeline_id == timeline.timeline_id)
            .order_by(TimelineStep.sequence_no)
        ).all()
        assert [step.sequence_no for step in steps] == list(range(1, 15))
        assert all(step.time_state == "NOT_STATED" for step in steps[:4])
        assert all(step.clock_from_ms is None and step.clock_to_ms is None for step in steps[:4])
        assert all(step.time_state == "STATED" for step in steps[4:])
        assert all(step.criticality == "UNKNOWN" for step in steps)


def test_synthetic_multi_stage_projection_retains_provisional_team_without_counting_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core, manifest, manifest_sha256 = build_synthetic_multi_stage_core(tmp_path)
    allow_synthetic_snapshot_row_count(monkeypatch, core)
    closure = load_pve_closure(core)
    synthetic_guide = next(
        guide for guide in closure.guides if guide["guide_id"] == SYNTHETIC_GUIDE_ID
    )
    synthetic_team = next(
        team for team in closure.teams if team["team_id"] == SYNTHETIC_TEAM_ID
    )

    assert len(closure.guides) == 3
    assert len(closure.teams) == 6
    assert len(closure.timelines) == 11
    assert synthetic_guide["team_count"] == "0"
    assert synthetic_team["clear_status"] == "PROVISIONAL"
    assert synthetic_team["tw_availability_check"] == "PASS"

    engine = sqlite_engine()
    with Session(engine) as session:
        result = import_pve_projection(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )

        assert result.row_counts == {
            "stages": 3,
            "teams": 6,
            "team_members": 30,
            "characters": 17,
            "evidence": 34,
            "claims": 27,
            "operation_timelines": 11,
            "timeline_steps": 19,
        }
        stored_stage = session.get(Stage, SYNTHETIC_GUIDE_ID)
        stored_team = session.get(Team, SYNTHETIC_TEAM_ID)
        stored_axis = session.get(OperationTimeline, SYNTHETIC_AXIS_ID)
        assert stored_stage is not None
        assert stored_stage.team_count == 0
        assert stored_team is not None
        assert stored_team.clear_status == "PROVISIONAL"
        assert stored_axis is not None
        assert stored_axis.team_id == SYNTHETIC_TEAM_ID


def test_team_count_mismatch_is_rejected_before_any_write(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "24_PVE_GUIDE_REGISTRY.csv"

    def mutate(rows):
        for row in rows:
            if row["guide_id"] == TARGET_GUIDE_ID:
                row["team_count"] = "2"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="team_count differs"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.scalar(select(func.count()).select_from(Stage)) == 0


def test_unknown_unit_is_rejected_before_any_write(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "25_PVE_TEAM_REGISTRY.csv"

    def mutate(rows):
        rows[0]["slot1"] = "missing_unit_key"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="missing ids"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


def test_team_must_match_its_guides_server_and_stage_before_any_write(
    tmp_path: Path,
) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "25_PVE_TEAM_REGISTRY.csv"

    def mutate(rows):
        team = next(row for row in rows if row["team_id"] == "TM-F810-01")
        team["stage"] = "紅焰10-10"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="server/stage differs"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.scalar(select(func.count()).select_from(Stage)) == 0


def test_timeline_ref_must_equal_the_team_source_axis_closure(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "25_PVE_TEAM_REGISTRY.csv"

    def mutate(rows):
        team = next(row for row in rows if row["team_id"] == "TM-F810-02")
        requirements = fixture_module.json.loads(team["requirements"])
        requirements["timeline_ref"] = "AX-F810-02-EV070"
        team["requirements"] = fixture_module.json.dumps(
            requirements, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="timeline_ref differs"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


def test_timeline_locator_must_remain_inside_its_evidence_locator(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "26_PVE_OPERATION_TIMELINES.csv"

    def mutate(rows):
        rows[0]["source_locator"] = "unrelated_source#invented"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="Evidence locator"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


def test_unstated_source_time_cannot_be_invented(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "27_PVE_TIMELINE_STEPS.csv"

    def mutate(rows):
        step = next(row for row in rows if row["timeline_step_id"] == "TLS-F810-02-001")
        step["time_state"] = "STATED"
        step["clock_from_ms"] = "90000"
        step["clock_to_ms"] = "90000"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="strengthens an unstated source time"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


def test_timeline_actor_must_be_a_member_of_its_team(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "27_PVE_TIMELINE_STEPS.csv"

    def mutate(rows):
        rows[4]["actor_unit_key"] = "maho_summer"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="not a member of its team"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


@pytest.mark.parametrize(
    "unsafe_url",
    ["javascript:alert(1)", "https://pcrdfans.com/jp/battle"],
)
def test_unaudited_or_restricted_evidence_url_is_rejected(
    tmp_path: Path, unsafe_url: str
) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "92_EVIDENCE_LEDGER.csv"

    def mutate(rows):
        for row in rows:
            if row["evidence_id"] == "ev050":
                row["source_url"] = unsafe_url

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="audited HTTPS source"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


def test_database_failure_rolls_back_whole_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="database-failure",
    )
    engine = sqlite_engine()
    original_upsert = fixture_module._upsert
    calls = 0

    def fail_after_first_row(session, model, key, values):
        nonlocal calls
        calls += 1
        original_upsert(session, model, key, values)
        if calls == 2:
            raise RuntimeError("injected failure")

    monkeypatch.setattr(fixture_module, "_upsert", fail_after_first_row)
    with Session(engine) as session:
        with pytest.raises(RuntimeError, match="injected failure"):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.scalar(select(func.count()).select_from(Claim)) == 0


def test_timeline_step_failure_rolls_back_the_whole_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="timeline-step-failure",
    )
    engine = sqlite_engine()
    original_upsert = fixture_module._upsert

    def fail_on_timeline_step(session, model, key, values):
        original_upsert(session, model, key, values)
        if model is TimelineStep:
            raise RuntimeError("injected timeline step failure")

    monkeypatch.setattr(fixture_module, "_upsert", fail_on_timeline_step)
    with Session(engine) as session:
        with pytest.raises(RuntimeError, match="timeline step failure"):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )
        for model in (ImportRun, Stage, Team, OperationTimeline, TimelineStep):
            assert session.scalar(select(func.count()).select_from(model)) == 0


def test_idempotent_replay_detects_stage_materialized_row_drift(
    tmp_path: Path,
) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="stage-drift",
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        import_fire_8_10(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
        stage = session.get(Stage, "TW_DEEP_FIRE_10_10_20260802")
        assert stage is not None
        stage.source_payload = {**stage.source_payload, "notes": "tampered"}
        session.commit()

        with pytest.raises(
            MirrorDriftError,
            match="stage TW_DEEP_FIRE_10_10_20260802 drifted",
        ):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )


def test_idempotent_replay_detects_materialized_row_drift(tmp_path: Path) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="team-drift",
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        import_fire_8_10(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
        team = session.get(Team, "TM-F810-01")
        assert team is not None
        team.source_payload = {**team.source_payload, "notes": "tampered"}
        session.commit()

        with pytest.raises(MirrorDriftError, match="TM-F810-01 drifted"):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )


def test_idempotent_replay_detects_timeline_materialization_drift(
    tmp_path: Path,
) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="timeline-drift",
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        import_fire_8_10(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
        timeline = session.get(OperationTimeline, "AX-F810-02-EV073")
        assert timeline is not None
        timeline.reproducibility = "TW_REPRODUCED"
        session.commit()

        with pytest.raises(MirrorDriftError, match="timeline AX-F810-02-EV073 drifted"):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )


def test_dangling_evidence_claim_rejects_entire_serving_import(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "92_EVIDENCE_LEDGER.csv"

    def mutate(rows):
        for row in rows:
            if row["evidence_id"] == "ev050":
                row["claim_id"] = "CLM-DOES-NOT-EXIST"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="selected evidence references missing claims"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.get(Claim, "CLM-DOES-NOT-EXIST") is None
        assert session.get(Evidence, "ev050") is None


def test_unreviewed_changed_tree_is_rejected_before_database_write(tmp_path: Path) -> None:
    reviewed_core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="reviewed-base",
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        original = import_fire_8_10(
            session,
            reviewed_core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )

        core = tmp_path / "pcr_tw_project"
        shutil.copytree(reviewed_core, core)
        path = core / "24_PVE_GUIDE_REGISTRY.csv"

        def mutate(rows):
            for row in rows:
                if row["guide_id"] == TARGET_GUIDE_ID:
                    row["notes"] = f"{row['notes']} test-only-source-revision"

        rewrite_csv(path, mutate)
        with pytest.raises(SnapshotValidationError, match="file SHA-256 mismatch"):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )

        assert session.scalar(select(func.count()).select_from(ImportRun)) == 1
        stage = session.get(Stage, TARGET_GUIDE_ID)
        assert stage is not None
        assert stage.import_run_id == original.import_run_id
        assert "test-only-source-revision" not in stage.notes


def test_source_change_between_closure_and_snapshot_is_rejected_before_database_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "24_PVE_GUIDE_REGISTRY.csv"
    canonical_content = path.read_bytes()
    manifest = tmp_path / "toctou.sha256"
    manifest_sha256 = write_tree_manifest(core, manifest)

    def mutate(rows):
        for row in rows:
            if row["guide_id"] == TARGET_GUIDE_ID:
                row["notes"] = f"{row['notes']} transient-unreviewed-source"

    rewrite_csv(path, mutate)
    original_loader = fixture_module.load_research_core_snapshot

    def restore_canonical_then_load(*args, **kwargs):
        path.write_bytes(canonical_content)
        return original_loader(*args, **kwargs)

    monkeypatch.setattr(
        fixture_module,
        "load_research_core_snapshot",
        restore_canonical_then_load,
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(
            FixtureValidationError,
            match="source files changed during import snapshot capture",
        ):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )

        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.scalar(select(func.count()).select_from(CoreRevision)) == 0
        assert session.scalar(select(func.count()).select_from(Stage)) == 0
        assert session.scalar(select(func.count()).select_from(MaterializationState)) == 0


def test_new_revision_activation_and_rollback_preserve_immutable_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = sqlite_engine()
    first_core = tmp_path / "first" / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, first_core)
    first_manifest = tmp_path / "first.sha256"
    first_manifest_sha256 = write_tree_manifest(first_core, first_manifest)
    second_core, second_manifest, second_manifest_sha256 = (
        build_synthetic_multi_stage_core(tmp_path, name="second")
    )
    allow_synthetic_snapshot_row_count(monkeypatch, second_core)

    with Session(engine) as session:
        first = import_fire_8_10(
            session,
            first_core,
            manifest_path=first_manifest,
            expected_manifest_sha256=first_manifest_sha256,
        )
        second = import_fire_8_10(
            session,
            second_core,
            manifest_path=second_manifest,
            expected_manifest_sha256=second_manifest_sha256,
        )
        assert second.created is True
        assert second.activated is True
        assert second.revision_id != first.revision_id
        state = session.get(MaterializationState, 1)
        assert state is not None
        assert state.active_revision_id == second.revision_id
        assert session.scalar(select(func.count()).select_from(CoreRevision)) == 2
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 2
        assert session.get(Stage, SYNTHETIC_GUIDE_ID) is not None
        assert session.get(Team, SYNTHETIC_TEAM_ID) is not None
        assert session.get(OperationTimeline, SYNTHETIC_AXIS_ID) is not None
        session.rollback()  # end the read-only transaction opened by assertions

        rollback = import_fire_8_10(
            session,
            first_core,
            manifest_path=first_manifest,
            expected_manifest_sha256=first_manifest_sha256,
        )
        assert rollback.created is False
        assert rollback.activated is True
        assert rollback.revision_id == first.revision_id
        session.refresh(state)
        assert state.active_revision_id == first.revision_id
        assert session.get(Stage, SYNTHETIC_GUIDE_ID) is None
        assert session.get(Team, SYNTHETIC_TEAM_ID) is None
        assert session.get(OperationTimeline, SYNTHETIC_AXIS_ID) is None
        assert session.scalar(select(func.count()).select_from(Stage)) == 2
        assert session.scalar(select(func.count()).select_from(Team)) == 5
        assert session.scalar(select(func.count()).select_from(OperationTimeline)) == 10
        session.rollback()  # end the read-only transaction opened by assertions

        reactivate = import_fire_8_10(
            session,
            second_core,
            manifest_path=second_manifest,
            expected_manifest_sha256=second_manifest_sha256,
        )
        assert reactivate.created is False
        assert reactivate.activated is True
        assert reactivate.revision_id == second.revision_id
        session.refresh(state)
        assert state.active_revision_id == second.revision_id
        assert session.get(Stage, SYNTHETIC_GUIDE_ID) is not None
        assert session.get(Team, SYNTHETIC_TEAM_ID) is not None
        assert session.get(OperationTimeline, SYNTHETIC_AXIS_ID) is not None
        assert session.scalar(select(func.count()).select_from(Stage)) == 3
        assert session.scalar(select(func.count()).select_from(Team)) == 6
        assert session.scalar(select(func.count()).select_from(OperationTimeline)) == 11
        activations = session.scalars(
            select(RevisionActivation).order_by(RevisionActivation.sequence_no)
        ).all()
        assert [activation.kind for activation in activations] == [
            "IMPORT",
            "IMPORT",
            "ROLLBACK",
            "REACTIVATE",
        ]
        assert [activation.sequence_no for activation in activations] == [1, 2, 3, 4]
        assert session.scalar(select(func.count()).select_from(CoreRevision)) == 2
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 2
        assert {revision.status for revision in session.scalars(select(CoreRevision))} == {
            "SUCCEEDED"
        }


def test_legacy_b1_manifest_rolls_back_and_reactivates_without_projection_drift(
    tmp_path: Path,
) -> None:
    first_core = export_checkpoint_core(tmp_path)
    assert snapshot_contract_for_manifest(RP_A2_MANIFEST_SHA256) == (
        RP_A2_SNAPSHOT_CONTRACT
    )

    engine = sqlite_engine()
    with Session(engine) as session:
        first = import_pve_projection(
            session,
            first_core,
            manifest_path=RP_A2_MANIFEST,
            expected_manifest_sha256=RP_A2_MANIFEST_SHA256,
            application_version="3.0.0-b1",
        )
        assert first.row_counts["stages"] == 1
        assert first.row_counts["teams"] == 3
        assert first.row_counts["characters"] == 8
        assert first.row_counts["evidence"] == 18
        assert first.row_counts["operation_timelines"] == 8
        assert first.row_counts["timeline_steps"] == 14
        first_run = session.get(ImportRun, first.import_run_id)
        assert first_run is not None
        assert first_run.manifest["projection"] == fixture_module.LEGACY_FIRE_PROJECTION

        # Simulate the immutable manifest shape written by the deployed B1
        # importer before projection became an explicit field.
        legacy_manifest = dict(first_run.manifest)
        legacy_manifest.pop("projection")
        legacy_manifest["target_guide_id"] = TARGET_GUIDE_ID
        # SQLite has no V0003 history trigger; a bulk update is used only to
        # construct the pre-existing B1 database fixture.  Application ORM
        # writes remain protected by the immutable-history guard.
        session.execute(
            update(ImportRun)
            .where(ImportRun.id == first.import_run_id)
            .values(manifest=legacy_manifest)
            .execution_options(synchronize_session=False)
        )
        session.commit()
        session.expire_all()

        second = import_pve_projection(
            session,
            RESEARCH_CORE,
            manifest_path=A3_MANIFEST,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )
        assert second.row_counts["stages"] == 2
        assert second.row_counts["teams"] == 5
        assert session.get(Stage, "TW_DEEP_FIRE_10_10_20260802") is not None
        assert session.get(Character, "anne_grea_orig") is not None
        session.rollback()

        rollback = import_pve_projection(
            session,
            first_core,
            manifest_path=RP_A2_MANIFEST,
            expected_manifest_sha256=RP_A2_MANIFEST_SHA256,
        )
        assert rollback.created is False
        assert rollback.activated is True
        assert session.scalar(select(func.count()).select_from(Stage)) == 1
        assert session.scalar(select(func.count()).select_from(Team)) == 3
        assert session.scalar(select(func.count()).select_from(Character)) == 8
        assert session.scalar(select(func.count()).select_from(Evidence)) == 18
        assert session.scalar(select(func.count()).select_from(OperationTimeline)) == 8
        assert session.scalar(select(func.count()).select_from(TimelineStep)) == 14
        assert session.get(Stage, "TW_DEEP_FIRE_10_10_20260802") is None
        assert session.get(Character, "anne_grea_orig") is None
        first_run = session.get(ImportRun, first.import_run_id)
        assert first_run is not None
        assert "projection" not in first_run.manifest
        assert first_run.manifest["target_guide_id"] == TARGET_GUIDE_ID
        session.rollback()

        reactivate = import_pve_projection(
            session,
            RESEARCH_CORE,
            manifest_path=A3_MANIFEST,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )
        assert reactivate.created is False
        assert reactivate.activated is True
        assert session.get(Stage, "TW_DEEP_FIRE_10_10_20260802") is not None
        assert session.get(Character, "anne_grea_orig") is not None
        activations = session.scalars(
            select(RevisionActivation).order_by(RevisionActivation.sequence_no)
        ).all()
        assert [activation.kind for activation in activations] == [
            "IMPORT",
            "IMPORT",
            "ROLLBACK",
            "REACTIVATE",
        ]
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 2
        assert session.scalar(select(func.count()).select_from(CoreRevision)) == 2


def test_failed_revision_switch_rolls_back_rows_pointer_and_artifact_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = sqlite_engine()
    first_core, first_manifest, first_manifest_sha256 = build_manifested_core(
        tmp_path,
        name="failed-base",
    )
    second_core = tmp_path / "failed" / "pcr_tw_project"
    shutil.copytree(first_core, second_core)
    readme = second_core / "README.md"
    readme.write_bytes(readme.read_bytes() + b"\n")
    second_manifest = tmp_path / "failed.sha256"
    second_manifest_sha256 = write_tree_manifest(second_core, second_manifest)

    with Session(engine) as session:
        first = import_fire_8_10(
            session,
            first_core,
            manifest_path=first_manifest,
            expected_manifest_sha256=first_manifest_sha256,
        )
        original_upsert = fixture_module._upsert

        def fail_first_typed_row(session, model, key, values):
            original_upsert(session, model, key, values)
            raise RuntimeError("injected revision switch failure")

        monkeypatch.setattr(fixture_module, "_upsert", fail_first_typed_row)
        with pytest.raises(RuntimeError, match="revision switch failure"):
            import_fire_8_10(
                session,
                second_core,
                manifest_path=second_manifest,
                expected_manifest_sha256=second_manifest_sha256,
            )

        state = session.get(MaterializationState, 1)
        stage = session.get(Stage, TARGET_GUIDE_ID)
        assert state is not None
        assert stage is not None
        assert state.active_revision_id == first.revision_id
        assert stage.import_run_id == first.import_run_id
        assert session.scalar(select(func.count()).select_from(CoreRevision)) == 1
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 1
        assert session.scalar(select(func.count()).select_from(RevisionActivation)) == 1
