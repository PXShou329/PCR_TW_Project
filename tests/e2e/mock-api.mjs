// TEST_ONLY fixture server. It never writes to the research core or canonical database.
import { createServer } from "node:http";

const host = "127.0.0.1";
const port = 4100;
const guideId = "TW_DEEP_FIRE_08_10_20260802";

const character = {
  luisemarie_orig: "露易絲瑪莉",
  lailael_xmas: "萊拉耶爾（聖誕節）",
  croce_aerial: "克蘿茜（航空）",
  vurm_orig: "烏爾姆",
  lind_orig: "琳德",
  shizuru_valentine: "靜流（情人節）",
  maho_summer: "真步（夏日）",
  yui_xmas: "優衣（聖誕節）",
  anne_grea_orig: "安＆古蕾婭",
  mio_ngs: "未央（NGs）",
};

const teamSeeds = [
  {
    team_id: "TM-F810-01",
    operation_mode: "SOURCE_CONFLICT",
    stability: "多來源交叉驗證",
    units: ["luisemarie_orig", "lailael_xmas", "croce_aerial", "vurm_orig", "lind_orig"],
    source_ids: ["appmatch_fire_guide", "yt_jkPXr3aUZZQ", "yt_tYwLvHHbKXo"],
    evidence_ids: ["ev050", "ev052", "ev056", "ev057", "ev058", "ev059", "ev060", "ev069"],
    operation_mode_claims: [
      { mode: "AUTO", source_id: "appmatch_fire_guide" },
      { mode: "SEMI_AUTO", source_id: "yt_jkPXr3aUZZQ" },
      { mode: "SEMI_AUTO", source_id: "yt_tYwLvHHbKXo" },
    ],
    timeline_ref: "AX-F810-01-EV050;AX-F810-01-EV052;AX-F810-01-EV069",
    support: { unit: "SOURCE_CONFLICT", requirements: "yt_tYwLvHHbKXo=lind_orig borrowed; other sources=UNKNOWN" },
    notes: "相同五人來源已合併；AUTO 與 SEMI_AUTO 聲明衝突；逐 slot 未知條件均保留 UNKNOWN。",
  },
  {
    team_id: "TM-F810-02",
    operation_mode: "SEMI_AUTO",
    stability: "多來源交叉驗證",
    units: ["shizuru_valentine", "lailael_xmas", "croce_aerial", "vurm_orig", "luisemarie_orig"],
    source_ids: ["yt_F39PkRIg0T4", "yt_OtiJrk3jacg", "yt_i4pE3GxTMMA", "gamewith_fire_8_10"],
    evidence_ids: ["ev056", "ev057", "ev058", "ev060", "ev070", "ev071", "ev072", "ev073", "ev074", "ev075"],
    operation_mode_claims: [
      { mode: "SEMI_AUTO", source_id: "yt_F39PkRIg0T4" },
      { mode: "SEMI_AUTO", source_id: "yt_OtiJrk3jacg" },
      { mode: "SEMI_AUTO", source_id: "yt_i4pE3GxTMMA" },
      { mode: "SEMI_AUTO", source_id: "gamewith_fire_8_10" },
    ],
    timeline_ref: "AX-F810-02-EV070;AX-F810-02-EV071;AX-F810-02-EV072;AX-F810-02-EV073",
    support: { unit: "UNKNOWN", requirements: "UNKNOWN" },
    notes: "操作含 SET 切換，歸類為 SEMI_AUTO；泛化練度不拆填逐 slot。",
  },
  {
    team_id: "TM-F810-03",
    operation_mode: "SEMI_AUTO",
    stability: "單一實戰",
    units: ["maho_summer", "lailael_xmas", "croce_aerial", "vurm_orig", "yui_xmas"],
    source_ids: ["yt_ZXUDJm_AsSA", "gamewith_fire_8_10"],
    evidence_ids: ["ev051", "ev057", "ev058", "ev060", "ev073", "ev075", "ev076"],
    operation_mode_claims: [{ mode: "SEMI_AUTO", source_id: "yt_ZXUDJm_AsSA" }],
    timeline_ref: "AX-F810-03-EV051",
    support: { unit: "croce_aerial", requirements: "yt_ZXUDJm_AsSA=borrowed Croce (Aerial); exact build UNKNOWN" },
    notes: "僅供參考：單一實戰；克蘿茜（航空）為借角，精確練度仍 UNKNOWN。",
  },
  {
    team_id: "TM-F810-04",
    operation_mode: "UNKNOWN",
    stability: "單一實戰",
    units: ["lailael_xmas", "croce_aerial", "vurm_orig", "anne_grea_orig", "yui_xmas"],
    source_ids: ["yt_p95ZoBCWuYE"],
    evidence_ids: ["ev057", "ev058", "ev060", "ev076", "ev078", "ev079", "ev082"],
    operation_mode_claims: [{ mode: "UNKNOWN", source_id: "yt_p95ZoBCWuYE" }],
    timeline_ref: "AX-F810-04-EV082",
    support: { unit: "UNKNOWN", requirements: "UNKNOWN" },
    notes: "僅供參考：單一實戰；來源未充分聲明操作模式，故 operation mode 與逐 slot 條件均維持 UNKNOWN。",
  },
  {
    team_id: "TM-F810-05",
    operation_mode: "SEMI_AUTO",
    stability: "單一實戰",
    units: ["croce_aerial", "vurm_orig", "mio_ngs", "anne_grea_orig", "yui_xmas"],
    source_ids: ["yt_Zw31omyYDKI"],
    evidence_ids: ["ev057", "ev060", "ev076", "ev078", "ev079", "ev080", "ev081", "ev083"],
    operation_mode_claims: [{ mode: "SEMI_AUTO", source_id: "yt_Zw31omyYDKI" }],
    timeline_ref: "AX-F810-05-EV083",
    support: { unit: "UNKNOWN", requirements: "UNKNOWN" },
    failure_conditions: [
      "來源全域養成條件只作整隊說明，不拆填逐 slot。",
      "來源只寫優衣（聖誕節）＝適当，精確條件 UNKNOWN。",
    ],
    notes: "僅供參考：來源聲明 SEMI_AUTO；不明確的 actor/action 只保存為 SOURCE_TEXT_ONLY／NO_ACTION。",
  },
];

