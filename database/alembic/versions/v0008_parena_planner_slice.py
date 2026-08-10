"""V0008: normalized Princess Arena exact-case serving closure."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "v0008_parena_planner_slice"
down_revision: str | None = "v0007_gacha_timeline_slice"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

jsonb = postgresql.JSONB(astext_type=sa.Text())

PARENA_EPOCH_TABLES = (
    "arena_source_records",
    "parena_cases",
    "parena_case_matchups",
    "parena_case_sources",
    "parena_case_evidence",
    "parena_case_claims",
)

V4_TABLES = (
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
    "arena_defenses",
    "arena_defense_members",
    "arena_counters",
    "arena_counter_members",
    "arena_counter_evidence",
    "arena_counter_claims",
    "gacha_timeline_events",
    "gacha_timeline_evidence",
    "gacha_timeline_claims",
    "gacha_community_sources",
    "gacha_timeline_community_sources",
)


def _epoch_trigger_name(table_name: str) -> str:
    return f"trg_{table_name}_materialization_epoch"


def upgrade() -> None:
    # Required by the composite FK below: a matchup must bind one counter to
    # the same defense that owns that exact Arena result.
    op.create_unique_constraint(
        "uq_arena_counters_counter_defense",
        "arena_counters",
        ["counter_id", "defense_id"],
    )

    op.create_table(
        "arena_source_records",
        sa.Column("source_id", sa.String(140), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(100), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("server", sa.String(16), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("last_checked", sa.Date(), nullable=False),
        sa.Column("freshness_window", sa.String(24), nullable=True),
        sa.Column("access_status", sa.String(24), nullable=False),
        sa.Column("confidence_cap", sa.String(8), nullable=False),
        sa.Column("extraction_method", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.CheckConstraint(
            "server IN ('TW','JP')",
            name=op.f("ck_arena_source_records_arena_source_record_server"),
        ),
        sa.CheckConstraint(
            "access_status IN ('ACTIVE','PARTIAL','BLOCKED','STALE','ARCHIVED')",
            name=op.f("ck_arena_source_records_arena_source_record_access_status"),
        ),
        sa.CheckConstraint(
            "confidence_cap IN ('C','D','E')",
            name=op.f("ck_arena_source_records_arena_source_record_confidence_cap"),
        ),
        sa.CheckConstraint(
            "length(title) > 0",
            name=op.f("ck_arena_source_records_arena_source_record_title_nonempty"),
        ),
        sa.CheckConstraint(
            "length(url) > 0",
            name=op.f("ck_arena_source_records_arena_source_record_url_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_arena_source_records_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("source_id", name=op.f("pk_arena_source_records")),
    )
    op.create_index(
        "ix_arena_source_records_server_status_checked",
        "arena_source_records",
        ["server", "access_status", "last_checked"],
        unique=False,
    )

    op.create_table(
        "parena_cases",
        sa.Column("case_id", sa.String(140), nullable=False),
        sa.Column("server", sa.String(16), nullable=False),
        sa.Column("environment_version", sa.String(100), nullable=False),
        sa.Column("defense_signature", sa.String(1900), nullable=False),
        sa.Column("counter_signature", sa.String(1900), nullable=False),
        sa.Column("case_win_claim_id", sa.String(140), nullable=False),
        sa.Column("case_win_confidence", sa.String(8), nullable=False),
        sa.Column("hidden_team_mode", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("verified_date", sa.Date(), nullable=False),
        sa.Column("tw_availability_check", sa.String(20), nullable=False),
        sa.Column("non_overlap_check", sa.String(20), nullable=False),
        sa.Column("reproducibility", sa.String(32), nullable=False),
        sa.Column("last_review_due", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.CheckConstraint("server = 'TW'", name=op.f("ck_parena_cases_parena_case_server")),
        sa.CheckConstraint(
            "case_win_confidence IN ('B','C','D')",
            name=op.f("ck_parena_cases_parena_case_win_confidence"),
        ),
        sa.CheckConstraint(
            "status = 'VERIFIED'", name=op.f("ck_parena_cases_parena_case_status")
        ),
        sa.CheckConstraint(
            "hidden_team_mode = 'NONE'",
            name=op.f("ck_parena_cases_parena_case_hidden_mode"),
        ),
        sa.CheckConstraint(
            "tw_availability_check = 'PASS'",
            name=op.f("ck_parena_cases_parena_case_tw_availability"),
        ),
        sa.CheckConstraint(
            "non_overlap_check = 'PASS'",
            name=op.f("ck_parena_cases_parena_case_non_overlap"),
        ),
        sa.CheckConstraint(
            "reproducibility = 'CONFIRMED'",
            name=op.f("ck_parena_cases_parena_case_reproducibility"),
        ),
        sa.CheckConstraint(
            "length(environment_version) > 0 AND environment_version != 'UNKNOWN'",
            name=op.f("ck_parena_cases_parena_case_environment_known"),
        ),
        sa.CheckConstraint(
            "length(notes) > 0", name=op.f("ck_parena_cases_parena_case_notes_nonempty")
        ),
        sa.ForeignKeyConstraint(
            ["case_win_claim_id"],
            ["claims.claim_id"],
            name="fk_parena_cases_case_win_claim_id_claims",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_parena_cases_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("case_id", name=op.f("pk_parena_cases")),
        sa.UniqueConstraint(
            "server",
            "environment_version",
            "defense_signature",
            name="uq_parena_cases_server_environment_defense",
        ),
        sa.UniqueConstraint(
            "case_win_claim_id", name="uq_parena_cases_case_win_claim"
        ),
    )
    op.create_index(
        "ix_parena_cases_server_environment_status",
        "parena_cases",
        ["server", "environment_version", "status"],
        unique=False,
    )

    op.create_table(
        "parena_case_matchups",
        sa.Column("case_id", sa.String(140), nullable=False),
        sa.Column("matchup_no", sa.Integer(), nullable=False),
        sa.Column("defense_id", sa.String(140), nullable=False),
        sa.Column("counter_id", sa.String(140), nullable=False),
        sa.Column("result_claim_id", sa.String(140), nullable=False),
        sa.CheckConstraint(
            "matchup_no BETWEEN 1 AND 3",
            name=op.f("ck_parena_case_matchups_parena_case_matchup_number_range"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["parena_cases.case_id"],
            name="fk_parena_case_matchups_case_id_parena_cases",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["counter_id", "defense_id"],
            ["arena_counters.counter_id", "arena_counters.defense_id"],
            name="fk_parena_case_matchups_counter_defense",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["result_claim_id"],
            ["claims.claim_id"],
            name="fk_parena_case_matchups_result_claim_id_claims",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "case_id", "matchup_no", name=op.f("pk_parena_case_matchups")
        ),
        sa.UniqueConstraint(
            "case_id", "defense_id", name="uq_parena_case_matchups_case_defense"
        ),
        sa.UniqueConstraint(
            "case_id", "counter_id", name="uq_parena_case_matchups_case_counter"
        ),
        sa.UniqueConstraint(
            "case_id",
            "result_claim_id",
            name="uq_parena_case_matchups_case_result_claim",
        ),
    )

    relation_specs = (
        ("parena_case_sources", "source_id", "arena_source_records", "source_id"),
        ("parena_case_evidence", "evidence_id", "evidence", "evidence_id"),
        ("parena_case_claims", "claim_id", "claims", "claim_id"),
    )
    for table_name, child_column, parent_table, parent_column in relation_specs:
        op.create_table(
            table_name,
            sa.Column("case_id", sa.String(140), nullable=False),
            sa.Column(child_column, sa.String(140), nullable=False),
            sa.ForeignKeyConstraint(
                ["case_id"],
                ["parena_cases.case_id"],
                name=f"fk_{table_name}_case_id_parena_cases",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                [child_column],
                [f"{parent_table}.{parent_column}"],
                name=f"fk_{table_name}_{child_column}_{parent_table}",
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint(
                "case_id", child_column, name=op.f(f"pk_{table_name}")
            ),
        )

    for table_name in PARENA_EPOCH_TABLES:
        op.execute(
            f'CREATE TRIGGER "{_epoch_trigger_name(table_name)}" '
            f'AFTER INSERT OR UPDATE OR DELETE ON "{table_name}" '
            "FOR EACH STATEMENT EXECUTE FUNCTION pcr_bump_materialization_epoch()"
        )


def downgrade() -> None:
    """Drop V0008 only from fresh state or an exact active v4 materialization.

    An active v5 manifest is never silently projected back to v4, even when
    its case tables happen to be empty.  Operators must first reactivate the
    immutable v4 checkpoint and verify its full 23-table ownership.
    """

    op.execute("SELECT pg_advisory_xact_lock(344726848049)")
    for table_name in reversed(PARENA_EPOCH_TABLES):
        op.execute(f'LOCK TABLE "{table_name}" IN ACCESS EXCLUSIVE MODE')
    op.execute('LOCK TABLE "materialization_state" IN ACCESS EXCLUSIVE MODE')
    op.execute('LOCK TABLE "core_revisions" IN SHARE MODE')
    op.execute('LOCK TABLE "import_runs" IN SHARE MODE')

    expected_tables = ",".join(V4_TABLES)
    expected_count = len(V4_TABLES)
    op.execute(
        f"""
        DO $$
        DECLARE
            state_row materialization_state%ROWTYPE;
            active_run_status TEXT;
            active_revision_status TEXT;
            active_run_materialization JSONB;
            revision_materialization_sha256 TEXT;
        BEGIN
            IF EXISTS (SELECT 1 FROM arena_source_records LIMIT 1)
               OR EXISTS (SELECT 1 FROM parena_cases LIMIT 1)
               OR EXISTS (SELECT 1 FROM parena_case_matchups LIMIT 1)
               OR EXISTS (SELECT 1 FROM parena_case_sources LIMIT 1)
               OR EXISTS (SELECT 1 FROM parena_case_evidence LIMIT 1)
               OR EXISTS (SELECT 1 FROM parena_case_claims LIMIT 1)
            THEN
                RAISE EXCEPTION
                    'refusing V0008 downgrade while P-Arena serving rows exist';
            END IF;

            SELECT * INTO state_row
            FROM materialization_state
            WHERE id = 1;

            IF NOT FOUND THEN
                RAISE EXCEPTION
                    'refusing V0008 downgrade without materialization state';
            END IF;

            IF state_row.active_revision_id IS NULL
               AND state_row.active_import_run_id IS NULL
               AND state_row.materialization_sha256 IS NULL
            THEN
                IF state_row.serving_counts <> '{{}}'::jsonb
                   OR EXISTS (SELECT 1 FROM core_revisions LIMIT 1)
                   OR EXISTS (SELECT 1 FROM import_runs LIMIT 1)
                THEN
                    RAISE EXCEPTION
                        'refusing V0008 downgrade from a non-fresh unowned mirror';
                END IF;
            ELSE
                SELECT
                    run.status,
                    revision.status,
                    run.manifest -> 'materialization',
                    revision.materialization_sha256
                INTO
                    active_run_status,
                    active_revision_status,
                    active_run_materialization,
                    revision_materialization_sha256
                FROM import_runs AS run
                JOIN core_revisions AS revision
                  ON revision.revision_id = state_row.active_revision_id
                 AND revision.import_run_id = state_row.active_import_run_id
                WHERE run.id = state_row.active_import_run_id;

                IF NOT FOUND
                   OR active_run_status IS DISTINCT FROM 'SUCCEEDED'
                   OR active_revision_status IS DISTINCT FROM 'SUCCEEDED'
                   OR jsonb_typeof(active_run_materialization) IS DISTINCT FROM 'object'
                   OR active_run_materialization ->> 'schema_version' IS DISTINCT FROM '4'
                   OR active_run_materialization ->> 'sha256'
                      IS DISTINCT FROM state_row.materialization_sha256
                   OR revision_materialization_sha256
                      IS DISTINCT FROM state_row.materialization_sha256
                   OR jsonb_typeof(active_run_materialization -> 'tables')
                      IS DISTINCT FROM 'object'
                   OR (SELECT count(*) FROM jsonb_object_keys(
                        CASE WHEN jsonb_typeof(active_run_materialization -> 'tables') = 'object'
                             THEN active_run_materialization -> 'tables'
                             ELSE '{{}}'::jsonb END)) <> {expected_count}
                   OR NOT ((active_run_materialization -> 'tables') ?&
                           string_to_array('{expected_tables}', ','))
                   OR jsonb_typeof(state_row.serving_counts) IS DISTINCT FROM 'object'
                   OR (SELECT count(*) FROM jsonb_object_keys(
                        CASE WHEN jsonb_typeof(state_row.serving_counts) = 'object'
                             THEN state_row.serving_counts ELSE '{{}}'::jsonb END))
                      <> {expected_count}
                   OR NOT (state_row.serving_counts ?&
                           string_to_array('{expected_tables}', ','))
                   OR EXISTS (
                        SELECT 1
                        FROM jsonb_each(active_run_materialization -> 'tables')
                             AS table_entry(table_name, table_manifest)
                        WHERE jsonb_typeof(table_manifest) IS DISTINCT FROM 'object'
                           OR jsonb_typeof(table_manifest -> 'primary_keys')
                              IS DISTINCT FROM 'array'
                           OR jsonb_typeof(state_row.serving_counts -> table_name)
                              IS DISTINCT FROM 'number'
                           OR (state_row.serving_counts ->> table_name)::integer
                              IS DISTINCT FROM jsonb_array_length(
                                  table_manifest -> 'primary_keys')
                   )
                THEN
                    RAISE EXCEPTION
                        'refusing V0008 downgrade unless an exact active v4 materialization owns the mirror';
                END IF;
            END IF;
        END
        $$
        """
    )

    for table_name in reversed(PARENA_EPOCH_TABLES):
        op.execute(
            f'DROP TRIGGER IF EXISTS "{_epoch_trigger_name(table_name)}" ON "{table_name}"'
        )

    op.drop_table("parena_case_claims")
    op.drop_table("parena_case_evidence")
    op.drop_table("parena_case_sources")
    op.drop_table("parena_case_matchups")
    op.drop_index("ix_parena_cases_server_environment_status", table_name="parena_cases")
    op.drop_table("parena_cases")
    op.drop_index(
        "ix_arena_source_records_server_status_checked",
        table_name="arena_source_records",
    )
    op.drop_table("arena_source_records")
    op.drop_constraint(
        "uq_arena_counters_counter_defense",
        "arena_counters",
        type_="unique",
    )
