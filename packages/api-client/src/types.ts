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
  api_version: "v1";
  generated_at: string;
  server: "TW" | "JP" | "MIXED" | "UNKNOWN";
  environment_version: string;
  verified_at: string | null;
  stale_status: "CURRENT" | "STALE" | "UNKNOWN";
  confidence: "A" | "B" | "C" | "D" | "E" | "UNKNOWN";
  evidence_ids: string[];
  claim_ids: string[];
  data_revision: string;
  source: SourceMetadata;
  warnings: string[];
}

export interface ApiEnvelope<T> {
  data: T;
  meta: ApiMetadata;
}

export interface PveLibrarySourceWorkbook {
  filename: string;
  sha256: string;
  byte_length: number;
  staging_catalog_sha256: string;
}

export interface PveLibraryMeta {
  api_version: "v1";
  schema_version: "private-pve-local-catalog/v1";
  dataset_sha256: string;
  source_status: "SOURCE_PROVIDED";
  independent_clear_verification: "NOT_PERFORMED";
  source_workbooks: PveLibrarySourceWorkbook[];
}

export interface PveLibraryEnvelope<T> {
  data: T;
  meta: PveLibraryMeta;
}

export interface PveStageRef {
  kind: string;
  area: number;
  stage: number;
}

export interface PveProvenance {
  source_workbook_sha256: string;
  source_workbook_filename: string;
  staging_catalog_sha256: string;
  sheet_name: string;
  source_range: string;
}

export interface PveStageSummary {
  stage_id: string;
  mode: string;
  element: string;
  label_raw: string | null;
  stage_refs: PveStageRef[];
  team_count: number;
  provenance: PveProvenance;
}

export interface PveLibraryStageFilters {
  mode?: string;
  element?: string;
  area?: number;
  stage?: number;
}

export interface PveStageListData {
  items: PveStageSummary[];
  filters: {
    mode: string | null;
    element: string | null;
    area: number | null;
    stage: number | null;
  };
  available_filters: {
    modes: string[];
    elements: string[];
    areas: number[];
    stages: number[];
  };
  total: number;
}

export interface PveYoutubeMedia {
  kind: "YOUTUBE";
  external_url: string;
  embed_url: string;
  video_id: string;
}

export interface PveExternalMedia {
  kind: "EXTERNAL";
  external_url: string;
  embed_url: null;
  video_id: null;
}

export type PveLinkMedia = PveYoutubeMedia | PveExternalMedia;

export interface PveSourceLink {
  kind: string;
  label_raw: string | null;
  origin_cell: string;
  resolution_status: string;
  alias_id: string | null;
  alias_label: string | null;
  applies_to_cell: string | null;
  url: string | null;
  media: PveLinkMedia | null;
}

export type PveSourceOrderState = "SET" | "NOT_SET";

export interface PveOperationVariant {
  kind: string;
  raw: string;
  origin_field: string;
  origin_cell: string;
  source_order_states: PveSourceOrderState[];
}

export interface PveOperation {
  kind: string;
  order_basis: string;
  member_alignment: string;
  execution_hints: string[];
  variants: PveOperationVariant[];
}

export interface PveAxis {
  axis_id: string;
  operation_raw: string | null;
  notes_raw: string | null;
  source_cell: string;
  operation: PveOperation;
  source_links: PveSourceLink[];
}

export type PveDisplayRarity = "THREE_STAR" | "SIX_STAR";

export interface PvePortrait {
  display_position: number;
  asset_sha256: string;
  asset_url: string;
  icon_url: string | null;
  mapping_status: string;
  unit_key: string | null;
  tw_name: string | null;
  display_rarity: PveDisplayRarity | null;
  display_source: string;
  anchor_cell: string;
}

export interface PveTeam {
  team_id: string;
  display_order: number;
  notes_raw: string | null;
  flags: string[];
  source_range: string;
  portraits: PvePortrait[];
  axes: PveAxis[];
  source_links: PveSourceLink[];
  provenance: PveProvenance;
}

