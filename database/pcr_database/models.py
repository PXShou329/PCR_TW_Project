from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

json_type = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class ImportRun(Base):
    __tablename__ = "import_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fixture_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    canonical_source: Mapped[str] = mapped_column(String(80), nullable=False)
    research_core_version: Mapped[str] = mapped_column(String(40), nullable=False)
    application_version: Mapped[str] = mapped_column(String(40), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    row_counts: Mapped[dict[str, int]] = mapped_column(json_type, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('RUNNING','SUCCEEDED','FAILED')", name="import_status"),
    )


class Character(Base):
    __tablename__ = "characters"

    unit_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    tw_name: Mapped[str] = mapped_column(String(160), nullable=False)
    jp_name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    tw_release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    availability_status: Mapped[str] = mapped_column(String(32), nullable=False)
    ue1_status: Mapped[str] = mapped_column(String(32), nullable=False)
    ue2_status: Mapped[str] = mapped_column(String(32), nullable=False)
    six_star_status: Mapped[str] = mapped_column(String(32), nullable=False)
    connect_rank_status: Mapped[str] = mapped_column(String(32), nullable=False)
    element: Mapped[str] = mapped_column(String(32), nullable=False)
    source_evidence_ids: Mapped[list[str]] = mapped_column(json_type, nullable=False)
    last_verified: Mapped[date] = mapped_column(Date, nullable=False)
    last_review_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("import_runs.id", ondelete="RESTRICT"), nullable=False
    )


class Claim(Base):
    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(String(140), primary_key=True)
    module: Mapped[str] = mapped_column(String(40), nullable=False)
    server: Mapped[str] = mapped_column(String(40), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False)
    claim_confidence: Mapped[str] = mapped_column(String(8), nullable=False)
    independence_check: Mapped[str] = mapped_column(String(20), nullable=False)
    version_match: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    verified_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_review_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    affected_files: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    declared_evidence_ids: Mapped[list[str]] = mapped_column(json_type, nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("import_runs.id", ondelete="RESTRICT"), nullable=False
    )


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    declared_claim_id: Mapped[str | None] = mapped_column(String(140), nullable=True)
    linked_claim_id: Mapped[str | None] = mapped_column(
        ForeignKey("claims.claim_id", ondelete="RESTRICT"), nullable=True
    )
    module: Mapped[str] = mapped_column(String(40), nullable=False)
    server: Mapped[str] = mapped_column(String(40), nullable=False)
    source_tier: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_confidence: Mapped[str] = mapped_column(String(8), nullable=False)
    source_title: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    published_date_precision: Mapped[str] = mapped_column(String(20), nullable=False)
    verified_date: Mapped[date] = mapped_column(Date, nullable=False)
    claim_summary: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    affected_files: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("import_runs.id", ondelete="RESTRICT"), nullable=False
    )


class Stage(Base):
    __tablename__ = "stages"

    guide_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    server: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    area: Mapped[str] = mapped_column(String(80), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    verified_date: Mapped[date] = mapped_column(Date, nullable=False)
    applicable_version: Mapped[str] = mapped_column(String(80), nullable=False)
    team_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_tier: Mapped[str] = mapped_column(String(40), nullable=False)
    claim_confidence: Mapped[str] = mapped_column(String(8), nullable=False)
    reproducibility: Mapped[str] = mapped_column(String(32), nullable=False)
    last_review_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("import_runs.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        CheckConstraint("team_count >= 0", name="stage_team_count_nonnegative"),
        Index("ix_stages_server_mode_area_stage", "server", "mode", "area", "stage"),
    )


class Team(Base):
    __tablename__ = "teams"

    team_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    guide_id: Mapped[str] = mapped_column(
        ForeignKey("stages.guide_id", ondelete="RESTRICT"), nullable=False
    )
    server: Mapped[str] = mapped_column(String(16), nullable=False)
    stage_label: Mapped[str] = mapped_column(String(100), nullable=False)
    support_slot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    operation_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    requirements: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    requirements_raw: Mapped[str] = mapped_column(Text, nullable=False)
    clear_status: Mapped[str] = mapped_column(String(32), nullable=False)
    stability: Mapped[str] = mapped_column(String(80), nullable=False)
    source_ids: Mapped[list[str]] = mapped_column(json_type, nullable=False)
    tw_availability_check: Mapped[str] = mapped_column(String(20), nullable=False)
    verified_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_review_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    signature: Mapped[str] = mapped_column(String(600), nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("import_runs.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("guide_id", "signature", name="uq_teams_guide_signature"),
    )


class TeamMember(Base):
    __tablename__ = "team_members"

    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.team_id", ondelete="CASCADE"), primary_key=True
    )
    slot: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit_key: Mapped[str] = mapped_column(
        ForeignKey("characters.unit_key", ondelete="RESTRICT"), nullable=False
    )
    is_borrowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint("slot BETWEEN 1 AND 5", name="team_member_slot_range"),
        UniqueConstraint("team_id", "unit_key", name="uq_team_members_team_unit"),
    )


