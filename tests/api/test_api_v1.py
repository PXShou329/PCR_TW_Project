from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from pcr_api.config import Settings
from pcr_api.main import create_app
from pcr_api.repository import effective_team_signatures
from pcr_database.models import Character, Team, TeamEvidence, TeamMember

from .conftest import make_factory


GUIDE_ID = "TW_DEEP_FIRE_08_10_20260802"


def assert_meta(payload: dict) -> None:
    meta = payload["meta"]
    assert meta["api_version"] == "v1"
    assert len(meta["source"]["fixture_sha256"]) == 64
    assert meta["source"]["canonical_source"] == "research_core_file_ssot"
    assert meta["source"]["research_core_version"] == "v1.5"


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


def test_readiness_fails_closed_when_materialized_team_is_deleted() -> None:
    factory = make_factory()
    with factory() as session:
        session.execute(delete(Team).where(Team.team_id == "TM-F810-03"))
        session.commit()

    app = create_app(
        settings=Settings(database_url="sqlite://", application_version="3.0.0-b0"),
        session_factory=factory,
    )
    with TestClient(app) as drifted_client:
        response = drifted_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "ok", "fixture": "row_count_drift"},
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
        settings=Settings(database_url="sqlite://", application_version="3.0.0-b0"),
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
        settings=Settings(database_url="sqlite://", application_version="3.0.0-b0"),
        session_factory=factory,
    )
    with TestClient(app) as drifted_client:
        response = drifted_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["fixture"] == "materialization_teams_drift"


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

    assert _effective_team_count(factory) == 2


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

    assert _effective_team_count(factory) == 2


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

    assert _effective_team_count(factory) == 2


def test_baseline_reports_real_counts_and_research_gates(client: TestClient) -> None:
    response = client.get("/api/v1/baseline")
    assert response.status_code == 200
    payload = response.json()
    assert_meta(payload)
    data = payload["data"]
    assert data["research_core_version"] == "v1.5"
    assert data["application_version"] == "3.0.0-b0"
    assert data["counts"] == {
        "stages": 1,
        "teams": 3,
        "team_members": 15,
        "characters": 8,
        "evidence": 18,
        "claims": 13,
    }
    assert data["gates"]["gate_a"] is False
    assert data["gates"]["gate_b"] is False
    assert data["gates"]["gate_c"] is False
    assert data["featured_stage"]["guide_id"] == GUIDE_ID


def test_stage_exposes_all_three_teams_and_honest_maturity_gap(client: TestClient) -> None:
    response = client.get(f"/api/v1/stages/{GUIDE_ID}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "PROVISIONAL"
    assert data["reproducibility"] == "PENDING"
    assert data["team_count"] == 3
    assert [team["team_id"] for team in data["teams"]] == [
        "TM-F810-01",
        "TM-F810-02",
        "TM-F810-03",
    ]
    assert data["coverage"] == {
        "verified_distinct_teams": 3,
        "maturity_target": 5,
        "remaining": 2,
        "is_mature": False,
    }


def test_source_conflict_unknowns_and_timeline_gap_are_not_strengthened(client: TestClient) -> None:
    response = client.get("/api/v1/teams/TM-F810-01")
    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]
    assert data["operation_mode"] == "SOURCE_CONFLICT"
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
    assert data["timeline"]["steps"] == []
    assert data["timeline"]["references"]
    assert "STRUCTURED_TIMELINE_SOURCE_GAP" in payload["meta"]["warnings"]


def test_evidence_claim_drawer_and_pvp_no_result(client: TestClient) -> None:
    evidence = client.get("/api/v1/evidence/ev050")
    assert evidence.status_code == 200
    evidence_data = evidence.json()["data"]
    assert evidence_data["source_url"].startswith("https://")
    assert evidence_data["linked_claim_id"] == evidence_data["declared_claim_id"]

    claim_id = evidence_data["linked_claim_id"]
    claim = client.get(f"/api/v1/claims/{claim_id}")
    assert claim.status_code == 200
    assert "ev050" in claim.json()["data"]["evidence_ids"]

    no_result = client.get("/api/v1/pvp/counters")
    assert no_result.status_code == 200
    assert no_result.json()["data"] == []
    assert "NO_VERIFIED_COUNTER" in no_result.json()["meta"]["warnings"]


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
        "/api/v1/evidence/{evidence_id}",
        "/api/v1/claims/{claim_id}",
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