const unknownSlot = () => ({
  connect_rank: "UNKNOWN",
  element_boost: "UNKNOWN",
  rank: "UNKNOWN",
  six_star: "UNKNOWN",
  star: "UNKNOWN",
  ue1: "UNKNOWN",
  ue2: "UNKNOWN",
});

const members = (seed) => seed.units.map((unit_key, index) => ({
  slot: index + 1,
  unit_key,
  tw_name: character[unit_key],
  is_borrowed: seed.team_id === "TM-F810-03" && index === 2,
}));

const teamSummary = (seed) => ({
  team_id: seed.team_id,
  operation_mode: seed.operation_mode,
  clear_status: "VERIFIED",
  stability: seed.stability,
  members: members(seed),
});

const stageSummary = {
  guide_id: guideId,
  server: "TW",
  mode: "DEEP",
  area: "紅焰",
  stage: "8-10",
  status: "VERIFIED",
  team_count: 5,
  reproducibility: "CONFIRMED",
  verified_date: "2026-08-08",
};

const secondaryStageSummary = {
  guide_id: "TW_DEEP_FIRE_10_10_20260802",
  server: "TW",
  mode: "DEEP",
  area: "紅焰",
  stage: "10-10",
  status: "IN_RESEARCH",
  team_count: 0,
  reproducibility: "PENDING",
  verified_date: "2026-08-02",
};

const meta = (warnings = []) => ({
  api_version: "v1",
  generated_at: "2026-08-08T00:00:00Z",
  source: {
    canonical_source: "research_core_file_ssot",
    fixture_sha256: "a".repeat(64),
    import_run_id: "00000000-0000-4000-8000-000000000001",
    revision_id: "a".repeat(64),
    imported_at: "2026-08-08T00:00:00Z",
    research_core_version: "v1.5",
    raw_tree_sha256: "a".repeat(64),
    semantic_tree_sha256: "c".repeat(64),
    materialization_sha256: "d".repeat(64),
  },
  warnings,
});

const envelope = (data, warnings = []) => ({ data, meta: meta(warnings) });

const baseline = envelope({
  research_core_version: "v1.5",
  application_version: "3.0.0-a3",
  canonical_source: "research_core_file_ssot",
  generated_at: "2026-08-08T00:00:00Z",
  counts: {
    stages: 2,
    teams: 5,
    team_members: 25,
    characters: 17,
    evidence: 34,
    claims: 27,
    operation_timelines: 10,
    timeline_steps: 19,
  },
  gates: { gate_a: false, gate_b: false, gate_c: false },
  featured_stage: stageSummary,
});

const stageDetail = envelope({
  ...stageSummary,
  applicable_version: "ch16/Lv373",
  source_tier: "SINGLE_PLAYER_REPORT",
  claim_confidence: "D",
  last_review_due: "2026-09-30",
  notes: "實際開頁與逐幀核對後取得 5 支不同五人的 VERIFIED effective teams；相同五人多來源已去重，未知操作模式與逐 slot 條件仍誠實保留。",
  coverage: { verified_distinct_teams: 5, maturity_target: 5, remaining: 0, is_mature: true },
  teams: teamSeeds.map(teamSummary),
  evidence_ids: ["ev050", "ev051", "ev052", "ev056", "ev057", "ev058", "ev059", "ev060", "ev069", "ev070", "ev071", "ev072", "ev073", "ev074", "ev075", "ev076", "ev077", "ev078", "ev079", "ev080", "ev081", "ev082", "ev083"],
  claim_ids: ["CLM-PVE-F810-STD", "CLM-PVE-F810-SHIZURU", "CLM-PVE-F810-NOLUISE", "CLM-PVE-F810-ANNEGREA", "CLM-PVE-F810-MIO", "CLM-PVE-TL-F810-MIO", "CLM-TW-LUISE-ORIG-REL", "CLM-TW-CROCE-AERIAL-REL", "CLM-TW-LAILAEL-XMAS-REL", "CLM-TW-LIND-REL", "CLM-TW-VURM-REL", "CLM-TW-SHIZURU-VAL-AVAILABLE", "CLM-TW-MAHO-SUMMER-AVAILABLE", "CLM-TW-YUI-XMAS-REL", "CLM-TW-LAILAEL-XMAS-UE1", "CLM-TW-ANNE-GREA-REL", "CLM-LOC-ANNE-GREA", "CLM-TW-MIO-NGS-AVAILABLE", "CLM-LOC-MIO-NGS"].sort(),
});

const secondaryStageDetail = envelope({
  ...secondaryStageSummary,
  applicable_version: "ch16/Lv373",
  source_tier: "SINGLE_PLAYER_REPORT",
  claim_confidence: "D",
  last_review_due: "2026-08-31",
  notes: "目前只有稀缺性與版本脈絡，尚無符合完整五人、明確關卡及實際通關三項條件的有效隊伍。",
  coverage: { verified_distinct_teams: 0, maturity_target: 5, remaining: 5, is_mature: false },
  teams: [],
  evidence_ids: ["ev029", "ev054", "ev055"],
  claim_ids: ["CLM-PVE-F1010-SCARCE"],
});

function splitTimeline(raw) {
  return raw.split(";").map((value) => {
    const [source_id, locator = "UNKNOWN"] = value.split("@");
    return { source_id, locator, raw: value };
  });
}

function gapSource({ axis, source, evidence, locator, variant, operationMode, notes }) {
  return {
    source_axis_id: axis,
    timeline_id: null,
    source_id: source,
    source_evidence_id: evidence,
    source_locator: locator,
    timeline_variant_name: variant,
    operation_mode: operationMode,
    clock_mode: null,
    battle_duration_ms: null,
    initial_auto_state: null,
    status: "SOURCE_GAP",
    reproducibility: "UNKNOWN",
    gap_reason: "INSUFFICIENT_SOURCE_DETAIL",
    last_verified_at: "2026-08-08",
    notes,
    steps: [],
  };
}

