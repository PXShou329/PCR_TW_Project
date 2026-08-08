from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from pcr_database.materialization import SERVING_MODELS
from pcr_database.models import (
    Base,
    CoreCsvRow,
    CoreFile,
    CoreRevision,
    ImmutableCoreRevisionError,
    ImmutableImportRunError,
    ImmutableMaterializationStateError,
    ImmutableRevisionActivationError,
    ImportRun,
    MaterializationState,
    NonMonotonicMaterializationEpochError,
    RevisionActivation,
)


ROOT = Path(__file__).resolve().parents[2]
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
EXPECTED_EPOCH_TABLES = {
    "import_runs",
    *(model.__tablename__ for model in SERVING_MODELS),
    "core_revisions",
    "core_files",
    "core_csv_rows",
}


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


def revision(**overrides) -> CoreRevision:
    values = {
        "revision_id": HASH_A,
        "raw_tree_sha256": HASH_A,
        "semantic_tree_sha256": HASH_B,
        "manifest_sha256": HASH_C,
        "materialization_sha256": None,
        "file_count": 48,
        "csv_file_count": 13,
        "csv_row_count": 215,
        "evidence_to_claim_count": 75,
        "evidence_to_claim_sha256": HASH_C,
        "claim_to_evidence_count": 162,
        "claim_to_evidence_sha256": HASH_D,
        "status": "STAGING",
        "manifest": {"schema_version": 1},
        "project_version": "v1.5",
        "serialization_version": 1,
    }
    values.update(overrides)
    return CoreRevision(**values)


def import_run(run_id: str, fixture_sha256: str) -> ImportRun:
    return ImportRun(
        id=run_id,
        fixture_sha256=fixture_sha256,
        canonical_source="research_core_file_ssot",
        research_core_version="v1.5",
        application_version="3.0.0-b1",
        imported_at=datetime.now(timezone.utc),
        status="RUNNING",
        manifest={},
        row_counts={},
    )


