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
};

const teamSeeds = [
  {
    team_id: "TM-F810-01",
    operation_mode: "SOURCE_CONFLICT",
    stability: "多來源交叉驗證",
    units: ["luisemarie_orig", "lailael_xmas", "croce_aerial", "vurm_orig", "lind_orig"],
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
    evidence_ids: ["ev051", "ev057", "ev058", "ev060", "ev073", "ev075", "ev076"],
    operation_mode_claims: [{ mode: "SEMI_AUTO", source_id: "yt_ZXUDJm_AsSA" }],
    timeline_ref: "AX-F810-03-EV051",
    support: { unit: "croce_aerial", requirements: "yt_ZXUDJm_AsSA=borrowed Croce (Aerial); exact build UNKNOWN" },
    notes: "僅供參考：單一實戰；克蘿茜（航空）為借角，精確練度仍 UNKNOWN。",
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
  status: "PROVISIONAL",
  team_count: 3,
  reproducibility: "PENDING",
  verified_date: "2026-08-08",
};

const meta = (warnings = []) => ({
  api_version: "v1",
  generated_at: "2026-08-08T00:00:00Z",
  source: {
    canonical_source: "research_core_file_ssot",
    fixture_sha256: "a".repeat(64),
    import_run_id: "00000000-0000-4000-8000-000000000001",
    imported_at: "2026-08-08T00:00:00Z",
    research_core_version: "v1.5",
  },
  warnings,
});

const envelope = (data, warnings = []) => ({ data, meta: meta(warnings) });

const baseline = envelope({
  research_core_version: "v1.5",
  application_version: "3.0.0-b0",
  canonical_source: "research_core_file_ssot",
  generated_at: "2026-08-08T00:00:00Z",
  counts: {
    stages: 1,
    teams: 3,
    team_members: 15,
    characters: 8,
    evidence: 18,
    claims: 13,
    operation_timelines: 8,
    timeline_steps: 14,
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
  notes: "本輪實際開頁與逐幀核對後取得 3 支不同五人的 VERIFIED effective teams；距成熟門檻 5 支仍差 2 支。",
  coverage: { verified_distinct_teams: 3, maturity_target: 5, remaining: 2, is_mature: false },
  teams: teamSeeds.map(teamSummary),
  evidence_ids: ["ev050", "ev051", "ev052", "ev056", "ev057", "ev058", "ev059", "ev060", "ev069", "ev070", "ev071", "ev072", "ev073", "ev074", "ev075", "ev076", "ev077"],
  claim_ids: ["CLM-PVE-F810-STD", "CLM-PVE-F810-SHIZURU", "CLM-PVE-F810-NOLUISE"],
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
    timeline_id: "TL-F810-02-EV073",
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
      failure_conditions: ["UNKNOWN"],
      timeline_ref: seed.timeline_ref,
    },
    timeline: timelineForTeam(seed),
    source_ids: seed.operation_mode_claims.map((claim) => claim.source_id),
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
  limitations: "大型攻略站單頁上限 D；此操作軸來自日服，尚未逐步於台服重現，且來源未明載戰鬥總長、容錯與漏按結果。",
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
  ["ev050", supportingEvidence({ evidenceId: "ev050", claimId: "CLM-PVE-F810-STD", server: "JP", sourceTier: "UNKNOWN", sourceTitle: "スマホゲームNavi 紅焔の深域完全攻略（2026-01-31發布・2026-07-14更新）", sourceUrl: "https://games.appmatch.jp/gamewiki/princessconnect/1134429300-89/", sourceLocator: "appmatch_fire_deep_guide", publishedDate: "2026-01-31", verifiedDate: "2026-08-02" })],
  ["ev051", supportingEvidence({ evidenceId: "ev051", claimId: "CLM-PVE-F810-NOLUISE", server: "JP", sourceTier: "SINGLE_PLAYER_REPORT", sourceTitle: "YouTube 深域クエスト火属性8-10「ルイズなしクローチェエアリアルサポ借り想定」", sourceUrl: "https://www.youtube.com/watch?v=ZXUDJm_AsSA", sourceLocator: "yt_ZXUDJm_AsSA@00:12-03:15", publishedDate: "2025-11-30" })],
  ["ev052", evidence052],
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
  if (url.pathname === "/api/v1/stages") return send(response, 200, envelope([stageSummary]));
  if (url.pathname === `/api/v1/stages/${guideId}`) return send(response, 200, stageDetail);
  if (url.pathname === "/api/v1/pvp/counters") {
    return send(response, 200, envelope([], ["NO_VERIFIED_COUNTER"]));
  }
  const evidenceMatch = url.pathname.match(/^\/api\/v1\/evidence\/(ev\d+)$/);
  if (evidenceMatch && evidenceFixtures.has(evidenceMatch[1])) {
    return send(response, 200, evidenceFixtures.get(evidenceMatch[1]));
  }
  const timelineMatch = url.pathname.match(/^\/api\/v1\/teams\/(TM-F810-0[1-3])\/timelines$/);
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
  const teamMatch = url.pathname.match(/^\/api\/v1\/teams\/(TM-F810-0[1-3])$/);
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