class OperationTimeline(Base):
    __tablename__ = "operation_timelines"

    source_axis_id: Mapped[str] = mapped_column(String(140), primary_key=True)
    timeline_id: Mapped[str | None] = mapped_column(String(140), nullable=True, unique=True)
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.team_id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[str] = mapped_column(String(160), nullable=False)
    source_evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence.evidence_id", ondelete="RESTRICT"), nullable=False
    )
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    timeline_variant_name: Mapped[str] = mapped_column(Text, nullable=False)
    operation_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    clock_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    battle_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    initial_auto_state: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    reproducibility: Mapped[str] = mapped_column(String(32), nullable=False)
    gap_reason: Mapped[str] = mapped_column(String(48), nullable=False)
    last_verified_at: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("import_runs.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("team_id", "source_id", name="uq_operation_timelines_team_source"),
        CheckConstraint(
            "operation_mode IN ('AUTO','SEMI_AUTO','MANUAL_TIMELINE')",
            name="operation_timeline_mode",
        ),
        CheckConstraint(
            "clock_mode IN ('COUNTDOWN','ELAPSED','UNKNOWN')",
            name="operation_timeline_clock_mode",
        ),
        CheckConstraint(
            "initial_auto_state IN ('ON','OFF','UNKNOWN')",
            name="operation_timeline_initial_auto_state",
        ),
        CheckConstraint(
            "reproducibility IN ('UNVERIFIED_ON_TW','TW_REPRODUCED','UNKNOWN')",
            name="operation_timeline_reproducibility",
        ),
        CheckConstraint(
            "gap_reason IN ('NONE','INSUFFICIENT_SOURCE_DETAIL','PENDING_EXTRACTION')",
            name="operation_timeline_gap_reason",
        ),
        CheckConstraint(
            "battle_duration_ms IS NULL OR battle_duration_ms > 0",
            name="operation_timeline_duration_positive",
        ),
        CheckConstraint(
            "(status = 'STRUCTURED' AND timeline_id IS NOT NULL "
            "AND clock_mode IN ('COUNTDOWN','ELAPSED') "
            "AND initial_auto_state IN ('ON','OFF') AND gap_reason = 'NONE') "
            "OR (status = 'SOURCE_GAP' AND timeline_id IS NULL "
            "AND clock_mode = 'UNKNOWN' AND battle_duration_ms IS NULL "
            "AND initial_auto_state = 'UNKNOWN' AND reproducibility = 'UNKNOWN' "
            "AND gap_reason IN ('INSUFFICIENT_SOURCE_DETAIL','PENDING_EXTRACTION'))",
            name="operation_timeline_status_shape",
        ),
        Index("ix_operation_timelines_team_status", "team_id", "status"),
    )