def test_v0003_offline_sql_is_additive_and_installs_epoch_guards(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv(
        "PCR_DATABASE_URL",
        "postgresql+psycopg://migration_test:unused@localhost:5432/pcr_tw",
    )
    command.upgrade(Config(str(ROOT / "database" / "alembic.ini")), "head", sql=True)
    sql = capsys.readouterr().out

    for table in (
        "core_revisions",
        "core_files",
        "core_csv_rows",
        "materialization_state",
        "revision_activations",
    ):
        assert f"CREATE TABLE {table}" in sql
    assert "VALUES (1, 0, '{}'::jsonb, CURRENT_TIMESTAMP)" in sql
    assert sql.count("EXECUTE FUNCTION pcr_bump_materialization_epoch()") == len(
        EXPECTED_EPOCH_TABLES
    )
    for table in EXPECTED_EPOCH_TABLES:
        assert f'trg_{table}_materialization_epoch' in sql
    assert "FOR EACH STATEMENT EXECUTE FUNCTION pcr_bump_materialization_epoch()" in sql
    assert "revision_activations is append-only" in sql
    assert "kind IN ('IMPORT','ROLLBACK','REACTIVATE')" in sql
    assert "materialization_state singleton cannot be deleted" in sql
    assert "materialization_state epoch must strictly increase" in sql
    assert "trg_materialization_state_epoch_monotonic" in sql
    assert "EXECUTE FUNCTION pcr_require_monotonic_materialization_epoch()" in sql
    assert "import runs must be inserted in RUNNING status" in sql
    assert "terminal import run % is immutable" in sql
    assert "trg_import_runs_history_guard" in sql
    assert "EXECUTE FUNCTION pcr_guard_import_run_history()" in sql
    assert "core revisions must be inserted in STAGING status" in sql
    assert "terminal core revision % is immutable" in sql
    assert "artifact revision % is not mutable STAGING data" in sql
    assert sql.count("FOR SHARE") >= 2
    assert "UNIQUE (revision_id, import_run_id)" in sql
    assert (
        "FOREIGN KEY(active_revision_id, active_import_run_id) "
        "REFERENCES core_revisions (revision_id, import_run_id)"
    ) in sql
    assert "DROP TABLE" not in sql


def test_v0003_downgrade_drops_guards_and_tables_in_dependency_order(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv(
        "PCR_DATABASE_URL",
        "postgresql+psycopg://migration_test:unused@localhost:5432/pcr_tw",
    )
    command.downgrade(
        Config(str(ROOT / "database" / "alembic.ini")),
        "v0003_core_revision_mirror:v0002_operation_timelines",
        sql=True,
    )
    sql = capsys.readouterr().out

    assert "DROP FUNCTION IF EXISTS pcr_bump_materialization_epoch()" in sql
    assert "DROP FUNCTION IF EXISTS pcr_guard_core_artifact_history()" in sql
    assert "DROP FUNCTION IF EXISTS pcr_guard_core_revision_history()" in sql
    assert "DROP FUNCTION IF EXISTS pcr_guard_import_run_history()" in sql
    assert "DROP TRIGGER IF EXISTS trg_import_runs_history_guard ON import_runs" in sql
    assert (
        "DROP FUNCTION IF EXISTS pcr_require_monotonic_materialization_epoch()"
        in sql
    )
    assert "DROP TRIGGER IF EXISTS trg_materialization_state_epoch_monotonic" in sql
    assert "SELECT active_import_run_id" in sql
    assert "WHERE status = 'SUCCEEDED'" in sql
    assert "latest_succeeded_at + INTERVAL '1 microsecond'" in sql
    assert "active run % is not SUCCEEDED" in sql
    assert "DROP TABLE revision_activations" in sql
    assert "DROP TABLE materialization_state" in sql
    assert "DROP TABLE core_csv_rows" in sql
    assert "DROP TABLE core_files" in sql
    assert "DROP TABLE core_revisions" in sql
    assert sql.index("DROP TABLE core_csv_rows") < sql.index("DROP TABLE core_files")
    assert sql.index("DROP TABLE core_files") < sql.index("DROP TABLE core_revisions")
    assert sql.index("DROP TRIGGER IF EXISTS trg_import_runs_history_guard") < sql.index(
        "SELECT active_import_run_id"
    )
    assert sql.index("SELECT active_import_run_id") < sql.index(
        "DROP TABLE materialization_state"
    )


def test_downgrade_reconciliation_projects_active_run_as_legacy_latest() -> None:
    """Model the V0002 query after an A -> B -> A activation history."""

    engine = sqlite_engine()
    run_a_id = "00000000-0000-0000-0000-000000000101"
    run_b_id = "00000000-0000-0000-0000-000000000102"
    revision_b_id = "e" * 64
    imported_a = datetime(2026, 8, 8, 1, 0, tzinfo=timezone.utc)
    imported_b = datetime(2026, 8, 8, 2, 0, tzinfo=timezone.utc)

    def legacy_latest(session: Session) -> ImportRun | None:
        return session.scalar(
            select(ImportRun)
            .where(ImportRun.status == "SUCCEEDED")
            .order_by(ImportRun.imported_at.desc(), ImportRun.id.desc())
            .limit(1)
        )

    with Session(engine) as session:
        run_a = import_run(run_a_id, "1" * 64)
        run_b = import_run(run_b_id, "2" * 64)
        run_a.imported_at = imported_a
        run_b.imported_at = imported_b
        session.add_all([run_a, run_b])
        session.flush()
        run_a.status = "SUCCEEDED"
        run_b.status = "SUCCEEDED"
        session.flush()

        revision_a = revision(import_run_id=run_a_id)
        revision_b = revision(
            revision_id=revision_b_id,
            raw_tree_sha256=revision_b_id,
            semantic_tree_sha256="f" * 64,
            import_run_id=run_b_id,
        )
        session.add_all([revision_a, revision_b])
        session.flush()
        revision_a.materialization_sha256 = HASH_D
        revision_b.materialization_sha256 = HASH_D
        revision_a.status = "SUCCEEDED"
        revision_b.status = "SUCCEEDED"
        session.flush()

        session.add_all(
            [
                RevisionActivation(
                    activation_id="00000000-0000-0000-0000-000000000201",
                    sequence_no=1,
                    from_revision_id=None,
                    to_revision_id=HASH_A,
                    kind="IMPORT",
                    reason="initial A",
                    actor="pytest",
                    epoch=1,
                ),
                RevisionActivation(
                    activation_id="00000000-0000-0000-0000-000000000202",
                    sequence_no=2,
                    from_revision_id=HASH_A,
                    to_revision_id=revision_b_id,
                    kind="IMPORT",
                    reason="switch to B",
                    actor="pytest",
                    epoch=2,
                ),
                RevisionActivation(
                    activation_id="00000000-0000-0000-0000-000000000203",
                    sequence_no=3,
                    from_revision_id=revision_b_id,
                    to_revision_id=HASH_A,
                    kind="ROLLBACK",
                    reason="rollback to A",
                    actor="pytest",
                    epoch=3,
                ),
                MaterializationState(
                    id=1,
                    active_revision_id=HASH_A,
                    active_import_run_id=run_a_id,
                    epoch=3,
                    materialization_sha256=HASH_D,
                    serving_counts={},
                ),
            ]
        )
        session.commit()

    with Session(engine) as session:
        before = legacy_latest(session)
        state = session.get(MaterializationState, 1)
        assert before is not None and before.id == run_b_id
        assert state is not None and state.active_import_run_id == run_a_id
        latest_succeeded_at = session.scalar(
            select(func.max(ImportRun.imported_at)).where(
                ImportRun.status == "SUCCEEDED"
            )
        )
        assert latest_succeeded_at is not None

        # This bulk UPDATE intentionally models the transactional downgrade SQL
        # after its runtime history trigger has been removed.
        session.execute(
            update(ImportRun)
            .where(ImportRun.id == state.active_import_run_id)
            .values(imported_at=latest_succeeded_at + timedelta(microseconds=1))
            .execution_options(synchronize_session=False)
        )
        session.commit()

    with Session(engine) as session:
        after = legacy_latest(session)
        assert after is not None and after.id == run_a_id


def test_orm_contract_matches_snapshot_materializer() -> None:
    assert [column.name for column in CoreRevision.__table__.primary_key.columns] == [
        "revision_id"
    ]
    assert CoreRevision.__table__.c.revision_id.type.length == 64
    assert [column.name for column in CoreFile.__table__.primary_key.columns] == [
        "revision_id",
        "relative_path",
    ]
    assert [column.name for column in CoreCsvRow.__table__.primary_key.columns] == [
        "revision_id",
        "relative_path",
        "ordinal",
    ]
    assert CoreCsvRow.__table__.c["values"].nullable is False
    assert MaterializationState.__table__.c.active_revision_id.nullable is True
    assert MaterializationState.__table__.c.active_import_run_id.nullable is True
    assert RevisionActivation.__table__.c.to_revision_id.nullable is False
    activation_kind_constraints = {
        str(constraint.sqltext)
        for constraint in RevisionActivation.__table__.constraints
        if constraint.__class__.__name__ == "CheckConstraint"
        and str(constraint.name).endswith("revision_activation_kind")
    }
    assert activation_kind_constraints == {"kind IN ('IMPORT','ROLLBACK','REACTIVATE')"}
    assert {
        tuple(column.name for column in constraint.columns)
        for constraint in CoreRevision.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    } >= {("revision_id", "import_run_id")}


def test_core_file_and_csv_row_composite_fk_and_unique_key() -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        session.add(revision())
        session.flush()
        session.add(
            CoreFile(
                revision_id=HASH_A,
                relative_path="92_EVIDENCE_LEDGER.csv",
                ordinal=1,
                sha256=HASH_A,
                semantic_sha256=HASH_B,
                size_bytes=10,
                content=b"evidence\n",
                is_csv=True,
                natural_key_field="evidence_id",
                header=["evidence_id"],
            )
        )
        session.flush()
        session.add(
            CoreCsvRow(
                revision_id=HASH_A,
                relative_path="92_EVIDENCE_LEDGER.csv",
                ordinal=1,
                natural_key="ev001",
                values=["ev001"],
                row_sha256=HASH_C,
            )
        )
        session.commit()

        session.add(
            CoreCsvRow(
                revision_id=HASH_A,
                relative_path="92_EVIDENCE_LEDGER.csv",
                ordinal=2,
                natural_key="ev001",
                values=["ev001"],
                row_sha256=HASH_C,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_core_revision_status_and_csv_shape_fail_closed() -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        session.add(revision(status="ACTIVE"))
        with pytest.raises(ImmutableCoreRevisionError, match="inserted in STAGING"):
            session.commit()

    with Session(engine) as session:
        session.add(revision())
        session.add(
            CoreFile(
                revision_id=HASH_A,
                relative_path="README.md",
                ordinal=1,
                sha256=HASH_A,
                semantic_sha256=HASH_A,
                size_bytes=1,
                content=b"x",
                is_csv=False,
                natural_key_field="forbidden",
                header=None,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


@pytest.mark.parametrize("terminal_status", ["SUCCEEDED", "FAILED"])
def test_import_run_lifecycle_is_append_only_after_finalization(
    terminal_status: str,
) -> None:
    engine = sqlite_engine()
    invalid_run_id = "00000000-0000-0000-0000-000000000010"
    valid_run_id = "00000000-0000-0000-0000-000000000011"

    with Session(engine) as session:
        invalid_run = import_run(invalid_run_id, "8" * 64)
        invalid_run.status = terminal_status
        session.add(invalid_run)
        with pytest.raises(ImmutableImportRunError, match="inserted in RUNNING"):
            session.flush()

    with Session(engine) as session:
        session.add(import_run(valid_run_id, "9" * 64))
        session.flush()
        stored = session.get(ImportRun, valid_run_id)
        assert stored is not None
        stored.manifest = {"finalized": True}
        stored.row_counts = {"teams": 1}
        stored.status = terminal_status
        session.commit()

    with Session(engine) as session:
        stored = session.get(ImportRun, valid_run_id)
        assert stored is not None
        assert stored.status == terminal_status
        stored.manifest = {"tampered": True}
        with pytest.raises(ImmutableImportRunError, match="terminal import run"):
            session.flush()

    with Session(engine) as session:
        stored = session.get(ImportRun, valid_run_id)
        assert stored is not None
        stored.status = "RUNNING"
        session.delete(stored)
        with pytest.raises(ImmutableImportRunError, match="terminal import run"):
            session.flush()

    with Session(engine) as session:
        stored = session.get(ImportRun, valid_run_id)
        assert stored is not None
        session.delete(stored)
        with pytest.raises(ImmutableImportRunError, match="terminal import run"):
            session.flush()

    with Session(engine) as session:
        stored = session.get(ImportRun, valid_run_id)
        assert stored is not None
        session.expire(stored)
        stored.status = "RUNNING"
        with pytest.raises(ImmutableImportRunError, match="terminal import run"):
            session.flush()

    with Session(engine) as session:
        stored = session.get(ImportRun, valid_run_id)
        assert stored is not None
        session.expire(stored)
        stored.canonical_source = "expired-object-tamper"
        with pytest.raises(ImmutableImportRunError, match="terminal import run"):
            session.flush()


def test_non_csv_header_none_is_stored_as_sql_null() -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        session.add(revision())
        session.flush()
        session.add(
            CoreFile(
                revision_id=HASH_A,
                relative_path="README.md",
                ordinal=1,
                sha256=HASH_A,
                semantic_sha256=HASH_A,
                size_bytes=1,
                content=b"x",
                is_csv=False,
                natural_key_field=None,
                header=None,
            )
        )
        session.commit()

        stored = session.get(CoreFile, (HASH_A, "README.md"))
        assert stored is not None
        assert stored.header is None


def test_terminal_revision_and_children_are_immutable_in_orm_tools() -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        session.add(revision())
        session.flush()
        session.add(
            CoreFile(
                revision_id=HASH_A,
                relative_path="92_EVIDENCE_LEDGER.csv",
                ordinal=1,
                sha256=HASH_A,
                semantic_sha256=HASH_B,
                size_bytes=10,
                content=b"evidence\n",
                is_csv=True,
                natural_key_field="evidence_id",
                header=["evidence_id"],
            )
        )
        session.flush()
        session.add(
            CoreCsvRow(
                revision_id=HASH_A,
                relative_path="92_EVIDENCE_LEDGER.csv",
                ordinal=1,
                natural_key="ev001",
                values=["ev001"],
                row_sha256=HASH_C,
            )
        )
        session.flush()
        stored_revision = session.get(CoreRevision, HASH_A)
        assert stored_revision is not None
        stored_revision.status = "SUCCEEDED"
        session.commit()

    with Session(engine) as session:
        stored_revision = session.get(CoreRevision, HASH_A)
        assert stored_revision is not None
        stored_revision.manifest = {"tampered": True}
        with pytest.raises(ImmutableCoreRevisionError, match="terminal core revision"):
            session.commit()

    with Session(engine) as session:
        stored_revision = session.get(CoreRevision, HASH_A)
        assert stored_revision is not None
        session.expire(stored_revision)
        stored_revision.status = "STAGING"
        stored_revision.manifest = {"expired_object_tamper": True}
        with pytest.raises(ImmutableCoreRevisionError, match="terminal core revision"):
            session.flush()

    with Session(engine) as session:
        stored_revision = session.get(CoreRevision, HASH_A)
        assert stored_revision is not None
        stored_revision.status = "STAGING"
        session.delete(stored_revision)
        with pytest.raises(ImmutableCoreRevisionError, match="terminal core revision"):
            session.flush()

    with Session(engine) as session:
        stored_file = session.get(CoreFile, (HASH_A, "92_EVIDENCE_LEDGER.csv"))
        assert stored_file is not None
        stored_file.content = b"tampered"
        with pytest.raises(ImmutableCoreRevisionError, match="not mutable STAGING"):
            session.commit()

    with Session(engine) as session:
        stored_row = session.get(
            CoreCsvRow,
            (HASH_A, "92_EVIDENCE_LEDGER.csv", 1),
        )
        assert stored_row is not None
        session.delete(stored_row)
        with pytest.raises(ImmutableCoreRevisionError, match="not mutable STAGING"):
            session.commit()


def test_materialization_state_requires_complete_active_pointer() -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        session.add(revision())
        session.flush()
        session.add(
            MaterializationState(
                id=1,
                active_revision_id=HASH_A,
                active_import_run_id=None,
                epoch=1,
                materialization_sha256=HASH_D,
                serving_counts={},
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_materialization_state_epoch_must_strictly_increase_in_orm_tools() -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        session.add(
            MaterializationState(
                id=1,
                active_revision_id=None,
                active_import_run_id=None,
                epoch=5,
                materialization_sha256=None,
                serving_counts={},
            )
        )
        session.commit()

    with Session(engine) as session:
        state = session.get(MaterializationState, 1)
        assert state is not None
        state.serving_counts = {"tampered": 1}
        with pytest.raises(
            NonMonotonicMaterializationEpochError,
            match=r"old 5, new 5",
        ):
            session.flush()

    with Session(engine) as session:
        state = session.get(MaterializationState, 1)
        assert state is not None
        session.expire(state)
        state.epoch = 4
        with pytest.raises(
            NonMonotonicMaterializationEpochError,
            match=r"old 5, new 4",
        ):
            session.flush()

    with Session(engine) as session:
        state = session.get(MaterializationState, 1)
        assert state is not None
        state.epoch = 6
        state.serving_counts = {"teams": 1}
        session.commit()

    with Session(engine) as session:
        state = session.get(MaterializationState, 1)
        assert state is not None
        assert state.epoch == 6
        assert state.serving_counts == {"teams": 1}

    with Session(engine) as session:
        state = session.get(MaterializationState, 1)
        assert state is not None
        session.delete(state)
        with pytest.raises(
            ImmutableMaterializationStateError,
            match="singleton cannot be deleted",
        ):
            session.flush()


def test_materialization_state_rejects_mismatched_revision_import_pair() -> None:
    engine = sqlite_engine()
    run_a = "00000000-0000-0000-0000-000000000001"
    run_b = "00000000-0000-0000-0000-000000000002"
    revision_b = "e" * 64
    with Session(engine) as session:
        session.add_all(
            [
                import_run(run_a, "1" * 64),
                import_run(run_b, "2" * 64),
            ]
        )
        session.flush()
        session.add_all(
            [
                revision(import_run_id=run_a),
                revision(
                    revision_id=revision_b,
                    raw_tree_sha256=revision_b,
                    semantic_tree_sha256="f" * 64,
                    import_run_id=run_b,
                ),
            ]
        )
        session.flush()
        session.add(
            MaterializationState(
                id=1,
                active_revision_id=HASH_A,
                active_import_run_id=run_b,
                epoch=1,
                materialization_sha256=HASH_D,
                serving_counts={},
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_revision_activation_rejects_same_from_and_to_revision() -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        session.add(revision())
        session.flush()
        session.add(
            RevisionActivation(
                activation_id="00000000-0000-0000-0000-000000000001",
                sequence_no=1,
                from_revision_id=HASH_A,
                to_revision_id=HASH_A,
                kind="ROLLBACK",
                reason="invalid test fixture",
                actor="pytest",
                epoch=1,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_revision_activation_is_append_only_in_orm_tools() -> None:
    engine = sqlite_engine()
    activation_id = "00000000-0000-0000-0000-000000000003"
    with Session(engine) as session:
        session.add(revision())
        session.flush()
        session.add(
            RevisionActivation(
                activation_id=activation_id,
                sequence_no=1,
                from_revision_id=None,
                to_revision_id=HASH_A,
                kind="IMPORT",
                reason="initial activation",
                actor="pytest",
                epoch=1,
            )
        )
        session.commit()

    with Session(engine) as session:
        activation = session.get(RevisionActivation, activation_id)
        assert activation is not None
        activation.reason = "tampered"
        with pytest.raises(
            ImmutableRevisionActivationError,
            match="append-only",
        ):
            session.flush()

    with Session(engine) as session:
        activation = session.get(RevisionActivation, activation_id)
        assert activation is not None
        session.delete(activation)
        with pytest.raises(
            ImmutableRevisionActivationError,
            match="append-only",
        ):
            session.flush()
