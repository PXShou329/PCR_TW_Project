from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from pcr_api.config import Settings
from pcr_api.main import create_app
from pcr_api.repository import (
    ResponseMetaRecord,
    _arena_display_name,
    _arena_verified_serving_closure_is_mature,
    arena_counter_results,
    conservative_response_metadata,
    pvp_character_options,
)
from pcr_api.routes import v1 as v1_routes
from pcr_database.models import (
    ArenaCounter,
    ArenaCounterClaim,
    ArenaCounterEvidence,
    ArenaCounterMember,
    ArenaDefense,
    ArenaDefenseMember,
    Base,
    Character,
    Claim,
    Evidence,
    ImportRun,
    arena_formation_signature,
)


RUN_ID = "00000000-0000-0000-0000-000000000006"
HASH = "6" * 64
DEFENSE_KEYS = [
    "eris_orig",
    "presia_fallen",
    "rei_ny",
    "neya_orig",
    "matsuri_orig",
]
COUNTER_ONE_KEYS = [
    "kaya_orig",
    "aira_orig",
    "rem_orig",
    "yuki_orig",
    "saren_sum",
]
COUNTER_TWO_KEYS = [
    "kaya_orig",
    "aira_orig",
    "mahiru_orig",
    "yuki_orig",
    "saren_sum",
]
TW_NAMES = {
    "eris_orig": "厄莉絲",
    "presia_fallen": "普蕾西亞（墮落）",
    "rei_ny": "怜（新年）",
    "neya_orig": "涅婭",
    "matsuri_orig": "茉莉",
    "kaya_orig": "嘉夜",
    "aira_orig": "埃拉",
    "rem_orig": "雷姆",
    "mahiru_orig": "真陽",
    "yuki_orig": "雪",
    "saren_sum": "咲戀（夏日）",
}
JP_FUTURE_KEY = "fubuki_sum"
JP_FUTURE_NAME = "フブキ（サマー）"


def _factory(
    *,
    include_arena: bool,
    materialization_version: int,
    include_jp_future: bool = False,
) -> sessionmaker[Session]:
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
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        tables = {}
        if materialization_version == 3:
            tables = {
                name: {}
                for name in (
                    "arena_defenses",
                    "arena_defense_members",
                    "arena_counters",
                    "arena_counter_members",
                    "arena_counter_evidence",
                    "arena_counter_claims",
                )
            }
        run = ImportRun(
            id=RUN_ID,
            fixture_sha256=HASH,
            canonical_source="research_core/pcr_tw_project",
            research_core_version="v1.5-guide-only-pve-wave1-r3i-b3-a5",
            application_version="3.0.0-a5",
            imported_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
            status="RUNNING",
            manifest={
                "materialization": {
                    "schema_version": materialization_version,
                    "tables": tables,
                },
                "warnings": [],
            },
            row_counts={},
        )
        session.add(run)
        session.flush()
        if include_arena:
            _seed_arena(session, include_jp_future=include_jp_future)
        run.status = "SUCCEEDED"
        session.commit()
    return factory


