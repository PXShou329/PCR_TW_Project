"""V0006: normalized Battle Arena defense and exact-counter serving slice."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "v0006_arena_counter_slice"
down_revision: str | None = "v0005_borrowed_tristate"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

jsonb = postgresql.JSONB(astext_type=sa.Text())

ARENA_EPOCH_TABLES = (
    "arena_defenses",
    "arena_defense_members",
    "arena_counters",
    "arena_counter_members",
    "arena_counter_evidence",
    "arena_counter_claims",
)


def _epoch_trigger_name(table_name: str) -> str:
    return f"trg_{table_name}_materialization_epoch"


def upgrade() -> None:
    op.create_table(
        "arena_defenses",
        sa.Column("defense_id", sa.String(140), nullable=False),
        sa.Column("server", sa.String(16), nullable=False),
        sa.Column("formation_signature", sa.String(600), nullable=False),
        sa.Column("environment_version", sa.String(100), nullable=False),
        sa.Column("arena_bracket", sa.String(100), nullable=False),
        sa.Column("core_tags", jsonb, nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("verified_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.CheckConstraint(
            "server IN ('TW','JP')",
            name=op.f("ck_arena_defenses_arena_defense_server"),
        ),
        sa.CheckConstraint(
            "status IN "
            "('VERIFIED','PROVISIONAL','SINGLE_REPORT','STALE','REJECTED')",
            name=op.f("ck_arena_defenses_arena_defense_status"),
        ),
        sa.CheckConstraint(
            "review_status IN ('CURRENT','REVALIDATE_REQUIRED','STALE')",
            name=op.f("ck_arena_defenses_arena_defense_review_status"),
        ),
        sa.CheckConstraint(
            "length(formation_signature) > 0",
            name=op.f("ck_arena_defenses_arena_defense_signature_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_arena_defenses_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("defense_id", name="pk_arena_defenses"),
        sa.UniqueConstraint(
            "server",
            "environment_version",
            "formation_signature",
            name="uq_arena_defenses_server_environment_signature",
        ),
    )
    op.create_index(
        "ix_arena_defenses_server_status",
        "arena_defenses",
        ["server", "status", "review_status"],
        unique=False,
    )

    op.create_table(
        "arena_defense_members",
        sa.Column("defense_id", sa.String(140), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("unit_key", sa.String(100), nullable=False),
        sa.CheckConstraint(
            "slot BETWEEN 1 AND 5",
            name=op.f("ck_arena_defense_members_arena_defense_member_slot_range"),
        ),
        sa.ForeignKeyConstraint(
            ["defense_id"],
            ["arena_defenses.defense_id"],
            name="fk_arena_defense_members_defense_id_arena_defenses",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["unit_key"],
            ["characters.unit_key"],
            name="fk_arena_defense_members_unit_key_characters",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "defense_id",
            "slot",
            name="pk_arena_defense_members",
        ),
        sa.UniqueConstraint(
            "defense_id",
            "unit_key",
            name="uq_arena_defense_members_defense_unit",
        ),
    )

    op.create_table(
        "arena_counters",
        sa.Column("counter_id", sa.String(140), nullable=False),
        sa.Column("defense_id", sa.String(140), nullable=False),
        sa.Column("formation_signature", sa.String(600), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("match_type", sa.String(16), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("verification", sa.String(32), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("wins", sa.Integer(), nullable=True),
        sa.Column("losses", sa.Integer(), nullable=True),
        sa.Column("empirical_win_rate", sa.Integer(), nullable=True),
        sa.Column("randomness", sa.Text(), nullable=False),
        sa.Column("rng_risk", sa.String(16), nullable=False),
        sa.Column("claim_confidence", sa.String(8), nullable=False),
        sa.Column("reproducibility", sa.String(32), nullable=False),
        sa.Column("source_tier", sa.String(40), nullable=False),
        sa.Column("source_record_count", sa.Integer(), nullable=False),
        sa.Column("source_platforms", jsonb, nullable=False),
        sa.Column("tw_availability_check", sa.String(20), nullable=False),
        sa.Column("unavailable_unit_ids", jsonb, nullable=False),
        sa.Column("required_upgrade_check", sa.String(24), nullable=False),
        sa.Column("operation_mode", sa.String(24), nullable=False),
        sa.Column("environment_match", sa.String(20), nullable=False),
        sa.Column("speed_conditions", sa.Text(), nullable=False),
        sa.Column("initial_action_notes", sa.Text(), nullable=False),
        sa.Column("verified_date", sa.Date(), nullable=False),
        sa.Column("last_review_due", sa.Date(), nullable=False),
        sa.Column("record_date_min", sa.Date(), nullable=False),
        sa.Column("record_date_max", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.CheckConstraint(
            "status IN "
            "('VERIFIED','PROVISIONAL','SINGLE_REPORT','STALE','REJECTED')",
            name=op.f("ck_arena_counters_arena_counter_status"),
        ),
        sa.CheckConstraint(
            "match_type = 'EXACT'",
            name=op.f("ck_arena_counters_arena_counter_match_type"),
        ),
        sa.CheckConstraint(
            "outcome IN ('WIN','LOSS','MIXED','UNKNOWN')",
            name=op.f("ck_arena_counters_arena_counter_outcome"),
        ),
        sa.CheckConstraint(
            "verification IN ('SCREENSHOT_RESULT','VIDEO_RESULT','TEXT_REPORT','UNKNOWN')",
            name=op.f("ck_arena_counters_arena_counter_verification"),
        ),
        sa.CheckConstraint(
            "(sample_size IS NULL AND wins IS NULL AND losses IS NULL) OR "
            "(sample_size IS NOT NULL AND wins IS NOT NULL AND losses IS NOT NULL "
            "AND sample_size = wins + losses)",
            name=op.f("ck_arena_counters_arena_counter_sample_shape"),
        ),
        sa.CheckConstraint(
            "(outcome != 'WIN' OR (wins IS NOT NULL AND wins >= 1)) AND "
            "(outcome != 'LOSS' OR (losses IS NOT NULL AND losses >= 1))",
            name=op.f("ck_arena_counters_arena_counter_outcome_count"),
        ),
        sa.CheckConstraint(
            "sample_size IS NULL OR sample_size >= 1",
            name=op.f("ck_arena_counters_arena_counter_sample_size_positive"),
        ),
        sa.CheckConstraint(
            "wins IS NULL OR wins >= 0",
            name=op.f("ck_arena_counters_arena_counter_wins_nonnegative"),
        ),
        sa.CheckConstraint(
            "losses IS NULL OR losses >= 0",
            name=op.f("ck_arena_counters_arena_counter_losses_nonnegative"),
        ),
        sa.CheckConstraint(
            "empirical_win_rate IS NULL OR "
            "(sample_size IS NOT NULL AND empirical_win_rate BETWEEN 0 AND 100 "
            "AND sample_size >= 2)",
            name=op.f("ck_arena_counters_arena_counter_empirical_rate"),
        ),
        sa.CheckConstraint(
            "status != 'SINGLE_REPORT' OR empirical_win_rate IS NULL",
            name=op.f(
                "ck_arena_counters_arena_counter_single_report_no_empirical_rate"
            ),
        ),
        sa.CheckConstraint(
            "rng_risk IN ('LOW','MEDIUM','HIGH','UNKNOWN')",
            name=op.f("ck_arena_counters_arena_counter_rng_risk"),
        ),
        sa.CheckConstraint(
            "claim_confidence IN ('B','C','D','E')",
            name=op.f("ck_arena_counters_arena_counter_claim_confidence"),
        ),
        sa.CheckConstraint(
            "status != 'SINGLE_REPORT' OR claim_confidence = 'D'",
            name=op.f("ck_arena_counters_arena_counter_single_report_confidence"),
        ),
        sa.CheckConstraint(
            "status != 'VERIFIED' OR claim_confidence IN ('B','C')",
            name=op.f("ck_arena_counters_arena_counter_verified_confidence"),
        ),
        sa.CheckConstraint(
            "reproducibility IN "
            "('CONFIRMED','UNVERIFIED_REPEATABILITY',"
            "'UNVERIFIED_ON_TW','UNKNOWN')",
            name=op.f("ck_arena_counters_arena_counter_reproducibility"),
        ),
        sa.CheckConstraint(
            "status != 'VERIFIED' OR reproducibility = 'CONFIRMED'",
            name=op.f("ck_arena_counters_arena_counter_verified_reproducibility"),
        ),
        sa.CheckConstraint(
            "status != 'VERIFIED' OR ("
            "outcome = 'WIN' AND verification != 'UNKNOWN' "
            "AND source_tier IN "
            "('OFFICIAL','MAJOR_GUIDE','STRUCTURED_DB','COMMUNITY_WIKI',"
            "'MULTI_PLAYER_REPORT') "
            "AND source_record_count >= 2 "
            "AND sample_size IS NOT NULL AND sample_size >= 2 "
            "AND wins IS NOT NULL AND wins >= 2 "
            "AND environment_match = 'EXACT')",
            name=op.f(
                "ck_arena_counters_arena_counter_verified_multi_source_shape"
            ),
        ),
        sa.CheckConstraint(
            "length(randomness) > 0",
            name=op.f("ck_arena_counters_arena_counter_randomness_nonempty"),
        ),
        sa.CheckConstraint(
            "length(source_tier) > 0",
            name=op.f("ck_arena_counters_arena_counter_source_tier_nonempty"),
        ),
        sa.CheckConstraint(
            "source_record_count >= 1",
            name=op.f("ck_arena_counters_arena_counter_source_record_count_positive"),
        ),
        sa.CheckConstraint(
            "tw_availability_check IN ('PASS','FAIL','UNVERIFIED')",
            name=op.f("ck_arena_counters_arena_counter_tw_availability_check"),
        ),
        sa.CheckConstraint(
            "required_upgrade_check IN ('PASS','FAIL','UNKNOWN','NOT_APPLICABLE')",
            name=op.f("ck_arena_counters_arena_counter_required_upgrade_check"),
        ),
        sa.CheckConstraint(
            "record_date_min <= record_date_max",
            name=op.f("ck_arena_counters_arena_counter_record_date_range"),
        ),
        sa.CheckConstraint(
            "operation_mode IN ('AUTO_SYSTEM','MANUAL','UNKNOWN')",
            name=op.f("ck_arena_counters_arena_counter_operation_mode"),
        ),
        sa.CheckConstraint(
            "environment_match IN ('EXACT','COMPATIBLE','MISMATCH','UNKNOWN')",
            name=op.f("ck_arena_counters_arena_counter_environment_match"),
        ),
        sa.CheckConstraint(
            "length(formation_signature) > 0",
            name=op.f("ck_arena_counters_arena_counter_signature_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["defense_id"],
            ["arena_defenses.defense_id"],
            name="fk_arena_counters_defense_id_arena_defenses",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_arena_counters_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("counter_id", name="pk_arena_counters"),
        sa.UniqueConstraint(
            "defense_id",
            "formation_signature",
            name="uq_arena_counters_defense_signature",
        ),
    )
    op.create_index(
        "ix_arena_counters_defense_status",
        "arena_counters",
        ["defense_id", "status"],
        unique=False,
    )

    op.create_table(
        "arena_counter_members",
        sa.Column("counter_id", sa.String(140), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("unit_key", sa.String(100), nullable=False),
        sa.CheckConstraint(
            "slot BETWEEN 1 AND 5",
            name=op.f("ck_arena_counter_members_arena_counter_member_slot_range"),
        ),
        sa.ForeignKeyConstraint(
            ["counter_id"],
            ["arena_counters.counter_id"],
            name="fk_arena_counter_members_counter_id_arena_counters",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["unit_key"],
            ["characters.unit_key"],
            name="fk_arena_counter_members_unit_key_characters",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "counter_id",
            "slot",
            name="pk_arena_counter_members",
        ),
        sa.UniqueConstraint(
            "counter_id",
            "unit_key",
            name="uq_arena_counter_members_counter_unit",
        ),
    )

    op.create_table(
        "arena_counter_evidence",
        sa.Column("counter_id", sa.String(140), nullable=False),
        sa.Column("evidence_id", sa.String(80), nullable=False),
        sa.ForeignKeyConstraint(
            ["counter_id"],
            ["arena_counters.counter_id"],
            name="fk_arena_counter_evidence_counter_id_arena_counters",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.evidence_id"],
            name="fk_arena_counter_evidence_evidence_id_evidence",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "counter_id",
            "evidence_id",
            name="pk_arena_counter_evidence",
        ),
    )

    op.create_table(
        "arena_counter_claims",
        sa.Column("counter_id", sa.String(140), nullable=False),
        sa.Column("claim_id", sa.String(140), nullable=False),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["claims.claim_id"],
            name="fk_arena_counter_claims_claim_id_claims",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["counter_id"],
            ["arena_counters.counter_id"],
            name="fk_arena_counter_claims_counter_id_arena_counters",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "counter_id",
            "claim_id",
            name="pk_arena_counter_claims",
        ),
    )

    for table_name in ARENA_EPOCH_TABLES:
        trigger_name = _epoch_trigger_name(table_name)
        op.execute(
            f'CREATE TRIGGER "{trigger_name}" '
            f'AFTER INSERT OR UPDATE OR DELETE ON "{table_name}" '
            "FOR EACH STATEMENT EXECUTE FUNCTION pcr_bump_materialization_epoch()"
        )


def downgrade() -> None:
    # Serialize with canonical activation, then keep concurrent direct writes
    # out until this migration transaction commits. The table order matches
    # the importer's FK-safe Arena delete order.
    op.execute("SELECT pg_advisory_xact_lock(344726848049)")
    for table_name in reversed(ARENA_EPOCH_TABLES):
        op.execute(f'LOCK TABLE "{table_name}" IN ACCESS EXCLUSIVE MODE')
    op.execute('LOCK TABLE "materialization_state" IN ACCESS EXCLUSIVE MODE')
    op.execute('LOCK TABLE "core_revisions" IN SHARE MODE')
    op.execute('LOCK TABLE "import_runs" IN SHARE MODE')

    # Empty tables alone are insufficient: a verified legacy-v2 activation
    # must own the mirror (or this must be a genuinely fresh database).
    op.execute(
        """
        DO $$
        DECLARE
            state_row materialization_state%ROWTYPE;
            active_run_status TEXT;
            active_revision_status TEXT;
            active_run_materialization JSONB;
            revision_materialization_sha256 TEXT;
        BEGIN
            SELECT * INTO state_row
            FROM materialization_state
            WHERE id = 1;

            IF NOT FOUND THEN
                RAISE EXCEPTION
                    'refusing V0006 downgrade without materialization state';
            END IF;

            IF state_row.active_revision_id IS NULL
               AND state_row.active_import_run_id IS NULL
               AND state_row.materialization_sha256 IS NULL
            THEN
                IF state_row.serving_counts <> '{}'::jsonb
                   OR EXISTS (SELECT 1 FROM core_revisions LIMIT 1)
                   OR EXISTS (SELECT 1 FROM import_runs LIMIT 1)
                THEN
                    RAISE EXCEPTION
                        'refusing V0006 downgrade from a non-fresh unowned mirror';
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
                   OR jsonb_typeof(active_run_materialization)
                      IS DISTINCT FROM 'object'
                   OR active_run_materialization ->> 'schema_version'
                      IS DISTINCT FROM '2'
                   OR active_run_materialization ->> 'sha256'
                      IS DISTINCT FROM state_row.materialization_sha256
                   OR revision_materialization_sha256
                      IS DISTINCT FROM state_row.materialization_sha256
                   OR jsonb_typeof(active_run_materialization -> 'tables')
                      IS DISTINCT FROM 'object'
                   OR (
                       SELECT count(*)
                       FROM jsonb_object_keys(
                           CASE
                               WHEN jsonb_typeof(active_run_materialization -> 'tables') = 'object'
                               THEN active_run_materialization -> 'tables'
                               ELSE '{}'::jsonb
                           END
                       )
                   ) <> 12
                   OR NOT (
                       (active_run_materialization -> 'tables') ?& ARRAY[
                           'stages',
                           'teams',
                           'team_members',
                           'characters',
                           'evidence',
                           'claims',
                           'stage_evidence',
                           'stage_claims',
                           'team_evidence',
                           'claim_evidence',
                           'operation_timelines',
                           'timeline_steps'
                       ]
                   )
                THEN
                    RAISE EXCEPTION
                        'refusing V0006 downgrade unless a verified legacy v2 materialization owns the mirror';
                END IF;
            END IF;

            IF EXISTS (SELECT 1 FROM arena_defenses LIMIT 1)
               OR EXISTS (SELECT 1 FROM arena_defense_members LIMIT 1)
               OR EXISTS (SELECT 1 FROM arena_counters LIMIT 1)
               OR EXISTS (SELECT 1 FROM arena_counter_members LIMIT 1)
               OR EXISTS (SELECT 1 FROM arena_counter_evidence LIMIT 1)
               OR EXISTS (SELECT 1 FROM arena_counter_claims LIMIT 1)
            THEN
                RAISE EXCEPTION
                    'refusing V0006 downgrade while Arena serving rows exist';
            END IF;
        END
        $$
        """
    )

    for table_name in reversed(ARENA_EPOCH_TABLES):
        trigger_name = _epoch_trigger_name(table_name)
        op.execute(
            f'DROP TRIGGER IF EXISTS "{trigger_name}" ON "{table_name}"'
        )

    op.drop_table("arena_counter_claims")
    op.drop_table("arena_counter_evidence")
    op.drop_table("arena_counter_members")
    op.drop_index("ix_arena_counters_defense_status", table_name="arena_counters")
    op.drop_table("arena_counters")
    op.drop_table("arena_defense_members")
    op.drop_index("ix_arena_defenses_server_status", table_name="arena_defenses")
    op.drop_table("arena_defenses")
