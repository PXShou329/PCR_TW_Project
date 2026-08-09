from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from pcr_api.config import Settings
from pcr_api.main import create_app
from pcr_api import database as database_module
from pcr_api import repository as repository_module
from pcr_api.repository import (
    effective_team_signatures,
    latest_import,
    mirror_readiness,
)
from pcr_database.models import (
    Character,
    CoreCsvRow,
    CoreFile,
    ImportRun,
    MaterializationState,
    OperationTimeline,
    Team,
    TeamEvidence,
    TeamMember,
)

from .conftest import make_factory


GUIDE_ID = "TW_DEEP_FIRE_08_10_20260802"
WATER_GUIDE_ID = "TW_DEEP_WATER_08_10_20260808"
APPLICATION_VERSION = "3.0.0-b5"


def test_postgresql_engine_uses_repeatable_read_for_route_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    sentinel = object()

    def fake_create_engine(url: str, **options: object):
        calls.append((url, options))
        return sentinel

    monkeypatch.setattr(database_module, "create_engine", fake_create_engine)
    postgres = database_module.build_engine(
        Settings(database_url="postgresql+psycopg://reader:secret@db/pcr_tw")
    )
    sqlite = database_module.build_engine(Settings(database_url="sqlite://"))

    assert postgres is sentinel
    assert sqlite is sentinel
    assert calls[0][1] == {
        "pool_pre_ping": True,
        "isolation_level": "REPEATABLE READ",
    }
    assert calls[1][1] == {"pool_pre_ping": True}


def assert_meta(payload: dict) -> None:
    meta = payload["meta"]
    assert meta["api_version"] == "v1"
    assert meta["server"] in {"TW", "JP", "MIXED", "UNKNOWN"}
    assert isinstance(meta["environment_version"], str)
    assert meta["stale_status"] in {"CURRENT", "STALE", "UNKNOWN"}
    assert meta["confidence"] in {"A", "B", "C", "D", "E", "UNKNOWN"}
    assert meta["evidence_ids"] == sorted(set(meta["evidence_ids"]))
    assert meta["claim_ids"] == sorted(set(meta["claim_ids"]))
    assert len(meta["source"]["fixture_sha256"]) == 64
    assert meta["source"]["canonical_source"] == "research_core_file_ssot"
    assert meta["source"]["research_core_version"] == "v1.5"
    assert meta["source"]["revision_id"]
    assert len(meta["source"]["raw_tree_sha256"]) == 64
    assert len(meta["source"]["semantic_tree_sha256"]) == 64
    assert len(meta["source"]["materialization_sha256"]) == 64
    assert meta["data_revision"] == meta["source"]["revision_id"]