def _seed_arena(session: Session, *, include_jp_future: bool) -> None:
    today = date(2026, 8, 8)
    counter_two_keys = (
        [*COUNTER_TWO_KEYS[:2], JP_FUTURE_KEY, *COUNTER_TWO_KEYS[3:]]
        if include_jp_future
        else COUNTER_TWO_KEYS
    )
    all_keys = dict.fromkeys([*DEFENSE_KEYS, *COUNTER_ONE_KEYS, *counter_two_keys])
    session.add_all(
        Character(
            unit_key=unit_key,
            tw_name=TW_NAMES.get(unit_key, "UNKNOWN"),
            jp_name=JP_FUTURE_NAME if unit_key == JP_FUTURE_KEY else "UNKNOWN",
            version="original",
            tw_release_date=None,
            availability_status=(
                "NOT_RELEASED" if unit_key == JP_FUTURE_KEY else "AVAILABLE"
            ),
            ue1_status="UNKNOWN",
            ue2_status="UNKNOWN",
            six_star_status="UNKNOWN",
            connect_rank_status="UNKNOWN",
            element="UNKNOWN",
            source_evidence_ids=(
                []
                if unit_key == JP_FUTURE_KEY
                else [f"ev-official-{unit_key}"]
            ),
            last_verified=today,
            last_review_due=None,
            notes="Arena API fixture",
            source_payload={},
            import_run_id=RUN_ID,
        )
        for unit_key in all_keys
    )
    claims = {
        "CLM-ARENA-DEF": ["ev113"],
        "CLM-ARENA-01": ["ev114"],
        "CLM-ARENA-02": ["ev115"],
    }
    session.add_all(
        Claim(
            claim_id=claim_id,
            module="arena",
            server="TW",
            claim_text="單一玩家貼出的精確五人戰果",
            claim_type="SINGLE_REPORT",
            claim_confidence="D",
            independence_check="SINGLE_SOURCE",
            version_match="EXACT",
            status="ACTIVE",
            verified_date=today,
            next_review_due=date(2026, 8, 23),
            affected_files="39_ARENA_COUNTER_REGISTRY.csv",
            notes="僅供參考",
            declared_evidence_ids=evidence_ids,
            source_payload={},
            import_run_id=RUN_ID,
        )
        for claim_id, evidence_ids in claims.items()
    )
    session.flush()
    evidence_claims = {
        "ev113": "CLM-ARENA-DEF",
        "ev114": "CLM-ARENA-01",
        "ev115": "CLM-ARENA-02",
    }
    session.add_all(
        Evidence(
            evidence_id=evidence_id,
            declared_claim_id=claim_id,
            linked_claim_id=claim_id,
            module="arena",
            server="TW",
            source_tier="SINGLE_PLAYER_REPORT",
            evidence_confidence="D",
            source_title="巴哈姆特 Arena 單筆戰果",
            source_url=f"https://example.test/{evidence_id}",
            source_locator="正文截圖",
            published_date=date(2026, 5, 25),
            published_date_precision="DAY",
            verified_date=today,
            claim_summary="完整五人與勝利畫面",
            limitations="單一來源、單一樣本，不代表可重現性。",
            affected_files="39_ARENA_COUNTER_REGISTRY.csv",
            status="ACTIVE",
            source_payload={},
            import_run_id=RUN_ID,
        )
        for evidence_id, claim_id in evidence_claims.items()
    )
    session.add_all(
        Evidence(
            evidence_id=f"ev-official-{unit_key}",
            declared_claim_id=None,
            linked_claim_id=None,
            module="availability",
            server="TW",
            source_tier="OFFICIAL",
            evidence_confidence="A",
            source_title=f"台服官方角色公告 {TW_NAMES[unit_key]}",
            source_url=f"https://example.test/official/{unit_key}",
            source_locator=f"official-{unit_key}",
            published_date=date(2026, 1, 1),
            published_date_precision="DAY",
            verified_date=today,
            claim_summary="台服官方名稱與 AVAILABLE 狀態",
            limitations="只證明台服官方名稱與已實裝。",
            affected_files="18_TW_CHARACTER_AVAILABILITY.csv",
            status="ACTIVE",
            source_payload={},
            import_run_id=RUN_ID,
        )
        for unit_key in all_keys
        if unit_key != JP_FUTURE_KEY
    )
    defense_id = "TW-2026-05-25:" + arena_formation_signature(DEFENSE_KEYS)
    session.add(
        ArenaDefense(
            defense_id=defense_id,
            server="TW",
            formation_signature=arena_formation_signature(DEFENSE_KEYS),
            environment_version="TW-2026-05-25",
            arena_bracket="UNKNOWN",
            core_tags=[],
            status="SINGLE_REPORT",
            review_status="CURRENT",
            verified_date=today,
            notes="單一來源防守",
            source_payload={},
            import_run_id=RUN_ID,
        )
    )
    session.flush()
    session.add_all(
        ArenaDefenseMember(defense_id=defense_id, slot=slot, unit_key=unit_key)
        for slot, unit_key in enumerate(DEFENSE_KEYS, 1)
    )
    for counter_id, member_keys, evidence_ids, claim_ids in (
        ("TW_ARENA_20260525_01", COUNTER_ONE_KEYS, ["ev113", "ev114"], ["CLM-ARENA-DEF", "CLM-ARENA-01"]),
        ("TW_ARENA_20260525_02", counter_two_keys, ["ev113", "ev115"], ["CLM-ARENA-DEF", "CLM-ARENA-02"]),
    ):
        session.add(
            ArenaCounter(
                counter_id=counter_id,
                defense_id=defense_id,
                formation_signature=arena_formation_signature(member_keys),
                status="SINGLE_REPORT",
                match_type="EXACT",
                outcome="WIN",
                verification="SCREENSHOT_RESULT",
                sample_size=1,
                wins=1,
                losses=0,
                empirical_win_rate=None,
                randomness="UNKNOWN（原樓主稱網站測試有贏也有輸）",
                rng_risk="UNKNOWN",
                claim_confidence="D",
                reproducibility="UNVERIFIED_REPEATABILITY",
                source_tier="SINGLE_PLAYER_REPORT",
                source_record_count=1,
                source_platforms=["巴哈姆特"],
                tw_availability_check=(
                    "FAIL" if JP_FUTURE_KEY in member_keys else "PASS"
                ),
                unavailable_unit_ids=(
                    [JP_FUTURE_KEY] if JP_FUTURE_KEY in member_keys else []
                ),
                required_upgrade_check="UNKNOWN",
                operation_mode="UNKNOWN",
                environment_match="UNKNOWN",
                speed_conditions="UNKNOWN",
                initial_action_notes="UNKNOWN",
                verified_date=today,
                last_review_due=date(2026, 8, 23),
                record_date_min=date(2026, 5, 25),
                record_date_max=date(2026, 5, 25),
                notes="僅供參考",
                source_payload={},
                import_run_id=RUN_ID,
            )
        )
        session.flush()
        session.add_all(
            ArenaCounterMember(counter_id=counter_id, slot=slot, unit_key=unit_key)
            for slot, unit_key in enumerate(member_keys, 1)
        )
        session.add_all(
            ArenaCounterEvidence(counter_id=counter_id, evidence_id=evidence_id)
            for evidence_id in evidence_ids
        )
        session.add_all(
            ArenaCounterClaim(counter_id=counter_id, claim_id=claim_id)
            for claim_id in claim_ids
        )