function timelineStep({
  id,
  timelineId = "TL-F810-02-EV073",
  sequence,
  sourceStep,
  timeState,
  milliseconds,
  trigger,
  triggerActor = "NONE",
  actor,
  action,
  autoState,
  cue,
  instruction,
  locator,
}) {
  return {
    timeline_step_id: id,
    timeline_id: timelineId,
    sequence_no: sequence,
    source_step_no: sourceStep,
    time_state: timeState,
    trigger_type: trigger,
    trigger_actor_unit_key: triggerActor,
    clock_from_ms: timeState === "STATED" ? milliseconds : null,
    clock_to_ms: timeState === "STATED" ? milliseconds : null,
    actor_unit_key: actor,
    action_type: action,
    target_unit_key: "NONE",
    auto_state_after: autoState,
    animation_cue: cue,
    hp_threshold: "UNKNOWN",
    tolerance_ms: null,
    criticality: "UNKNOWN",
    instruction_zh_tw: instruction,
    failure_if_missed: "UNKNOWN",
    source_locator: locator,
  };
}

const tm2StructuredSteps = [
  timelineStep({ id: "TLS-F810-02-001", sequence: 1, sourceStep: 1, timeState: "NOT_STATED", milliseconds: null, trigger: "WAVE_START", actor: "luisemarie_orig", action: "SET_ON", autoState: "ON", cue: "戰鬥開始", instruction: "開場將露易絲瑪莉設為 SET。", locator: "2025年9月魔法半自動／手順1" }),
  timelineStep({ id: "TLS-F810-02-002", sequence: 2, sourceStep: 1, timeState: "NOT_STATED", milliseconds: null, trigger: "WAVE_START", actor: "lailael_xmas", action: "SET_ON", autoState: "ON", cue: "戰鬥開始", instruction: "開場將萊拉耶爾（聖誕節）設為 SET。", locator: "2025年9月魔法半自動／手順1" }),
  timelineStep({ id: "TLS-F810-02-003", sequence: 3, sourceStep: 1, timeState: "NOT_STATED", milliseconds: null, trigger: "WAVE_START", actor: "croce_aerial", action: "SET_ON", autoState: "ON", cue: "戰鬥開始", instruction: "開場將克蘿茜（航空）設為 SET。", locator: "2025年9月魔法半自動／手順1" }),
  timelineStep({ id: "TLS-F810-02-004", sequence: 4, sourceStep: 1, timeState: "NOT_STATED", milliseconds: null, trigger: "WAVE_START", actor: "shizuru_valentine", action: "SET_ON", autoState: "ON", cue: "戰鬥開始", instruction: "開場將靜流（情人節）設為 SET；烏爾姆先不設 SET。", locator: "2025年9月魔法半自動／手順1" }),
  timelineStep({ id: "TLS-F810-02-005", sequence: 5, sourceStep: 2, timeState: "STATED", milliseconds: 70000, trigger: "ANIMATION_CUE", triggerActor: "vurm_orig", actor: "vurm_orig", action: "SET_ON", autoState: "ON", cue: "烏爾姆 UB 結束後", instruction: "倒數 1:10 左右，在烏爾姆 UB 後開啟烏爾姆 SET。", locator: "2025年9月魔法半自動／手順2" }),
  timelineStep({ id: "TLS-F810-02-006", sequence: 6, sourceStep: 3, timeState: "STATED", milliseconds: 62000, trigger: "ANIMATION_CUE", triggerActor: "croce_aerial", actor: "vurm_orig", action: "SET_OFF", autoState: "ON", cue: "克蘿茜（航空）UB 結束後", instruction: "倒數 1:02 左右，在克蘿茜（航空）UB 後關閉烏爾姆 SET。", locator: "2025年9月魔法半自動／手順3" }),
  timelineStep({ id: "TLS-F810-02-007", sequence: 7, sourceStep: 3, timeState: "STATED", milliseconds: 62000, trigger: "ANIMATION_CUE", triggerActor: "croce_aerial", actor: "croce_aerial", action: "SET_OFF", autoState: "ON", cue: "克蘿茜（航空）UB 結束後", instruction: "同一時間點關閉克蘿茜（航空）SET。", locator: "2025年9月魔法半自動／手順3" }),
  timelineStep({ id: "TLS-F810-02-008", sequence: 8, sourceStep: 4, timeState: "STATED", milliseconds: 53000, trigger: "ANIMATION_CUE", triggerActor: "shizuru_valentine", actor: "vurm_orig", action: "SET_ON", autoState: "ON", cue: "靜流（情人節）UB 結束後", instruction: "倒數 0:53 左右，在靜流（情人節）UB 後開啟烏爾姆 SET。", locator: "2025年9月魔法半自動／手順4" }),
  timelineStep({ id: "TLS-F810-02-009", sequence: 9, sourceStep: 4, timeState: "STATED", milliseconds: 53000, trigger: "ANIMATION_CUE", triggerActor: "shizuru_valentine", actor: "croce_aerial", action: "SET_ON", autoState: "ON", cue: "靜流（情人節）UB 結束後", instruction: "同一時間點開啟克蘿茜（航空）SET。", locator: "2025年9月魔法半自動／手順4" }),
  timelineStep({ id: "TLS-F810-02-010", sequence: 10, sourceStep: 4, timeState: "STATED", milliseconds: 53000, trigger: "ANIMATION_CUE", triggerActor: "shizuru_valentine", actor: "NONE", action: "AUTO_OFF", autoState: "OFF", cue: "靜流（情人節）UB 結束後", instruction: "完成兩個 SET 切換後關閉 AUTO。", locator: "2025年9月魔法半自動／手順4" }),
  timelineStep({ id: "TLS-F810-02-011", sequence: 11, sourceStep: 5, timeState: "STATED", milliseconds: 34000, trigger: "ANIMATION_CUE", triggerActor: "shizuru_valentine", actor: "shizuru_valentine", action: "SET_OFF", autoState: "OFF", cue: "靜流（情人節）UB 結束後", instruction: "倒數 0:34 左右，在靜流（情人節）UB 後關閉其 SET。", locator: "2025年9月魔法半自動／手順5" }),
  timelineStep({ id: "TLS-F810-02-012", sequence: 12, sourceStep: 6, timeState: "STATED", milliseconds: 25000, trigger: "ANIMATION_CUE", triggerActor: "lailael_xmas", actor: "shizuru_valentine", action: "SET_ON", autoState: "OFF", cue: "萊拉耶爾（聖誕節）UB 結束後", instruction: "倒數 0:25 左右開啟靜流（情人節）SET，並於途中取消來源所稱「セグメント」技能動作。", locator: "2025年9月魔法半自動／手順6" }),
  timelineStep({ id: "TLS-F810-02-013", sequence: 13, sourceStep: 7, timeState: "STATED", milliseconds: 17000, trigger: "ANIMATION_CUE", triggerActor: "shizuru_valentine", actor: "shizuru_valentine", action: "SET_OFF", autoState: "OFF", cue: "靜流（情人節）UB 結束後", instruction: "倒數 0:17 左右，在靜流（情人節）UB 後關閉其 SET。", locator: "2025年9月魔法半自動／手順7" }),
  timelineStep({ id: "TLS-F810-02-014", sequence: 14, sourceStep: 8, timeState: "STATED", milliseconds: 5000, trigger: "ANIMATION_CUE", triggerActor: "croce_aerial", actor: "shizuru_valentine", action: "USE_UB", autoState: "OFF", cue: "克蘿茜（航空）UB 結束後", instruction: "倒數 0:05 左右，在克蘿茜（航空）UB 後立即施放靜流（情人節）UB，以取消來源所稱「セグメント」技能動作。", locator: "2025年9月魔法半自動／手順8" }),
];

