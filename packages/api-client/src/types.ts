export type StrategyStatus =
  | "VERIFIED"
  | "PROVISIONAL"
  | "IN_RESEARCH"
  | "PENDING";

export type GuideReproducibility = "CONFIRMED" | "PENDING";

export type OperationMode =
  | "AUTO"
  | "SEMI_AUTO"
  | "MANUAL_TIMELINE"
  | "SOURCE_CONFLICT"
  | "UNKNOWN";

export interface SourceMetadata {
  canonical_source: string;
  fixture_sha256: string;
  import_run_id: string;
  revision_id: string;
  imported_at: string;
  research_core_version: string;
  raw_tree_sha256: string;
  semantic_tree_sha256: string;
  materialization_sha256: string;
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
  operation_timelines: number;
  timeline_steps: number;
  arena_defenses: number;
  arena_defense_members: number;
  arena_counters: number;
  arena_counter_members: number;
  arena_counter_evidence: number;
  arena_counter_claims: number;
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
  reproducibility: GuideReproducibility;
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
  /** true/false only when the source states it; null means unknown/conflicting. */
  is_borrowed: boolean | null;
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

export interface SlotRequirements {
  slot1: SlotRequirement;
  slot2: SlotRequirement;
  slot3: SlotRequirement;
  slot4: SlotRequirement;
  slot5: SlotRequirement;
}

export interface OperationModeClaim {
  source_id: string;
  mode: Exclude<OperationMode, "SOURCE_CONFLICT">;
}

export interface TeamSupport {
  unit: string;
  requirements: string;
}

export interface TeamRequirements {
  schema_version: "1.0";
  slots: SlotRequirements;
  support: TeamSupport;
  operation_mode_claims: OperationModeClaim[];
  failure_conditions: string[];
  timeline_ref: string;
}

export type TimelineStatus = "STRUCTURED" | "PARTIAL" | "SOURCE_GAP" | "MISSING";
export type TimelineSourceStatus = "STRUCTURED" | "SOURCE_GAP";
export type TimelineOperationMode = "AUTO" | "SEMI_AUTO" | "MANUAL_TIMELINE" | "UNKNOWN";
export type TimelineClockMode = "COUNTDOWN" | "ELAPSED";
export type KnownTimelineAutoState = "ON" | "OFF";
export type TimelineAutoState = KnownTimelineAutoState | "UNKNOWN";
export type TimelineReproducibility = "UNVERIFIED_ON_TW" | "TW_REPRODUCED" | "UNKNOWN";
export type TimelineGapReason = "INSUFFICIENT_SOURCE_DETAIL" | "PENDING_EXTRACTION";
export type TimelineTriggerType =
  | "CLOCK"
  | "UB_READY"
  | "ANIMATION_CUE"
  | "HP_THRESHOLD"
  | "WAVE_START"
  | "BOSS_ACTION"
  | "SOURCE_TEXT_ONLY";
export type TimelineActionType =
  | "USE_UB"
  | "WAIT"
  | "AUTO_ON"
  | "AUTO_OFF"
  | "SET_ON"
  | "SET_OFF"
  | "PAUSE"
  | "RESUME"
  | "TARGET"
  | "NO_ACTION";
export type TimelineCriticality = "NORMAL" | "CRITICAL" | "UNKNOWN";
export type TimelineTimeState = "STATED" | "NOT_STATED";

export interface TimelineReference {
  source_id: string;
  locator: string;
  raw: string;
}

export interface TimelineStep {
  timeline_step_id: string;
  timeline_id: string;
  sequence_no: number;
  source_step_no: number;
  time_state: TimelineTimeState;
  trigger_type: TimelineTriggerType;
  trigger_actor_unit_key: string;
  clock_from_ms: number | null;
  clock_to_ms: number | null;
  actor_unit_key: string;
  action_type: TimelineActionType;
  target_unit_key: string;
  auto_state_after: TimelineAutoState;
  animation_cue: string;
  hp_threshold: string;
  tolerance_ms: number | null;
  criticality: TimelineCriticality;
  instruction_zh_tw: string;
  failure_if_missed: string;
  source_locator: string;
}

interface TimelineSourceBase {
  source_axis_id: string;
  source_id: string;
  source_evidence_id: string;
  source_locator: string;
  timeline_variant_name: string;
  operation_mode: TimelineOperationMode;
  reproducibility: TimelineReproducibility;
  last_verified_at: string;
  notes: string;
}

export interface StructuredTimelineSource extends TimelineSourceBase {
  status: "STRUCTURED";
  timeline_id: string;
  clock_mode: TimelineClockMode;
  battle_duration_ms: number | null;
  initial_auto_state: KnownTimelineAutoState;
  gap_reason: null;
  steps: TimelineStep[];
}

export interface GapTimelineSource extends TimelineSourceBase {
  status: "SOURCE_GAP";
  timeline_id: null;
  clock_mode: null;
  battle_duration_ms: null;
  initial_auto_state: null;
  gap_reason: TimelineGapReason;
  steps: [];
}

export type TimelineSource = StructuredTimelineSource | GapTimelineSource;

export interface TeamTimeline {
  status: TimelineStatus;
  structured_sources: number;
  registered_sources: number;
  sources: TimelineSource[];
  references: TimelineReference[];
  /** @deprecated Source axes must never be flattened or merged. */
  steps: [];
}

export interface TeamDetail extends TeamSummary {
  guide_id: string;
  server: string;
  stage: string;
  support_slot: string | null;
  requirements: TeamRequirements;
  timeline: TeamTimeline;
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

export type ArenaStatus =
  | "VERIFIED"
  | "PROVISIONAL"
  | "SINGLE_REPORT"
  | "STALE"
  | "REJECTED";
export type ArenaOutcome = "WIN" | "LOSS" | "MIXED" | "UNKNOWN";
export type ArenaVerification =
  | "SCREENSHOT_RESULT"
  | "VIDEO_RESULT"
  | "TEXT_REPORT"
  | "UNKNOWN";
export type ArenaRngRisk = "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN";
export type ArenaReproducibility =
  | "CONFIRMED"
  | "UNVERIFIED_REPEATABILITY"
  | "UNVERIFIED_ON_TW"
  | "UNKNOWN";
export type ArenaOperationMode = "AUTO_SYSTEM" | "MANUAL" | "UNKNOWN";
export type ArenaEnvironmentMatch = "EXACT" | "COMPATIBLE" | "MISMATCH" | "UNKNOWN";

export interface ArenaMember {
  slot: number;
  unit_key: string;
  display_name: string;
  display_name_source: "TW_OFFICIAL" | "JP_OFFICIAL";
}

export interface PvpCounter {
  counter_id: string;
  defense_id: string;
  server: "TW" | "JP";
  environment_version: string;
  arena_bracket: string;
  defense_signature: string;
  counter_signature: string;
  defense_members: ArenaMember[];
  counter_members: ArenaMember[];
  status: ArenaStatus;
  match_type: "EXACT";
  outcome: ArenaOutcome;
  verification: ArenaVerification;
  sample_size: number | null;
  wins: number | null;
  losses: number | null;
  empirical_win_rate: number | null;
  randomness: string;
  rng_risk: ArenaRngRisk;
  claim_confidence: "B" | "C" | "D" | "E";
  reproducibility: ArenaReproducibility;
  source_tier: string;
  source_record_count: number;
  source_platforms: string[];
  tw_availability_check: "PASS" | "FAIL" | "UNVERIFIED";
  unavailable_unit_ids: string[];
  required_upgrade_check: "PASS" | "FAIL" | "UNKNOWN" | "NOT_APPLICABLE";
  operation_mode: ArenaOperationMode;
  environment_match: ArenaEnvironmentMatch;
  speed_conditions: string;
  initial_action_notes: string;
  verified_date: string;
  last_review_due: string | null;
  record_date_min: string | null;
  record_date_max: string | null;
  notes: string;
  evidence_ids: string[];
  claim_ids: string[];
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
    id?: string | null;
    reason?: string;
  };
}