def _client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    include_arena: bool,
    materialization_version: int,
    include_jp_future: bool = False,
) -> TestClient:
    factory = _factory(
        include_arena=include_arena,
        materialization_version=materialization_version,
        include_jp_future=include_jp_future,
    )

    return _client_for_factory(monkeypatch, factory)


def _client_for_factory(
    monkeypatch: pytest.MonkeyPatch,
    factory: sessionmaker[Session],
) -> TestClient:

    def ready(session: Session):
        return session.get(ImportRun, RUN_ID), SimpleNamespace(
            revision_id=HASH,
            raw_tree_sha256=HASH,
            semantic_tree_sha256=HASH,
            materialization_sha256=HASH,
        )

    monkeypatch.setattr(v1_routes, "_run_or_503", ready)
    return TestClient(
        create_app(
            settings=Settings(database_url="sqlite://", application_version="3.0.0-a5"),
            session_factory=factory,
        )
    )


def test_pvp_returns_typed_exact_single_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(monkeypatch, include_arena=True, materialization_version=3) as client:
        response = client.get("/api/v1/pvp/counters")

    assert response.status_code == 200
    payload = response.json()
    assert [row["counter_id"] for row in payload["data"]] == [
        "TW_ARENA_20260525_01",
        "TW_ARENA_20260525_02",
    ]
    assert payload["meta"]["warnings"] == [
        "NO_VERIFIED_COUNTER",
        "SINGLE_REPORT_REFERENCE_ONLY",
    ]
    assert payload["meta"]["server"] == "TW"
    assert payload["meta"]["environment_version"] == "TW-2026-05-25"
    assert payload["meta"]["verified_at"] is None
    assert payload["meta"]["stale_status"] == "UNKNOWN"
    assert payload["meta"]["confidence"] == "UNKNOWN"
    assert payload["meta"]["evidence_ids"] == ["ev113", "ev114", "ev115"]
    assert payload["meta"]["claim_ids"] == [
        "CLM-ARENA-01",
        "CLM-ARENA-02",
        "CLM-ARENA-DEF",
    ]
    assert payload["meta"]["data_revision"] == HASH
    for row in payload["data"]:
        assert row["status"] == "SINGLE_REPORT"
        assert row["claim_confidence"] == "D"
        assert row["match_type"] == "EXACT"
        assert row["reproducibility"] == "UNVERIFIED_REPEATABILITY"
        assert row["tw_availability_check"] == "PASS"
        assert row["unavailable_unit_ids"] == []
        assert len(row["defense_members"]) == 5
        assert len({member["unit_key"] for member in row["defense_members"]}) == 5
        assert len(row["counter_members"]) == 5
        assert len({member["unit_key"] for member in row["counter_members"]}) == 5
        assert len(row["evidence_ids"]) == 2
        assert len(row["claim_ids"]) == 2
        assert all("tw_name" not in member for member in row["defense_members"])
        assert all(
            member["display_name_source"] == "TW_OFFICIAL"
            for member in [*row["defense_members"], *row["counter_members"]]
        )