const tm5SourceTextSteps = [
  timelineStep({ id: "TLS-F810-05-001", timelineId: "TL-F810-05-EV083", sequence: 1, sourceStep: 1, timeState: "STATED", milliseconds: 90000, trigger: "SOURCE_TEXT_ONLY", actor: "NONE", action: "NO_ACTION", autoState: "OFF", cue: "raw_set_pattern=[〇〇〇〇〇]", instruction: "來源原文：1:30 [〇〇〇〇〇](OFF)；actor 未標示，方括號圖樣定義 UNKNOWN。", locator: "影片說明／timeline 1" }),
  timelineStep({ id: "TLS-F810-05-002", timelineId: "TL-F810-05-EV083", sequence: 2, sourceStep: 2, timeState: "STATED", milliseconds: 38000, trigger: "SOURCE_TEXT_ONLY", triggerActor: "anne_grea_orig", actor: "anne_grea_orig", action: "NO_ACTION", autoState: "OFF", cue: "raw_set_pattern=[〇〇〇ー〇]", instruction: "來源原文：0:38 アングレア [〇〇〇ー〇](OFF)；僅保存角色 marker，不推定動作。", locator: "影片說明／timeline 2" }),
  timelineStep({ id: "TLS-F810-05-003", timelineId: "TL-F810-05-EV083", sequence: 3, sourceStep: 3, timeState: "STATED", milliseconds: 27000, trigger: "SOURCE_TEXT_ONLY", triggerActor: "vurm_orig", actor: "vurm_orig", action: "NO_ACTION", autoState: "OFF", cue: "raw_set_pattern=[〇〇〇〇〇]", instruction: "來源原文：0:27 ヴルム [〇〇〇〇〇](OFF)；僅保存角色 marker，不推定動作。", locator: "影片說明／timeline 3" }),
  timelineStep({ id: "TLS-F810-05-004", timelineId: "TL-F810-05-EV083", sequence: 4, sourceStep: 4, timeState: "STATED", milliseconds: 26000, trigger: "SOURCE_TEXT_ONLY", triggerActor: "yui_xmas", actor: "yui_xmas", action: "NO_ACTION", autoState: "OFF", cue: "raw_set_pattern=[〇〇〇〇ー]", instruction: "來源原文：0:26 ユイ [〇〇〇〇ー](OFF)；僅保存角色 marker，不推定動作。", locator: "影片說明／timeline 4" }),
  timelineStep({ id: "TLS-F810-05-005", timelineId: "TL-F810-05-EV083", sequence: 5, sourceStep: 5, timeState: "STATED", milliseconds: 7000, trigger: "SOURCE_TEXT_ONLY", triggerActor: "vurm_orig", actor: "vurm_orig", action: "NO_ACTION", autoState: "ON", cue: "raw_set_pattern=[〇〇〇〇ー]", instruction: "來源原文：0:07 ヴルム [〇〇〇〇ー](ON)；僅保存角色 marker，不推定動作。", locator: "影片說明／timeline 5" }),
];