export interface PveStageDetail extends PveStageSummary {
  teams: PveTeam[];
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
  gacha_timeline_events: number;
  gacha_timeline_evidence: number;
  gacha_timeline_claims: number;
  gacha_community_sources: number;
  gacha_timeline_community_sources: number;
  arena_source_records: number;
  parena_cases: number;
  parena_case_matchups: number;
  parena_case_sources: number;
  parena_case_evidence: number;
  parena_case_claims: number;
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

export interface PvpCharacter {
  unit_key: string;
  tw_name: string;
  jp_name: string;
  tw_availability_status: "AVAILABLE";
}

export type GachaForecastMethod =
  | "MODEL_ONLY"
  | "MODEL_PLUS_COMMUNITY"
  | "OFFICIAL_OVERRIDE";
export type GachaLimitedStatus = "YES" | "NO" | "UNKNOWN";
export type GachaMaturity = "MATURE" | "RESEARCH";

export interface GachaTimelineEvent {
  event_id: string;
  source_server: "JP";
  target_server: "TW";
  jp_date: string;
  model_estimate_start: string | null;
  model_estimate_end: string | null;
  tw_estimate_start: string | null;
  tw_estimate_end: string | null;
  forecast_method: GachaForecastMethod;
  confidence: string;
  character_name_jp: string;
  /** Null until a TW official name exists; never a translated or JP fallback. */
  tw_name: string | null;
  pool_type: string;
  limited_status: GachaLimitedStatus;
  /** Provenance for YES/NO; null exactly when limited_status is UNKNOWN. */
  limited_claim_id: string | null;
  arena_value: string;
  p_arena_value: string;
  pve_value: string;
  clan_value: string;
  future_upgrade: string;
  relative_priority: string;
  anchor_track: string;
  anchor_count: number;
  forecast_basis: string;
  last_verified: string;
  status: string;
  maturity: GachaMaturity;
  last_review_due: string | null;
  community_estimate_start: string | null;
  community_estimate_end: string | null;
  community_order_consensus: string;
  community_source_count: number;
  community_last_checked: string | null;
  community_disagreement: string;
  forecast_notes: string;
  evidence_ids: string[];
  claim_ids: string[];
  community_source_ids: string[];
}

export type GachaCommunitySourceType =
  | "MAINTAINED_TABLE"
  | "FORUM_TIMELINE"
  | "CREATOR_ANALYSIS"
  | "VIDEO_SERIES";
export type GachaCommunityUpdateStatus = "PENDING_FETCH" | "CHECKED" | "STALE";
export type GachaCommunityConfidenceCap = "C" | "D" | "E";

export interface GachaCommunitySource {
  source_id: string;
  title: string;
  platform: string;
  author: string;
  source_type: GachaCommunitySourceType;
  url: string;
  last_seen_update: string | null;
  coverage_start: string | null;
  coverage_end: string | null;
  update_status: GachaCommunityUpdateStatus;
  confidence_cap: GachaCommunityConfidenceCap;
  usage: string;
  last_checked: string;
  notes: string;
}

export type GachaLibraryPoolKind =
  | "LIMITED_PICKUP"
  | "PERMANENT_PICKUP"
  | "RERUN";

export interface GachaLibraryForecast {
  candidate_id: string;
  review_order: number;
  source_declared_pool_kind: GachaLibraryPoolKind;
  /** User-supplied document labels; never treated as official TW names. */
  raw_character_names: string[];
  forecast_start: string;
  forecast_end: string;
  raw_sequence_label: string | null;
  raw_description_lines: string[];
  raw_forecast_text: string;
  precision: "DAY";
  date_boundary_semantics: "SOURCE_UNSPECIFIED";
  identity_status: "UNVERIFIED_COMMUNITY_NAME";
  review_status: "PENDING";
  review_reason:
    | "EXACT_EVENT_LINK_NOT_REVIEWED"
    | "UNDELIMITED_CHARACTER_TEXT_REQUIRES_REVIEW";
  promotion_eligible: false;
  proposed_event_id: null;
  parser_warnings: Array<"UNQUOTED_CHARACTER_SEQUENCE">;
  image: {
    sha256: string;
    mime_type: "image/jpeg" | "image/png" | "image/webp";
    byte_length: number;
    /** Must be a same-origin /api/v1/gacha-library/assets/<sha256> path. */
    asset_url: string;
  };
  provenance: {
    description_locators: string[];
    source_locator: string;
    image_locator: string;
    relationship_id: string;
    package_path: string;
  };
}

export interface GachaLibrarySourceDocument {
  content_addressed_filename: string;
  sha256: string;
  byte_length: number;
}

export interface GachaLibraryForecastData {
  items: GachaLibraryForecast[];
  total: number;
}

export interface GachaLibraryMeta {
  api_version: "v1";
  schema_version: "gacha-community-docx-candidates/v1";
  dataset_sha256: string;
  source_status: "USER_SUPPLIED";
  authority: "COMMUNITY_FORECAST";
  source_id: "GACHA-COMM-002";
  independence_group: "GACHA-COMM-002";
  canonical_write_count: 0;
  source_document: GachaLibrarySourceDocument;
}

export interface GachaLibraryEnvelope<T> {
  data: T;
  meta: GachaLibraryMeta;
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

export interface ParenaEnvironment {
  server: "TW";
  environment_version: string;
  verified_case_count: number;
}

export interface ParenaSolveRequest {
  server: "TW";
  environment_version: string;
  defense_teams: string[][];
}

export interface ArenaSourceRecord {
  source_id: string;
  title: string;
  platform: string;
  source_type: string;
  server: "TW";
  url: string;
  last_checked: string;
  freshness_window: string | null;
  access_status: "ACTIVE";
  confidence_cap: "C" | "D" | "E";
  extraction_method: string;
  notes: string;
}

export interface ParenaMatchup {
  matchup_no: number;
  defense_input_index: number;
  result_claim_id: string;
  counter: PvpCounter;
}

export interface ParenaCase {
  case_id: string;
  server: "TW";
  environment_version: string;
  status: "VERIFIED";
  hidden_team_mode: "NONE";
  verified_date: string;
  reproducibility: "CONFIRMED";
  last_review_due: string;
  notes: string;
  case_win_claim_id: string;
  case_win_confidence: "B" | "C" | "D";
  sources: ArenaSourceRecord[];
  evidence_ids: string[];
  claim_ids: string[];
  matchups: ParenaMatchup[];
}

export interface ParenaSolveData {
  match_type: "EXACT";
  similar_enabled: false;
  query_signature: string;
  defense_teams: string[][];
  cases: ParenaCase[];
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
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, string | number | null>;
  };
}
