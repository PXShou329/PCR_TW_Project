"""V0007: normalized Gacha future-sight serving closure."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "v0007_gacha_timeline_slice"
down_revision: str | None = "v0006_arena_counter_slice"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

jsonb = postgresql.JSONB(astext_type=sa.Text())

GACHA_EPOCH_TABLES = (
    "gacha_timeline_events",
    "gacha_timeline_evidence",
    "gacha_timeline_claims",
    "gacha_community_sources",
    "gacha_timeline_community_sources",
)


def _epoch_trigger_name(table_name: str) -> str:
    return f"trg_{table_name}_materialization_epoch"


def upgrade() -> None:
    op.create_table(
        "gacha_timeline_events",
        sa.Column("event_id", sa.String(160), nullable=False),
        sa.Column("source_server", sa.String(16), nullable=False),
        sa.Column("target_server", sa.String(16), nullable=False),
        sa.Column("jp_date", sa.Date(), nullable=False),
        sa.Column("model_estimate_start", sa.Date(), nullable=True),
        sa.Column("model_estimate_end", sa.Date(), nullable=True),
        sa.Column("tw_estimate_start", sa.Date(), nullable=True),
        sa.Column("tw_estimate_end", sa.Date(), nullable=True),
        sa.Column("forecast_method", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Text(), nullable=False),
        sa.Column("character_name_jp", sa.String(200), nullable=False),
        sa.Column("tw_name", sa.String(200), nullable=True),
        sa.Column("pool_type", sa.String(160), nullable=False),
        sa.Column("limited_status", sa.String(16), nullable=False),
        sa.Column("limited_claim_id", sa.String(140), nullable=True),
        sa.Column("arena_value", sa.Text(), nullable=False),
        sa.Column("p_arena_value", sa.Text(), nullable=False),
        sa.Column("pve_value", sa.Text(), nullable=False),
        sa.Column("clan_value", sa.Text(), nullable=False),
        sa.Column("future_upgrade", sa.Text(), nullable=False),
        sa.Column("relative_priority", sa.Text(), nullable=False),
        sa.Column("anchor_track", sa.String(40), nullable=False),
        sa.Column("anchor_count", sa.Integer(), nullable=False),
        sa.Column("forecast_basis", sa.Text(), nullable=False),
        sa.Column("last_verified", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("maturity", sa.String(16), nullable=False),
        sa.Column("last_review_due", sa.Date(), nullable=False),
        sa.Column("community_estimate_start", sa.Date(), nullable=True),
        sa.Column("community_estimate_end", sa.Date(), nullable=True),
        sa.Column("community_order_consensus", sa.Text(), nullable=False),
        sa.Column("community_source_count", sa.Integer(), nullable=False),
        sa.Column("community_last_checked", sa.Date(), nullable=True),
        sa.Column("community_disagreement", sa.Text(), nullable=False),
        sa.Column("forecast_notes", sa.Text(), nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.CheckConstraint("source_server = 'JP'", name=op.f("ck_gacha_timeline_events_gacha_event_source_server")),
        sa.CheckConstraint("target_server = 'TW'", name=op.f("ck_gacha_timeline_events_gacha_event_target_server")),
        sa.CheckConstraint(
            "forecast_method IN ('MODEL_ONLY','MODEL_PLUS_COMMUNITY','OFFICIAL_OVERRIDE')",
            name=op.f("ck_gacha_timeline_events_gacha_event_forecast_method"),
        ),
        sa.CheckConstraint(
            "limited_status IN ('YES','NO','UNKNOWN')",
            name=op.f("ck_gacha_timeline_events_gacha_event_limited_status"),
        ),
        sa.CheckConstraint(
            "(limited_status = 'UNKNOWN' AND limited_claim_id IS NULL) OR "
            "(limited_status IN ('YES','NO') AND limited_claim_id IS NOT NULL)",
            name=op.f("ck_gacha_timeline_events_gacha_event_limited_claim_shape"),
        ),
        sa.CheckConstraint("anchor_count >= 0", name=op.f("ck_gacha_timeline_events_gacha_event_anchor_count_nonnegative")),
        sa.CheckConstraint("community_source_count >= 0", name=op.f("ck_gacha_timeline_events_gacha_event_community_count_nonnegative")),
        sa.CheckConstraint(
            "(model_estimate_start IS NULL AND model_estimate_end IS NULL) OR "
            "(model_estimate_start IS NOT NULL AND model_estimate_end IS NOT NULL AND model_estimate_start <= model_estimate_end)",
            name=op.f("ck_gacha_timeline_events_gacha_event_model_range"),
        ),
        sa.CheckConstraint(
            "(tw_estimate_start IS NULL AND tw_estimate_end IS NULL) OR "
            "(tw_estimate_start IS NOT NULL AND tw_estimate_end IS NOT NULL AND tw_estimate_start <= tw_estimate_end)",
            name=op.f("ck_gacha_timeline_events_gacha_event_tw_range"),
        ),
        sa.CheckConstraint(
            "(community_estimate_start IS NULL AND community_estimate_end IS NULL) OR "
            "(community_estimate_start IS NOT NULL AND community_estimate_end IS NOT NULL AND community_estimate_start <= community_estimate_end)",
            name=op.f("ck_gacha_timeline_events_gacha_event_community_range"),
        ),
        sa.CheckConstraint("maturity IN ('MATURE','RESEARCH')", name=op.f("ck_gacha_timeline_events_gacha_event_maturity")),
        sa.CheckConstraint(
            "maturity != 'RESEARCH' OR (arena_value = 'NOT_EVALUATED' AND p_arena_value = 'NOT_EVALUATED' AND pve_value = 'NOT_EVALUATED' AND clan_value = 'NOT_EVALUATED' AND relative_priority = 'NOT_EVALUATED' AND future_upgrade IN ('UNKNOWN','NOT_EVALUATED'))",
            name=op.f("ck_gacha_timeline_events_gacha_event_research_not_evaluated"),
        ),
        sa.CheckConstraint(
            "forecast_method != 'MODEL_ONLY' OR (tw_estimate_start = model_estimate_start AND tw_estimate_end = model_estimate_end AND community_source_count = 0)",
            name=op.f("ck_gacha_timeline_events_gacha_event_model_only_shape"),
        ),
        sa.CheckConstraint(
            "forecast_method != 'MODEL_PLUS_COMMUNITY' OR (community_estimate_start IS NOT NULL AND community_estimate_end IS NOT NULL AND tw_estimate_start IS NOT NULL AND tw_estimate_end IS NOT NULL AND model_estimate_start IS NOT NULL AND model_estimate_end IS NOT NULL AND tw_estimate_start <= model_estimate_start AND tw_estimate_start <= community_estimate_start AND tw_estimate_end >= model_estimate_end AND tw_estimate_end >= community_estimate_end)",
            name=op.f("ck_gacha_timeline_events_gacha_event_model_plus_community_shape"),
        ),
        sa.ForeignKeyConstraint(
            ["limited_claim_id"], ["claims.claim_id"],
            name="fk_gacha_timeline_events_limited_claim_id_claims",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"], ["import_runs.id"],
            name="fk_gacha_timeline_events_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_gacha_timeline_events")),
    )
    op.create_index(
        "ix_gacha_timeline_events_target_date",
        "gacha_timeline_events",
        ["target_server", "tw_estimate_start", "status"],
        unique=False,
    )

    op.create_table(
        "gacha_community_sources",
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(100), nullable=False),
        sa.Column("author", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("last_seen_update", sa.Date(), nullable=True),
        sa.Column("coverage_start", sa.String(10), nullable=True),
        sa.Column("coverage_end", sa.String(10), nullable=True),
        sa.Column("update_status", sa.String(24), nullable=False),
        sa.Column("confidence_cap", sa.String(16), nullable=False),
        sa.Column("usage", sa.Text(), nullable=False),
        sa.Column("last_checked", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('MAINTAINED_TABLE','FORUM_TIMELINE','CREATOR_ANALYSIS','VIDEO_SERIES')",
            name=op.f("ck_gacha_community_sources_gacha_community_source_type"),
        ),
        sa.CheckConstraint(
            "update_status IN ('PENDING_FETCH','CHECKED','STALE')",
            name=op.f("ck_gacha_community_sources_gacha_community_update_status"),
        ),
        sa.CheckConstraint(
            "confidence_cap IN ('C','D','E')",
            name=op.f("ck_gacha_community_sources_gacha_community_confidence_cap"),
        ),
        sa.CheckConstraint(
            "(coverage_start IS NULL AND coverage_end IS NULL) OR (coverage_start IS NOT NULL AND coverage_end IS NOT NULL)",
            name=op.f("ck_gacha_community_sources_gacha_community_coverage_range"),
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"], ["import_runs.id"],
            name="fk_gacha_community_sources_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("source_id", name=op.f("pk_gacha_community_sources")),
    )
    op.create_index(
        "ix_gacha_community_sources_status_checked",
        "gacha_community_sources",
        ["update_status", "last_checked"],
        unique=False,
    )

    op.create_table(
        "gacha_timeline_evidence",
        sa.Column("event_id", sa.String(160), nullable=False),
        sa.Column("evidence_id", sa.String(80), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["gacha_timeline_events.event_id"], name="fk_gacha_timeline_evidence_event_id_gacha_timeline_events", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.evidence_id"], name="fk_gacha_timeline_evidence_evidence_id_evidence", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("event_id", "evidence_id", name=op.f("pk_gacha_timeline_evidence")),
    )
    op.create_table(
        "gacha_timeline_claims",
        sa.Column("event_id", sa.String(160), nullable=False),
        sa.Column("claim_id", sa.String(140), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["gacha_timeline_events.event_id"], name="fk_gacha_timeline_claims_event_id_gacha_timeline_events", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.claim_id"], name="fk_gacha_timeline_claims_claim_id_claims", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("event_id", "claim_id", name=op.f("pk_gacha_timeline_claims")),
    )
    op.create_table(
        "gacha_timeline_community_sources",
        sa.Column("event_id", sa.String(160), nullable=False),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["gacha_timeline_events.event_id"], name="fk_gacha_tl_community_event", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["gacha_community_sources.source_id"], name="fk_gacha_tl_community_source", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("event_id", "source_id", name=op.f("pk_gacha_timeline_community_sources")),
    )

    for table_name in GACHA_EPOCH_TABLES:
        op.execute(
            f'CREATE TRIGGER "{_epoch_trigger_name(table_name)}" '
            f'AFTER INSERT OR UPDATE OR DELETE ON "{table_name}" '
            "FOR EACH STATEMENT EXECUTE FUNCTION pcr_bump_materialization_epoch()"
        )


def downgrade() -> None:
    op.execute("SELECT pg_advisory_xact_lock(344726848049)")
    for table_name in reversed(GACHA_EPOCH_TABLES):
        op.execute(f'LOCK TABLE "{table_name}" IN ACCESS EXCLUSIVE MODE')
    op.execute('LOCK TABLE "materialization_state" IN ACCESS EXCLUSIVE MODE')
    op.execute('LOCK TABLE "core_revisions" IN SHARE MODE')
    op.execute('LOCK TABLE "import_runs" IN SHARE MODE')

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
                    'refusing V0007 downgrade without materialization state';
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
                        'refusing V0007 downgrade from a non-fresh unowned mirror';
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
                      IS DISTINCT FROM '3'
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
                   ) <> 18
                   OR NOT (
                       (active_run_materialization -> 'tables') ?& ARRAY[
                           'stages', 'teams', 'team_members', 'characters',
                           'evidence', 'claims', 'stage_evidence', 'stage_claims',
                           'team_evidence', 'claim_evidence', 'operation_timelines',
                           'timeline_steps', 'arena_defenses', 'arena_defense_members',
                           'arena_counters', 'arena_counter_members',
                           'arena_counter_evidence', 'arena_counter_claims'
                       ]
                   )
                   OR jsonb_typeof(state_row.serving_counts)
                      IS DISTINCT FROM 'object'
                   OR (
                       SELECT count(*)
                       FROM jsonb_object_keys(
                           CASE
                               WHEN jsonb_typeof(state_row.serving_counts) = 'object'
                               THEN state_row.serving_counts
                               ELSE '{}'::jsonb
                           END
                       )
                   ) <> 18
                   OR NOT (
                       state_row.serving_counts ?& ARRAY[
                           'stages', 'teams', 'team_members', 'characters',
                           'evidence', 'claims', 'stage_evidence', 'stage_claims',
                           'team_evidence', 'claim_evidence', 'operation_timelines',
                           'timeline_steps', 'arena_defenses', 'arena_defense_members',
                           'arena_counters', 'arena_counter_members',
                           'arena_counter_evidence', 'arena_counter_claims'
                       ]
                   )
                   OR EXISTS (
                       SELECT 1
                       FROM jsonb_each(
                           CASE
                               WHEN jsonb_typeof(active_run_materialization -> 'tables') = 'object'
                               THEN active_run_materialization -> 'tables'
                               ELSE '{}'::jsonb
                           END
                       ) AS table_entry(table_name, table_manifest)
                       WHERE jsonb_typeof(table_manifest) IS DISTINCT FROM 'object'
                          OR jsonb_typeof(table_manifest -> 'primary_keys')
                             IS DISTINCT FROM 'array'
                          OR jsonb_typeof(state_row.serving_counts -> table_name)
                             IS DISTINCT FROM 'number'
                          OR (state_row.serving_counts ->> table_name)::integer
                             IS DISTINCT FROM jsonb_array_length(
                                 table_manifest -> 'primary_keys'
                             )
                   )
                THEN
                    RAISE EXCEPTION
                        'refusing V0007 downgrade unless a verified Arena v3 materialization owns the mirror';
                END IF;
            END IF;

            IF EXISTS (SELECT 1 FROM gacha_timeline_events LIMIT 1)
               OR EXISTS (SELECT 1 FROM gacha_timeline_evidence LIMIT 1)
               OR EXISTS (SELECT 1 FROM gacha_timeline_claims LIMIT 1)
               OR EXISTS (SELECT 1 FROM gacha_community_sources LIMIT 1)
               OR EXISTS (SELECT 1 FROM gacha_timeline_community_sources LIMIT 1)
            THEN
                RAISE EXCEPTION
                    'refusing V0007 downgrade while Gacha serving rows exist';
            END IF;
        END
        $$
        """
    )

    for table_name in reversed(GACHA_EPOCH_TABLES):
        op.execute(
            f'DROP TRIGGER IF EXISTS "{_epoch_trigger_name(table_name)}" ON "{table_name}"'
        )

    op.drop_table("gacha_timeline_community_sources")
    op.drop_table("gacha_timeline_claims")
    op.drop_table("gacha_timeline_evidence")
    op.drop_index(
        "ix_gacha_community_sources_status_checked",
        table_name="gacha_community_sources",
    )
    op.drop_table("gacha_community_sources")
    op.drop_index(
        "ix_gacha_timeline_events_target_date",
        table_name="gacha_timeline_events",
    )
    op.drop_table("gacha_timeline_events")