const sourcesByTeam = {
  "TM-F810-01": [
    gapSource({ axis: "AX-F810-01-EV050", source: "appmatch_fire_guide", evidence: "ev050", locator: "appmatch_fire_deep_guide", variant: "AUTO 聲明來源", operationMode: "AUTO", notes: "正文只聲明全自動編成；未提供可驗證的逐步操作軸" }),
    gapSource({ axis: "AX-F810-01-EV052", source: "yt_jkPXr3aUZZQ", evidence: "ev052", locator: "yt_jkPXr3aUZZQ@00:45-05:50", variant: "目押三次實戰來源", operationMode: "SEMI_AUTO", notes: "影片可定位隊伍與通關；本輪未取得可逐步轉錄的完整操作軸" }),
    gapSource({ axis: "AX-F810-01-EV069", source: "yt_tYwLvHHbKXo", evidence: "ev069", locator: "yt_tYwLvHHbKXo@00:00-05:05", variant: "四次手動實戰來源", operationMode: "SEMI_AUTO", notes: "影片可定位隊伍與通關；本輪未取得可逐步轉錄的完整操作軸" }),
  ],
  "TM-F810-02": [
    gapSource({ axis: "AX-F810-02-EV070", source: "yt_F39PkRIg0T4", evidence: "ev070", locator: "yt_F39PkRIg0T4@02:34-05:27", variant: "攻略彙整影片來源", operationMode: "SEMI_AUTO", notes: "影片展示操作表與通關；未逐項轉錄為可驗證步驟" }),
    gapSource({ axis: "AX-F810-02-EV071", source: "yt_OtiJrk3jacg", evidence: "ev071", locator: "yt_OtiJrk3jacg@00:58-04:37", variant: "台服創作者實戰來源", operationMode: "SEMI_AUTO", notes: "台服影片可定位隊伍與通關；未取得完整文字化操作軸" }),
    gapSource({ axis: "AX-F810-02-EV072", source: "yt_i4pE3GxTMMA", evidence: "ev072", locator: "yt_i4pE3GxTMMA@04:11-07:18", variant: "原始作業影片來源", operationMode: "SEMI_AUTO", notes: "影片可定位隊伍與通關且可見 SET 切換；未逐項轉錄為可驗證步驟" }),
    {
      source_axis_id: "AX-F810-02-EV073",
      timeline_id: "TL-F810-02-EV073",
      source_id: "gamewith_fire_8_10",
      source_evidence_id: "ev073",
      source_locator: "gamewith_fire_8_10#2025-09-magic-semi-auto-steps-1-8",
      timeline_variant_name: "2025 年 9 月魔法半自動",
      operation_mode: "SEMI_AUTO",
      clock_mode: "COUNTDOWN",
      battle_duration_ms: null,
      initial_auto_state: "ON",
      status: "STRUCTURED",
      reproducibility: "UNVERIFIED_ON_TW",
      gap_reason: null,
      last_verified_at: "2026-08-08",
      notes: "依已實開 GameWith 正文的八個來源步驟拆成原子操作；來源未明載戰鬥總長；本操作軸尚未逐步於台服重現。",
      steps: tm2StructuredSteps,
    },
  ],
  "TM-F810-03": [
    gapSource({ axis: "AX-F810-03-EV051", source: "yt_ZXUDJm_AsSA", evidence: "ev051", locator: "yt_ZXUDJm_AsSA@00:12-03:15", variant: "無露易絲瑪莉實戰來源", operationMode: "SEMI_AUTO", notes: "影片可定位隊伍與通關且操作需 AUTO／SET 切換；未取得完整逐步操作軸" }),
  ],
  "TM-F810-04": [
    gapSource({ axis: "AX-F810-04-EV082", source: "yt_p95ZoBCWuYE", evidence: "ev082", locator: "yt_p95ZoBCWuYE@00:00-02:35", variant: "安＆古蕾婭實戰來源", operationMode: "UNKNOWN", notes: "影片可定位關卡、完整五人與 Boss HP 歸零；AUTO／SET 畫面不足以證明全程模式。" }),
  ],
  "TM-F810-05": [
    {
      source_axis_id: "AX-F810-05-EV083",
      timeline_id: "TL-F810-05-EV083",
      source_id: "yt_Zw31omyYDKI",
      source_evidence_id: "ev083",
      source_locator: "yt_Zw31omyYDKI@00:00-01:56#description-timeline",
      timeline_variant_name: "未央（NGs）半自動來源文字",
      operation_mode: "SEMI_AUTO",
      clock_mode: "COUNTDOWN",
      battle_duration_ms: null,
      initial_auto_state: "OFF",
      status: "STRUCTURED",
      reproducibility: "UNVERIFIED_ON_TW",
      gap_reason: null,
      last_verified_at: "2026-08-08",
      notes: "只保存來源明載時間、文字與 AUTO 狀態；不明確 actor/action 不推定；尚未在台服逐步重現。",
      steps: tm5SourceTextSteps,
    },
  ],
};

function timelineForTeam(seed) {
  const sources = sourcesByTeam[seed.team_id] ?? [];
  const structuredSources = sources.filter((source) => source.status === "STRUCTURED").length;
  const status = sources.length === 0
    ? "MISSING"
    : structuredSources === 0
      ? "SOURCE_GAP"
      : structuredSources === sources.length
        ? "STRUCTURED"
        : "PARTIAL";
  return {
    status,
    structured_sources: structuredSources,
    registered_sources: sources.length,
    sources,
    references: splitTimeline(seed.timeline_ref),
    steps: [],
  };
}

function teamDetail(seed) {
  return envelope({
    ...teamSummary(seed),
    guide_id: guideId,
    server: "TW",
    stage: "紅焰8-10",
    support_slot: seed.team_id === "TM-F810-03" ? "slot3" : null,
    requirements: {
      schema_version: "1.0",
      slots: Object.fromEntries([1, 2, 3, 4, 5].map((slot) => [`slot${slot}`, unknownSlot()])),
      support: seed.support,
      operation_mode_claims: seed.operation_mode_claims,
      failure_conditions: seed.failure_conditions ?? ["UNKNOWN"],
      timeline_ref: seed.timeline_ref,
    },
    timeline: timelineForTeam(seed),
    source_ids: seed.source_ids,
    evidence_ids: seed.evidence_ids,
    tw_availability_check: "PASS",
    verified_date: "2026-08-08",
    last_review_due: "2026-09-30",
    notes: seed.notes,
  });
}

const evidence052 = envelope({
  evidence_id: "ev052",
  declared_claim_id: "CLM-PVE-F810-STD",
  linked_claim_id: "CLM-PVE-F810-STD",
  module: "pve",
  server: "JP",
  source_tier: "SINGLE_PLAYER_REPORT",
  evidence_confidence: "D",
  source_title: "YouTube 深域クエスト火8-10攻略編成動画（目押し3回・RANK382・參考Corki JG）",
  source_url: "https://www.youtube.com/watch?v=jkPXr3aUZZQ",
  source_locator: "yt_jkPXr3aUZZQ@00:45-05:50",
  published_date: "2025-09-06",
  published_date_precision: "DAY",
  verified_date: "2026-08-08",
  claim_summary: "火8-10 實戰完整五人可辨識，且影片顯示初回通關；影片聲明目押し 3 回。",
  limitations: "單一玩家影片，逐 slot 強化條件仍 UNKNOWN；與 AUTO 聲明衝突時保留 SOURCE_CONFLICT。",
  status: "ACTIVE",
});