def test_environment_settings_require_database_url(monkeypatch) -> None:
    monkeypatch.delenv("PCR_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="PCR_DATABASE_URL is required"):
        Settings.from_environment()


def test_health_is_split_between_liveness_and_fixture_readiness(client: TestClient) -> None:
    assert client.get("/health/live").json() == {
        "status": "ok",
        "checks": {"process": "ok"},
    }
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"] == {"database": "ok", "fixture": "imported"}

    empty_app = create_app(
        settings=Settings(database_url="sqlite://"),
        session_factory=make_factory(imported=False),
    )
    with TestClient(empty_app) as empty_client:
        response = empty_client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["checks"]["fixture"] == "missing"


def test_database_unavailable_is_a_uniform_structured_503() -> None:
    factory = make_factory()
    engine = factory.kw["bind"]
    engine.dispose()
    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    endpoints = [
        "/api/v1/baseline",
        "/api/v1/stages",
        f"/api/v1/stages/{GUIDE_ID}",
        "/api/v1/teams/TM-F810-01",
        "/api/v1/teams/TM-F810-01/timelines",
        "/api/v1/evidence/ev050",
        "/api/v1/claims/CLM-PVE-F810-MAIN",
        "/api/v1/pvp/characters",
        "/api/v1/pvp/counters",
    ]
    expected = {
        "detail": {
            "code": "DATABASE_UNAVAILABLE",
            "resource": "database",
            "id": None,
        }
    }
    with TestClient(app) as unavailable_client:
        health = unavailable_client.get("/health/ready")
        responses = [unavailable_client.get(path) for path in endpoints]

    assert health.status_code == 503
    assert health.json() == {
        "status": "not_ready",
        "checks": {"database": "error", "fixture": "unknown"},
    }
    assert all(response.status_code == 503 for response in responses)
    assert all(response.json() == expected for response in responses)


def test_latest_import_uses_active_pointer_not_newest_succeeded_run() -> None:
    factory = make_factory()
    with factory() as session:
        active = latest_import(session)
        assert active is not None
        active_id = active.id
        newer = ImportRun(
            id=str(uuid4()),
            fixture_sha256="0" * 64,
            canonical_source=active.canonical_source,
            research_core_version=active.research_core_version,
            application_version=active.application_version,
            imported_at=active.imported_at + timedelta(days=1),
            status="RUNNING",
            manifest=deepcopy(active.manifest),
            row_counts=dict(active.row_counts),
        )
        session.add(newer)
        session.flush()
        newer.status = "SUCCEEDED"
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    with TestClient(app) as pointer_client:
        response = pointer_client.get("/api/v1/baseline")

    assert response.status_code == 200
    assert response.json()["meta"]["source"]["import_run_id"] == active_id


def test_readiness_rejects_import_run_fixture_raw_tree_mismatch() -> None:
    factory = make_factory()
    with factory() as session:
        active = latest_import(session)
        assert active is not None
        session.execute(
            update(ImportRun)
            .where(ImportRun.id == active.id)
            .values(fixture_sha256="0" * 64)
        )
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    with TestClient(app) as provenance_client:
        response = provenance_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["fixture"] == "active_revision_drift"


def test_readiness_fails_closed_on_serving_count_key_set_drift() -> None:
    factory = make_factory()
    with factory() as session:
        state = session.get(MaterializationState, 1)
        assert state is not None
        counts = dict(state.serving_counts)
        counts.pop("claim_evidence")
        state.serving_counts = counts
        state.epoch += 1
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    with TestClient(app) as drifted_client:
        response = drifted_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["fixture"] == "serving_count_state_drift"


def test_readiness_fails_closed_on_run_manifest_table_set_drift() -> None:
    factory = make_factory()
    with factory() as session:
        run = latest_import(session)
        assert run is not None
        manifest = deepcopy(run.manifest)
        manifest["materialization"]["tables"].pop("claim_evidence")
        session.execute(
            update(ImportRun)
            .where(ImportRun.id == run.id)
            .values(manifest=manifest)
        )
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    with TestClient(app) as drifted_client:
        response = drifted_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["fixture"] == "serving_count_manifest_drift"


def test_readiness_fails_closed_on_declared_serving_count_key_set_drift() -> None:
    factory = make_factory()
    with factory() as session:
        run = latest_import(session)
        assert run is not None
        manifest = deepcopy(run.manifest)
        manifest["serving_row_counts"].pop("claim_evidence")
        session.execute(
            update(ImportRun)
            .where(ImportRun.id == run.id)
            .values(manifest=manifest)
        )
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    with TestClient(app) as drifted_client:
        response = drifted_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["fixture"] == "serving_count_manifest_drift"


def test_readiness_fails_closed_on_import_run_core_revision_provenance_drift() -> None:
    factory = make_factory()
    with factory() as session:
        run = latest_import(session)
        assert run is not None
        manifest = deepcopy(run.manifest)
        manifest["core_revision"]["semantic_tree_sha256"] = "0" * 64
        session.execute(
            update(ImportRun)
            .where(ImportRun.id == run.id)
            .values(manifest=manifest)
        )
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    with TestClient(app) as drifted_client:
        response = drifted_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["fixture"] == "core_revision_manifest_drift"


def test_full_core_file_content_drift_blocks_strategy_reads() -> None:
    factory = make_factory()
    with factory() as session:
        state = session.get(MaterializationState, 1)
        assert state is not None
        content = session.scalar(
            select(CoreFile.content).where(
                CoreFile.revision_id == state.active_revision_id,
                CoreFile.relative_path == "00_PROJECT_INSTRUCTIONS.md",
            )
        )
        assert content is not None
        session.execute(
            update(CoreFile.__table__)
            .where(
                CoreFile.revision_id == state.active_revision_id,
                CoreFile.relative_path == "00_PROJECT_INSTRUCTIONS.md",
            )
            .values(content=b"tampered\n" + bytes(content))
        )
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    with TestClient(app) as drifted_client:
        readiness = drifted_client.get("/health/ready")
        strategy = drifted_client.get("/api/v1/baseline")

    assert readiness.status_code == 503
    assert readiness.json()["checks"]["fixture"] == "core_files_drift"
    assert strategy.status_code == 503
    assert strategy.json()["detail"]["reason"] == "core_files_drift"


def test_full_core_csv_row_reorder_blocks_strategy_reads() -> None:
    factory = make_factory()
    with factory() as session:
        state = session.get(MaterializationState, 1)
        assert state is not None
        rows = session.scalars(
            select(CoreCsvRow)
            .where(
                CoreCsvRow.revision_id == state.active_revision_id,
                CoreCsvRow.relative_path == "18_TW_CHARACTER_AVAILABILITY.csv",
                CoreCsvRow.ordinal.in_([1, 2]),
            )
            .order_by(CoreCsvRow.ordinal)
        ).all()
        assert len(rows) == 2
        first, second = rows
        first_payload = (first.natural_key, list(first.values), first.row_sha256)
        second_payload = (second.natural_key, list(second.values), second.row_sha256)
        table = CoreCsvRow.__table__
        row_filter = (
            (CoreCsvRow.revision_id == state.active_revision_id)
            & (CoreCsvRow.relative_path == "18_TW_CHARACTER_AVAILABILITY.csv")
        )
        session.execute(
            update(table)
            .where(row_filter, CoreCsvRow.ordinal == first.ordinal)
            .values(natural_key="__row_swap_staging__")
        )
        session.execute(
            update(table)
            .where(row_filter, CoreCsvRow.ordinal == second.ordinal)
            .values(
                natural_key=first_payload[0],
                values=first_payload[1],
                row_sha256=first_payload[2],
            )
        )
        session.execute(
            update(table)
            .where(row_filter, CoreCsvRow.ordinal == first.ordinal)
            .values(
                natural_key=second_payload[0],
                values=second_payload[1],
                row_sha256=second_payload[2],
            )
        )
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    with TestClient(app) as drifted_client:
        readiness = drifted_client.get("/health/ready")
        strategy = drifted_client.get("/api/v1/baseline")

    assert readiness.status_code == 503
    assert readiness.json()["checks"]["fixture"] == "core_csv_rows_drift"
    assert strategy.status_code == 503
    assert strategy.json()["detail"]["reason"] == "core_csv_rows_drift"


@pytest.mark.parametrize(
    ("drift_kind", "expected_reason"),
    [
        ("core", "core_files_drift"),
        ("typed", "materialization_teams_drift"),
    ],
)
def test_postgresql_epoch_change_forces_readiness_revalidation(
    monkeypatch,
    drift_kind: str,
    expected_reason: str,
) -> None:
    factory = make_factory()
    monkeypatch.setattr(repository_module, "_is_postgresql", lambda _session: True)
    with factory() as session:
        run = latest_import(session)
        assert run is not None
        assert mirror_readiness(session, run) == (True, "imported")

    with factory() as session:
        state = session.get(MaterializationState, 1)
        assert state is not None
        if drift_kind == "core":
            content = session.scalar(
                select(CoreFile.content).where(
                    CoreFile.revision_id == state.active_revision_id,
                    CoreFile.relative_path == "00_PROJECT_INSTRUCTIONS.md",
                )
            )
            assert content is not None
            session.execute(
                update(CoreFile.__table__)
                .where(
                    CoreFile.revision_id == state.active_revision_id,
                    CoreFile.relative_path == "00_PROJECT_INSTRUCTIONS.md",
                )
                .values(content=b"epoch tamper\n" + bytes(content))
            )
        else:
            team = session.get(Team, "TM-F810-01")
            assert team is not None
            team.notes = "epoch tamper"
        state.epoch += 1
        session.commit()

    with factory() as session:
        run = latest_import(session)
        assert run is not None
        assert mirror_readiness(session, run) == (False, expected_reason)


def test_readiness_fails_closed_when_materialized_team_is_deleted() -> None:
    factory = make_factory()
    with factory() as session:
        session.execute(delete(Team).where(Team.team_id == "TM-F810-03"))
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    with TestClient(app) as drifted_client:
        response = drifted_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {
            "database": "ok",
            "fixture": "materialization_operation_timelines_drift",
        },
    }


