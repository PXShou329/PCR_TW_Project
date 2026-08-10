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
    ARENA_SERVING_MODELS,
    LEGACY_MATERIALIZATION_MANIFEST_VERSION,
    LEGACY_SERVING_MODELS,
    MATERIALIZATION_MANIFEST_VERSION,
    SERVING_MODELS,
    build_materialization_manifest,
    materialization_drift_reason,
)
from pcr_database.models import (
    ArenaCounter,
    ArenaCounterClaim,
    ArenaCounterEvidence,
    ArenaCounterMember,
    ArenaDefense,
    ArenaDefenseMember,
    Base,
    Character,
    ImportRun,
    arena_formation_signature,
)


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "00000000-0000-0000-0000-000000000601"
HASH_A = "a" * 64


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


def import_run(run_id: str = RUN_ID) -> ImportRun:
    return ImportRun(
        id=run_id,
        fixture_sha256=HASH_A,
        canonical_source="research_core_file_ssot",
        research_core_version="v1.5",
        application_version="3.0.0-b3",
        imported_at=datetime.now(timezone.utc),
        status="RUNNING",
        manifest={},
        row_counts={},
    )


def character(unit_key: str, *, run_id: str = RUN_ID) -> Character:
    return Character(
        unit_key=unit_key,
        tw_name=unit_key,
        jp_name=unit_key,
        version="ORIGINAL",
        tw_release_date=None,
        availability_status="AVAILABLE",
        ue1_status="UNKNOWN",
        ue2_status="UNKNOWN",
        six_star_status="UNKNOWN",
        connect_rank_status="UNKNOWN",
        element="UNKNOWN",
        source_evidence_ids=[],
        last_verified=date(2026, 8, 8),
        last_review_due=None,
        notes="pytest",
        source_payload={"unit_key": unit_key},
        import_run_id=run_id,
    )


def defense(*, defense_id: str = "AD-TW-001", run_id: str = RUN_ID) -> ArenaDefense:
    members = [f"defense_{slot}" for slot in range(1, 6)]
    return ArenaDefense(
        defense_id=defense_id,
        server="TW",
        formation_signature=arena_formation_signature(members),
        environment_version="UNKNOWN",
        arena_bracket="UNKNOWN",
        core_tags=[],
        status="PROVISIONAL",
        review_status="CURRENT",
        verified_date=date(2026, 8, 8),
        notes="pytest",
        source_payload={"defense_id": defense_id},
        import_run_id=run_id,
    )


def counter(*, counter_id: str = "AC-TW-001", defense_id: str = "AD-TW-001") -> ArenaCounter:
    members = [f"counter_{slot}" for slot in range(1, 6)]
    return ArenaCounter(
        counter_id=counter_id,
        defense_id=defense_id,
        formation_signature=arena_formation_signature(members),
        status="SINGLE_REPORT",
        match_type="EXACT",
        outcome="WIN",
        verification="SCREENSHOT_RESULT",
        sample_size=1,
        wins=1,
        losses=0,
        empirical_win_rate=None,
        randomness="UNKNOWN（single observed result）",
        rng_risk="UNKNOWN",
        claim_confidence="D",
        reproducibility="UNVERIFIED_REPEATABILITY",
        source_tier="SINGLE_PLAYER_REPORT",
        source_record_count=1,
        source_platforms=["Bahamut"],
        tw_availability_check="PASS",
        unavailable_unit_ids=[],
        required_upgrade_check="UNKNOWN",
        operation_mode="AUTO_SYSTEM",
        environment_match="EXACT",
        speed_conditions="UNKNOWN",
        initial_action_notes="UNKNOWN",
        verified_date=date(2026, 8, 8),
        last_review_due=date(2026, 8, 23),
        record_date_min=date(2026, 5, 25),
        record_date_max=date(2026, 5, 25),
        notes="pytest",
        source_payload={"counter_id": counter_id},
        import_run_id=RUN_ID,
    )