const evidence073 = envelope({
  evidence_id: "ev073",
  declared_claim_id: "CLM-PVE-F810-SHIZURU",
  linked_claim_id: "CLM-PVE-F810-SHIZURU",
  module: "pve",
  server: "JP",
  source_tier: "MAJOR_GUIDE",
  evidence_confidence: "D",
  source_title: "GameWith 深域クエスト「火8-10」攻略（2025年12月／9月編成）",
  source_url: "https://gamewith.jp/pricone-re/article/show/507373",
  source_locator: "gamewith_fire_8_10",
  published_date: "2026-08-07",
  published_date_precision: "DAY",
  verified_date: "2026-08-08",
  claim_summary: "全文實開：2025年9月魔法半自動完整列出同五人及操作步驟；本測試資料依 canonical 手順 1–8 呈現十四個原子動作。",
  limitations: "大型攻略站單頁上限 D；全自動②雖列完整五人但頁面未提供可定位的 WIN／結算證據故不建立正式隊；只作文字化與版本辨識旁證",
  status: "ACTIVE",
});

const evidence029 = envelope({
  evidence_id: "ev029",
  declared_claim_id: "CLM-TW-DEEP-A10",
  linked_claim_id: "CLM-TW-DEEP-A10",
  module: "baseline",
  server: "TW",
  source_tier: "OFFICIAL",
  evidence_confidence: "A",
  source_title: "台服官網 2026/07/14 公告（「深域冒險」追加新冒險）",
  source_url: "https://www.princessconnect.so-net.tw/news/newsDetail/3938",
  source_locator: "tw_official_notice_3938",
  published_date: "2026-07-14",
  published_date_precision: "DAY",
  verified_date: "2026-08-02",
  claim_summary: "2026/07/15 16:00起深域冒險追加：紅焰/蒼波/翠嵐/珀天/紫冥 各10-1~10-10（63-1 NORMAL通關後解放）",
  limitations: "無（2026-08-02官方直頁完整抓取確認；來源映射更正為#3938）",
  status: "ACTIVE",
});

const evidence054 = envelope({
  evidence_id: "ev054",
  declared_claim_id: "CLM-PVE-F1010-SCARCE",
  linked_claim_id: "CLM-PVE-F1010-SCARCE",
  module: "pve",
  server: "JP",
  source_tier: "UNKNOWN",
  evidence_confidence: "D",
  source_title: "nicozon 深域クエスト標籤全量清點（73件・第1–2頁完整開啟）",
  source_url: "https://www.nicozon.net/tag/%E6%B7%B1%E5%9F%9F%E3%82%AF%E3%82%A8%E3%82%B9%E3%83%88",
  source_locator: "nicozon_tag_deep",
  published_date: "2026-08-02",
  published_date_precision: "DAY",
  verified_date: "2026-08-02",
  claim_summary: "niconico範圍內風10-10・闇10-10（闇含完整文字TL＝プリキャル／水ホマレ／ニャル／ヴァイオレット／エリス）已存在而火10-10缺席",
  limitations: "平台範圍限niconico；不代表全網",
  status: "ACTIVE",
});

const evidence055 = envelope({
  evidence_id: "ev055",
  declared_claim_id: "CLM-PVE-F1010-SCARCE",
  linked_claim_id: "CLM-PVE-F1010-SCARCE",
  module: "pve",
  server: "TW",
  source_tier: "SINGLE_PLAYER_REPORT",
  evidence_confidence: "D",
  source_title: "YouTube 煌靈／LongTimeNoC 火屬性深域10-1到10-9打法分享（台服）",
  source_url: "https://www.youtube.com/watch?v=y41LtKnRPvs",
  source_locator: "yt_y41LtKnRPvs",
  published_date: "2026-07-01",
  published_date_precision: "MONTH",
  verified_date: "2026-08-02",
  claim_summary: "台服主要深域創作者於第10區開放後約三週僅發布至10-9＝台服火10-10公開通關未見；頻道主身分經播放清單中繼資料確認",
  limitations: "搜尋摘要層引用；發布日僅月精度",
  status: "ACTIVE",
});

function supportingEvidence({
  evidenceId,
  claimId,
  server,
  sourceTier,
  sourceTitle,
  sourceUrl,
  sourceLocator,
  publishedDate,
  verifiedDate = "2026-08-08",
}) {
  return envelope({
    evidence_id: evidenceId,
    declared_claim_id: claimId,
    linked_claim_id: claimId,
    module: "pve",
    server,
    source_tier: sourceTier,
    evidence_confidence: sourceTier === "OFFICIAL" ? "A" : "D",
    source_title: sourceTitle,
    source_url: sourceUrl,
    source_locator: sourceLocator,
    published_date: publishedDate,
    published_date_precision: "DAY",
    verified_date: verifiedDate,
    claim_summary: `TEST_ONLY：${evidenceId} 的完整正文摘要由整合測試資料庫驗證。`,
    limitations: "TEST_ONLY mock 僅驗證 Web 互動與 API 契約，不替代 canonical Evidence Ledger。",
    status: "ACTIVE",
  });
}

