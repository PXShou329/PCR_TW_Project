from __future__ import annotations

from datetime import date, datetime, timezone
from collections.abc import Iterable
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

json_type = JSON().with_variant(JSONB(), "postgresql")
nullable_json_type = JSON(none_as_null=True).with_variant(
    JSONB(none_as_null=True), "postgresql"
)


def arena_formation_signature(unit_keys: Iterable[str]) -> str:
    """Return the canonical order-insensitive identity for one five-unit team.

    Arena display slots remain ordered in the member tables.  Search identity is
    deliberately independent of those slots so the same five units cannot be
    counted twice merely because a source lists them in a different order.
    """

    normalized = [unit_key.strip() for unit_key in unit_keys]
    if len(normalized) != 5:
        raise ValueError("Arena formations require exactly five members")
    if any(not unit_key for unit_key in normalized):
        raise ValueError("Arena formation unit_key values must be non-empty")
    if len(set(normalized)) != len(normalized):
        raise ValueError("Arena formation members must be unique")
    return ";".join(sorted(normalized))


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
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, active_history=True
    )
    manifest: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    row_counts: Mapped[dict[str, int]] = mapped_column(json_type, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('RUNNING','SUCCEEDED','FAILED')", name="import_status"),
    )


class CoreRevision(Base):
    """Immutable full research-core artifact revision metadata.

    The file SSOT remains writable through B7.  A revision therefore records a
    lossless database mirror and its parity fingerprints; activation is kept in
    ``MaterializationState`` instead of being inferred from timestamps.
    """

    __tablename__ = "core_revisions"

    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    import_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("import_runs.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    raw_tree_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    semantic_tree_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    materialization_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    csv_file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    csv_row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_to_claim_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_to_claim_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    claim_to_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    claim_to_evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, active_history=True
    )
    manifest: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False, default=dict)
    project_version: Mapped[str] = mapped_column(String(40), nullable=False, default="UNKNOWN")
    serialization_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint("length(raw_tree_sha256) = 64", name="core_revision_raw_hash"),
        CheckConstraint(
            "length(semantic_tree_sha256) = 64", name="core_revision_semantic_hash"
        ),
        CheckConstraint("length(manifest_sha256) = 64", name="core_revision_manifest_hash"),
        CheckConstraint(
            "materialization_sha256 IS NULL OR length(materialization_sha256) = 64",
            name="core_revision_materialization_hash",
        ),
        CheckConstraint("file_count >= 1", name="core_revision_file_count_positive"),
        CheckConstraint(
            "csv_file_count >= 1 AND csv_file_count <= file_count",
            name="core_revision_csv_file_count_range",
        ),
        CheckConstraint("csv_row_count >= 0", name="core_revision_csv_row_count_nonnegative"),
        CheckConstraint(
            "evidence_to_claim_count >= 0", name="core_revision_evidence_edge_count"
        ),
        CheckConstraint(
            "claim_to_evidence_count >= 0", name="core_revision_claim_edge_count"
        ),
        CheckConstraint(
            "length(evidence_to_claim_sha256) = 64",
            name="core_revision_evidence_edge_hash",
        ),
        CheckConstraint(
            "length(claim_to_evidence_sha256) = 64",
            name="core_revision_claim_edge_hash",
        ),
        CheckConstraint(
            "status IN ('STAGING','SUCCEEDED','FAILED')", name="core_revision_status"
        ),
        CheckConstraint(
            "serialization_version >= 1", name="core_revision_serialization_version"
        ),
        Index("ix_core_revisions_status_created", "status", "created_at"),
        UniqueConstraint(
            "revision_id",
            "import_run_id",
            name="uq_core_revisions_revision_import_run",
        ),
    )