def test_pvp_character_options_exclude_not_released_and_are_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _client(
        monkeypatch,
        include_arena=True,
        materialization_version=3,
        include_jp_future=True,
    ) as client:
        response = client.get("/api/v1/pvp/characters")

    assert response.status_code == 200
    payload = response.json()
    assert JP_FUTURE_KEY not in {row["unit_key"] for row in payload["data"]}
    assert all(
        row["tw_availability_status"] == "AVAILABLE" for row in payload["data"]
    )
    assert [
        (row["tw_name"], row["unit_key"]) for row in payload["data"]
    ] == sorted((row["tw_name"], row["unit_key"]) for row in payload["data"])
    assert payload["meta"]["server"] == "TW"
    assert payload["meta"]["environment_version"] == "UNKNOWN"
    assert payload["meta"]["verified_at"] is None
    assert payload["meta"]["stale_status"] == "UNKNOWN"
    assert payload["meta"]["confidence"] == "UNKNOWN"
    assert payload["meta"]["evidence_ids"] == sorted(
        f"ev-official-{row['unit_key']}" for row in payload["data"]
    )
    assert payload["meta"]["claim_ids"] == []


def test_tw_available_picker_character_without_official_name_fails_closed() -> None:
    factory = _factory(include_arena=True, materialization_version=3)
    with factory() as session:
        character = session.get(Character, DEFENSE_KEYS[0])
        assert character is not None
        character.tw_name = "UNKNOWN"
        session.flush()
        with pytest.raises(RuntimeError, match="no stored official name"):
            pvp_character_options(session)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_tier", "COMMUNITY_WIKI"),
        ("status", "PENDING_REVIEW"),
    ],
)
def test_pvp_character_picker_rejects_weak_or_inactive_referenced_evidence(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    factory = _factory(include_arena=True, materialization_version=3)
    with factory() as session:
        evidence = session.get(Evidence, f"ev-official-{DEFENSE_KEYS[0]}")
        assert evidence is not None
        setattr(evidence, field, value)
        session.commit()

    with _client_for_factory(monkeypatch, factory) as client:
        response = client.get("/api/v1/pvp/characters")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "FIXTURE_DRIFT",
            "resource": "pvp_characters",
            "id": None,
            "reason": "character_serving_closure_invalid",
        }
    }


def test_pvp_character_picker_rejects_missing_referenced_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = _factory(include_arena=True, materialization_version=3)
    with factory() as session:
        character = session.get(Character, DEFENSE_KEYS[0])
        assert character is not None
        character.source_evidence_ids = ["ev-does-not-exist"]
        session.commit()

    with _client_for_factory(monkeypatch, factory) as client:
        response = client.get("/api/v1/pvp/characters")

    assert response.status_code == 503
    assert response.json()["detail"]["reason"] == "character_serving_closure_invalid"


