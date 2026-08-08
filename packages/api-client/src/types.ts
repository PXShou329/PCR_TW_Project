export type StrategyStatus =
  | "VERIFIED"
  | "PROVISIONAL"
  | "IN_RESEARCH"
  | "PENDING";

export type OperationMode = "AUTO" | "SEMI_AUTO" | "MANUAL" | "SOURCE_CONFLICT";

export interface SourceMetadata {
  canonical_source: string;
  fixture_sha256: string;
  import_run_id: string;
  imported_at: string;
  research_core_version: string;
}

export interface ApiMetadata {
  api_version: string;
  generated_at: string;
  source: SourceMetadata;
  warnings: string[];
}

export interface ApiEnvelope<T> {
  data: T;
  meta: ApiMetadata;
}

export interface GateSummary {
  gate_a: boolean;
  gate_b: boolean;
  gate_c: boolean;
  blocking_warnings?: number;
}

export interface Baseline {
  research_core_version: string;
  application_version: string;
  canonical_source: string;
  generated_at: string;
  counts: BaselineCounts;
  gates: GateSummary;
  featured_stage: StageSummary | null;
}

export interface BaselineCounts {
  stages: number;
  teams: number;
  team_members: number;
  characters: number;
  evidence: number;
  claims: number;
}

export interface Coverage {
  verified_distinct_teams: number;
  maturity_target: number;
  remaining: number;
  is_mature: boolean;
}

export interface StageSummary {
  guide_id: string;
  server: string;
  mode: string;
  area: string;
  stage: string;
  status: StrategyStatus;
  verified_date: string;
  team_count: number;
  reproducibility: StrategyStatus;
}

export interface TeamSummary {
  team_id: string;
  operation_mode: OperationMode;
  clear_status: StrategyStatus;
  stability: string;
  members: TeamMember[];
}

export interface StageDetail extends StageSummary {
  applicable_version: string;
  last_review_due: string | null;
  claim_confidence: string;
  source_tier: string;
  evidence_ids: string[];
  claim_ids: string[];
  notes: string;
  coverage: Coverage;
  teams: TeamSummary[];
}

export interface TeamMember {
  slot: number;
  unit_key: string;
  tw_name: string;
  is_borrowed: boolean;
}

export interface SlotRequirement {
  star: string;
  rank: string;
  ue1: string;
  ue2: string;
  six_star: string;
  connect_rank: string;
  element_boost: string;
}

export interface OperationModeClaim {
  source_id: string;
  mode: Exclude<OperationMode, "SOURCE_CONFLICT">;
}

export interface TeamRequirements {
  schema_version: string;
  slots: Record<string, SlotRequirement>;
  support: {
    unit: string;
    requirements: string;
  };
  operation_mode_claims: OperationModeClaim[];
  failure_conditions: string[];
  timeline_ref?: string;
}

export interface TimelineGap {
  status: "SOURCE_GAP" | "MISSING";
  references: Array<{
    source_id: string;
    locator: string;
    raw: string;
  }>;
  steps: Array<Record<string, unknown>>;
}

export interface TeamDetail extends TeamSummary {
  guide_id: string;
  server: string;
  stage: string;
  support_slot: string | null;
  requirements: TeamRequirements;
  timeline: TimelineGap;
  source_ids: string[];
  evidence_ids: string[];
  verified_date: string;
  last_review_due: string | null;
  tw_availability_check: string;
  notes: string;
}

export interface Evidence {
  evidence_id: string;
  declared_claim_id: string | null;
  linked_claim_id: string | null;
  module: string;
  server: string;
  source_tier: string;
  evidence_confidence: string;
  source_title: string;
  source_url: string;
  source_locator: string;
  published_date: string | null;
  published_date_precision: string;
  verified_date: string;
  claim_summary: string;
  limitations: string;
  status: string;
}

export interface PvpCounter {
  counter_id: string;
}

export interface Claim {
  claim_id: string;
  module: string;
  server: string;
  claim_text: string;
  claim_type: string;
  claim_confidence: string;
  independence_check: string;
  version_match: string;
  status: string;
  verified_date: string;
  next_review_due: string | null;
  evidence_ids: string[];
  notes: string;
}

export interface ApiProblem {
  detail?: {
    code?: string;
    resource?: string;
    id?: string;
    reason?: string;
  };
}