class CoreFile(Base):
    """Lossless bytes and structural metadata for one file in a core revision."""

    __tablename__ = "core_files"

    revision_id: Mapped[str] = mapped_column(
        ForeignKey("core_revisions.revision_id", ondelete="CASCADE"), primary_key=True
    )
    relative_path: Mapped[str] = mapped_column(String(500), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    semantic_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    is_csv: Mapped[bool] = mapped_column(Boolean, nullable=False)
    natural_key_field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    header: Mapped[list[str] | None] = mapped_column(nullable_json_type, nullable=True)

    __table_args__ = (
        UniqueConstraint("revision_id", "ordinal", name="uq_core_files_revision_ordinal"),
        CheckConstraint("length(relative_path) > 0", name="core_file_path_nonempty"),
        CheckConstraint("ordinal >= 1", name="core_file_ordinal_positive"),
        CheckConstraint("length(sha256) = 64", name="core_file_hash"),
        CheckConstraint("length(semantic_sha256) = 64", name="core_file_semantic_hash"),
        CheckConstraint("size_bytes >= 0", name="core_file_size_nonnegative"),
        CheckConstraint(
            "(is_csv AND header IS NOT NULL AND natural_key_field IS NOT NULL) OR "
            "(NOT is_csv AND header IS NULL AND natural_key_field IS NULL)",
            name="core_file_csv_shape",
        ),
        Index("ix_core_files_revision_csv", "revision_id", "is_csv"),
    )


class CoreCsvRow(Base):
    """Ordered, lossless string-cell projection of a canonical CSV record."""

    __tablename__ = "core_csv_rows"

    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    relative_path: Mapped[str] = mapped_column(String(500), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    natural_key: Mapped[str] = mapped_column(Text, nullable=False)
    values: Mapped[list[str]] = mapped_column(json_type, nullable=False)
    row_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["revision_id", "relative_path"],
            ["core_files.revision_id", "core_files.relative_path"],
            name="fk_core_csv_rows_revision_path_core_files",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "revision_id",
            "relative_path",
            "natural_key",
            name="uq_core_csv_rows_revision_path_key",
        ),
        CheckConstraint("ordinal >= 1", name="core_csv_row_ordinal_positive"),
        CheckConstraint("length(natural_key) > 0", name="core_csv_row_key_nonempty"),
        CheckConstraint("length(row_sha256) = 64", name="core_csv_row_hash"),
        Index("ix_core_csv_rows_revision_path", "revision_id", "relative_path"),
    )


class MaterializationState(Base):
    """Singleton pointer and cache epoch for the active read mirror."""

    __tablename__ = "materialization_state"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False, default=1
    )
    active_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active_import_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    epoch: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, active_history=True
    )
    materialization_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    serving_counts: Mapped[dict[str, int]] = mapped_column(json_type, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint("id = 1", name="materialization_state_singleton"),
        CheckConstraint("epoch >= 0", name="materialization_state_epoch_nonnegative"),
        CheckConstraint(
            "(active_revision_id IS NULL AND active_import_run_id IS NULL "
            "AND materialization_sha256 IS NULL) OR "
            "(active_revision_id IS NOT NULL AND active_import_run_id IS NOT NULL "
            "AND materialization_sha256 IS NOT NULL "
            "AND length(materialization_sha256) = 64)",
            name="materialization_state_active_shape",
        ),
        ForeignKeyConstraint(
            ["active_revision_id", "active_import_run_id"],
            ["core_revisions.revision_id", "core_revisions.import_run_id"],
            name="fk_materialization_state_active_revision_run",
            ondelete="RESTRICT",
        ),
    )