def test_pvp_character_picker_evidence_query_count_is_constant() -> None:
    factory = _factory(include_arena=True, materialization_version=3)
    statements: list[str] = []

    def track_query(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    with factory() as session:
        bind = session.get_bind()
        event.listen(bind, "before_cursor_execute", track_query)
        try:
            characters, _records = pvp_character_options(session)
        finally:
            event.remove(bind, "before_cursor_execute", track_query)

    assert len(characters) == len(TW_NAMES)
    assert len(statements) == 2


def test_pvp_counter_meta_does_not_infer_freshness_or_confidence_from_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = _factory(include_arena=True, materialization_version=3)
    with factory() as session:
        defense = session.scalar(select(ArenaDefense))
        claim = session.get(Claim, "CLM-ARENA-DEF")
        assert defense is not None
        assert claim is not None
        defense.verified_date = date(2026, 7, 1)
        claim.claim_confidence = "E"
        session.commit()

    with _client_for_factory(monkeypatch, factory) as client:
        response = client.get("/api/v1/pvp/counters")

    assert response.status_code == 200
    meta = response.json()["meta"]
    assert meta["server"] == "TW"
    assert meta["environment_version"] == "TW-2026-05-25"
    assert meta["evidence_ids"] == ["ev113", "ev114", "ev115"]
    assert meta["claim_ids"] == [
        "CLM-ARENA-01",
        "CLM-ARENA-02",
        "CLM-ARENA-DEF",
    ]
    assert meta["verified_at"] is None
    assert meta["stale_status"] == "UNKNOWN"
    assert meta["confidence"] == "UNKNOWN"


def test_conservative_response_metadata_uses_complete_closure_only() -> None:
    aggregate = conservative_response_metadata(
        [
            ResponseMetaRecord(
                server="TW",
                environment_version="TW-1",
                verified_at=date(2026, 8, 8),
                stale_status="CURRENT",
                confidence="B",
                evidence_ids=("ev-b", "ev-a"),
                claim_ids=("clm-b",),
            ),
            ResponseMetaRecord(
                server="JP",
                environment_version="TW-1",
                verified_at=date(2026, 8, 7),
                stale_status="STALE",
                confidence="D",
                evidence_ids=("ev-a", "ev-c"),
                claim_ids=("clm-a",),
            ),
        ]
    )

    assert aggregate == {
        "server": "MIXED",
        "environment_version": "TW-1",
        "verified_at": date(2026, 8, 7),
        "stale_status": "STALE",
        "confidence": "D",
        "evidence_ids": ["ev-a", "ev-b", "ev-c"],
        "claim_ids": ["clm-a", "clm-b"],
    }
    unknown = conservative_response_metadata(
        [
            ResponseMetaRecord(
                server="TW",
                environment_version="TW-1",
                verified_at=date(2026, 8, 8),
                stale_status="CURRENT",
                confidence="B",
            ),
            ResponseMetaRecord(server="TW"),
        ]
    )
    assert unknown["environment_version"] == "UNKNOWN"
    assert unknown["verified_at"] is None
    assert unknown["stale_status"] == "UNKNOWN"
    assert unknown["confidence"] == "UNKNOWN"


def test_not_released_member_helper_uses_stored_jp_official_name() -> None:
    assert _arena_display_name(
        unit_key=JP_FUTURE_KEY,
        availability="NOT_RELEASED",
        tw_name="【待查證】",
        jp_name=JP_FUTURE_NAME,
    ) == (JP_FUTURE_NAME, "JP_OFFICIAL")


def test_fail_availability_row_is_not_published(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(
        monkeypatch,
        include_arena=True,
        materialization_version=3,
        include_jp_future=True,
    ) as client:
        response = client.get("/api/v1/pvp/counters")

    assert response.status_code == 200
    assert [row["counter_id"] for row in response.json()["data"]] == [
        "TW_ARENA_20260525_01"
    ]
    assert all(
        member["unit_key"] != JP_FUTURE_KEY
        for row in response.json()["data"]
        for member in row["counter_members"]
    )


def test_arena_member_without_any_stored_official_name_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="no stored official display name"):
        _arena_display_name(
            unit_key="missing_name_unit",
            availability="NOT_RELEASED",
            tw_name="UNKNOWN",
            jp_name="【待查證】",
        )


def test_available_member_without_tw_official_name_does_not_fallback_to_jp() -> None:
    with pytest.raises(RuntimeError, match="no stored official display name"):
        _arena_display_name(
            unit_key="available_but_unmapped",
            availability="AVAILABLE",
            tw_name="UNKNOWN",
            jp_name="保存済み日本語名",
        )


def test_verified_arena_serving_closure_requires_independent_result_sources() -> None:
    counter = SimpleNamespace(
        status="VERIFIED",
        outcome="WIN",
        verification="SCREENSHOT_RESULT",
        claim_confidence="C",
        reproducibility="CONFIRMED",
        source_tier="MULTI_PLAYER_REPORT",
        source_record_count=2,
        sample_size=2,
        wins=2,
        environment_match="EXACT",
    )
    claim = SimpleNamespace(
        status="ACTIVE",
        module="arena",
        server="TW",
        claim_type="SOURCE_FACT",
        claim_confidence="C",
        independence_check="YES",
        version_match="YES",
    )
    evidence_by_id = {
        "ev-a": SimpleNamespace(
            status="ACTIVE",
            module="arena",
            server="TW",
            declared_claim_id="CLM-RESULT",
            source_tier="SINGLE_PLAYER_REPORT",
            source_url="https://forum.gamer.com.tw/a",
            source_locator="record-a",
            source_title="source-a",
        ),
        "ev-b": SimpleNamespace(
            status="ACTIVE",
            module="arena",
            server="TW",
            declared_claim_id="CLM-RESULT",
            source_tier="SINGLE_PLAYER_REPORT",
            source_url="https://gamewith.jp/b",
            source_locator="record-b",
            source_title="source-b",
        ),
    }
    kwargs = {
        "evidence_ids": ["ev-a", "ev-b"],
        "claim_ids": ["CLM-RESULT"],
        "evidence_by_id": evidence_by_id,
        "claim_by_id": {"CLM-RESULT": claim},
        "claim_evidence_ids": {"CLM-RESULT": ["ev-a", "ev-b"]},
    }

    assert _arena_verified_serving_closure_is_mature(counter, **kwargs)

    uppercase_claim = SimpleNamespace(**vars(claim))
    uppercase_claim.module = "ARENA"
    assert not _arena_verified_serving_closure_is_mature(
        counter,
        **{**kwargs, "claim_by_id": {"CLM-RESULT": uppercase_claim}},
    )

    uppercase_evidence = dict(evidence_by_id)
    uppercase_evidence["ev-b"] = SimpleNamespace(
        **{**vars(evidence_by_id["ev-b"]), "module": "ARENA"}
    )
    assert not _arena_verified_serving_closure_is_mature(
        counter,
        **{**kwargs, "evidence_by_id": uppercase_evidence},
    )

    blank_url_evidence = dict(evidence_by_id)
    blank_url_evidence["ev-b"] = SimpleNamespace(
        **{**vars(evidence_by_id["ev-b"]), "source_url": ""}
    )
    assert not _arena_verified_serving_closure_is_mature(
        counter,
        **{**kwargs, "evidence_by_id": blank_url_evidence},
    )

    weak_counter = SimpleNamespace(**vars(counter))
    weak_counter.source_record_count = 1
    assert not _arena_verified_serving_closure_is_mature(weak_counter, **kwargs)

    mismatched_counter = SimpleNamespace(**vars(counter))
    mismatched_counter.environment_match = "MISMATCH"
    assert not _arena_verified_serving_closure_is_mature(mismatched_counter, **kwargs)

    invented_tier_counter = SimpleNamespace(**vars(counter))
    invented_tier_counter.source_tier = "FAKE_STRONG"
    assert not _arena_verified_serving_closure_is_mature(
        invented_tier_counter,
        **kwargs,
    )

    same_host_evidence = dict(evidence_by_id)
    same_host_evidence["ev-b"] = SimpleNamespace(
        **{
            **vars(evidence_by_id["ev-b"]),
            "source_url": "https://forum.gamer.com.tw/b",
        }
    )
    assert not _arena_verified_serving_closure_is_mature(
        counter,
        **{**kwargs, "evidence_by_id": same_host_evidence},
    )

    invented_evidence_tier = dict(evidence_by_id)
    invented_evidence_tier["ev-b"] = SimpleNamespace(
        **{
            **vars(evidence_by_id["ev-b"]),
            "source_tier": "FAKE_STRONG",
        }
    )
    assert not _arena_verified_serving_closure_is_mature(
        counter,
        **{**kwargs, "evidence_by_id": invented_evidence_tier},
    )


@pytest.mark.parametrize(
    "repository_error",
    [
        "invalid Arena formation closure: broken-counter",
        "Arena member has no stored official display name: broken-unit",
    ],
)
def test_arena_repository_runtime_drift_is_structured_503(
    monkeypatch: pytest.MonkeyPatch,
    repository_error: str,
) -> None:
    with _client(
        monkeypatch,
        include_arena=True,
        materialization_version=3,
    ) as client:
        def fail_repository(*_args, **_kwargs):
            raise RuntimeError(repository_error)

        monkeypatch.setattr(v1_routes, "arena_counter_results", fail_repository)
        response = client.get("/api/v1/pvp/counters")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "FIXTURE_DRIFT",
            "resource": "arena_materialization",
            "id": None,
            "reason": "arena_serving_closure_invalid",
        }
    }