def test_readiness_fails_closed_when_team_evidence_link_is_deleted() -> None:
    factory = make_factory()
    with factory() as session:
        session.execute(
            delete(TeamEvidence).where(
                TeamEvidence.team_id == "TM-F810-01",
                TeamEvidence.evidence_id == "ev050",
            )
        )
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    with TestClient(app) as drifted_client:
        response = drifted_client.get("/health/ready")
        strategy_response = drifted_client.get("/api/v1/teams/TM-F810-01")

    assert response.status_code == 503
    assert response.json()["checks"]["fixture"] == "materialization_team_evidence_drift"
    assert strategy_response.status_code == 503
    assert strategy_response.json()["detail"]["code"] == "FIXTURE_DRIFT"
    assert (
        strategy_response.json()["detail"]["reason"]
        == "materialization_team_evidence_drift"
    )


def test_readiness_fails_closed_when_normalized_team_field_is_tampered() -> None:
    factory = make_factory()
    with factory() as session:
        team = session.get(Team, "TM-F810-01")
        assert team is not None
        team.notes = "tampered without changing source_payload"
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    with TestClient(app) as drifted_client:
        response = drifted_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["fixture"] == "materialization_teams_drift"


def test_all_strategy_reads_fail_closed_on_timeline_materialization_drift() -> None:
    factory = make_factory()
    with factory() as session:
        timeline = session.get(OperationTimeline, "AX-F810-02-EV073")
        assert timeline is not None
        timeline.notes = "tampered without changing source_payload"
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version=APPLICATION_VERSION),
        session_factory=factory,
    )
    endpoints = [
        "/api/v1/baseline",
        "/api/v1/stages",
        f"/api/v1/stages/{GUIDE_ID}",
        "/api/v1/teams/TM-F810-02",
        "/api/v1/teams/TM-F810-02/timelines",
        "/api/v1/evidence/ev073",
        "/api/v1/claims/CLM-PVE-F810-SHIZURU",
        "/api/v1/gacha/timeline",
        "/api/v1/gacha/community-sources",
        "/api/v1/pvp/characters",
        "/api/v1/pvp/counters",
    ]
    with TestClient(app) as drifted_client:
        readiness = drifted_client.get("/health/ready")
        responses = [drifted_client.get(path) for path in endpoints]

    assert readiness.status_code == 503
    assert (
        readiness.json()["checks"]["fixture"]
        == "materialization_operation_timelines_drift"
    )
    assert all(response.status_code == 503 for response in responses)
    assert {
        response.json()["detail"]["reason"] for response in responses
    } == {"materialization_operation_timelines_drift"}


