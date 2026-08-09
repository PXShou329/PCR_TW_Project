from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from pcr_database.materialization import MATERIALIZATION_MANIFEST_VERSION, SERVING_MODELS
from pcr_database.models import Base, OperationTimeline, TeamMember, TimelineStep
from pcr_pipeline.pve_fixture import import_fire_8_10


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_CORE = ROOT / "research_core" / "pcr_tw_project"


def imported_engine():
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
    with Session(engine) as session:
        import_fire_8_10(session, RESEARCH_CORE)
    return engine


def test_v0006_is_the_single_migration_head() -> None:
    config = Config("database/alembic.ini")
    script = ScriptDirectory.from_config(config)

    assert script.get_current_head() == "v0006_arena_counter_slice"
    revision = script.get_revision("v0006_arena_counter_slice")
    assert revision is not None
    assert revision.down_revision == "v0005_borrowed_tristate"
    revision = script.get_revision("v0005_borrowed_tristate")
    assert revision is not None
    assert revision.down_revision == "v0004_unknown_operation_mode"
    revision = script.get_revision("v0004_unknown_operation_mode")
    assert revision is not None
    assert revision.down_revision == "v0003_core_revision_mirror"
    revision = script.get_revision("v0003_core_revision_mirror")
    assert revision is not None
    assert revision.down_revision == "v0002_operation_timelines"
    previous = script.get_revision("v0002_operation_timelines")
    assert previous is not None
    assert previous.down_revision == "v0001_b0_read_mirror"


def test_v0002_offline_postgres_sql_contains_both_additive_tables(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv(
        "PCR_DATABASE_URL",
        "postgresql+psycopg://migration_test:unused@localhost:5432/pcr_tw",
    )
    command.upgrade(Config("database/alembic.ini"), "head", sql=True)
    sql = capsys.readouterr().out

    assert "CREATE TABLE operation_timelines" in sql
    assert "CREATE TABLE timeline_steps" in sql
    assert "source_axis_id VARCHAR(140) NOT NULL" in sql
    assert "timeline_id VARCHAR(140)" in sql
    assert "time_state VARCHAR(20) NOT NULL" in sql
    assert "ALTER TABLE operation_timelines DROP CONSTRAINT" in sql
    assert "'UNKNOWN'" in sql
    assert "ALTER TABLE team_members ALTER COLUMN is_borrowed DROP NOT NULL" in sql
    assert "DROP TABLE" not in sql


def test_v0005_offline_downgrade_fails_closed_without_coercing_borrowed_state(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv(
        "PCR_DATABASE_URL",
        "postgresql+psycopg://migration_test:unused@localhost:5432/pcr_tw",
    )
    command.downgrade(
        Config("database/alembic.ini"),
        "v0005_borrowed_tristate:v0004_unknown_operation_mode",
        sql=True,
    )
    sql = capsys.readouterr().out

    assert "ALTER TABLE team_members ALTER COLUMN is_borrowed SET NOT NULL" in sql
    assert "UPDATE team_members" not in sql
    assert "DELETE FROM team_members" not in sql


def test_v0004_offline_downgrade_preserves_unknown_as_a_validated_blocker(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv(
        "PCR_DATABASE_URL",
        "postgresql+psycopg://migration_test:unused@localhost:5432/pcr_tw",
    )
    command.downgrade(
        Config("database/alembic.ini"),
        "v0004_unknown_operation_mode:v0003_core_revision_mirror",
        sql=True,
    )
    sql = capsys.readouterr().out

    assert "operation_mode IN ('AUTO','SEMI_AUTO','MANUAL_TIMELINE')" in sql
    assert "'UNKNOWN'" not in sql
    assert "UPDATE operation_timelines" not in sql
    assert "DELETE FROM operation_timelines" not in sql


def test_orm_and_materialization_cover_the_source_axis_tables() -> None:
    timeline = OperationTimeline.__table__
    step = TimelineStep.__table__
    member = TeamMember.__table__

    assert [column.name for column in timeline.primary_key.columns] == ["source_axis_id"]
    assert timeline.c.timeline_id.nullable is True
    assert step.c.timeline_id.nullable is False
    assert step.c.time_state.nullable is False
    assert member.c.is_borrowed.nullable is True
    assert MATERIALIZATION_MANIFEST_VERSION == 3
    assert {model.__tablename__ for model in SERVING_MODELS} >= {
        "operation_timelines",
        "timeline_steps",
    }


def test_database_rejects_gap_identity_strengthening() -> None:
    engine = imported_engine()
    with Session(engine) as session:
        with pytest.raises(IntegrityError):
            session.execute(
                update(OperationTimeline)
                .where(OperationTimeline.source_axis_id == "AX-F810-01-EV050")
                .values(timeline_id="TL-INVENTED")
            )
            session.commit()


def test_database_preserves_unknown_source_operation_mode() -> None:
    engine = imported_engine()
    with Session(engine) as session:
        timeline = session.get(OperationTimeline, "AX-F810-04-EV082")
        assert timeline is not None
        assert timeline.status == "SOURCE_GAP"
        assert timeline.operation_mode == "UNKNOWN"


def test_database_rejects_not_stated_step_with_a_clock() -> None:
    engine = imported_engine()
    with Session(engine) as session:
        with pytest.raises(IntegrityError):
            session.execute(
                update(TimelineStep)
                .where(TimelineStep.timeline_step_id == "TLS-F810-02-001")
                .values(clock_from_ms=90000, clock_to_ms=90000)
            )
            session.commit()


def test_database_rejects_actor_from_another_team() -> None:
    engine = imported_engine()
    with Session(engine) as session:
        with pytest.raises(IntegrityError):
            session.execute(
                update(TimelineStep)
                .where(TimelineStep.timeline_step_id == "TLS-F810-02-005")
                .values(actor_unit_key="maho_summer")
            )
            session.commit()