def test_arena_repository_query_count_is_constant() -> None:
    factory = _factory(include_arena=True, materialization_version=3)
    statements: list[str] = []

    def track_query(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    with factory() as session:
        bind = session.get_bind()
        event.listen(bind, "before_cursor_execute", track_query)
        try:
            counters = arena_counter_results(session)
        finally:
            event.remove(bind, "before_cursor_execute", track_query)

    assert len(counters) == 2
    assert len(statements) == 5


def test_pvp_exact_lookup_is_order_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(monkeypatch, include_arena=True, materialization_version=3) as client:
        response = client.get(
            "/api/v1/pvp/counters",
            params={"defense_signature": ";".join(reversed(DEFENSE_KEYS))},
        )

    assert response.status_code == 200
    assert len(response.json()["data"]) == 2


def test_pvp_four_of_five_does_not_fallback_to_similar(monkeypatch: pytest.MonkeyPatch) -> None:
    four_of_five = [*DEFENSE_KEYS[:4], "kaya_orig"]
    with _client(monkeypatch, include_arena=True, materialization_version=3) as client:
        response = client.get(
            "/api/v1/pvp/counters",
            params={"defense_signature": ";".join(four_of_five)},
        )

    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["warnings"] == [
        "NO_EXACT_COUNTER",
        "NO_VERIFIED_COUNTER",
    ]
    assert response.json()["meta"]["server"] == "UNKNOWN"
    assert response.json()["meta"]["environment_version"] == "UNKNOWN"
    assert response.json()["meta"]["verified_at"] is None
    assert response.json()["meta"]["stale_status"] == "UNKNOWN"
    assert response.json()["meta"]["confidence"] == "UNKNOWN"
    assert response.json()["meta"]["evidence_ids"] == []
    assert response.json()["meta"]["claim_ids"] == []


@pytest.mark.parametrize(
    "signature",
    [
        ";".join(DEFENSE_KEYS[:4]),
        ";".join([*DEFENSE_KEYS[:4], DEFENSE_KEYS[0]]),
        ";".join([*DEFENSE_KEYS, "kaya_orig"]),
    ],
)
def test_pvp_rejects_malformed_defense_signature(
    monkeypatch: pytest.MonkeyPatch,
    signature: str,
) -> None:
    with _client(monkeypatch, include_arena=True, materialization_version=3) as client:
        response = client.get(
            "/api/v1/pvp/counters",
            params={"defense_signature": signature},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_DEFENSE_SIGNATURE"


def test_pvp_legacy_materialization_is_explicitly_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _client(monkeypatch, include_arena=False, materialization_version=2) as client:
        response = client.get("/api/v1/pvp/counters")

    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["warnings"] == [
        "NO_ARENA_MATERIALIZATION",
        "NO_VERIFIED_COUNTER",
    ]