def _effective_team_count(factory) -> int:
    with factory() as session:
        return len(effective_team_signatures(session, GUIDE_ID))


def test_coverage_excludes_provisional_team() -> None:
    factory = make_factory()
    with factory() as session:
        team = session.get(Team, "TM-F810-03")
        assert team is not None
        team.clear_status = "PROVISIONAL"
        session.commit()

    assert _effective_team_count(factory) == 4


def test_coverage_excludes_team_with_incomplete_evidence_closure() -> None:
    factory = make_factory()
    with factory() as session:
        evidence_id = session.scalar(
            select(TeamEvidence.evidence_id)
            .where(TeamEvidence.team_id == "TM-F810-03")
            .limit(1)
        )
        assert evidence_id is not None
        session.execute(
            delete(TeamEvidence).where(
                TeamEvidence.team_id == "TM-F810-03",
                TeamEvidence.evidence_id == evidence_id,
            )
        )
        session.commit()

    assert _effective_team_count(factory) == 4


def test_coverage_excludes_team_with_unavailable_character() -> None:
    factory = make_factory()
    with factory() as session:
        target_members = list(
            session.scalars(
                select(TeamMember.unit_key).where(TeamMember.team_id == "TM-F810-03")
            ).all()
        )
        all_members = list(session.scalars(select(TeamMember.unit_key)).all())
        unique_unit = next(unit for unit in target_members if all_members.count(unit) == 1)
        character = session.get(Character, unique_unit)
        assert character is not None
        character.availability_status = "UNAVAILABLE"
        session.commit()

    assert _effective_team_count(factory) == 4


