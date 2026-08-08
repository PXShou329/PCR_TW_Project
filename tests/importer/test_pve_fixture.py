from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import pcr_pipeline.pve_fixture as fixture_module
from pcr_database.models import (
    Base,
    Claim,
    Evidence,
    ImportRun,
    OperationTimeline,
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
    load_fire_8_10_closure,
)


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_CORE = ROOT / "research_core" / "pcr_tw_project"


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


def test_loader_builds_exact_three_team_closure_without_strengthening_unknowns() -> None:
    closure = load_fire_8_10_closure(RESEARCH_CORE)

    assert closure.guide["status"] == "PROVISIONAL"
    assert closure.guide["team_count"] == "3"
    assert [team["team_id"] for team in closure.teams] == [
        "TM-F810-01",
        "TM-F810-02",
        "TM-F810-03",
    ]
    assert len(closure.characters) == 8
    assert len(closure.evidence) == 18
    assert len(closure.claims) == 13
    assert len(closure.timelines) == 8
    assert len(closure.timeline_steps) == 14
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


def test_import_is_atomic_idempotent_and_preserves_fk_closure() -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        first = import_fire_8_10(session, RESEARCH_CORE)
        second = import_fire_8_10(session, RESEARCH_CORE)

        assert first.created is True
        assert second.created is False
        assert first.import_run_id == second.import_run_id
        assert first.fixture_sha256 == second.fixture_sha256
        assert first.row_counts == {
            "stages": 1,
            "teams": 3,
            "team_members": 15,
            "characters": 8,
            "evidence": 18,
            "claims": 13,
            "operation_timelines": 8,
            "timeline_steps": 14,
        }
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 1
        assert session.scalar(select(func.count()).select_from(Team)) == 3
        assert session.scalar(select(func.count()).select_from(TeamMember)) == 15
        assert session.scalar(select(func.count()).select_from(OperationTimeline)) == 8
        assert session.scalar(select(func.count()).select_from(TimelineStep)) == 14
        stage = session.get(Stage, TARGET_GUIDE_ID)
        assert stage is not None
        assert stage.team_count == 3

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
        rows[0]["time_state"] = "STATED"
        rows[0]["clock_from_ms"] = "90000"
        rows[0]["clock_to_ms"] = "90000"

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


def test_database_failure_rolls_back_whole_import(monkeypatch) -> None:
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
            import_fire_8_10(session, RESEARCH_CORE)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.scalar(select(func.count()).select_from(Claim)) == 0


def test_timeline_step_failure_rolls_back_the_whole_import(monkeypatch) -> None:
    engine = sqlite_engine()
    original_upsert = fixture_module._upsert

    def fail_on_timeline_step(session, model, key, values):
        original_upsert(session, model, key, values)
        if model is TimelineStep:
            raise RuntimeError("injected timeline step failure")

    monkeypatch.setattr(fixture_module, "_upsert", fail_on_timeline_step)
    with Session(engine) as session:
        with pytest.raises(RuntimeError, match="timeline step failure"):
            import_fire_8_10(session, RESEARCH_CORE)
        for model in (ImportRun, Stage, Team, OperationTimeline, TimelineStep):
            assert session.scalar(select(func.count()).select_from(model)) == 0


def test_idempotent_replay_detects_materialized_row_drift() -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        import_fire_8_10(session, RESEARCH_CORE)
        team = session.get(Team, "TM-F810-01")
        assert team is not None
        team.source_payload = {**team.source_payload, "notes": "tampered"}
        session.commit()

        with pytest.raises(MirrorDriftError, match="TM-F810-01 drifted"):
            import_fire_8_10(session, RESEARCH_CORE)


def test_idempotent_replay_detects_timeline_materialization_drift() -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        import_fire_8_10(session, RESEARCH_CORE)
        timeline = session.get(OperationTimeline, "AX-F810-02-EV073")
        assert timeline is not None
        timeline.reproducibility = "TW_REPRODUCED"
        session.commit()

        with pytest.raises(MirrorDriftError, match="timeline AX-F810-02-EV073 drifted"):
            import_fire_8_10(session, RESEARCH_CORE)


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


def test_changed_fixture_requires_disposable_mirror_rebuild(tmp_path: Path) -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        original = import_fire_8_10(session, RESEARCH_CORE)

        core = tmp_path / "pcr_tw_project"
        shutil.copytree(RESEARCH_CORE, core)
        path = core / "24_PVE_GUIDE_REGISTRY.csv"

        def mutate(rows):
            for row in rows:
                if row["guide_id"] == TARGET_GUIDE_ID:
                    row["notes"] = f"{row['notes']} test-only-source-revision"

        rewrite_csv(path, mutate)
        with pytest.raises(MirrorDriftError, match="different fixture fingerprint"):
            import_fire_8_10(session, core)

        assert session.scalar(select(func.count()).select_from(ImportRun)) == 1
        stage = session.get(Stage, TARGET_GUIDE_ID)
        assert stage is not None
        assert stage.import_run_id == original.import_run_id
        assert "test-only-source-revision" not in stage.notes
