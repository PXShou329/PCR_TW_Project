from __future__ import annotations

from datetime import date, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class SourceMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_source: str
    fixture_sha256: str
    import_run_id: str
    imported_at: datetime
    research_core_version: str


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
    status: str
    team_count: int
    reproducibility: str
    verified_date: date


class TeamMemberData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: int
    unit_key: str
    tw_name: str
    is_borrowed: bool


class TeamSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: str
    operation_mode: str
    clear_status: str
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


class TimelineReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    locator: str
    raw: str


class TimelineData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    references: list[TimelineReference]
    steps: list[dict[str, Any]]


class TeamDetail(TeamSummary):
    guide_id: str
    server: str
    stage: str
    support_slot: str | None
    requirements: dict[str, Any]
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


class BaselineData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_core_version: str
    application_version: str
    canonical_source: str
    generated_at: datetime
    counts: BaselineCounts
    gates: dict[str, Any]
    featured_stage: StageSummary | None