const evidenceFixtures = new Map([
  ["ev029", evidence029],
  ["ev050", supportingEvidence({ evidenceId: "ev050", claimId: "CLM-PVE-F810-STD", server: "JP", sourceTier: "UNKNOWN", sourceTitle: "スマホゲームNavi 紅焔の深域完全攻略（2026-01-31發布・2026-07-14更新）", sourceUrl: "https://games.appmatch.jp/gamewiki/princessconnect/1134429300-89/", sourceLocator: "appmatch_fire_deep_guide", publishedDate: "2026-01-31", verifiedDate: "2026-08-02" })],
  ["ev051", supportingEvidence({ evidenceId: "ev051", claimId: "CLM-PVE-F810-NOLUISE", server: "JP", sourceTier: "SINGLE_PLAYER_REPORT", sourceTitle: "YouTube 深域クエスト火属性8-10「ルイズなしクローチェエアリアルサポ借り想定」", sourceUrl: "https://www.youtube.com/watch?v=ZXUDJm_AsSA", sourceLocator: "yt_ZXUDJm_AsSA@00:12-03:15", publishedDate: "2025-11-30" })],
  ["ev052", evidence052],
  ["ev054", evidence054],
  ["ev055", evidence055],
  ["ev056", supportingEvidence({ evidenceId: "ev056", claimId: "CLM-TW-LUISE-ORIG-REL", server: "TW", sourceTier: "OFFICIAL", sourceTitle: "台服官網 2025/09/03 公告（精選轉蛋 期間限定角色「露易絲瑪莉」登場）", sourceUrl: "https://www.princessconnect.so-net.tw/news/newsDetail/3529", sourceLocator: "tw_official_notice_3529", publishedDate: "2025-09-03", verifiedDate: "2026-08-02" })],
  ["ev057", supportingEvidence({ evidenceId: "ev057", claimId: "CLM-TW-CROCE-AERIAL-REL", server: "TW", sourceTier: "OFFICIAL", sourceTitle: "台服官網 2025/08/08 公告（精選轉蛋 期間限定角色「克蘿茜（航空）」登場）", sourceUrl: "https://www.princessconnect.so-net.tw/news/newsDetail/3500", sourceLocator: "tw_official_notice_3500", publishedDate: "2025-08-08", verifiedDate: "2026-08-02" })],
  ["ev058", supportingEvidence({ evidenceId: "ev058", claimId: "CLM-TW-LAILAEL-XMAS-REL", server: "TW", sourceTier: "OFFICIAL", sourceTitle: "台服官網 2025/03/31 公告（精選轉蛋 期間限定角色「萊拉耶爾（聖誕節）」登場）", sourceUrl: "https://www.princessconnect.so-net.tw/news/newsDetail/3313", sourceLocator: "tw_official_notice_3313", publishedDate: "2025-03-31", verifiedDate: "2026-08-02" })],
  ["ev059", supportingEvidence({ evidenceId: "ev059", claimId: "CLM-TW-LIND-REL", server: "TW", sourceTier: "OFFICIAL", sourceTitle: "台服官網 2025/02/09 公告（精選轉蛋 新角色「琳德」登場）", sourceUrl: "https://www.princessconnect.so-net.tw/news/newsDetail/3247", sourceLocator: "tw_official_notice_3247", publishedDate: "2025-02-09", verifiedDate: "2026-08-03" })],
  ["ev060", supportingEvidence({ evidenceId: "ev060", claimId: "CLM-TW-VURM-REL", server: "TW", sourceTier: "OFFICIAL", sourceTitle: "台服官網 2025/02/16 公告（精選轉蛋 新角色「烏爾姆」登場）", sourceUrl: "https://www.princessconnect.so-net.tw/news/newsDetail/3257", sourceLocator: "tw_official_notice_3257", publishedDate: "2025-02-16", verifiedDate: "2026-08-03" })],
  ["ev069", supportingEvidence({ evidenceId: "ev069", claimId: "CLM-PVE-F810-STD", server: "JP", sourceTier: "SINGLE_PLAYER_REPORT", sourceTitle: "YouTube Deep Quest Fire 8-10 4 Manuals", sourceUrl: "https://www.youtube.com/watch?v=tYwLvHHbKXo", sourceLocator: "yt_tYwLvHHbKXo@00:00-05:05", publishedDate: "2025-07-15" })],
  ["ev070", supportingEvidence({ evidenceId: "ev070", claimId: "CLM-PVE-F810-SHIZURU", server: "JP", sourceTier: "SINGLE_PLAYER_REPORT", sourceTitle: "YouTube 深域クエスト8-10攻略編成まとめ（火・風・光・闇）", sourceUrl: "https://www.youtube.com/watch?v=F39PkRIg0T4", sourceLocator: "yt_F39PkRIg0T4@02:34-05:27", publishedDate: "2025-09-18" })],
  ["ev071", supportingEvidence({ evidenceId: "ev071", claimId: "CLM-PVE-F810-SHIZURU", server: "TW", sourceTier: "SINGLE_PLAYER_REPORT", sourceTitle: "YouTube 煌靈／LongTimeNoC 火屬性深域 8-10 半自動刀", sourceUrl: "https://www.youtube.com/watch?v=OtiJrk3jacg", sourceLocator: "yt_OtiJrk3jacg@00:58-04:37", publishedDate: "2025-11-15" })],
  ["ev072", supportingEvidence({ evidenceId: "ev072", claimId: "CLM-PVE-F810-SHIZURU", server: "JP", sourceTier: "SINGLE_PLAYER_REPORT", sourceTitle: "YouTube 深域クエスト火属性8-10ボスクリア（目押しなしTPチャージLv4星0）", sourceUrl: "https://www.youtube.com/watch?v=i4pE3GxTMMA", sourceLocator: "yt_i4pE3GxTMMA@04:11-07:18", publishedDate: "2025-08-19" })],
  ["ev073", evidence073],
  ["ev074", supportingEvidence({ evidenceId: "ev074", claimId: "CLM-TW-SHIZURU-VAL-AVAILABLE", server: "TW", sourceTier: "OFFICIAL", sourceTitle: "台服官網 2026/05/31 自選角色精選獎勵轉蛋公告", sourceUrl: "https://www.princessconnect.so-net.tw/news/newsDetail/3873", sourceLocator: "tw_official_notice_3873", publishedDate: "2026-05-31" })],
  ["ev075", supportingEvidence({ evidenceId: "ev075", claimId: "CLM-TW-MAHO-SUMMER-AVAILABLE", server: "TW", sourceTier: "OFFICIAL", sourceTitle: "台服官網 2024/06/16 火屬性自選★3必中白金轉蛋公告", sourceUrl: "https://www.princessconnect.so-net.tw/news/newsDetail/2873", sourceLocator: "tw_official_notice_2873", publishedDate: "2024-06-16" })],
  ["ev076", supportingEvidence({ evidenceId: "ev076", claimId: "CLM-TW-YUI-XMAS-REL", server: "TW", sourceTier: "OFFICIAL", sourceTitle: "台服官網 2026/03/31 優衣（聖誕節）精選轉蛋公告", sourceUrl: "https://www.princessconnect.so-net.tw/news/newsDetail/3795", sourceLocator: "tw_official_notice_3795", publishedDate: "2026-03-31" })],
  ["ev077", supportingEvidence({ evidenceId: "ev077", claimId: "CLM-TW-LAILAEL-XMAS-UE1", server: "TW", sourceTier: "OFFICIAL", sourceTitle: "台服官網 2026/04/10 角色專用裝備1追加公告", sourceUrl: "https://www.princessconnect.so-net.tw/news/newsDetail/3805", sourceLocator: "tw_official_notice_3805", publishedDate: "2026-04-10" })],
  ["ev078", supportingEvidence({ evidenceId: "ev078", claimId: "CLM-TW-ANNE-GREA-REL", server: "TW", sourceTier: "OFFICIAL", sourceTitle: "台服官網 2023/05/03 安＆古蕾婭公主祭典精選轉蛋公告", sourceUrl: "https://www.princessconnect.so-net.tw/news/newsDetail/2246", sourceLocator: "tw_official_notice_2246", publishedDate: "2023-05-03" })],
  ["ev079", supportingEvidence({ evidenceId: "ev079", claimId: "CLM-LOC-ANNE-GREA", server: "JP", sourceTier: "OFFICIAL", sourceTitle: "日服官網 2023/01/06 アン＆グレア登場公告", sourceUrl: "https://priconne-redive.jp/news/information/20815/", sourceLocator: "jp_official_20815", publishedDate: "2023-01-06" })],
  ["ev080", supportingEvidence({ evidenceId: "ev080", claimId: "CLM-TW-MIO-NGS-AVAILABLE", server: "TW", sourceTier: "OFFICIAL", sourceTitle: "台服官網 2026/04/08 復刻 NGs 活動公告", sourceUrl: "https://www.princessconnect.so-net.tw/news/newsDetail/3802", sourceLocator: "tw_official_notice_3802", publishedDate: "2026-04-08" })],
  ["ev081", supportingEvidence({ evidenceId: "ev081", claimId: "CLM-LOC-MIO-NGS", server: "JP", sourceTier: "OFFICIAL", sourceTitle: "日服官網 2022/11/15 ミオ（デレマス）相關公告", sourceUrl: "https://priconne-redive.jp/news/information/20200/", sourceLocator: "jp_official_20200", publishedDate: "2022-11-15" })],
  ["ev082", supportingEvidence({ evidenceId: "ev082", claimId: "CLM-PVE-F810-ANNEGREA", server: "JP", sourceTier: "SINGLE_PLAYER_REPORT", sourceTitle: "YouTube 深域火 8-10 安＆古蕾婭通關實戰", sourceUrl: "https://www.youtube.com/watch?v=p95ZoBCWuYE", sourceLocator: "yt_p95ZoBCWuYE@00:00-02:35", publishedDate: "2025-12-03" })],
  ["ev083", supportingEvidence({ evidenceId: "ev083", claimId: "CLM-PVE-F810-MIO", server: "JP", sourceTier: "SINGLE_PLAYER_REPORT", sourceTitle: "YouTube 深域火 8-10 未央（NGs）半自動通關實戰", sourceUrl: "https://www.youtube.com/watch?v=Zw31omyYDKI", sourceLocator: "yt_Zw31omyYDKI@00:00-01:56", publishedDate: "2026-01-02" })],
]);