def test_baseline_reports_real_counts_and_research_gates(client: TestClient) -> None:
    response = client.get("/api/v1/baseline")
    assert response.status_code == 200
    payload = response.json()
    assert_meta(payload)
    data = payload["data"]
    assert data["research_core_version"] == "v1.5"
    assert data["application_version"] == "3.0.0-b5"
    assert data["counts"] == {
        "stages": 3,
        "teams": 10,
        "team_members": 50,
        "characters": 35,
        "evidence": 73,
        "claims": 69,
        "operation_timelines": 15,
        "timeline_steps": 37,
        "arena_defenses": 1,
        "arena_defense_members": 5,
        "arena_counters": 2,
        "arena_counter_members": 10,
        "arena_counter_evidence": 4,
        "arena_counter_claims": 4,
        "gacha_timeline_events": 5,
        "gacha_timeline_evidence": 10,
        "gacha_timeline_claims": 8,
        "gacha_community_sources": 4,
        "gacha_timeline_community_sources": 0,
    }
    assert data["gates"]["gate_a"] is False
    assert data["gates"]["gate_b"] is False
    assert data["gates"]["gate_c"] is False
    assert data["featured_stage"]["guide_id"] == GUIDE_ID


def test_stage_exposes_all_five_teams_and_mature_coverage(client: TestClient) -> None:
    response = client.get(f"/api/v1/stages/{GUIDE_ID}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["area"] == "紅焰"
    assert data["stage"] == "8-10"
    assert data["status"] == "VERIFIED"
    assert data["reproducibility"] == "CONFIRMED"
    assert data["team_count"] == 5
    assert [team["team_id"] for team in data["teams"]] == [
        "TM-F810-01",
        "TM-F810-02",
        "TM-F810-03",
        "TM-F810-04",
        "TM-F810-05",
    ]
    assert data["coverage"] == {
        "verified_distinct_teams": 5,
        "maturity_target": 5,
        "remaining": 0,
        "is_mature": True,
    }


def test_water_stage_exposes_five_verified_distinct_teams(client: TestClient) -> None:
    stages = client.get("/api/v1/stages")
    assert stages.status_code == 200
    assert [stage["guide_id"] for stage in stages.json()["data"]] == [
        GUIDE_ID,
        "TW_DEEP_FIRE_10_10_20260802",
        WATER_GUIDE_ID,
    ]

    response = client.get(f"/api/v1/stages/{WATER_GUIDE_ID}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["area"] == "蒼波"
    assert data["stage"] == "8-10"
    assert data["status"] == "VERIFIED"
    assert data["reproducibility"] == "CONFIRMED"
    assert data["team_count"] == 5
    assert [team["team_id"] for team in data["teams"]] == [
        "TM-W810-01",
        "TM-W810-02",
        "TM-W810-03",
        "TM-W810-04",
        "TM-W810-05",
    ]
    assert [team["operation_mode"] for team in data["teams"]] == [
        "MANUAL_TIMELINE",
        "SEMI_AUTO",
        "AUTO",
        "AUTO",
        "AUTO",
    ]
    assert data["coverage"] == {
        "verified_distinct_teams": 5,
        "maturity_target": 5,
        "remaining": 0,
        "is_mature": True,
    }


@pytest.mark.parametrize(
    ("team_id", "mode", "timeline_id", "step_count"),
    [
        ("TM-W810-01", "MANUAL_TIMELINE", "TL-W810-01-EV084", 9),
        ("TM-W810-02", "SEMI_AUTO", "TL-W810-02-EV085", 6),
        ("TM-W810-03", "AUTO", "TL-W810-03-EV086", 1),
        ("TM-W810-04", "AUTO", "TL-W810-04-EV087", 1),
        ("TM-W810-05", "AUTO", "TL-W810-05-EV088", 1),
    ],
)
def test_water_team_timelines_preserve_source_modes_and_unknown_requirements(
    client: TestClient,
    team_id: str,
    mode: str,
    timeline_id: str,
    step_count: int,
) -> None:
    response = client.get(f"/api/v1/teams/{team_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["clear_status"] == "VERIFIED"
    assert data["operation_mode"] == mode
    assert data["stage"] == "蒼波8-10"
    assert all(member["is_borrowed"] is None for member in data["members"])
    assert data["requirements"]["support"] == {
        "requirements": "UNKNOWN",
        "unit": "UNKNOWN",
    }
    assert all(
        value == "UNKNOWN"
        for slot in data["requirements"]["slots"].values()
        for value in slot.values()
    )

    timeline = data["timeline"]
    assert timeline["status"] == "STRUCTURED"
    assert timeline["registered_sources"] == 1
    assert timeline["structured_sources"] == 1
    source = timeline["sources"][0]
    assert source["timeline_id"] == timeline_id
    assert source["operation_mode"] == mode
    assert source["battle_duration_ms"] == 90000
    assert source["reproducibility"] == "TW_REPRODUCED"
    assert len(source["steps"]) == step_count
    if team_id in {"TM-W810-03", "TM-W810-04", "TM-W810-05"}:
        assert source["steps"][0]["trigger_type"] == "WAVE_START"
        assert source["steps"][0]["action_type"] == "NO_ACTION"

    nested = client.get(f"/api/v1/teams/{team_id}/timelines")
    assert nested.status_code == 200
    assert nested.json()["data"] == timeline


def test_water_evidence_drawer_excludes_rejected_non_clears(client: TestClient) -> None:
    active = client.get("/api/v1/evidence/ev084")
    assert active.status_code == 200
    assert active.json()["data"]["source_url"] == (
        "https://www.youtube.com/watch?v=w3My0QHcoTA"
    )

    for evidence_id in ("ev089", "ev090"):
        rejected = client.get(f"/api/v1/evidence/{evidence_id}")
        assert rejected.status_code == 404
        assert rejected.json()["detail"] == {
            "code": "NOT_FOUND",
            "resource": "evidence",
            "id": evidence_id,
        }


def test_source_conflict_unknowns_and_timeline_gap_are_not_strengthened(client: TestClient) -> None:
    response = client.get("/api/v1/teams/TM-F810-01")
    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]
    assert data["operation_mode"] == "SOURCE_CONFLICT"
    assert all(member["is_borrowed"] is None for member in data["members"])
    assert {claim["mode"] for claim in data["requirements"]["operation_mode_claims"]} == {
        "AUTO",
        "SEMI_AUTO",
    }
    assert all(
        value == "UNKNOWN"
        for slot in data["requirements"]["slots"].values()
        for value in slot.values()
    )
    assert data["timeline"]["status"] == "SOURCE_GAP"
    assert data["timeline"]["structured_sources"] == 0
    assert data["timeline"]["registered_sources"] == 3
    assert all(
        source["status"] == "SOURCE_GAP" for source in data["timeline"]["sources"]
    )
    assert data["timeline"]["steps"] == []
    assert [reference["raw"] for reference in data["timeline"]["references"]] == [
        "AX-F810-01-EV050",
        "AX-F810-01-EV052",
        "AX-F810-01-EV069",
    ]
    assert "STRUCTURED_TIMELINE_SOURCE_GAP" in payload["meta"]["warnings"]


def test_partial_timeline_is_source_separated_and_preserves_cross_server_status(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/teams/TM-F810-02")
    assert response.status_code == 200
    payload = response.json()
    timeline = payload["data"]["timeline"]
    assert timeline["status"] == "PARTIAL"
    assert timeline["registered_sources"] == 4
    assert timeline["structured_sources"] == 1
    assert timeline["steps"] == []
    assert [source["source_axis_id"] for source in timeline["sources"]] == [
        "AX-F810-02-EV070",
        "AX-F810-02-EV071",
        "AX-F810-02-EV072",
        "AX-F810-02-EV073",
    ]

    structured = next(
        source for source in timeline["sources"] if source["status"] == "STRUCTURED"
    )
    assert structured["timeline_id"] == "TL-F810-02-EV073"
    assert structured["source_evidence_id"] == "ev073"
    assert structured["battle_duration_ms"] is None
    assert structured["reproducibility"] == "UNVERIFIED_ON_TW"
    assert structured["gap_reason"] is None
    assert len(structured["steps"]) == 14
    assert [step["sequence_no"] for step in structured["steps"]] == list(range(1, 15))
    assert all(step["criticality"] == "UNKNOWN" for step in structured["steps"])
    assert all(
        step["time_state"] == "NOT_STATED"
        and step["clock_from_ms"] is None
        and step["clock_to_ms"] is None
        for step in structured["steps"][:4]
    )
    assert structured["steps"][4]["time_state"] == "STATED"
    assert structured["steps"][4]["clock_from_ms"] == 70000
    assert "STRUCTURED_TIMELINE_PARTIAL" in payload["meta"]["warnings"]

    nested = client.get("/api/v1/teams/TM-F810-02/timelines")
    assert nested.status_code == 200
    assert nested.json()["data"] == timeline


def test_unknown_operation_mode_and_source_gap_are_preserved(client: TestClient) -> None:
    response = client.get("/api/v1/teams/TM-F810-04")
    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]

    assert data["operation_mode"] == "UNKNOWN"
    assert all(member["is_borrowed"] is None for member in data["members"])
    assert data["requirements"]["operation_mode_claims"] == [
        {"mode": "UNKNOWN", "source_id": "yt_p95ZoBCWuYE"}
    ]
    assert all(
        value == "UNKNOWN"
        for slot in data["requirements"]["slots"].values()
        for value in slot.values()
    )
    assert data["timeline"]["status"] == "SOURCE_GAP"
    assert data["timeline"]["registered_sources"] == 1
    assert data["timeline"]["structured_sources"] == 0
    assert data["timeline"]["sources"][0]["operation_mode"] == "UNKNOWN"
    assert data["timeline"]["sources"][0]["steps"] == []
    assert "STRUCTURED_TIMELINE_SOURCE_GAP" in payload["meta"]["warnings"]


def test_source_text_only_timeline_does_not_invent_actions(client: TestClient) -> None:
    response = client.get("/api/v1/teams/TM-F810-05/timelines")
    assert response.status_code == 200
    timeline = response.json()["data"]

    assert timeline["status"] == "STRUCTURED"
    assert timeline["registered_sources"] == 1
    assert timeline["structured_sources"] == 1
    source = timeline["sources"][0]
    assert source["source_axis_id"] == "AX-F810-05-EV083"
    assert source["timeline_id"] == "TL-F810-05-EV083"
    assert source["operation_mode"] == "SEMI_AUTO"
    assert source["initial_auto_state"] == "OFF"
    assert source["reproducibility"] == "UNVERIFIED_ON_TW"
    assert len(source["steps"]) == 5
    assert [step["clock_from_ms"] for step in source["steps"]] == [
        90000,
        38000,
        27000,
        26000,
        7000,
    ]
    assert all(step["trigger_type"] == "SOURCE_TEXT_ONLY" for step in source["steps"])
    assert all(step["action_type"] == "NO_ACTION" for step in source["steps"])
    assert [step["auto_state_after"] for step in source["steps"]] == [
        "OFF",
        "OFF",
        "OFF",
        "OFF",
        "ON",
    ]
    assert all(step["criticality"] == "UNKNOWN" for step in source["steps"])


def test_evidence_claim_drawer_and_pvp_single_reports(client: TestClient) -> None:
    evidence = client.get("/api/v1/evidence/ev050")
    assert evidence.status_code == 200
    evidence_data = evidence.json()["data"]
    assert evidence_data["source_url"].startswith("https://")
    assert evidence_data["linked_claim_id"] == evidence_data["declared_claim_id"]

    claim_id = evidence_data["linked_claim_id"]
    claim = client.get(f"/api/v1/claims/{claim_id}")
    assert claim.status_code == 200
    assert "ev050" in claim.json()["data"]["evidence_ids"]

    pvp = client.get("/api/v1/pvp/counters")
    assert pvp.status_code == 200
    assert [row["counter_id"] for row in pvp.json()["data"]] == [
        "TW_ARENA_20260525_01",
        "TW_ARENA_20260525_02",
    ]
    assert all(row["tw_availability_check"] == "PASS" for row in pvp.json()["data"])
    assert "NO_VERIFIED_COUNTER" in pvp.json()["meta"]["warnings"]
    assert "SINGLE_REPORT_REFERENCE_ONLY" in pvp.json()["meta"]["warnings"]


def test_pvp_character_picker_options_are_tw_available_and_stably_sorted(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/pvp/characters")

    assert response.status_code == 200
    payload = response.json()
    assert_meta(payload)
    assert payload["data"]
    assert all(
        row["tw_availability_status"] == "AVAILABLE" for row in payload["data"]
    )
    assert all(row["tw_name"] not in {"UNKNOWN", "【待查證】"} for row in payload["data"])
    assert [
        (row["tw_name"], row["unit_key"]) for row in payload["data"]
    ] == sorted((row["tw_name"], row["unit_key"]) for row in payload["data"])
    assert payload["meta"]["server"] == "TW"
    assert payload["meta"]["environment_version"] == "UNKNOWN"
    assert payload["meta"]["verified_at"] is None
    assert payload["meta"]["stale_status"] == "UNKNOWN"
    assert payload["meta"]["confidence"] == "UNKNOWN"
    assert payload["meta"]["claim_ids"] == []


def test_unknown_resource_is_structured_404(client: TestClient) -> None:
    response = client.get("/api/v1/teams/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {
        "detail": {
            "code": "NOT_FOUND",
            "resource": "team",
            "id": "does-not-exist",
        }
    }


def test_openapi_contains_only_get_for_public_strategy_routes(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    expected = {
        "/api/v1/baseline",
        "/api/v1/stages",
        "/api/v1/stages/{guide_id}",
        "/api/v1/teams/{team_id}",
        "/api/v1/teams/{team_id}/timelines",
        "/api/v1/evidence/{evidence_id}",
        "/api/v1/claims/{claim_id}",
        "/api/v1/pvp/characters",
        "/api/v1/pvp/counters",
    }
    assert expected <= schema["paths"].keys()
    for path in expected:
        assert set(schema["paths"][path]) == {"get"}


def test_cors_is_explicit_read_only_allowlist(client: TestClient) -> None:
    allowed = client.options(
        "/api/v1/evidence/ev050",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert "GET" in allowed.headers["access-control-allow-methods"]
    assert "access-control-allow-credentials" not in allowed.headers

    rejected = client.options(
        "/api/v1/evidence/ev050",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers

    write_preflight = client.options(
        "/api/v1/evidence/ev050",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert write_preflight.status_code == 400
