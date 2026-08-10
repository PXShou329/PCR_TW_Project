from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import tarfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select

from pcr_api.repository import _stored_relation_ids, parena_case_results
from pcr_api.config import Settings
from pcr_api.main import create_app
from pcr_api.routes import v1 as v1_routes
from pcr_database.materialization import PARENA_SERVING_MODELS
from pcr_database.models import Character
from pcr_pipeline.pve_fixture import import_pve_projection
from pcr_pipeline.research_core_snapshot import RP_A6_0_MANIFEST_SHA256

from .conftest import ROOT, make_factory


def _available_keys(client: TestClient) -> list[str]:
    response = client.get("/api/v1/pvp/characters")
    assert response.status_code == 200
    keys = [row["unit_key"] for row in response.json()["data"]]
    assert len(keys) >= 15
    return keys[:15]


def _request(keys: list[str], *, environment: str = "TW-TEST-2026-08") -> dict:
    return {
        "server": "TW",
        "environment_version": environment,
        "defense_teams": [keys[0:5], keys[5:10], keys[10:15]],
    }


def _a6_client(tmp_path: Path, *, physical_v7: bool = False) -> TestClient:
    archive = tmp_path / "rp-a6-0.tar"
    subprocess.run(
        [
            "git",
            "archive",
            "--format=tar",
            f"--output={archive}",
            "rp-a6-0",
            "research_core/pcr_tw_project",
            "scripts/research_core_rp_a6_0_manifest.sha256",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    destination = tmp_path / "rp-a6-0"
    destination.mkdir()
    with tarfile.open(archive, mode="r:") as bundle:
        bundle.extractall(destination, filter="data")

    factory = make_factory(imported=False)
    with factory() as session:
        import_pve_projection(
            session,
            destination / "research_core" / "pcr_tw_project",
            manifest_path=(
                destination / "scripts" / "research_core_rp_a6_0_manifest.sha256"
            ),
            expected_manifest_sha256=RP_A6_0_MANIFEST_SHA256,
            application_version="3.0.0-a6",
        )
    if physical_v7:
        engine = factory.kw["bind"]
        for model in reversed(PARENA_SERVING_MODELS):
            model.__table__.drop(engine)
    return TestClient(
        create_app(
            settings=Settings(
                database_url="sqlite://",
                application_version="3.0.0-a6",
            ),
            session_factory=factory,
        )
    )


def test_v4_parena_endpoints_fail_closed(tmp_path: Path) -> None:
    with _a6_client(tmp_path) as client:
        keys = _available_keys(client)
        environments = client.get("/api/v1/parena/environments")
        solve = client.post("/api/v1/solver/parena", json=_request(keys))

        assert environments.status_code == 503
        assert solve.status_code == 503
        assert environments.json()["detail"]["code"] == "NO_PARENA_MATERIALIZATION"
        assert solve.json()["detail"]["code"] == "NO_PARENA_MATERIALIZATION"


def test_v4_api_stays_ready_after_physical_v8_tables_are_downgraded(
    tmp_path: Path,
) -> None:
    with _a6_client(tmp_path, physical_v7=True) as client:
        readiness = client.get("/health/ready")
        baseline = client.get("/api/v1/baseline")
        environments = client.get("/api/v1/parena/environments")

    assert readiness.status_code == 200
    assert readiness.json()["checks"] == {
        "database": "ok",
        "fixture": "imported",
    }
    assert baseline.status_code == 200
    assert environments.status_code == 503
    assert environments.json()["detail"]["code"] == "NO_PARENA_MATERIALIZATION"


def test_v5_zero_case_is_truthful_empty(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(v1_routes, "has_parena_materialization", lambda _run: True)
    keys = _available_keys(client)

    environments = client.get("/api/v1/parena/environments")
    solve = client.post("/api/v1/solver/parena", json=_request(keys))

    assert environments.status_code == 200
    assert environments.json()["data"] == []
    assert environments.json()["meta"]["warnings"] == ["NO_MATURE_PARENA_CASE"]
    assert solve.status_code == 200
    payload = solve.json()
    assert payload["data"]["match_type"] == "EXACT"
    assert payload["data"]["similar_enabled"] is False
    assert payload["data"]["cases"] == []
    assert payload["meta"]["warnings"] == ["NO_MATURE_PARENA_CASE"]
    assert payload["meta"]["server"] == "UNKNOWN"
    assert payload["meta"]["environment_version"] == "UNKNOWN"
    assert payload["meta"]["verified_at"] is None
    assert payload["meta"]["evidence_ids"] == []
    assert payload["meta"]["claim_ids"] == []
    assert payload["meta"]["data_revision"] == payload["meta"]["source"]["revision_id"]


def test_nonempty_registry_exact_miss_is_not_mature_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(v1_routes, "has_parena_materialization", lambda _run: True)
    monkeypatch.setattr(v1_routes, "mature_parena_case_count", lambda _session: 2)
    keys = _available_keys(client)

    response = client.post("/api/v1/solver/parena", json=_request(keys))

    assert response.status_code == 200
    assert response.json()["data"]["cases"] == []
    assert response.json()["meta"]["warnings"] == ["NO_EXACT_PARENA_PLAN"]


def test_solver_rejects_unknown_or_nonavailable_units(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(v1_routes, "has_parena_materialization", lambda _run: True)
    keys = _available_keys(client)
    unavailable = [*keys[:14], "future_unit_not_available"]

    bad_environment = client.post(
        "/api/v1/solver/parena",
        json=_request(keys, environment="UNKNOWN"),
    )
    bad_character = client.post(
        "/api/v1/solver/parena",
        json=_request(unavailable),
    )

    assert bad_environment.status_code == 422
    assert bad_character.status_code == 422
    assert bad_character.json()["detail"] == {
        "code": "INVALID_PARENA_DEFENSE",
        "resource": "parena_defense",
        "id": None,
        "reason": "all 15 unit_keys must be TW AVAILABLE",
        "unavailable_unit_ids": ["future_unit_not_available"],
    }


def test_solver_rejects_cross_team_overlap(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(v1_routes, "has_parena_materialization", lambda _run: True)
    keys = _available_keys(client)
    request = _request(keys)
    request["defense_teams"][2][4] = keys[0]

    response = client.post("/api/v1/solver/parena", json=request)

    assert response.status_code == 422


def test_environment_registry_positive_is_typed_and_stable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(v1_routes, "has_parena_materialization", lambda _run: True)
    monkeypatch.setattr(
        v1_routes,
        "parena_environment_results",
        lambda _session: [
            {
                "server": "TW",
                "environment_version": "TW-TEST-2026-08",
                "verified_case_count": 2,
            }
        ],
    )

    response = client.get("/api/v1/parena/environments")

    assert response.status_code == 200
    assert response.json()["data"] == [{
        "server": "TW",
        "environment_version": "TW-TEST-2026-08",
        "verified_case_count": 2,
    }]
    assert response.json()["meta"]["server"] == "TW"
    assert response.json()["meta"]["environment_version"] == "TW-TEST-2026-08"


def test_typed_case_closure_drift_is_503_not_empty(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(v1_routes, "has_parena_materialization", lambda _run: True)
    monkeypatch.setattr(
        v1_routes,
        "parena_case_results",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("P-Arena case has only two matchups")
        ),
    )
    keys = _available_keys(client)

    response = client.post("/api/v1/solver/parena", json=_request(keys))

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "FIXTURE_DRIFT",
        "resource": "parena_materialization",
        "id": None,
        "reason": "parena_serving_closure_invalid",
    }


def test_empty_exact_repository_query_is_bounded() -> None:
    factory = make_factory()
    statements: list[str] = []

    def track(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    with factory() as session:
        bind = session.get_bind()
        event.listen(bind, "before_cursor_execute", track)
        try:
            keys = [row[0] for row in session.execute(
                select(Character.unit_key)
                .where(Character.availability_status == "AVAILABLE")
                .order_by(Character.unit_key)
                .limit(15)
            )]
            statements.clear()
            signature, rows = parena_case_results(
                session,
                environment_version="TW-TEST-2026-08",
                defense_teams=[keys[0:5], keys[5:10], keys[10:15]],
            )
        finally:
            event.remove(bind, "before_cursor_execute", track)

    assert signature
    assert rows == []
    assert len(statements) <= 2


def test_raw_case_relation_declarations_are_losslessly_parsed() -> None:
    assert _stored_relation_ids("SRC-1;SRC-2") == ("SRC-1", "SRC-2")
    assert _stored_relation_ids(["EV-1", "EV-2"]) == ("EV-1", "EV-2")
    assert _stored_relation_ids("CL-1;CL-1") == ()
    assert _stored_relation_ids("UNKNOWN;") == ("UNKNOWN",)


@pytest.mark.parametrize(
    ("case_win_confidence", "expected_warnings"),
    [
        ("B", []),
        ("C", []),
        (
            "D",
            [
                "CASE_WIN_SINGLE_SOURCE_REFERENCE",
                "CASE_WIN_CONFIDENCE_D_BLOCKS_GATE_C",
            ],
        ),
    ],
)
def test_synthetic_exact_case_preserves_input_permutation_and_confidence(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    case_win_confidence: str,
    expected_warnings: list[str],
) -> None:
    monkeypatch.setattr(v1_routes, "has_parena_materialization", lambda _run: True)
    keys = _available_keys(client)
    arena_response = client.get("/api/v1/pvp/counters")
    assert arena_response.status_code == 200
    counter = deepcopy(arena_response.json()["data"][0])
    counter["status"] = "VERIFIED"
    counter["claim_confidence"] = "C"
    counter["reproducibility"] = "CONFIRMED"

    def synthetic_results(_session, *, environment_version, defense_teams):
        assert environment_version == "TW-TEST-2026-08"
        assert defense_teams == [keys[0:5], keys[5:10], keys[10:15]]
        case = {
            "case_id": "TEST-PARENA-001",
            "server": "TW",
            "environment_version": environment_version,
            "status": "VERIFIED",
            "hidden_team_mode": "NONE",
            "verified_date": "2026-08-10",
            "reproducibility": "CONFIRMED",
            "last_review_due": "2026-09-10",
            "notes": "synthetic API contract fixture only",
            "case_win_claim_id": "CLM-TEST-PARENA-WIN",
            "case_win_confidence": case_win_confidence,
            "sources": [{
                "source_id": "SRC-TEST-PARENA",
                "title": "Synthetic test source",
                "platform": "TEST_ONLY",
                "source_type": "TEST_FIXTURE",
                "server": "TW",
                "url": "https://example.invalid/parena-test",
                "last_checked": "2026-08-10",
                "freshness_window": "CURRENT",
                "access_status": "ACTIVE",
                "confidence_cap": "C",
                "extraction_method": "TEST_ONLY",
                "notes": "never canonical",
            }],
            "evidence_ids": ["ev114"],
            "claim_ids": [
                "CLM-TEST-PARENA-1",
                "CLM-TEST-PARENA-2",
                "CLM-TEST-PARENA-3",
                "CLM-TEST-PARENA-WIN",
            ],
            "matchups": [
                {
                    "matchup_no": matchup_no,
                    "defense_input_index": input_index,
                    "result_claim_id": f"CLM-TEST-PARENA-{input_index}",
                    "counter": counter,
                }
                for matchup_no, input_index in ((2, 1), (3, 2), (1, 3))
            ],
        }
        return "synthetic-query-signature", [case]

    monkeypatch.setattr(v1_routes, "parena_case_results", synthetic_results)
    response = client.post("/api/v1/solver/parena", json=_request(keys))

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["warnings"] == expected_warnings
    assert payload["meta"]["confidence"] == case_win_confidence
    assert payload["data"]["cases"][0]["case_win_confidence"] == case_win_confidence
    assert payload["data"]["query_signature"] == "synthetic-query-signature"
    assert [row["defense_input_index"] for row in payload["data"]["cases"][0]["matchups"]] == [1, 2, 3]
    assert payload["data"]["similar_enabled"] is False
