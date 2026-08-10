from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from pcr_database.materialization import (
    ARENA_MATERIALIZATION_MANIFEST_VERSION,
    ARENA_MATERIALIZATION_SERVING_MODELS,
    GACHA_MATERIALIZATION_MANIFEST_VERSION,
    GACHA_SERVING_MODELS,
    MATERIALIZATION_MANIFEST_VERSION,
    build_materialization_manifest,
)
from pcr_database.models import (
    Base,
    GachaCommunitySource,
    GachaTimelineClaim,
    GachaTimelineCommunitySource,
    GachaTimelineEvent,
    GachaTimelineEvidence,
    ImportRun,
)


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "00000000-0000-0000-0000-000000000701"


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


def import_run() -> ImportRun:
    return ImportRun(
        id=RUN_ID,
        fixture_sha256="7" * 64,
        canonical_source="research_core_file_ssot",
        research_core_version="v1.5",
        application_version="3.0.0-b5",
        imported_at=datetime.now(timezone.utc),
        status="RUNNING",
        manifest={},
        row_counts={},
    )


def gacha_event(**overrides) -> GachaTimelineEvent:
    values = {
        "event_id": "JP_20260815_vampy_summer",
        "source_server": "JP",
        "target_server": "TW",
        "jp_date": date(2026, 8, 15),
        "model_estimate_start": date(2026, 12, 15),
        "model_estimate_end": date(2026, 12, 17),
        "tw_estimate_start": date(2026, 12, 15),
        "tw_estimate_end": date(2026, 12, 17),
        "forecast_method": "MODEL_ONLY",
        "confidence": "低（研究列）",
        "character_name_jp": "ヴァンピィ（サマー）",
        "tw_name": None,
        "pool_type": "8.5 Year Anniversary ガチャ",
        "limited_status": "UNKNOWN",
        "limited_claim_id": None,
        "arena_value": "NOT_EVALUATED",
        "p_arena_value": "NOT_EVALUATED",
        "pve_value": "NOT_EVALUATED",
        "clan_value": "NOT_EVALUATED",
        "future_upgrade": "UNKNOWN",
        "relative_priority": "NOT_EVALUATED",
        "anchor_track": "ALL_NEW",
        "anchor_count": 7,
        "forecast_basis": "canonical anchors",
        "last_verified": date(2026, 8, 9),
        "status": "ACTIVE",
        "maturity": "RESEARCH",
        "last_review_due": date(2026, 8, 31),
        "community_estimate_start": None,
        "community_estimate_end": None,
        "community_order_consensus": "",
        "community_source_count": 0,
        "community_last_checked": None,
        "community_disagreement": "",
        "forecast_notes": "source truth retained",
        "source_payload": {"tw_temp_name": "【待查證】"},
        "import_run_id": RUN_ID,
    }
    values.update(overrides)
    return GachaTimelineEvent(**values)


def community_source(**overrides) -> GachaCommunitySource:
    values = {
        "source_id": "GACHA-COMM-TEST",
        "title": "pytest",
        "platform": "Bahamut",
        "author": "pytest",
        "source_type": "FORUM_TIMELINE",
        "url": "https://forum.gamer.com.tw/example",
        "last_seen_update": date(2026, 8, 1),
        "coverage_start": "2026-01",
        "coverage_end": "2026-12-01",
        "update_status": "CHECKED",
        "confidence_cap": "D",
        "usage": "source order only",
        "last_checked": date(2026, 8, 9),
        "notes": "pytest",
        "source_payload": {"confidence_cap": "D"},
        "import_run_id": RUN_ID,
    }
    values.update(overrides)
    return GachaCommunitySource(**values)