class RevisionActivation(Base):
    """Append-only audit record for import, rollback and forward reactivation."""

    __tablename__ = "revision_activations"

    activation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sequence_no: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    from_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("core_revisions.revision_id", ondelete="RESTRICT"), nullable=True
    )
    to_revision_id: Mapped[str] = mapped_column(
        ForeignKey("core_revisions.revision_id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(160), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    epoch: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("sequence_no >= 1", name="revision_activation_sequence_positive"),
        CheckConstraint("epoch >= 0", name="revision_activation_epoch_nonnegative"),
        CheckConstraint(
            "kind IN ('IMPORT','ROLLBACK','REACTIVATE')",
            name="revision_activation_kind",
        ),
        CheckConstraint(
            "from_revision_id IS NULL OR from_revision_id <> to_revision_id",
            name="revision_activation_distinct_revisions",
        ),
        Index("ix_revision_activations_activated_at", "activated_at"),
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
    # True/False are explicit source facts; None preserves an unstated or
    # source-conflicting support slot without strengthening it to "not borrowed".
    is_borrowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

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
            "operation_mode IN ('AUTO','SEMI_AUTO','MANUAL_TIMELINE','UNKNOWN')",
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


class ArenaDefense(Base):
    """One canonical Battle Arena defense in a specific server environment."""

    __tablename__ = "arena_defenses"

    defense_id: Mapped[str] = mapped_column(String(140), primary_key=True)
    server: Mapped[str] = mapped_column(String(16), nullable=False)
    formation_signature: Mapped[str] = mapped_column(String(600), nullable=False)
    environment_version: Mapped[str] = mapped_column(String(100), nullable=False)
    arena_bracket: Mapped[str] = mapped_column(String(100), nullable=False)
    core_tags: Mapped[list[str]] = mapped_column(json_type, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    verified_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("import_runs.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "server",
            "environment_version",
            "formation_signature",
            name="uq_arena_defenses_server_environment_signature",
        ),
        CheckConstraint("server IN ('TW','JP')", name="arena_defense_server"),
        CheckConstraint(
            "status IN ('VERIFIED','PROVISIONAL','SINGLE_REPORT','STALE','REJECTED')",
            name="arena_defense_status",
        ),
        CheckConstraint(
            "review_status IN ('CURRENT','REVALIDATE_REQUIRED','STALE')",
            name="arena_defense_review_status",
        ),
        CheckConstraint(
            "length(formation_signature) > 0",
            name="arena_defense_signature_nonempty",
        ),
        Index(
            "ix_arena_defenses_server_status",
            "server",
            "status",
            "review_status",
        ),
    )


class ArenaDefenseMember(Base):
    __tablename__ = "arena_defense_members"

    defense_id: Mapped[str] = mapped_column(
        ForeignKey("arena_defenses.defense_id", ondelete="CASCADE"), primary_key=True
    )
    slot: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit_key: Mapped[str] = mapped_column(
        ForeignKey("characters.unit_key", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        CheckConstraint("slot BETWEEN 1 AND 5", name="arena_defense_member_slot_range"),
        UniqueConstraint(
            "defense_id",
            "unit_key",
            name="uq_arena_defense_members_defense_unit",
        ),
    )


class ArenaCounter(Base):
    """A source-backed exact counter for one canonical Arena defense."""

    __tablename__ = "arena_counters"

    counter_id: Mapped[str] = mapped_column(String(140), primary_key=True)
    defense_id: Mapped[str] = mapped_column(
        ForeignKey("arena_defenses.defense_id", ondelete="CASCADE"), nullable=False
    )
    formation_signature: Mapped[str] = mapped_column(String(600), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    match_type: Mapped[str] = mapped_column(String(16), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    verification: Mapped[str] = mapped_column(String(32), nullable=False)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    losses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    empirical_win_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    randomness: Mapped[str] = mapped_column(Text, nullable=False)
    rng_risk: Mapped[str] = mapped_column(String(16), nullable=False)
    claim_confidence: Mapped[str] = mapped_column(String(8), nullable=False)
    reproducibility: Mapped[str] = mapped_column(String(32), nullable=False)
    source_tier: Mapped[str] = mapped_column(String(40), nullable=False)
    source_record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_platforms: Mapped[list[str]] = mapped_column(json_type, nullable=False)
    tw_availability_check: Mapped[str] = mapped_column(String(20), nullable=False)
    unavailable_unit_ids: Mapped[list[str]] = mapped_column(json_type, nullable=False)
    required_upgrade_check: Mapped[str] = mapped_column(String(24), nullable=False)
    operation_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    environment_match: Mapped[str] = mapped_column(String(20), nullable=False)
    speed_conditions: Mapped[str] = mapped_column(Text, nullable=False)
    initial_action_notes: Mapped[str] = mapped_column(Text, nullable=False)
    verified_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_review_due: Mapped[date] = mapped_column(Date, nullable=False)
    record_date_min: Mapped[date] = mapped_column(Date, nullable=False)
    record_date_max: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("import_runs.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "defense_id",
            "formation_signature",
            name="uq_arena_counters_defense_signature",
        ),
        CheckConstraint(
            "status IN "
            "('VERIFIED','PROVISIONAL','SINGLE_REPORT','STALE','REJECTED')",
            name="arena_counter_status",
        ),
        # A stored counter is exact for the defense it references.  Similar
        # search is a query-time reuse of another defense's exact record and
        # must remain visibly labelled by the API/UI.
        CheckConstraint("match_type = 'EXACT'", name="arena_counter_match_type"),
        CheckConstraint(
            "outcome IN ('WIN','LOSS','MIXED','UNKNOWN')",
            name="arena_counter_outcome",
        ),
        CheckConstraint(
            "verification IN ('SCREENSHOT_RESULT','VIDEO_RESULT','TEXT_REPORT','UNKNOWN')",
            name="arena_counter_verification",
        ),
        CheckConstraint(
            "(sample_size IS NULL AND wins IS NULL AND losses IS NULL) OR "
            "(sample_size IS NOT NULL AND wins IS NOT NULL AND losses IS NOT NULL "
            "AND sample_size = wins + losses)",
            name="arena_counter_sample_shape",
        ),
        CheckConstraint(
            "(outcome != 'WIN' OR (wins IS NOT NULL AND wins >= 1)) AND "
            "(outcome != 'LOSS' OR (losses IS NOT NULL AND losses >= 1))",
            name="arena_counter_outcome_count",
        ),
        CheckConstraint(
            "sample_size IS NULL OR sample_size >= 1",
            name="arena_counter_sample_size_positive",
        ),
        CheckConstraint("wins IS NULL OR wins >= 0", name="arena_counter_wins_nonnegative"),
        CheckConstraint(
            "losses IS NULL OR losses >= 0",
            name="arena_counter_losses_nonnegative",
        ),
        CheckConstraint(
            "empirical_win_rate IS NULL OR "
            "(sample_size IS NOT NULL AND empirical_win_rate BETWEEN 0 AND 100 "
            "AND sample_size >= 2)",
            name="arena_counter_empirical_rate",
        ),
        CheckConstraint(
            "status != 'SINGLE_REPORT' OR empirical_win_rate IS NULL",
            name="arena_counter_single_report_no_empirical_rate",
        ),
        CheckConstraint(
            "rng_risk IN ('LOW','MEDIUM','HIGH','UNKNOWN')",
            name="arena_counter_rng_risk",
        ),
        CheckConstraint(
            "claim_confidence IN ('B','C','D','E')",
            name="arena_counter_claim_confidence",
        ),
        CheckConstraint(
            "status != 'SINGLE_REPORT' OR claim_confidence = 'D'",
            name="arena_counter_single_report_confidence",
        ),
        CheckConstraint(
            "status != 'VERIFIED' OR claim_confidence IN ('B','C')",
            name="arena_counter_verified_confidence",
        ),
        CheckConstraint(
            "reproducibility IN "
            "('CONFIRMED','UNVERIFIED_REPEATABILITY',"
            "'UNVERIFIED_ON_TW','UNKNOWN')",
            name="arena_counter_reproducibility",
        ),
        CheckConstraint(
            "status != 'VERIFIED' OR reproducibility = 'CONFIRMED'",
            name="arena_counter_verified_reproducibility",
        ),
        CheckConstraint(
            "status != 'VERIFIED' OR ("
            "outcome = 'WIN' AND verification != 'UNKNOWN' "
            "AND source_tier IN "
            "('OFFICIAL','MAJOR_GUIDE','STRUCTURED_DB','COMMUNITY_WIKI',"
            "'MULTI_PLAYER_REPORT') "
            "AND source_record_count >= 2 "
            "AND sample_size IS NOT NULL AND sample_size >= 2 "
            "AND wins IS NOT NULL AND wins >= 2 "
            "AND environment_match = 'EXACT')",
            name="arena_counter_verified_multi_source_shape",
        ),
        CheckConstraint(
            "length(randomness) > 0",
            name="arena_counter_randomness_nonempty",
        ),
        CheckConstraint(
            "length(source_tier) > 0",
            name="arena_counter_source_tier_nonempty",
        ),
        CheckConstraint(
            "source_record_count >= 1",
            name="arena_counter_source_record_count_positive",
        ),
        CheckConstraint(
            "tw_availability_check IN ('PASS','FAIL','UNVERIFIED')",
            name="arena_counter_tw_availability_check",
        ),
        CheckConstraint(
            "required_upgrade_check IN ('PASS','FAIL','UNKNOWN','NOT_APPLICABLE')",
            name="arena_counter_required_upgrade_check",
        ),
        CheckConstraint(
            "record_date_min <= record_date_max",
            name="arena_counter_record_date_range",
        ),
        CheckConstraint(
            "operation_mode IN ('AUTO_SYSTEM','MANUAL','UNKNOWN')",
            name="arena_counter_operation_mode",
        ),
        CheckConstraint(
            "environment_match IN ('EXACT','COMPATIBLE','MISMATCH','UNKNOWN')",
            name="arena_counter_environment_match",
        ),
        CheckConstraint(
            "length(formation_signature) > 0",
            name="arena_counter_signature_nonempty",
        ),
        Index(
            "ix_arena_counters_defense_status",
            "defense_id",
            "status",
        ),
    )


class ArenaCounterMember(Base):
    __tablename__ = "arena_counter_members"

    counter_id: Mapped[str] = mapped_column(
        ForeignKey("arena_counters.counter_id", ondelete="CASCADE"), primary_key=True
    )
    slot: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit_key: Mapped[str] = mapped_column(
        ForeignKey("characters.unit_key", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        CheckConstraint("slot BETWEEN 1 AND 5", name="arena_counter_member_slot_range"),
        UniqueConstraint(
            "counter_id",
            "unit_key",
            name="uq_arena_counter_members_counter_unit",
        ),
    )


class ArenaCounterEvidence(Base):
    __tablename__ = "arena_counter_evidence"

    counter_id: Mapped[str] = mapped_column(
        ForeignKey("arena_counters.counter_id", ondelete="CASCADE"), primary_key=True
    )
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence.evidence_id", ondelete="RESTRICT"), primary_key=True
    )


class ArenaCounterClaim(Base):
    __tablename__ = "arena_counter_claims"

    counter_id: Mapped[str] = mapped_column(
        ForeignKey("arena_counters.counter_id", ondelete="CASCADE"), primary_key=True
    )
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.claim_id", ondelete="RESTRICT"), primary_key=True
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


class ImmutableCoreRevisionError(RuntimeError):
    """Raised by the ORM guard when terminal artifact history is mutated."""


class ImmutableImportRunError(RuntimeError):
    """Raised when an import run bypasses or rewrites its lifecycle."""


class NonMonotonicMaterializationEpochError(RuntimeError):
    """Raised when an ORM write would keep or rewind the serving epoch."""


class ImmutableMaterializationStateError(RuntimeError):
    """Raised when the singleton materialization pointer is deleted."""


class ImmutableRevisionActivationError(RuntimeError):
    """Raised when append-only revision activation audit is rewritten."""


_CORE_TERMINAL_STATUSES = frozenset({"SUCCEEDED", "FAILED"})
_IMPORT_RUN_TERMINAL_STATUSES = frozenset({"SUCCEEDED", "FAILED"})


def _persisted_import_run_status(
    session: Session,
    candidate: ImportRun,
) -> str | None:
    """Return OLD status even when the instance was expired before assignment."""

    history = inspect(candidate).attrs.status.history
    if history.deleted:
        return history.deleted[0]
    identity = inspect(candidate).identity
    if not identity:
        return None
    with session.no_autoflush:
        return session.scalar(
            select(ImportRun.status).where(ImportRun.id == identity[0])
        )


def _persisted_materialization_epoch(
    session: Session,
    candidate: MaterializationState,
) -> int | None:
    history = inspect(candidate).attrs.epoch.history
    if history.deleted:
        return history.deleted[0]
    identity = inspect(candidate).identity
    if not identity:
        return None
    with session.no_autoflush:
        return session.scalar(
            select(MaterializationState.epoch).where(
                MaterializationState.id == identity[0]
            )
        )


def _persisted_core_revision_status(
    session: Session,
    candidate: CoreRevision,
) -> str | None:
    """Return OLD revision status across expiration and reassignment."""

    history = inspect(candidate).attrs.status.history
    if history.deleted:
        return history.deleted[0]
    identity = inspect(candidate).identity
    if not identity:
        return None
    with session.no_autoflush:
        return session.scalar(
            select(CoreRevision.status).where(
                CoreRevision.revision_id == identity[0]
            )
        )


def _revision_status_for_guard(session: Session, revision_id: str) -> str | None:
    for candidate in session.new:
        if isinstance(candidate, CoreRevision) and candidate.revision_id == revision_id:
            return candidate.status
    for candidate in session.identity_map.values():
        if isinstance(candidate, CoreRevision) and candidate.revision_id == revision_id:
            return candidate.status
    with session.no_autoflush:
        return session.scalar(
            select(CoreRevision.status).where(CoreRevision.revision_id == revision_id)
        )


@event.listens_for(Session, "before_flush")
def guard_terminal_core_revision_history(
    session: Session,
    _flush_context: Any,
    _instances: Any,
) -> None:
    """Mirror PostgreSQL history guards for ORM-based SQLite tests and tools.

    Bulk SQL deliberately remains a database concern: PostgreSQL V0003 guards
    it with row triggers, while SQLite is used only for application tests.
    """

    for candidate in session.new:
        if isinstance(candidate, ImportRun) and candidate.status != "RUNNING":
            raise ImmutableImportRunError(
                "import runs must be inserted in RUNNING status"
            )
        if isinstance(candidate, CoreRevision) and candidate.status != "STAGING":
            raise ImmutableCoreRevisionError(
                "core revisions must be inserted in STAGING status"
            )

    for candidate in session.dirty:
        if isinstance(candidate, ImportRun):
            previous_status = _persisted_import_run_status(session, candidate)
            if previous_status in _IMPORT_RUN_TERMINAL_STATUSES:
                raise ImmutableImportRunError(
                    f"terminal import run {candidate.id} is immutable"
                )
            continue
        if isinstance(candidate, MaterializationState):
            if not session.is_modified(candidate, include_collections=True):
                continue
            previous_epoch = _persisted_materialization_epoch(session, candidate)
            if previous_epoch is not None and candidate.epoch <= previous_epoch:
                raise NonMonotonicMaterializationEpochError(
                    "materialization_state epoch must strictly increase "
                    f"(old {previous_epoch}, new {candidate.epoch})"
                )
            continue
        if isinstance(candidate, RevisionActivation):
            if session.is_modified(candidate, include_collections=True):
                raise ImmutableRevisionActivationError(
                    "revision_activations is append-only"
                )
            continue
        if not isinstance(candidate, CoreRevision):
            continue
        previous_status = _persisted_core_revision_status(session, candidate)
        if previous_status in _CORE_TERMINAL_STATUSES:
            raise ImmutableCoreRevisionError(
                f"terminal core revision {candidate.revision_id} is immutable"
            )

    for candidate in session.deleted:
        if isinstance(candidate, ImportRun):
            previous_status = _persisted_import_run_status(session, candidate)
            if previous_status in _IMPORT_RUN_TERMINAL_STATUSES:
                raise ImmutableImportRunError(
                    f"terminal import run {candidate.id} is immutable"
                )
        if isinstance(candidate, CoreRevision):
            previous_status = _persisted_core_revision_status(session, candidate)
            if previous_status in _CORE_TERMINAL_STATUSES:
                raise ImmutableCoreRevisionError(
                    f"terminal core revision {candidate.revision_id} is immutable"
                )
        if isinstance(candidate, MaterializationState):
            raise ImmutableMaterializationStateError(
                "materialization_state singleton cannot be deleted"
            )
        if isinstance(candidate, RevisionActivation):
            raise ImmutableRevisionActivationError(
                "revision_activations is append-only"
            )

    artifact_candidates = (
        list(session.new) + list(session.dirty) + list(session.deleted)
    )
    for candidate in artifact_candidates:
        if not isinstance(candidate, (CoreFile, CoreCsvRow)):
            continue
        revision_ids = {candidate.revision_id}
        revision_history = inspect(candidate).attrs.revision_id.history
        revision_ids.update(value for value in revision_history.deleted if value)
        for revision_id in revision_ids:
            status = _revision_status_for_guard(session, revision_id)
            if status != "STAGING":
                raise ImmutableCoreRevisionError(
                    f"artifact revision {revision_id} is not mutable STAGING data"
                )