function send(response, status, payload) {
  response.writeHead(status, {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
  });
  response.end(JSON.stringify(payload));
}

const server = createServer((request, response) => {
  const url = new URL(request.url ?? "/", `http://${host}:${port}`);
  if (request.method === "OPTIONS") return send(response, 204, {});
  if (request.method !== "GET") return send(response, 405, { detail: { code: "METHOD_NOT_ALLOWED" } });
  if (url.pathname === "/health/live" || url.pathname === "/health/ready") {
    return send(response, 200, { status: "ok", checks: { fixture: "TEST_ONLY" } });
  }
  if (url.pathname === "/api/v1/baseline") return send(response, 200, baseline);
  if (url.pathname === "/api/v1/stages") return send(response, 200, envelope([stageSummary, secondaryStageSummary]));
  if (url.pathname === `/api/v1/stages/${guideId}`) return send(response, 200, stageDetail);
  if (url.pathname === `/api/v1/stages/${secondaryStageSummary.guide_id}`) return send(response, 200, secondaryStageDetail);
  if (url.pathname === "/api/v1/pvp/counters") {
    return send(response, 200, envelope([], ["NO_VERIFIED_COUNTER"]));
  }
  const evidenceMatch = url.pathname.match(/^\/api\/v1\/evidence\/(ev\d+)$/);
  if (evidenceMatch && evidenceFixtures.has(evidenceMatch[1])) {
    return send(response, 200, evidenceFixtures.get(evidenceMatch[1]));
  }
  const timelineMatch = url.pathname.match(/^\/api\/v1\/teams\/(TM-F810-0[1-5])\/timelines$/);
  if (timelineMatch) {
    const seed = teamSeeds.find((item) => item.team_id === timelineMatch[1]);
    const timeline = timelineForTeam(seed);
    const warnings = timeline.status === "PARTIAL"
      ? ["STRUCTURED_TIMELINE_PARTIAL"]
      : timeline.status === "SOURCE_GAP"
        ? ["STRUCTURED_TIMELINE_SOURCE_GAP"]
        : [];
    return send(response, 200, envelope(timeline, warnings));
  }
  const teamMatch = url.pathname.match(/^\/api\/v1\/teams\/(TM-F810-0[1-5])$/);
  if (teamMatch) {
    const seed = teamSeeds.find((item) => item.team_id === teamMatch[1]);
    return send(response, 200, teamDetail(seed));
  }
  const parts = url.pathname.split("/");
  const id = parts.at(-1) ?? "";
  return send(response, 404, { detail: { code: "NOT_FOUND", resource: "fixture", id } });
});

server.listen(port, host);

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
