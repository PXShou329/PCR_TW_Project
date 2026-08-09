"""V0003: full research-core revision mirror and revision-aware epoch."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "v0003_core_revision_mirror"
down_revision: str | None = "v0002_operation_timelines"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

jsonb = postgresql.JSONB(astext_type=sa.Text())
nullable_jsonb = postgresql.JSONB(astext_type=sa.Text(), none_as_null=True)

# ImportRun is provenance rather than a serving-domain row, but changing it can
# change the active revision contract.  It therefore shares the same epoch as
# every normalized serving and core-artifact table.
EPOCH_TABLES = (
    "import_runs",
    "characters",
    "claims",
    "evidence",
    "stages",
    "teams",
    "team_members",
    "stage_evidence",
    "stage_claims",
    "team_evidence",
    "claim_evidence",
    "operation_timelines",
    "timeline_steps",
    "core_revisions",
    "core_files",
    "core_csv_rows",
)


def _epoch_trigger_name(table_name: str) -> str:
    return f"trg_{table_name}_materialization_epoch"


def upgrade() -> None:
    op.create_table(
        "core_revisions",
        sa.Column("revision_id", sa.String(64), nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=True),
        sa.Column("raw_tree_sha256", sa.String(64), nullable=False),
        sa.Column("semantic_tree_sha256", sa.String(64), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=False),
        sa.Column("materialization_sha256", sa.String(64), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("csv_file_count", sa.Integer(), nullable=False),
        sa.Column("csv_row_count", sa.Integer(), nullable=False),
        sa.Column("evidence_to_claim_count", sa.Integer(), nullable=False),
        sa.Column("evidence_to_claim_sha256", sa.String(64), nullable=False),
        sa.Column("claim_to_evidence_count", sa.Integer(), nullable=False),
        sa.Column("claim_to_evidence_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("manifest", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("project_version", sa.String(40), nullable=False),
        sa.Column("serialization_version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(raw_tree_sha256) = 64",
            name=op.f("ck_core_revisions_core_revision_raw_hash"),
        ),
        sa.CheckConstraint(
            "length(semantic_tree_sha256) = 64",
            name=op.f("ck_core_revisions_core_revision_semantic_hash"),
        ),
        sa.CheckConstraint(
            "length(manifest_sha256) = 64",
            name=op.f("ck_core_revisions_core_revision_manifest_hash"),
        ),
        sa.CheckConstraint(
            "materialization_sha256 IS NULL OR length(materialization_sha256) = 64",
            name=op.f("ck_core_revisions_core_revision_materialization_hash"),
        ),
        sa.CheckConstraint(
            "file_count >= 1",
            name=op.f("ck_core_revisions_core_revision_file_count_positive"),
        ),
        sa.CheckConstraint(
            "csv_file_count >= 1 AND csv_file_count <= file_count",
            name=op.f("ck_core_revisions_core_revision_csv_file_count_range"),
        ),
        sa.CheckConstraint(
            "csv_row_count >= 0",
            name=op.f("ck_core_revisions_core_revision_csv_row_count_nonnegative"),
        ),
        sa.CheckConstraint(
            "evidence_to_claim_count >= 0",
            name=op.f("ck_core_revisions_core_revision_evidence_edge_count"),
        ),
        sa.CheckConstraint(
            "claim_to_evidence_count >= 0",
            name=op.f("ck_core_revisions_core_revision_claim_edge_count"),
        ),
        sa.CheckConstraint(
            "length(evidence_to_claim_sha256) = 64",
            name=op.f("ck_core_revisions_core_revision_evidence_edge_hash"),
        ),
        sa.CheckConstraint(
            "length(claim_to_evidence_sha256) = 64",
            name=op.f("ck_core_revisions_core_revision_claim_edge_hash"),
        ),
        sa.CheckConstraint(
            "status IN ('STAGING','SUCCEEDED','FAILED')",
            name=op.f("ck_core_revisions_core_revision_status"),
        ),
        sa.CheckConstraint(
            "serialization_version >= 1",
            name=op.f("ck_core_revisions_core_revision_serialization_version"),
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name=op.f("fk_core_revisions_import_run_id_import_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("revision_id", name=op.f("pk_core_revisions")),
        sa.UniqueConstraint(
            "import_run_id", name=op.f("uq_core_revisions_import_run_id")
        ),
        sa.UniqueConstraint(
            "raw_tree_sha256", name=op.f("uq_core_revisions_raw_tree_sha256")
        ),
        sa.UniqueConstraint(
            "revision_id",
            "import_run_id",
            name=op.f("uq_core_revisions_revision_import_run"),
        ),
    )
    op.create_index(
        "ix_core_revisions_status_created",
        "core_revisions",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "core_files",
        sa.Column("revision_id", sa.String(64), nullable=False),
        sa.Column("relative_path", sa.String(500), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("semantic_sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("is_csv", sa.Boolean(), nullable=False),
        sa.Column("natural_key_field", sa.String(100), nullable=True),
        sa.Column("header", nullable_jsonb, nullable=True),
        sa.CheckConstraint(
            "length(relative_path) > 0",
            name=op.f("ck_core_files_core_file_path_nonempty"),
        ),
        sa.CheckConstraint(
            "ordinal >= 1", name=op.f("ck_core_files_core_file_ordinal_positive")
        ),
        sa.CheckConstraint(
            "length(sha256) = 64", name=op.f("ck_core_files_core_file_hash")
        ),
        sa.CheckConstraint(
            "length(semantic_sha256) = 64",
            name=op.f("ck_core_files_core_file_semantic_hash"),
        ),
        sa.CheckConstraint(
            "size_bytes >= 0", name=op.f("ck_core_files_core_file_size_nonnegative")
        ),
        sa.CheckConstraint(
            "(is_csv AND header IS NOT NULL AND natural_key_field IS NOT NULL) OR "
            "(NOT is_csv AND header IS NULL AND natural_key_field IS NULL)",
            name=op.f("ck_core_files_core_file_csv_shape"),
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["core_revisions.revision_id"],
            name=op.f("fk_core_files_revision_id_core_revisions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "revision_id", "relative_path", name=op.f("pk_core_files")
        ),
        sa.UniqueConstraint(
            "revision_id",
            "ordinal",
            name=op.f("uq_core_files_revision_ordinal"),
        ),
    )
    op.create_index(
        "ix_core_files_revision_csv",
        "core_files",
        ["revision_id", "is_csv"],
        unique=False,
    )

    op.create_table(
        "core_csv_rows",
        sa.Column("revision_id", sa.String(64), nullable=False),
        sa.Column("relative_path", sa.String(500), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("natural_key", sa.Text(), nullable=False),
        sa.Column("values", jsonb, nullable=False),
        sa.Column("row_sha256", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "ordinal >= 1", name=op.f("ck_core_csv_rows_core_csv_row_ordinal_positive")
        ),
        sa.CheckConstraint(
            "length(natural_key) > 0",
            name=op.f("ck_core_csv_rows_core_csv_row_key_nonempty"),
        ),
        sa.CheckConstraint(
            "length(row_sha256) = 64",
            name=op.f("ck_core_csv_rows_core_csv_row_hash"),
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "relative_path"],
            ["core_files.revision_id", "core_files.relative_path"],
            name="fk_core_csv_rows_revision_path_core_files",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "revision_id", "relative_path", "ordinal", name=op.f("pk_core_csv_rows")
        ),
        sa.UniqueConstraint(
            "revision_id",
            "relative_path",
            "natural_key",
            name=op.f("uq_core_csv_rows_revision_path_key"),
        ),
    )
    op.create_index(
        "ix_core_csv_rows_revision_path",
        "core_csv_rows",
        ["revision_id", "relative_path"],
        unique=False,
    )

    op.create_table(
        "materialization_state",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("active_revision_id", sa.String(64), nullable=True),
        sa.Column("active_import_run_id", sa.String(36), nullable=True),
        sa.Column("epoch", sa.BigInteger(), nullable=False),
        sa.Column("materialization_sha256", sa.String(64), nullable=True),
        sa.Column(
            "serving_counts", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "id = 1", name=op.f("ck_materialization_state_materialization_state_singleton")
        ),
        sa.CheckConstraint(
            "epoch >= 0",
            name=op.f("ck_materialization_state_materialization_state_epoch_nonnegative"),
        ),
        sa.CheckConstraint(
            "(active_revision_id IS NULL AND active_import_run_id IS NULL "
            "AND materialization_sha256 IS NULL) OR "
            "(active_revision_id IS NOT NULL AND active_import_run_id IS NOT NULL "
            "AND materialization_sha256 IS NOT NULL "
            "AND length(materialization_sha256) = 64)",
            name=op.f("ck_materialization_state_materialization_state_active_shape"),
        ),
        sa.ForeignKeyConstraint(
            ["active_revision_id", "active_import_run_id"],
            ["core_revisions.revision_id", "core_revisions.import_run_id"],
            name=op.f("fk_materialization_state_active_revision_run"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_materialization_state")),
    )
    op.execute(
        "INSERT INTO materialization_state "
        "(id, epoch, serving_counts, updated_at) "
        "VALUES (1, 0, '{}'::jsonb, CURRENT_TIMESTAMP)"
    )

    op.create_table(
        "revision_activations",
        sa.Column("activation_id", sa.String(36), nullable=False),
        sa.Column("sequence_no", sa.BigInteger(), nullable=False),
        sa.Column("from_revision_id", sa.String(64), nullable=True),
        sa.Column("to_revision_id", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(160), nullable=False),
        sa.Column(
            "activated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("epoch", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "sequence_no >= 1",
            name=op.f("ck_revision_activations_revision_activation_sequence_positive"),
        ),
        sa.CheckConstraint(
            "epoch >= 0",
            name=op.f("ck_revision_activations_revision_activation_epoch_nonnegative"),
        ),
        sa.CheckConstraint(
            "kind IN ('IMPORT','ROLLBACK','REACTIVATE')",
            name=op.f("ck_revision_activations_revision_activation_kind"),
        ),
        sa.CheckConstraint(
            "from_revision_id IS NULL OR from_revision_id <> to_revision_id",
            name=op.f("ck_revision_activations_revision_activation_distinct_revisions"),
        ),
        sa.ForeignKeyConstraint(
            ["from_revision_id"],
            ["core_revisions.revision_id"],
            name=op.f("fk_revision_activations_from_revision_id_core_revisions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["to_revision_id"],
            ["core_revisions.revision_id"],
            name=op.f("fk_revision_activations_to_revision_id_core_revisions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("activation_id", name=op.f("pk_revision_activations")),
        sa.UniqueConstraint(
            "sequence_no", name=op.f("uq_revision_activations_sequence_no")
        ),
    )
    op.create_index(
        "ix_revision_activations_activated_at",
        "revision_activations",
        ["activated_at"],
        unique=False,
    )

    op.execute(
        """
        CREATE FUNCTION pcr_guard_import_run_history()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.status <> 'RUNNING' THEN
                    RAISE EXCEPTION 'import runs must be inserted in RUNNING status';
                END IF;
                RETURN NEW;
            END IF;

            IF OLD.status IN ('SUCCEEDED', 'FAILED') THEN
                RAISE EXCEPTION 'terminal import run % is immutable', OLD.id;
            END IF;

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_import_runs_history_guard "
        "BEFORE INSERT OR UPDATE OR DELETE ON import_runs "
        "FOR EACH ROW EXECUTE FUNCTION pcr_guard_import_run_history()"
    )

    op.execute(
        """
        CREATE FUNCTION pcr_guard_core_revision_history()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.status <> 'STAGING' THEN
                    RAISE EXCEPTION 'core revisions must be inserted in STAGING status';
                END IF;
                RETURN NEW;
            END IF;

            IF OLD.status IN ('SUCCEEDED', 'FAILED') THEN
                RAISE EXCEPTION 'terminal core revision % is immutable', OLD.revision_id;
            END IF;

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_core_revisions_history_guard "
        "BEFORE INSERT OR UPDATE OR DELETE ON core_revisions "
        "FOR EACH ROW EXECUTE FUNCTION pcr_guard_core_revision_history()"
    )

    op.execute(
        """
        CREATE FUNCTION pcr_guard_core_artifact_history()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            guarded_revision_id varchar(64);
            guarded_status varchar(20);
        BEGIN
            IF TG_OP = 'INSERT' THEN
                guarded_revision_id := NEW.revision_id;
            ELSE
                guarded_revision_id := OLD.revision_id;
            END IF;

            SELECT status INTO guarded_status
            FROM core_revisions
            WHERE revision_id = guarded_revision_id
            FOR SHARE;
            IF guarded_status IS DISTINCT FROM 'STAGING' THEN
                RAISE EXCEPTION 'artifact revision % is not mutable STAGING data',
                    guarded_revision_id;
            END IF;

            IF TG_OP = 'UPDATE' AND NEW.revision_id <> OLD.revision_id THEN
                SELECT status INTO guarded_status
                FROM core_revisions
                WHERE revision_id = NEW.revision_id
                FOR SHARE;
                IF guarded_status IS DISTINCT FROM 'STAGING' THEN
                    RAISE EXCEPTION 'artifact revision % is not mutable STAGING data',
                        NEW.revision_id;
                END IF;
            END IF;

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    for table_name in ("core_files", "core_csv_rows"):
        op.execute(
            f'CREATE TRIGGER "trg_{table_name}_history_guard" '
            f'BEFORE INSERT OR UPDATE OR DELETE ON "{table_name}" '
            "FOR EACH ROW EXECUTE FUNCTION pcr_guard_core_artifact_history()"
        )

    op.execute(
        """
        CREATE FUNCTION pcr_require_monotonic_materialization_epoch()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            IF NEW.epoch <= OLD.epoch THEN
                RAISE EXCEPTION
                    'materialization_state epoch must strictly increase (old %, new %)',
                    OLD.epoch, NEW.epoch;
            END IF;
            RETURN NEW;
        END;
        $function$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_materialization_state_epoch_monotonic "
        "BEFORE UPDATE ON materialization_state "
        "FOR EACH ROW EXECUTE FUNCTION pcr_require_monotonic_materialization_epoch()"
    )

    op.execute(
        """
        CREATE FUNCTION pcr_bump_materialization_epoch()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            UPDATE materialization_state
            SET epoch = epoch + 1,
                updated_at = clock_timestamp()
            WHERE id = 1;
            RETURN NULL;
        END;
        $function$
        """
    )
    for table_name in EPOCH_TABLES:
        trigger_name = _epoch_trigger_name(table_name)
        op.execute(
            f'CREATE TRIGGER "{trigger_name}" '
            f'AFTER INSERT OR UPDATE OR DELETE ON "{table_name}" '
            "FOR EACH STATEMENT EXECUTE FUNCTION pcr_bump_materialization_epoch()"
        )

    op.execute(
        """
        CREATE FUNCTION pcr_reject_revision_activation_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            RAISE EXCEPTION 'revision_activations is append-only';
        END;
        $function$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_revision_activations_append_only "
        "BEFORE UPDATE OR DELETE ON revision_activations "
        "FOR EACH STATEMENT EXECUTE FUNCTION pcr_reject_revision_activation_mutation()"
    )

    op.execute(
        """
        CREATE FUNCTION pcr_protect_materialization_state()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            RAISE EXCEPTION 'materialization_state singleton cannot be deleted';
        END;
        $function$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_materialization_state_protect_singleton "
        "BEFORE DELETE ON materialization_state "
        "FOR EACH STATEMENT EXECUTE FUNCTION pcr_protect_materialization_state()"
    )


def downgrade() -> None:
    # V0002 has no active pointer: its legacy latest_import query selects the
    # newest SUCCEEDED ImportRun by imported_at.  Reconcile that projection
    # while V0003 state still exists, and only after removing the terminal-run
    # guard as an explicit, transactional downgrade-only operation.
    op.execute("DROP TRIGGER IF EXISTS trg_import_runs_history_guard ON import_runs")
    op.execute("DROP FUNCTION IF EXISTS pcr_guard_import_run_history()")
    op.execute(
        """
        DO $reconcile_legacy_latest$
        DECLARE
            active_run_id varchar(36);
            active_run_status varchar(20);
            latest_succeeded_at timestamptz;
        BEGIN
            SELECT active_import_run_id
            INTO active_run_id
            FROM materialization_state
            WHERE id = 1;
            IF NOT FOUND THEN
                RAISE EXCEPTION
                    'cannot reconcile legacy latest import: materialization_state is missing';
            END IF;

            IF active_run_id IS NOT NULL THEN
                SELECT status
                INTO active_run_status
                FROM import_runs
                WHERE id = active_run_id;
                IF active_run_status IS DISTINCT FROM 'SUCCEEDED' THEN
                    RAISE EXCEPTION
                        'cannot reconcile legacy latest import: active run % is not SUCCEEDED',
                        active_run_id;
                END IF;

                SELECT max(imported_at)
                INTO latest_succeeded_at
                FROM import_runs
                WHERE status = 'SUCCEEDED';

                UPDATE import_runs
                SET imported_at = latest_succeeded_at + INTERVAL '1 microsecond'
                WHERE id = active_run_id;
            END IF;
        END;
        $reconcile_legacy_latest$
        """
    )

    op.execute(
        "DROP TRIGGER IF EXISTS trg_materialization_state_epoch_monotonic "
        "ON materialization_state"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS pcr_require_monotonic_materialization_epoch()"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_materialization_state_protect_singleton "
        "ON materialization_state"
    )
    op.execute("DROP FUNCTION IF EXISTS pcr_protect_materialization_state()")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_revision_activations_append_only "
        "ON revision_activations"
    )
    op.execute("DROP FUNCTION IF EXISTS pcr_reject_revision_activation_mutation()")
    for table_name in ("core_csv_rows", "core_files"):
        op.execute(
            f'DROP TRIGGER IF EXISTS "trg_{table_name}_history_guard" ON "{table_name}"'
        )
    op.execute("DROP FUNCTION IF EXISTS pcr_guard_core_artifact_history()")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_core_revisions_history_guard ON core_revisions"
    )
    op.execute("DROP FUNCTION IF EXISTS pcr_guard_core_revision_history()")
    for table_name in reversed(EPOCH_TABLES):
        trigger_name = _epoch_trigger_name(table_name)
        op.execute(
            f'DROP TRIGGER IF EXISTS "{trigger_name}" ON "{table_name}"'
        )
    op.execute("DROP FUNCTION IF EXISTS pcr_bump_materialization_epoch()")

    op.drop_index("ix_revision_activations_activated_at", table_name="revision_activations")
    op.drop_table("revision_activations")
    op.drop_table("materialization_state")
    op.drop_index("ix_core_csv_rows_revision_path", table_name="core_csv_rows")
    op.drop_table("core_csv_rows")
    op.drop_index("ix_core_files_revision_csv", table_name="core_files")
    op.drop_table("core_files")
    op.drop_index("ix_core_revisions_status_created", table_name="core_revisions")
    op.drop_table("core_revisions")
