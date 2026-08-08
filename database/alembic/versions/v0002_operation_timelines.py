"""V0002: additive source-separated PVE operation timelines."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "v0002_operation_timelines"
down_revision: str | None = "v0001_b0_read_mirror"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

jsonb = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "operation_timelines",
        sa.Column("source_axis_id", sa.String(140), nullable=False),
        sa.Column("timeline_id", sa.String(140), nullable=True),
        sa.Column("team_id", sa.String(120), nullable=False),
        sa.Column("source_id", sa.String(160), nullable=False),
        sa.Column("source_evidence_id", sa.String(80), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("timeline_variant_name", sa.Text(), nullable=False),
        sa.Column("operation_mode", sa.String(32), nullable=False),
        sa.Column("clock_mode", sa.String(20), nullable=False),
        sa.Column("battle_duration_ms", sa.Integer(), nullable=True),
        sa.Column("initial_auto_state", sa.String(16), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reproducibility", sa.String(32), nullable=False),
        sa.Column("gap_reason", sa.String(48), nullable=False),
        sa.Column("last_verified_at", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.CheckConstraint(
            "operation_mode IN ('AUTO','SEMI_AUTO','MANUAL_TIMELINE')",
            name=op.f("ck_operation_timelines_operation_timeline_mode"),
        ),
        sa.CheckConstraint(
            "clock_mode IN ('COUNTDOWN','ELAPSED','UNKNOWN')",
            name=op.f("ck_operation_timelines_operation_timeline_clock_mode"),
        ),
        sa.CheckConstraint(
            "initial_auto_state IN ('ON','OFF','UNKNOWN')",
            name=op.f("ck_operation_timelines_operation_timeline_initial_auto_state"),
        ),
        sa.CheckConstraint(
            "reproducibility IN ('UNVERIFIED_ON_TW','TW_REPRODUCED','UNKNOWN')",
            name=op.f("ck_operation_timelines_operation_timeline_reproducibility"),
        ),
        sa.CheckConstraint(
            "gap_reason IN ('NONE','INSUFFICIENT_SOURCE_DETAIL','PENDING_EXTRACTION')",
            name=op.f("ck_operation_timelines_operation_timeline_gap_reason"),
        ),
        sa.CheckConstraint(
            "battle_duration_ms IS NULL OR battle_duration_ms > 0",
            name=op.f("ck_operation_timelines_operation_timeline_duration_positive"),
        ),
        sa.CheckConstraint(
            "(status = 'STRUCTURED' AND timeline_id IS NOT NULL "
            "AND clock_mode IN ('COUNTDOWN','ELAPSED') "
            "AND initial_auto_state IN ('ON','OFF') AND gap_reason = 'NONE') "
            "OR (status = 'SOURCE_GAP' AND timeline_id IS NULL "
            "AND clock_mode = 'UNKNOWN' AND battle_duration_ms IS NULL "
            "AND initial_auto_state = 'UNKNOWN' AND reproducibility = 'UNKNOWN' "
            "AND gap_reason IN ('INSUFFICIENT_SOURCE_DETAIL','PENDING_EXTRACTION'))",
            name=op.f("ck_operation_timelines_operation_timeline_status_shape"),
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_operation_timelines_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_evidence_id"],
            ["evidence.evidence_id"],
            name="fk_operation_timelines_source_evidence_id_evidence",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.team_id"],
            name="fk_operation_timelines_team_id_teams",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("source_axis_id", name="pk_operation_timelines"),
        sa.UniqueConstraint("timeline_id", name="uq_operation_timelines_timeline_id"),
        sa.UniqueConstraint(
            "team_id", "source_id", name="uq_operation_timelines_team_source"
        ),
    )
    op.create_index(
        "ix_operation_timelines_team_status",
        "operation_timelines",
        ["team_id", "status"],
        unique=False,
    )

    op.create_table(
        "timeline_steps",
        sa.Column("timeline_step_id", sa.String(140), nullable=False),
        sa.Column("timeline_id", sa.String(140), nullable=False),
        sa.Column("team_id", sa.String(120), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("source_step_no", sa.Integer(), nullable=False),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("trigger_actor_unit_key", sa.String(100), nullable=True),
        sa.Column("time_state", sa.String(20), nullable=False),
        sa.Column("clock_from_ms", sa.Integer(), nullable=True),
        sa.Column("clock_to_ms", sa.Integer(), nullable=True),
        sa.Column("actor_unit_key", sa.String(100), nullable=True),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("target_unit_key", sa.String(100), nullable=True),
        sa.Column("auto_state_after", sa.String(16), nullable=False),
        sa.Column("animation_cue", sa.Text(), nullable=False),
        sa.Column("hp_threshold", sa.String(80), nullable=False),
        sa.Column("tolerance_ms", sa.Integer(), nullable=True),
        sa.Column("criticality", sa.String(20), nullable=False),
        sa.Column("instruction_zh_tw", sa.Text(), nullable=False),
        sa.Column("failure_if_missed", sa.Text(), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("source_payload", jsonb, nullable=False),
        sa.Column("import_run_id", sa.String(36), nullable=False),
        sa.CheckConstraint(
            "sequence_no >= 1",
            name=op.f("ck_timeline_steps_timeline_step_sequence_positive"),
        ),
        sa.CheckConstraint(
            "source_step_no >= 1",
            name=op.f("ck_timeline_steps_timeline_step_source_sequence_positive"),
        ),
        sa.CheckConstraint(
            "trigger_type IN ('CLOCK','UB_READY','ANIMATION_CUE','HP_THRESHOLD',"
            "'WAVE_START','BOSS_ACTION','SOURCE_TEXT_ONLY')",
            name=op.f("ck_timeline_steps_timeline_step_trigger_type"),
        ),
        sa.CheckConstraint(
            "time_state IN ('STATED','NOT_STATED')",
            name=op.f("ck_timeline_steps_timeline_step_time_state"),
        ),
        sa.CheckConstraint(
            "(time_state = 'STATED' AND clock_from_ms IS NOT NULL AND clock_to_ms IS NOT NULL) "
            "OR (time_state = 'NOT_STATED' AND clock_from_ms IS NULL AND clock_to_ms IS NULL)",
            name=op.f("ck_timeline_steps_timeline_step_time_shape"),
        ),
        sa.CheckConstraint(
            "clock_from_ms IS NULL OR clock_from_ms >= 0",
            name=op.f("ck_timeline_steps_timeline_step_clock_from_nonnegative"),
        ),
        sa.CheckConstraint(
            "clock_to_ms IS NULL OR clock_to_ms >= 0",
            name=op.f("ck_timeline_steps_timeline_step_clock_to_nonnegative"),
        ),
        sa.CheckConstraint(
            "tolerance_ms IS NULL OR tolerance_ms >= 0",
            name=op.f("ck_timeline_steps_timeline_step_tolerance_nonnegative"),
        ),
        sa.CheckConstraint(
            "action_type IN ('USE_UB','WAIT','AUTO_ON','AUTO_OFF','SET_ON','SET_OFF',"
            "'PAUSE','RESUME','TARGET','NO_ACTION')",
            name=op.f("ck_timeline_steps_timeline_step_action_type"),
        ),
        sa.CheckConstraint(
            "auto_state_after IN ('ON','OFF','UNKNOWN')",
            name=op.f("ck_timeline_steps_timeline_step_auto_state"),
        ),
        sa.CheckConstraint(
            "criticality IN ('NORMAL','CRITICAL','UNKNOWN')",
            name=op.f("ck_timeline_steps_timeline_step_criticality"),
        ),
        sa.CheckConstraint(
            "action_type NOT IN ('USE_UB','SET_ON','SET_OFF','TARGET') "
            "OR actor_unit_key IS NOT NULL",
            name=op.f("ck_timeline_steps_timeline_step_actor_required"),
        ),
        sa.CheckConstraint(
            "action_type != 'TARGET' OR target_unit_key IS NOT NULL",
            name=op.f("ck_timeline_steps_timeline_step_target_required"),
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_timeline_steps_import_run_id_import_runs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["timeline_id"],
            ["operation_timelines.timeline_id"],
            name="fk_timeline_steps_timeline_id_operation_timelines",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.team_id"],
            name="fk_timeline_steps_team_id_teams",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id", "trigger_actor_unit_key"],
            ["team_members.team_id", "team_members.unit_key"],
            name="fk_timeline_steps_trigger_actor_team_member",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["team_id", "actor_unit_key"],
            ["team_members.team_id", "team_members.unit_key"],
            name="fk_timeline_steps_actor_team_member",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["team_id", "target_unit_key"],
            ["team_members.team_id", "team_members.unit_key"],
            name="fk_timeline_steps_target_team_member",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("timeline_step_id", name="pk_timeline_steps"),
        sa.UniqueConstraint(
            "timeline_id", "sequence_no", name="uq_timeline_steps_timeline_sequence"
        ),
    )
    op.create_index(
        "ix_timeline_steps_timeline_sequence",
        "timeline_steps",
        ["timeline_id", "sequence_no"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_timeline_steps_timeline_sequence", table_name="timeline_steps")
    op.drop_table("timeline_steps")
    op.drop_index("ix_operation_timelines_team_status", table_name="operation_timelines")
    op.drop_table("operation_timelines")