def test_v0007_is_head_and_offline_sql_is_additive_and_fail_closed(
    monkeypatch,
    capsys,
) -> None:
    config = Config(str(ROOT / "database" / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    assert script.get_current_head() == "v0008_parena_planner_slice"
    assert script.get_revision("v0007_gacha_timeline_slice").down_revision == (
        "v0006_arena_counter_slice"
    )

    monkeypatch.setenv(
        "PCR_DATABASE_URL",
        "postgresql+psycopg://migration_test:unused@localhost:5432/pcr_tw",
    )
    command.upgrade(config, "head", sql=True)
    sql = capsys.readouterr().out
    for model in GACHA_SERVING_MODELS:
        table_name = model.__tablename__
        assert f"CREATE TABLE {table_name}" in sql
        assert f"trg_{table_name}_materialization_epoch" in sql
    assert "source_server = 'JP'" in sql
    assert "target_server = 'TW'" in sql
    assert "MODEL_PLUS_COMMUNITY" in sql
    assert "maturity != 'RESEARCH'" in sql
    assert "limited_status = 'UNKNOWN' AND limited_claim_id IS NULL" in sql
    assert "FOREIGN KEY(evidence_id) REFERENCES evidence (evidence_id)" in sql
    assert "FOREIGN KEY(claim_id) REFERENCES claims (claim_id)" in sql
    assert "FOREIGN KEY(limited_claim_id) REFERENCES claims (claim_id)" in sql

    command.downgrade(
        config,
        "v0007_gacha_timeline_slice:v0006_arena_counter_slice",
        sql=True,
    )
    downgrade_sql = capsys.readouterr().out
    assert "pg_advisory_xact_lock(344726848049)" in downgrade_sql
    lock_names = tuple(
        reversed(tuple(model.__tablename__ for model in GACHA_SERVING_MODELS))
    )
    lock_positions = [
        downgrade_sql.index(f'LOCK TABLE "{table_name}" IN ACCESS EXCLUSIVE MODE')
        for table_name in lock_names
    ]
    assert lock_positions == sorted(lock_positions)
    assert 'LOCK TABLE "materialization_state" IN ACCESS EXCLUSIVE MODE' in downgrade_sql
    assert 'LOCK TABLE "core_revisions" IN SHARE MODE' in downgrade_sql
    assert 'LOCK TABLE "import_runs" IN SHARE MODE' in downgrade_sql
    owner_guard = downgrade_sql.index(
        "refusing V0007 downgrade unless a verified Arena v3 materialization owns the mirror"
    )
    row_guard = downgrade_sql.index(
        "refusing V0007 downgrade while Gacha serving rows exist"
    )
    assert lock_positions[-1] < owner_guard < row_guard
    assert "active_run_status IS DISTINCT FROM 'SUCCEEDED'" in downgrade_sql
    assert "active_revision_status IS DISTINCT FROM 'SUCCEEDED'" in downgrade_sql
    assert "IS DISTINCT FROM '3'" in downgrade_sql
    assert "revision_materialization_sha256" in downgrade_sql
    assert "state_row.materialization_sha256" in downgrade_sql
    assert ") <> 18" in downgrade_sql
    assert "state_row.serving_counts ?& ARRAY[" in downgrade_sql
    assert "jsonb_array_length(" in downgrade_sql
    assert row_guard < downgrade_sql.index("DROP TABLE gacha_timeline_community_sources")
    assert downgrade_sql.index("DROP TABLE gacha_timeline_evidence") < (
        downgrade_sql.index("DROP TABLE gacha_timeline_events")
    )


def test_gacha_orm_contract_and_manifest_v3_replay_boundary() -> None:
    assert GACHA_MATERIALIZATION_MANIFEST_VERSION == 4
    assert MATERIALIZATION_MANIFEST_VERSION == 5
    assert {model.__tablename__ for model in GACHA_SERVING_MODELS} == {
        "gacha_timeline_events",
        "gacha_timeline_evidence",
        "gacha_timeline_claims",
        "gacha_community_sources",
        "gacha_timeline_community_sources",
    }
    assert [
        column.name for column in GachaTimelineEvidence.__table__.primary_key.columns
    ] == ["event_id", "evidence_id"]
    assert [
        column.name for column in GachaTimelineClaim.__table__.primary_key.columns
    ] == ["event_id", "claim_id"]
    assert [
        column.name
        for column in GachaTimelineCommunitySource.__table__.primary_key.columns
    ] == ["event_id", "source_id"]
    assert GachaCommunitySource.__table__.c.coverage_start.type.length == 10
    assert GachaTimelineEvent.__table__.c.limited_claim_id.nullable is True
    assert {
        foreign_key.target_fullname
        for foreign_key in GachaTimelineEvent.__table__.c.limited_claim_id.foreign_keys
    } == {"claims.claim_id"}

    v3_shape = {
        "schema_version": ARENA_MATERIALIZATION_MANIFEST_VERSION,
        "tables": {
            model.__tablename__: {} for model in ARENA_MATERIALIZATION_SERVING_MODELS
        },
    }
    engine = sqlite_engine()
    with Session(engine) as session:
        replay = build_materialization_manifest(session, expected_manifest=v3_shape)
    assert replay["schema_version"] == ARENA_MATERIALIZATION_MANIFEST_VERSION
    assert set(replay["tables"]) == {
        model.__tablename__ for model in ARENA_MATERIALIZATION_SERVING_MODELS
    }

    with Session(engine) as session:
        session.add(import_run())
        session.flush()
        session.add(gacha_event())
        session.flush()
        current = build_materialization_manifest(session, expected_manifest=v3_shape)
    assert current["schema_version"] == MATERIALIZATION_MANIFEST_VERSION
    assert "gacha_timeline_events" in current["tables"]


def test_v0007_downgrade_rejects_active_v4_even_when_gacha_rows_are_empty(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv(
        "PCR_DATABASE_URL",
        "postgresql+psycopg://migration_test:unused@localhost:5432/pcr_tw",
    )
    command.downgrade(
        Config(str(ROOT / "database" / "alembic.ini")),
        "v0007_gacha_timeline_slice:v0006_arena_counter_slice",
        sql=True,
    )
    sql = capsys.readouterr().out

    # Ownership is evaluated before table emptiness.  Therefore a v4 active
    # pointer fails on the exact-v3 predicate even after manual row deletion.
    v3_predicate = sql.index("IS DISTINCT FROM '3'")
    owner_rejection = sql.index(
        "refusing V0007 downgrade unless a verified Arena v3 materialization owns the mirror"
    )
    empty_row_guard = sql.index(
        "refusing V0007 downgrade while Gacha serving rows exist"
    )
    assert v3_predicate < owner_rejection < empty_row_guard


@pytest.mark.parametrize(
    "changes",
    (
        {"source_server": "TW"},
        {"target_server": "JP"},
        {"limited_status": "YES_INFERRED"},
        {"limited_status": "YES", "limited_claim_id": None},
        {"limited_status": "UNKNOWN", "limited_claim_id": "CL-MISSING"},
        {"limited_status": "YES", "limited_claim_id": "CL-MISSING"},
        {"maturity": "RESEARCH", "pve_value": "高"},
        {"tw_estimate_start": date(2026, 12, 18)},
        {"community_source_count": 1},
    ),
)
def test_gacha_event_row_local_constraints_fail_closed(changes) -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        session.add(import_run())
        session.flush()
        session.add(gacha_event(**changes))
        with pytest.raises(IntegrityError):
            session.commit()


@pytest.mark.parametrize("confidence_cap", ("A", "B", "UNKNOWN"))
def test_gacha_community_confidence_cap_matches_research_validator(
    confidence_cap: str,
) -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        session.add(import_run())
        session.flush()
        session.add(community_source(confidence_cap=confidence_cap))
        with pytest.raises(IntegrityError):
            session.commit()
