from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Generic, Literal, TypeAlias, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


Sha256Hex: TypeAlias = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
OperationModeValue: TypeAlias = Literal[
    "AUTO",
    "SEMI_AUTO",
    "MANUAL_TIMELINE",
    "SOURCE_CONFLICT",
    "UNKNOWN",
]
StrategyStatusValue: TypeAlias = Literal[
    "VERIFIED",
    "PROVISIONAL",
    "IN_RESEARCH",
    "PENDING",
]
GuideReproducibilityValue: TypeAlias = Literal["CONFIRMED", "PENDING"]
ArenaStatusValue: TypeAlias = Literal[
    "VERIFIED",
    "PROVISIONAL",
    "SINGLE_REPORT",
    "STALE",
    "REJECTED",
]
ArenaOutcomeValue: TypeAlias = Literal["WIN", "LOSS", "MIXED", "UNKNOWN"]
ArenaVerificationValue: TypeAlias = Literal[
    "SCREENSHOT_RESULT",
    "VIDEO_RESULT",
    "TEXT_REPORT",
    "UNKNOWN",
]
ArenaRngRiskValue: TypeAlias = Literal["LOW", "MEDIUM", "HIGH", "UNKNOWN"]
ArenaReproducibilityValue: TypeAlias = Literal[
    "CONFIRMED",
    "UNVERIFIED_REPEATABILITY",
    "UNVERIFIED_ON_TW",
    "UNKNOWN",
]
ArenaOperationModeValue: TypeAlias = Literal["AUTO_SYSTEM", "MANUAL", "UNKNOWN"]
ArenaEnvironmentMatchValue: TypeAlias = Literal[
    "EXACT",
    "COMPATIBLE",
    "MISMATCH",
    "UNKNOWN",
]


class SourceMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_source: str
    fixture_sha256: Sha256Hex
    import_run_id: UUID
    revision_id: Sha256Hex
    imported_at: datetime
    research_core_version: str
    raw_tree_sha256: Sha256Hex
    semantic_tree_sha256: Sha256Hex
    materialization_sha256: Sha256Hex


class ResponseMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: str = "v1"
    generated_at: datetime
    source: SourceMeta
    warnings: list[str] = Field(default_factory=list)


DataT = TypeVar("DataT")


class Envelope(BaseModel, Generic[DataT]):
    model_config = ConfigDict(extra="forbid")

    data: DataT
    meta: ResponseMeta


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    checks: dict[str, str]


class StageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guide_id: str
    server: str
    mode: str
    area: str
    stage: str
    status: StrategyStatusValue
    team_count: int
    reproducibility: GuideReproducibilityValue
    verified_date: date


class TeamMemberData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: int
    unit_key: str
    tw_name: str
    is_borrowed: bool | None


class TeamSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: str
    operation_mode: OperationModeValue
    clear_status: StrategyStatusValue
    stability: str
    members: list[TeamMemberData]


class StageCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified_distinct_teams: int
    maturity_target: int
    remaining: int
    is_mature: bool


class StageDetail(StageSummary):
    applicable_version: str
    source_tier: str
    claim_confidence: str
    last_review_due: date | None
    notes: str
    coverage: StageCoverage
    teams: list[TeamSummary]
    evidence_ids: list[str]
    claim_ids: list[str]


class SlotRequirementData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    star: str
    rank: str
    ue1: str
    ue2: str
    six_star: str
    connect_rank: str
    element_boost: str


class SlotRequirementsData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot1: SlotRequirementData
    slot2: SlotRequirementData
    slot3: SlotRequirementData
    slot4: SlotRequirementData
    slot5: SlotRequirementData


class TeamSupportData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit: str
    requirements: str


class OperationModeClaimData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    mode: Literal["AUTO", "SEMI_AUTO", "MANUAL_TIMELINE", "UNKNOWN"]


class TeamRequirementsData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    slots: SlotRequirementsData
    support: TeamSupportData
    operation_mode_claims: list[OperationModeClaimData]
    failure_conditions: list[str]
    timeline_ref: str


class TimelineReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    locator: str
    raw: str


class TimelineStepData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timeline_step_id: str
    timeline_id: str
    sequence_no: int = Field(ge=1)
    source_step_no: int = Field(ge=1)
    trigger_type: Literal[
        "CLOCK",
        "UB_READY",
        "ANIMATION_CUE",
        "HP_THRESHOLD",
        "WAVE_START",
        "BOSS_ACTION",
        "SOURCE_TEXT_ONLY",
    ]
    trigger_actor_unit_key: str
    time_state: Literal["STATED", "NOT_STATED"]
    clock_from_ms: int | None = Field(ge=0)
    clock_to_ms: int | None = Field(ge=0)
    actor_unit_key: str
    action_type: Literal[
        "USE_UB",
        "WAIT",
        "AUTO_ON",
        "AUTO_OFF",
        "SET_ON",
        "SET_OFF",
        "PAUSE",
        "RESUME",
        "TARGET",
        "NO_ACTION",
    ]
    target_unit_key: str
    auto_state_after: Literal["ON", "OFF", "UNKNOWN"]
    animation_cue: str
    hp_threshold: str
    tolerance_ms: int | None = Field(ge=0)
    criticality: Literal["NORMAL", "CRITICAL", "UNKNOWN"]
    instruction_zh_tw: str
    failure_if_missed: str
    source_locator: str


class TimelineSourceBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_axis_id: str
    source_id: str
    source_evidence_id: str
    source_locator: str
    timeline_variant_name: str
    operation_mode: Literal["AUTO", "SEMI_AUTO", "MANUAL_TIMELINE", "UNKNOWN"]
    reproducibility: Literal["UNVERIFIED_ON_TW", "TW_REPRODUCED", "UNKNOWN"]
    last_verified_at: date
    notes: str


class StructuredTimelineSource(TimelineSourceBase):
    status: Literal["STRUCTURED"]
    timeline_id: str
    clock_mode: Literal["COUNTDOWN", "ELAPSED"]
    battle_duration_ms: int | None = Field(ge=1)
    initial_auto_state: Literal["ON", "OFF"]
    gap_reason: None
    steps: list[TimelineStepData]


class GapTimelineSource(TimelineSourceBase):
    status: Literal["SOURCE_GAP"]
    timeline_id: None
    clock_mode: None
    battle_duration_ms: None
    initial_auto_state: None
    gap_reason: Literal["INSUFFICIENT_SOURCE_DETAIL", "PENDING_EXTRACTION"]
    steps: list[TimelineStepData] = Field(..., max_length=0)


TimelineSourceData: TypeAlias = Annotated[
    StructuredTimelineSource | GapTimelineSource,
    Field(discriminator="status"),
]


class TimelineData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["STRUCTURED", "PARTIAL", "SOURCE_GAP", "MISSING"]
    structured_sources: int = Field(ge=0)
    registered_sources: int = Field(ge=0)
    sources: list[TimelineSourceData]
    references: list[TimelineReference]
    steps: list[dict[str, Any]] = Field(..., max_length=0)


class TeamDetail(TeamSummary):
    guide_id: str
    server: str
    stage: str
    support_slot: str | None
    requirements: TeamRequirementsData
    timeline: TimelineData
    source_ids: list[str]
    evidence_ids: list[str]
    tw_availability_check: str
    verified_date: date
    last_review_due: date | None
    notes: str


class EvidenceData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    declared_claim_id: str | None
    linked_claim_id: str | None
    module: str
    server: str
    source_tier: str
    evidence_confidence: str
    source_title: str
    source_url: str
    source_locator: str
    published_date: date | None
    published_date_precision: str
    verified_date: date
    claim_summary: str
    limitations: str
    status: str


class ArenaMemberData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: int = Field(ge=1, le=5)
    unit_key: str
    display_name: str
    display_name_source: Literal["TW_OFFICIAL", "JP_OFFICIAL"]


class ArenaCounterData(BaseModel):
    """One exact, source-backed Arena counter and its complete 5v5 formation."""

    model_config = ConfigDict(extra="forbid")

    counter_id: str
    defense_id: str
    server: Literal["TW", "JP"]
    environment_version: str
    arena_bracket: str
    defense_signature: str
    counter_signature: str
    defense_members: list[ArenaMemberData] = Field(min_length=5, max_length=5)
    counter_members: list[ArenaMemberData] = Field(min_length=5, max_length=5)
    status: ArenaStatusValue
    match_type: Literal["EXACT"]
    outcome: ArenaOutcomeValue
    verification: ArenaVerificationValue
    sample_size: int | None = Field(ge=1)
    wins: int | None = Field(ge=0)
    losses: int | None = Field(ge=0)
    empirical_win_rate: int | None = Field(ge=0, le=100)
    randomness: str
    rng_risk: ArenaRngRiskValue
    claim_confidence: Literal["B", "C", "D", "E"]
    reproducibility: ArenaReproducibilityValue
    source_tier: str
    source_record_count: int = Field(ge=1)
    source_platforms: list[str]
    tw_availability_check: Literal["PASS", "FAIL", "UNVERIFIED"]
    unavailable_unit_ids: list[str]
    required_upgrade_check: Literal["PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"]
    operation_mode: ArenaOperationModeValue
    environment_match: ArenaEnvironmentMatchValue
    speed_conditions: str
    initial_action_notes: str
    verified_date: date
    last_review_due: date | None
    record_date_min: date | None
    record_date_max: date | None
    notes: str
    evidence_ids: list[str]
    claim_ids: list[str]


class ClaimData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    module: str
    server: str
    claim_text: str
    claim_type: str
    claim_confidence: str
    independence_check: str
    version_match: str
    status: str
    verified_date: date
    next_review_due: date | None
    evidence_ids: list[str]
    notes: str


class BaselineCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stages: int
    teams: int
    team_members: int
    characters: int
    evidence: int
    claims: int
    operation_timelines: int
    timeline_steps: int
    arena_defenses: int
    arena_defense_members: int
    arena_counters: int
    arena_counter_members: int
    arena_counter_evidence: int
    arena_counter_claims: int


class GateSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_a: bool
    gate_b: bool
    gate_c: bool


class BaselineData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_core_version: str
    application_version: str
    canonical_source: str
    generated_at: datetime
    counts: BaselineCounts
    gates: GateSummary
    featured_stage: StageSummary | None