class TimelineStep(Base):
    __tablename__ = "timeline_steps"

    timeline_step_id: Mapped[str] = mapped_column(String(140), primary_key=True)
    timeline_id: Mapped[str] = mapped_column(
        ForeignKey("operation_timelines.timeline_id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.team_id", ondelete="CASCADE"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    source_step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_actor_unit_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    time_state: Mapped[str] = mapped_column(String(20), nullable=False)
    clock_from_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clock_to_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_unit_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_unit_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    auto_state_after: Mapped[str] = mapped_column(String(16), nullable=False)
    animation_cue: Mapped[str] = mapped_column(Text, nullable=False)
    hp_threshold: Mapped[str] = mapped_column(String(80), nullable=False)
    tolerance_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    criticality: Mapped[str] = mapped_column(String(20), nullable=False)
    instruction_zh_tw: Mapped[str] = mapped_column(Text, nullable=False)
    failure_if_missed: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("import_runs.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["team_id", "trigger_actor_unit_key"],
            ["team_members.team_id", "team_members.unit_key"],
            name="fk_timeline_steps_trigger_actor_team_member",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["team_id", "actor_unit_key"],
            ["team_members.team_id", "team_members.unit_key"],
            name="fk_timeline_steps_actor_team_member",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["team_id", "target_unit_key"],
            ["team_members.team_id", "team_members.unit_key"],
            name="fk_timeline_steps_target_team_member",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("timeline_id", "sequence_no", name="uq_timeline_steps_timeline_sequence"),
        CheckConstraint("sequence_no >= 1", name="timeline_step_sequence_positive"),
        CheckConstraint("source_step_no >= 1", name="timeline_step_source_sequence_positive"),
        CheckConstraint(
            "trigger_type IN ('CLOCK','UB_READY','ANIMATION_CUE','HP_THRESHOLD',"
            "'WAVE_START','BOSS_ACTION','SOURCE_TEXT_ONLY')",
            name="timeline_step_trigger_type",
        ),
        CheckConstraint(
            "time_state IN ('STATED','NOT_STATED')",
            name="timeline_step_time_state",
        ),
        CheckConstraint(
            "(time_state = 'STATED' AND clock_from_ms IS NOT NULL AND clock_to_ms IS NOT NULL) "
            "OR (time_state = 'NOT_STATED' AND clock_from_ms IS NULL AND clock_to_ms IS NULL)",
            name="timeline_step_time_shape",
        ),
        CheckConstraint(
            "clock_from_ms IS NULL OR clock_from_ms >= 0",
            name="timeline_step_clock_from_nonnegative",
        ),
        CheckConstraint(
            "clock_to_ms IS NULL OR clock_to_ms >= 0",
            name="timeline_step_clock_to_nonnegative",
        ),
        CheckConstraint(
            "tolerance_ms IS NULL OR tolerance_ms >= 0",
            name="timeline_step_tolerance_nonnegative",
        ),
        CheckConstraint(
            "action_type IN ('USE_UB','WAIT','AUTO_ON','AUTO_OFF','SET_ON','SET_OFF',"
            "'PAUSE','RESUME','TARGET','NO_ACTION')",
            name="timeline_step_action_type",
        ),
        CheckConstraint(
            "auto_state_after IN ('ON','OFF','UNKNOWN')",
            name="timeline_step_auto_state",
        ),
        CheckConstraint(
            "criticality IN ('NORMAL','CRITICAL','UNKNOWN')",
            name="timeline_step_criticality",
        ),
        CheckConstraint(
            "action_type NOT IN ('USE_UB','SET_ON','SET_OFF','TARGET') "
            "OR actor_unit_key IS NOT NULL",
            name="timeline_step_actor_required",
        ),
        CheckConstraint(
            "action_type != 'TARGET' OR target_unit_key IS NOT NULL",
            name="timeline_step_target_required",
        ),
        Index("ix_timeline_steps_timeline_sequence", "timeline_id", "sequence_no"),
    )


class StageEvidence(Base):
    __tablename__ = "stage_evidence"

    guide_id: Mapped[str] = mapped_column(
        ForeignKey("stages.guide_id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence.evidence_id", ondelete="RESTRICT"), primary_key=True
    )


class StageClaim(Base):
    __tablename__ = "stage_claims"

    guide_id: Mapped[str] = mapped_column(
        ForeignKey("stages.guide_id", ondelete="CASCADE"), primary_key=True
    )
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.claim_id", ondelete="RESTRICT"), primary_key=True
    )


class TeamEvidence(Base):
    __tablename__ = "team_evidence"

    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.team_id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence.evidence_id", ondelete="RESTRICT"), primary_key=True
    )


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"

    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.claim_id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence.evidence_id", ondelete="RESTRICT"), primary_key=True
    )


class SchedulerLease(Base):
    __tablename__ = "scheduler_leases"

    name: Mapped[str] = mapped_column(String(120), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(160), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("expires_at > acquired_at", name="scheduler_lease_positive_window"),
    )


class SchedulerRun(Base):
    __tablename__ = "scheduler_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(240), nullable=False, unique=True)
    job_name: Mapped[str] = mapped_column(String(120), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    shadow_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    owner_id: Mapped[str] = mapped_column(String(160), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)

    __table_args__ = (
        UniqueConstraint("job_name", "scheduled_for", name="uq_scheduler_runs_job_scheduled"),
        CheckConstraint(
            "status IN ('STARTED','SUCCEEDED','FAILED','SKIPPED')",
            name="scheduler_run_status",
        ),
    )
