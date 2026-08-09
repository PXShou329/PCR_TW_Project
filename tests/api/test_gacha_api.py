from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import event

from pcr_api.config import Settings
from pcr_api.main import create_app
from pcr_api.repository import (
    gacha_community_source_results,
    gacha_timeline_results,
)
from pcr_database.models import (
    GachaTimelineCommunitySource,
    GachaTimelineEvent,
)

from .conftest import make_factory


EVENT_IDS = [
    "JP_20260630_shefi_vardrache",
    "JP_20260703_luisemarie_summer",
    "JP_20260731_fubuki_summer",
    "JP_20260815_vampy_summer",
    "JP_20260823_tia",
]
SOURCE_IDS = [
    "GACHA-COMM-001",
    "GACHA-COMM-002",
    "GACHA-COMM-003",
    "GACHA-COMM-004",
]


def test_gacha_timeline_preserves_unknowns_and_conservative_metadata(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/gacha/timeline")

    assert response.status_code == 200
    payload = response.json()
    rows = payload["data"]
    assert [row["event_id"] for row in rows] == EVENT_IDS
    assert all(row["source_server"] == "JP" for row in rows)
    assert all(row["target_server"] == "TW" for row in rows)
    assert all(row["tw_name"] is None for row in rows)
    assert [row["limited_status"] for row in rows] == [
        "YES",
        "YES",
        "YES",
        "UNKNOWN",
        "UNKNOWN",
    ]
    assert [row["limited_claim_id"] for row in rows] == [
        "CLM-SHEFI-POOL",
        "CLM-LUISE-DATE",
        "CLM-JP-FUBUKI-DATE",
        None,
        None,
    ]
    assert all(row["evidence_ids"] == sorted(row["evidence_ids"]) for row in rows)
    assert all(row["claim_ids"] == sorted(row["claim_ids"]) for row in rows)
    assert all(
        row["community_source_ids"] == sorted(row["community_source_ids"])
        for row in rows
    )

    research_rows = [row for row in rows if row["maturity"] == "RESEARCH"]
    assert [row["event_id"] for row in research_rows] == EVENT_IDS[2:]
    for research in research_rows:
        assert {
            research["arena_value"],
            research["p_arena_value"],
            research["pve_value"],
            research["clan_value"],
        } == {"NOT_EVALUATED"}

    meta = payload["meta"]
    assert meta["server"] == "MIXED"
    assert meta["environment_version"] == "UNKNOWN"
    assert meta["verified_at"] is None
    assert meta["stale_status"] == "UNKNOWN"
    assert meta["confidence"] == "UNKNOWN"
    assert meta["evidence_ids"] == sorted(
        {identifier for row in rows for identifier in row["evidence_ids"]}
    )
    assert meta["claim_ids"] == sorted(
        {identifier for row in rows for identifier in row["claim_ids"]}
    )
    assert meta["data_revision"] == meta["source"]["revision_id"]


def test_gacha_community_registry_is_stable_and_never_promoted_to_official(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/gacha/community-sources")

    assert response.status_code == 200
    payload = response.json()
    rows = payload["data"]
    assert [row["source_id"] for row in rows] == SOURCE_IDS
    assert [row["update_status"] for row in rows] == [
        "CHECKED",
        "CHECKED",
        "STALE",
        "STALE",
    ]
    assert all(row["confidence_cap"] == "D" for row in rows)
    assert (rows[0]["coverage_start"], rows[0]["coverage_end"]) == (
        "2026-01",
        "2026-12",
    )
    assert (rows[1]["coverage_start"], rows[1]["coverage_end"]) == (
        "2025-05-04",
        "2026-12-01",
    )
    assert payload["meta"]["server"] == "UNKNOWN"
    assert payload["meta"]["environment_version"] == "UNKNOWN"
    assert payload["meta"]["verified_at"] is None
    assert payload["meta"]["stale_status"] == "UNKNOWN"
    assert payload["meta"]["confidence"] == "UNKNOWN"
    assert payload["meta"]["evidence_ids"] == []
    assert payload["meta"]["claim_ids"] == []


def test_gacha_repository_queries_are_constant_and_relations_are_sorted() -> None:
    factory = make_factory()
    statements: list[str] = []

    def track_query(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    with factory() as session:
        bind = session.get_bind()
        event.listen(bind, "before_cursor_execute", track_query)
        try:
            rows = gacha_timeline_results(session)
            sources = gacha_community_source_results(session)
        finally:
            event.remove(bind, "before_cursor_execute", track_query)

    assert [row["event_id"] for row in rows] == EVENT_IDS
    assert [source["source_id"] for source in sources] == SOURCE_IDS
    assert len(statements) == 5


def test_gacha_relation_ids_use_lexical_order() -> None:
    factory = make_factory()
    with factory() as session:
        timeline = session.get(GachaTimelineEvent, EVENT_IDS[0])
        assert timeline is not None
        timeline.forecast_method = "MODEL_PLUS_COMMUNITY"
        timeline.community_source_count = 2
        timeline.community_estimate_start = timeline.model_estimate_start
        timeline.community_estimate_end = timeline.model_estimate_end
        session.add_all(
            [
                GachaTimelineCommunitySource(
                    event_id=timeline.event_id,
                    source_id=source_id,
                )
                for source_id in reversed(SOURCE_IDS[:2])
            ]
        )
        session.commit()
        rows = gacha_timeline_results(session)

    assert rows[0]["community_source_ids"] == SOURCE_IDS[:2]


def test_gacha_repository_rejects_placeholder_tw_name() -> None:
    factory = make_factory()
    with factory() as session:
        timeline = session.get(GachaTimelineEvent, EVENT_IDS[0])
        assert timeline is not None
        timeline.tw_name = "【待查證】"
        session.commit()

        try:
            gacha_timeline_results(session)
        except RuntimeError as error:
            assert "invalid stored Gacha TW name" in str(error)
        else:
            raise AssertionError("placeholder TW name must fail closed")


def test_gacha_repository_rejects_limited_claim_outside_event_closure() -> None:
    factory = make_factory()
    with factory() as session:
        timeline = session.get(GachaTimelineEvent, EVENT_IDS[0])
        assert timeline is not None
        timeline.limited_claim_id = "CLM-LUISE-DATE"
        session.commit()

        try:
            gacha_timeline_results(session)
        except RuntimeError as error:
            assert "limited provenance is outside Claim closure" in str(error)
        else:
            raise AssertionError("unlinked limited Claim must fail closed")


def test_gacha_public_contract_has_no_write_or_personal_gem_route(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()
    for path in (
        "/api/v1/gacha/timeline",
        "/api/v1/gacha/community-sources",
    ):
        assert set(schema["paths"][path]) == {"get"}
    assert "/api/v1/gacha/gem-scenario" not in schema["paths"]


def test_gacha_routes_share_the_uniform_database_unavailable_problem() -> None:
    factory = make_factory(imported=False)
    factory.kw["bind"].dispose()
    app = create_app(
        settings=Settings(database_url="sqlite://"),
        session_factory=factory,
    )

    with TestClient(app) as client:
        responses = [
            client.get("/api/v1/gacha/timeline"),
            client.get("/api/v1/gacha/community-sources"),
        ]

    expected = {
        "detail": {
            "code": "DATABASE_UNAVAILABLE",
            "resource": "database",
            "id": None,
        }
    }
    assert all(response.status_code == 503 for response in responses)
    assert all(response.json() == expected for response in responses)
