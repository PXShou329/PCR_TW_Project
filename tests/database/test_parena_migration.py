from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from pcr_database.materialization import (
    GACHA_MATERIALIZATION_MANIFEST_VERSION,
    GACHA_MATERIALIZATION_SERVING_MODELS,
    MATERIALIZATION_MANIFEST_VERSION,
    PARENA_SERVING_MODELS,
    SERVING_MODELS,
    build_materialization_manifest,
    materialization_drift_reason,
)
from pcr_database.models import (
    ArenaSourceRecord,
    Base,
    Character,
    ImportRun,
    ParenaCaseMatchup,
)


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "00000000-0000-0000-0000-000000000801"


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


def test_v0008_is_additive_head_with_exact_v4_downgrade_guard(monkeypatch, capsys) -> None:
    config = Config(str(ROOT / "database" / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    assert script.get_current_head() == "v0008_parena_planner_slice"
    assert script.get_revision("v0008_parena_planner_slice").down_revision == (
        "v0007_gacha_timeline_slice"
    )
    monkeypatch.setenv(
        "PCR_DATABASE_URL",
        "postgresql+psycopg://migration_test:unused@localhost:5432/pcr_tw",
    )
    command.upgrade(config, "head", sql=True)
    sql = capsys.readouterr().out
    for model in PARENA_SERVING_MODELS:
        assert f"CREATE TABLE {model.__tablename__}" in sql
        assert f"trg_{model.__tablename__}_materialization_epoch" in sql
    assert "uq_arena_counters_counter_defense" in sql
    assert "fk_parena_case_matchups_counter_defense" in sql
    assert "case_win_confidence IN ('B','C','D')" in sql
    assert "access_status IN ('ACTIVE','PARTIAL','BLOCKED','STALE','ARCHIVED')" in sql
    assert "confidence_cap IN ('C','D','E')" in sql

    command.downgrade(
        config,
        "v0008_parena_planner_slice:v0007_gacha_timeline_slice",
        sql=True,
    )
    downgrade = capsys.readouterr().out
    row_guard = downgrade.index(
        "refusing V0008 downgrade while P-Arena serving rows exist"
    )
    owner_guard = downgrade.index(
        "refusing V0008 downgrade unless an exact active v4 materialization owns the mirror"
    )
    assert row_guard < owner_guard
    assert "IS DISTINCT FROM '4'" in downgrade
    assert ") <> 23" in downgrade
    assert "DROP TABLE parena_case_claims" in downgrade
    assert downgrade.index("DROP TABLE parena_case_matchups") < downgrade.index(
        "DROP TABLE parena_cases"
    )
    assert downgrade.index("DROP TABLE arena_source_records") < downgrade.index(
        "DROP CONSTRAINT uq_arena_counters_counter_defense"
    )


def test_v4_replay_is_exact_and_any_v5_row_forces_the_full_closure() -> None:
    assert GACHA_MATERIALIZATION_MANIFEST_VERSION == 4
    assert MATERIALIZATION_MANIFEST_VERSION == 5
    assert len(GACHA_MATERIALIZATION_SERVING_MODELS) == 23
    assert len(SERVING_MODELS) == 29
    assert {model.__tablename__ for model in PARENA_SERVING_MODELS} == {
        "arena_source_records",
        "parena_cases",
        "parena_case_matchups",
        "parena_case_sources",
        "parena_case_evidence",
        "parena_case_claims",
    }
    assert [column.name for column in ParenaCaseMatchup.__table__.primary_key.columns] == [
        "case_id",
        "matchup_no",
    ]

    v4_shape = {
        "schema_version": GACHA_MATERIALIZATION_MANIFEST_VERSION,
        "tables": {
            model.__tablename__: {} for model in GACHA_MATERIALIZATION_SERVING_MODELS
        },
    }
    engine = sqlite_engine()
    with Session(engine) as session:
        replay = build_materialization_manifest(session, expected_manifest=v4_shape)
        assert replay["schema_version"] == 4
        session.add(
            ImportRun(
                id=RUN_ID,
                fixture_sha256="8" * 64,
                canonical_source="research_core_file_ssot",
                research_core_version="v1.5",
                application_version="3.0.0-b4",
                imported_at=datetime.now(timezone.utc),
                status="RUNNING",
                manifest={},
                row_counts={},
            )
        )
        session.flush()
        session.add(
            ArenaSourceRecord(
                source_id="ARENA-SRC-TEST",
                title="pytest",
                platform="pytest",
                source_type="FORUM_THREAD",
                server="TW",
                url="https://forum.gamer.com.tw/example",
                last_checked=date(2026, 8, 10),
                freshness_window="90d",
                access_status="ACTIVE",
                confidence_cap="D",
                extraction_method="pytest",
                notes="pytest",
                source_payload={"source_id": "ARENA-SRC-TEST"},
                import_run_id=RUN_ID,
            )
        )
        session.flush()
        current = build_materialization_manifest(session, expected_manifest=v4_shape)
        assert current["schema_version"] == 5
    assert set(current["tables"]) == {model.__tablename__ for model in SERVING_MODELS}


def test_v4_replay_skips_absent_v5_tables_but_recomputes_the_v4_closure() -> None:
    v4_shape = {
        "schema_version": GACHA_MATERIALIZATION_MANIFEST_VERSION,
        "tables": {
            model.__tablename__: {} for model in GACHA_MATERIALIZATION_SERVING_MODELS
        },
    }
    engine = sqlite_engine()
    with Session(engine) as session:
        run = ImportRun(
            id=RUN_ID,
            fixture_sha256="8" * 64,
            canonical_source="research_core_file_ssot",
            research_core_version="v1.5",
            application_version="3.0.0-b4",
            imported_at=datetime.now(timezone.utc),
            status="RUNNING",
            manifest={},
            row_counts={},
        )
        session.add(run)
        session.flush()
        session.add(
            Character(
                unit_key="legacy_v4_unit",
                tw_name="legacy_v4_unit",
                jp_name="legacy_v4_unit",
                version="ORIGINAL",
                tw_release_date=None,
                availability_status="AVAILABLE",
                ue1_status="UNKNOWN",
                ue2_status="UNKNOWN",
                six_star_status="UNKNOWN",
                connect_rank_status="UNKNOWN",
                element="UNKNOWN",
                source_evidence_ids=[],
                last_verified=date(2026, 8, 10),
                last_review_due=None,
                notes="before downgrade",
                source_payload={"unit_key": "legacy_v4_unit"},
                import_run_id=RUN_ID,
            )
        )
        session.flush()
        expected = build_materialization_manifest(session, expected_manifest=v4_shape)
        run.manifest = {"materialization": expected}
        run.status = "SUCCEEDED"
        session.commit()

    for model in reversed(PARENA_SERVING_MODELS):
        model.__table__.drop(engine)

    with Session(engine) as session:
        replay = build_materialization_manifest(session)
        assert replay == expected

        character = session.get(Character, "legacy_v4_unit")
        assert character is not None
        character.notes = "drift after downgrade"
        session.flush()
        drifted = build_materialization_manifest(
            session,
            expected_manifest=expected,
        )

    assert drifted["schema_version"] == GACHA_MATERIALIZATION_MANIFEST_VERSION
    assert set(drifted["tables"]) == {
        model.__tablename__ for model in GACHA_MATERIALIZATION_SERVING_MODELS
    }
    assert drifted["tables"]["characters"] != expected["tables"]["characters"]
    assert (
        materialization_drift_reason(expected, drifted)
        == "materialization_characters_drift"
    )


@pytest.mark.parametrize(
    ("access_status", "confidence_cap"),
    [
        ("ACTIVE", "C"),
        ("PARTIAL", "D"),
        ("BLOCKED", "E"),
        ("STALE", "C"),
        ("ARCHIVED", "D"),
    ],
)
def test_arena_source_model_accepts_exact_canonical_enums(
    access_status: str,
    confidence_cap: str,
) -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        session.add(
            ImportRun(
                id=RUN_ID,
                fixture_sha256="8" * 64,
                canonical_source="research_core_file_ssot",
                research_core_version="v1.5",
                application_version="3.0.0-b4",
                imported_at=datetime.now(timezone.utc),
                status="RUNNING",
                manifest={},
                row_counts={},
            )
        )
        session.flush()
        session.add(
            ArenaSourceRecord(
                source_id="ARENA-SRC-ENUM",
                title="pytest",
                platform="pytest",
                source_type="FORUM_THREAD",
                server="TW",
                url="https://forum.gamer.com.tw/example",
                last_checked=date(2026, 8, 10),
                freshness_window="90d",
                access_status=access_status,
                confidence_cap=confidence_cap,
                extraction_method="pytest",
                notes="pytest",
                source_payload={},
                import_run_id=RUN_ID,
            )
        )
        session.commit()


@pytest.mark.parametrize(
    ("access_status", "confidence_cap"),
    [
        ("REJECTED", "D"),
        ("UNKNOWN", "D"),
        ("ACTIVE", "A"),
        ("ACTIVE", "B"),
        ("ACTIVE", "UNKNOWN"),
    ],
)
def test_arena_source_model_rejects_noncanonical_enums(
    access_status: str,
    confidence_cap: str,
) -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        session.add(
            ImportRun(
                id=RUN_ID,
                fixture_sha256="8" * 64,
                canonical_source="research_core_file_ssot",
                research_core_version="v1.5",
                application_version="3.0.0-b4",
                imported_at=datetime.now(timezone.utc),
                status="RUNNING",
                manifest={},
                row_counts={},
            )
        )
        session.flush()
        session.add(
            ArenaSourceRecord(
                source_id="ARENA-SRC-ENUM",
                title="pytest",
                platform="pytest",
                source_type="FORUM_THREAD",
                server="TW",
                url="https://forum.gamer.com.tw/example",
                last_checked=date(2026, 8, 10),
                freshness_window="90d",
                access_status=access_status,
                confidence_cap=confidence_cap,
                extraction_method="pytest",
                notes="pytest",
                source_payload={},
                import_run_id=RUN_ID,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