def legacy_manifest_shape() -> dict[str, object]:
    return {
        "schema_version": LEGACY_MATERIALIZATION_MANIFEST_VERSION,
        "tables": {model.__tablename__: {} for model in LEGACY_SERVING_MODELS},
    }


def test_v0006_remains_in_chain_and_offline_sql_contains_normalized_arena_schema(
    monkeypatch,
    capsys,
) -> None:
    config = Config(str(ROOT / "database" / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    assert script.get_current_head() == "v0008_parena_planner_slice"
    revision = script.get_revision("v0006_arena_counter_slice")
    assert revision is not None
    assert revision.down_revision == "v0005_borrowed_tristate"

    monkeypatch.setenv(
        "PCR_DATABASE_URL",
        "postgresql+psycopg://migration_test:unused@localhost:5432/pcr_tw",
    )
    command.upgrade(config, "head", sql=True)
    sql = capsys.readouterr().out

    for table_name in (
        "arena_defenses",
        "arena_defense_members",
        "arena_counters",
        "arena_counter_members",
        "arena_counter_evidence",
        "arena_counter_claims",
    ):
        assert f"CREATE TABLE {table_name}" in sql
        assert f"trg_{table_name}_materialization_epoch" in sql
    assert "FOREIGN KEY(unit_key) REFERENCES characters (unit_key)" in sql
    assert "FOREIGN KEY(evidence_id) REFERENCES evidence (evidence_id)" in sql
    assert "FOREIGN KEY(claim_id) REFERENCES claims (claim_id)" in sql
    assert "FOREIGN KEY(import_run_id) REFERENCES import_runs (id)" in sql
    assert "UNIQUE (server, environment_version, formation_signature)" in sql
    assert "UNIQUE (defense_id, formation_signature)" in sql
    assert "slot BETWEEN 1 AND 5" in sql
    assert "sample_size = wins + losses" in sql
    assert "sample_size IS NULL AND wins IS NULL AND losses IS NULL" in sql
    assert "outcome != 'WIN' OR (wins IS NOT NULL AND wins >= 1)" in sql
    assert "empirical_win_rate IS NULL OR" in sql
    assert "sample_size >= 2" in sql
    assert "status != 'SINGLE_REPORT' OR empirical_win_rate IS NULL" in sql
    assert "claim_confidence IN ('B','C','D','E')" in sql
    assert "status != 'SINGLE_REPORT' OR claim_confidence = 'D'" in sql
    assert "status != 'VERIFIED' OR claim_confidence IN ('B','C')" in sql
    assert "status != 'VERIFIED' OR reproducibility = 'CONFIRMED'" in sql
    assert "source_tier IN ('OFFICIAL','MAJOR_GUIDE','STRUCTURED_DB'" in sql
    assert "source_record_count >= 2" in sql
    assert "sample_size IS NOT NULL AND sample_size >= 2" in sql
    assert "wins IS NOT NULL AND wins >= 2" in sql
    assert "environment_match = 'EXACT'" in sql
    assert "CONFIRMED" in sql
    assert "UNVERIFIED_ON_TW" in sql
    assert "UNVERIFIED_REPEATABILITY" in sql
    assert "source_record_count >= 1" in sql
    assert "record_date_min <= record_date_max" in sql


def test_v0006_downgrade_is_empty_only_and_fk_safe(monkeypatch, capsys) -> None:
    monkeypatch.setenv(
        "PCR_DATABASE_URL",
        "postgresql+psycopg://migration_test:unused@localhost:5432/pcr_tw",
    )
    command.downgrade(
        Config(str(ROOT / "database" / "alembic.ini")),
        "v0006_arena_counter_slice:v0005_borrowed_tristate",
        sql=True,
    )
    sql = capsys.readouterr().out

    assert "pg_advisory_xact_lock(344726848049)" in sql
    lock_names = (
        "arena_counter_claims",
        "arena_counter_evidence",
        "arena_counter_members",
        "arena_counters",
        "arena_defense_members",
        "arena_defenses",
    )
    lock_positions = [
        sql.index(f'LOCK TABLE "{table_name}" IN ACCESS EXCLUSIVE MODE')
        for table_name in lock_names
    ]
    assert lock_positions == sorted(lock_positions)
    owner_guard = sql.index(
        "refusing V0006 downgrade unless a verified legacy v2 materialization owns the mirror"
    )
    assert sql.index("schema_version", lock_positions[-1]) < owner_guard
    assert sql.index("materialization_sha256", lock_positions[-1]) < owner_guard
    assert "active_revision_status IS DISTINCT FROM 'SUCCEEDED'" in sql
    assert "IS DISTINCT FROM 'object'" in sql
    assert "FROM jsonb_object_keys(" in sql
    assert "ELSE '{}'::jsonb" in sql
    assert "jsonb_object_length" not in sql
    assert "?& ARRAY[" in sql
    for legacy_table in (
        "stages",
        "teams",
        "team_members",
        "characters",
        "evidence",
        "claims",
        "stage_evidence",
        "stage_claims",
        "team_evidence",
        "claim_evidence",
        "operation_timelines",
        "timeline_steps",
    ):
        assert f"'{legacy_table}'" in sql[lock_positions[-1] : owner_guard]
    assert "refusing V0006 downgrade while Arena serving rows exist" in sql
    row_guard = sql.index("refusing V0006 downgrade while Arena serving rows exist")
    assert lock_positions[-1] < owner_guard < row_guard
    assert row_guard < sql.index("DROP TABLE arena_counter_claims")
    assert sql.index("DROP TABLE arena_counter_claims") < sql.index(
        "DROP TABLE arena_counters"
    )
    assert sql.index("DROP TABLE arena_counter_members") < sql.index(
        "DROP TABLE arena_counters"
    )
    assert sql.index("DROP TABLE arena_counters") < sql.index(
        "DROP TABLE arena_defenses"
    )
    assert sql.index("DROP TABLE arena_defense_members") < sql.index(
        "DROP TABLE arena_defenses"
    )


def test_arena_signatures_are_order_insensitive_and_require_five_unique_members() -> None:
    members = ["unit_e", "unit_b", "unit_d", "unit_a", "unit_c"]
    expected = "unit_a;unit_b;unit_c;unit_d;unit_e"

    assert arena_formation_signature(members) == expected
    assert arena_formation_signature(reversed(members)) == expected
    with pytest.raises(ValueError, match="exactly five"):
        arena_formation_signature(members[:4])
    with pytest.raises(ValueError, match="unique"):
        arena_formation_signature(["unit_a"] * 5)
    with pytest.raises(ValueError, match="non-empty"):
        arena_formation_signature(["unit_a", "unit_b", "unit_c", "unit_d", " "])


def test_arena_orm_contract_has_normalized_fks_and_materialization_closure() -> None:
    assert [column.name for column in ArenaDefenseMember.__table__.primary_key.columns] == [
        "defense_id",
        "slot",
    ]
    assert [column.name for column in ArenaCounterMember.__table__.primary_key.columns] == [
        "counter_id",
        "slot",
    ]
    assert [column.name for column in ArenaCounterEvidence.__table__.primary_key.columns] == [
        "counter_id",
        "evidence_id",
    ]
    assert [column.name for column in ArenaCounterClaim.__table__.primary_key.columns] == [
        "counter_id",
        "claim_id",
    ]
    assert ARENA_MATERIALIZATION_MANIFEST_VERSION == 3
    assert GACHA_MATERIALIZATION_MANIFEST_VERSION == 4
    assert MATERIALIZATION_MANIFEST_VERSION == 5
    assert {model.__tablename__ for model in ARENA_MATERIALIZATION_SERVING_MODELS} == {
        *(model.__tablename__ for model in LEGACY_SERVING_MODELS),
        *(model.__tablename__ for model in ARENA_SERVING_MODELS),
    }
    assert set(ARENA_MATERIALIZATION_SERVING_MODELS) < set(SERVING_MODELS)
    assert {model.__tablename__ for model in ARENA_SERVING_MODELS} == {
        "arena_defenses",
        "arena_defense_members",
        "arena_counters",
        "arena_counter_members",
        "arena_counter_evidence",
        "arena_counter_claims",
    }
    assert {
        "status",
        "verified_date",
        "randomness",
        "rng_risk",
        "source_tier",
        "source_record_count",
        "source_platforms",
        "tw_availability_check",
        "unavailable_unit_ids",
        "required_upgrade_check",
        "record_date_min",
        "record_date_max",
        "last_review_due",
        "source_payload",
    } <= set(ArenaCounter.__table__.c.keys())
    assert "result_status" not in ArenaCounter.__table__.c


def test_arena_members_enforce_slot_and_unique_unit() -> None:
    engine = sqlite_engine()
    defense_units = [f"defense_{slot}" for slot in range(1, 6)]
    with Session(engine) as session:
        session.add(import_run())
        session.flush()
        session.add_all(character(unit_key) for unit_key in defense_units)
        session.add(defense())
        session.flush()
        session.add_all(
            ArenaDefenseMember(defense_id="AD-TW-001", slot=slot, unit_key=unit_key)
            for slot, unit_key in enumerate(defense_units, start=1)
        )
        session.commit()

    with Session(engine) as session:
        session.add(
            ArenaDefenseMember(
                defense_id="AD-TW-001",
                slot=6,
                unit_key="defense_1",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()

    with Session(engine) as session:
        session.add(
            ArenaDefenseMember(
                defense_id="AD-TW-001",
                slot=5,
                unit_key="defense_1",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_counter_count_shape_and_single_report_rate_fail_closed() -> None:
    engine = sqlite_engine()
    all_units = [
        *(f"defense_{slot}" for slot in range(1, 6)),
        *(f"counter_{slot}" for slot in range(1, 6)),
    ]
    with Session(engine) as session:
        session.add(import_run())
        session.flush()
        session.add_all(character(unit_key) for unit_key in all_units)
        session.add(defense())
        session.flush()
        session.add(counter())
        session.commit()

    with Session(engine) as session:
        counts_unstated = counter(counter_id="AC-TW-SAMPLE-ONLY")
        counts_unstated.formation_signature = arena_formation_signature(
            ["counter_1", "counter_2", "counter_3", "counter_4", "defense_1"]
        )
        counts_unstated.status = "PROVISIONAL"
        counts_unstated.outcome = "UNKNOWN"
        counts_unstated.sample_size = 7
        counts_unstated.wins = None
        counts_unstated.losses = None
        with pytest.raises(IntegrityError):
            session.add(counts_unstated)
            session.commit()

    with Session(engine) as session:
        counts_fully_unstated = counter(counter_id="AC-TW-NO-SAMPLE")
        counts_fully_unstated.formation_signature = "no-sample"
        counts_fully_unstated.status = "PROVISIONAL"
        counts_fully_unstated.outcome = "UNKNOWN"
        counts_fully_unstated.sample_size = None
        counts_fully_unstated.wins = None
        counts_fully_unstated.losses = None
        session.add(counts_fully_unstated)
        session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-BAD-COUNT")
        invalid.sample_size = 2
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-BAD-CONFIDENCE")
        invalid.claim_confidence = "B"
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-BAD-SINGLE-E")
        invalid.claim_confidence = "E"
        invalid.formation_signature = "single-report-e"
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-BAD-CONFIDENCE-A")
        invalid.status = "PROVISIONAL"
        invalid.claim_confidence = "A"
        invalid.formation_signature = "provisional-a"
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-BAD-VERIFIED")
        invalid.status = "VERIFIED"
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-BAD-REPRODUCIBILITY")
        invalid.status = "PROVISIONAL"
        invalid.claim_confidence = "B"
        invalid.reproducibility = "TW_REPRODUCED"
        invalid.formation_signature = "timeline-only-reproducibility"
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    with Session(engine) as session:
        verified = counter(counter_id="AC-TW-CONFIRMED")
        verified.status = "VERIFIED"
        verified.claim_confidence = "C"
        verified.reproducibility = "CONFIRMED"
        verified.source_tier = "MULTI_PLAYER_REPORT"
        verified.source_record_count = 2
        verified.source_platforms = ["source-a", "source-b"]
        verified.sample_size = 2
        verified.wins = 2
        verified.losses = 0
        verified.formation_signature = "verified-and-confirmed"
        session.add(verified)
        session.commit()

    invalid_verified_values = (
        ("confidence", {"claim_confidence": "D"}),
        ("source-tier", {"source_tier": "SINGLE_PLAYER_REPORT"}),
        ("invented-source-tier", {"source_tier": "FAKE_STRONG"}),
        ("source-count", {"source_record_count": 1}),
        ("sample-count", {"sample_size": 1, "wins": 1, "losses": 0}),
        ("winning-sources", {"sample_size": 2, "wins": 1, "losses": 1}),
        ("outcome", {"outcome": "MIXED"}),
        ("verification", {"verification": "UNKNOWN"}),
        ("environment-match", {"environment_match": "MISMATCH"}),
    )
    for suffix, changes in invalid_verified_values:
        with Session(engine) as session:
            invalid = counter(counter_id=f"AC-TW-VERIFIED-{suffix.upper()}")
            invalid.status = "VERIFIED"
            invalid.claim_confidence = "C"
            invalid.reproducibility = "CONFIRMED"
            invalid.source_tier = "MULTI_PLAYER_REPORT"
            invalid.source_record_count = 2
            invalid.sample_size = 2
            invalid.wins = 2
            invalid.losses = 0
            invalid.formation_signature = f"verified-invalid-{suffix}"
            for field, value in changes.items():
                setattr(invalid, field, value)
            with pytest.raises(IntegrityError):
                session.add(invalid)
                session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-BAD-VERIFIED-E")
        invalid.status = "VERIFIED"
        invalid.claim_confidence = "E"
        invalid.reproducibility = "CONFIRMED"
        invalid.formation_signature = "verified-e"
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-BAD-RATE")
        invalid.empirical_win_rate = 100
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-SINGLE-REPORT-RATE")
        invalid.sample_size = 2
        invalid.wins = 2
        invalid.losses = 0
        invalid.empirical_win_rate = 100
        invalid.formation_signature = "single-report-rate"
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-WIN-WITH-ZERO-WINS")
        invalid.sample_size = 1
        invalid.wins = 0
        invalid.losses = 1
        invalid.formation_signature = "win-with-zero-wins"
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-RATE-WITHOUT-SAMPLE")
        invalid.sample_size = None
        invalid.wins = None
        invalid.losses = None
        invalid.empirical_win_rate = 50
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-NO-SOURCE")
        invalid.source_record_count = 0
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    with Session(engine) as session:
        invalid = counter(counter_id="AC-TW-INVERTED-DATES")
        invalid.record_date_min = date(2026, 5, 26)
        invalid.record_date_max = date(2026, 5, 25)
        with pytest.raises(IntegrityError):
            session.add(invalid)
            session.commit()

    for field in ("last_review_due", "record_date_min", "record_date_max"):
        with Session(engine) as session:
            invalid = counter(counter_id=f"AC-TW-NULL-{field.upper()}")
            invalid.formation_signature = f"null-{field}"
            setattr(invalid, field, None)
            with pytest.raises(IntegrityError):
                session.add(invalid)
                session.commit()


def test_defense_and_counter_signatures_are_unique_in_their_scope() -> None:
    engine = sqlite_engine()
    all_units = [
        *(f"defense_{slot}" for slot in range(1, 6)),
        *(f"counter_{slot}" for slot in range(1, 6)),
    ]
    with Session(engine) as session:
        session.add(import_run())
        session.flush()
        session.add_all(character(unit_key) for unit_key in all_units)
        session.add(defense())
        session.flush()
        session.add(counter())
        session.commit()

    with Session(engine) as session:
        duplicate_defense = defense(defense_id="AD-TW-DUPLICATE")
        session.add(duplicate_defense)
        with pytest.raises(IntegrityError):
            session.commit()

    with Session(engine) as session:
        duplicate_counter = counter(counter_id="AC-TW-DUPLICATE")
        session.add(duplicate_counter)
        with pytest.raises(IntegrityError):
            session.commit()


def test_counter_evidence_and_claim_require_canonical_rows() -> None:
    engine = sqlite_engine()
    all_units = [
        *(f"defense_{slot}" for slot in range(1, 6)),
        *(f"counter_{slot}" for slot in range(1, 6)),
    ]
    with Session(engine) as session:
        session.add(import_run())
        session.flush()
        session.add_all(character(unit_key) for unit_key in all_units)
        session.add(defense())
        session.flush()
        session.add(counter())
        session.flush()
        session.add_all(
            [
                ArenaCounterEvidence(counter_id="AC-TW-001", evidence_id="EV-MISSING"),
                ArenaCounterClaim(counter_id="AC-TW-001", claim_id="CL-MISSING"),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_legacy_manifest_recomputes_only_while_arena_tables_are_empty() -> None:
    engine = sqlite_engine()
    legacy_shape = legacy_manifest_shape()
    with Session(engine) as session:
        legacy = build_materialization_manifest(
            session,
            expected_manifest=legacy_shape,
        )
        replay = build_materialization_manifest(
            session,
            expected_manifest=legacy,
        )

    assert legacy["schema_version"] == LEGACY_MATERIALIZATION_MANIFEST_VERSION
    assert set(legacy["tables"]) == {
        model.__tablename__ for model in LEGACY_SERVING_MODELS
    }
    assert replay == legacy
    assert materialization_drift_reason(legacy, replay) is None


def test_persisted_legacy_run_is_auto_detected_for_reactivation_digest() -> None:
    engine = sqlite_engine()
    legacy_shape = legacy_manifest_shape()
    with Session(engine) as session:
        run = import_run()
        session.add(run)
        session.flush()
        session.add(character("legacy_unit"))
        session.flush()
        legacy = build_materialization_manifest(
            session,
            expected_manifest=legacy_shape,
        )
        run.manifest = {"materialization": legacy}
        run.status = "SUCCEEDED"
        session.commit()

    with Session(engine) as session:
        replay = build_materialization_manifest(session)

    assert replay == legacy
    assert replay["schema_version"] == LEGACY_MATERIALIZATION_MANIFEST_VERSION


def test_legacy_manifest_cannot_ignore_unprotected_arena_rows() -> None:
    engine = sqlite_engine()
    legacy_shape = legacy_manifest_shape()
    defense_units = [f"defense_{slot}" for slot in range(1, 6)]
    with Session(engine) as session:
        run = import_run()
        session.add(run)
        session.flush()
        session.add_all(character(unit_key) for unit_key in defense_units)
        session.add(defense())
        session.flush()

        actual = build_materialization_manifest(
            session,
            expected_manifest=legacy_shape,
        )

    assert actual["schema_version"] == MATERIALIZATION_MANIFEST_VERSION
    assert "arena_defenses" in actual["tables"]
    assert materialization_drift_reason(legacy_shape, actual) is not None
