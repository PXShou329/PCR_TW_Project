// TEST_ONLY fixture server. It never writes to the research core or canonical database.
import { createServer } from "node:http";

const host = "127.0.0.1";
const port = Number.parseInt(process.env.MOCK_API_PORT ?? "4100", 10);
const gachaCanonicalUnavailable = process.env.MOCK_GACHA_CANONICAL_UNAVAILABLE === "1";
const fireGuideId = "TW_DEEP_FIRE_08_10_20260802";
const waterGuideId = "TW_DEEP_WATER_08_10_20260808";

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
  yukino_orig: "雪野",
  ames_sum: "愛梅斯（夏日）",
  sono_orig: "苑",
  ninon_sum: "妮諾（夏日）",
  nanaka_sum: "七七香（夏日）",
  misora_xmas: "美空（聖誕節）",
  violet_isanami: "薇歐莉特（黃泉鯨命）",
  labyrista_alpha: "拉比林斯達（始源）",
};

const fireTeamSeeds = [
  {
    team_id: "TM-F810-01",
    support_slot: null,
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
    support_slot: null,
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
    support_slot: "slot3",
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
    support_slot: null,
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
    support_slot: null,
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
].map((seed) => ({
  ...seed,
  guide_id: fireGuideId,
  stage_label: "紅焰8-10",
  verified_date: "2026-08-08",
  last_review_due: "2026-09-30",
}));

const waterTeamSeeds = [
  {
    team_id: "TM-W810-01",
    support_slot: null,
    operation_mode: "MANUAL_TIMELINE",
    stability: "單一實戰",
    units: ["yukino_orig", "ames_sum", "misora_xmas", "nanaka_sum", "violet_isanami"],
    source_ids: ["yt_w3My0QHcoTA"],
    evidence_ids: ["ev084", "ev091", "ev092", "ev093", "ev094", "ev099", "ev100", "ev101", "ev102", "ev103", "ev104"],
    operation_mode_claims: [{ mode: "MANUAL_TIMELINE", source_id: "yt_w3My0QHcoTA" }],
    timeline_ref: "AX-W810-01-EV084",
    support: { unit: "UNKNOWN", requirements: "UNKNOWN" },
    failure_conditions: [
      "來源全域養成：全屬性Lv1000、屬性技能第6頁第8分流MAX、大師技能118、職階全5.5；未逐slot歸屬",
      "來源採本影片世界線B（0:41 Boss UB）；世界線A的0:40／0:20分支只作風險備註",
      "0:59與0:48為來源標☆之目押；逐slot星級、RANK、UE與TP需求UNKNOWN",
    ],
    notes: "【僅供參考】台服單一玩家實戰：HP bar清空後回到蒼波地圖且8-10顯示CLEAR；來源聲明2目押，故為MANUAL_TIMELINE；單一來源上限D，不保證其他練度或世界線穩定",
  },
  {
    team_id: "TM-W810-02",
    support_slot: null,
    operation_mode: "SEMI_AUTO",
    stability: "單一實戰",
    units: ["yukino_orig", "ames_sum", "sono_orig", "ninon_sum", "violet_isanami"],
    source_ids: ["yt_w3My0QHcoTA"],
    evidence_ids: ["ev085", "ev091", "ev092", "ev093", "ev094", "ev095", "ev096", "ev097", "ev098", "ev103", "ev104"],
    operation_mode_claims: [{ mode: "SEMI_AUTO", source_id: "yt_w3My0QHcoTA" }],
    timeline_ref: "AX-W810-02-EV085",
    support: { unit: "UNKNOWN", requirements: "UNKNOWN" },
    failure_conditions: [
      "來源全域養成：全屬性Lv1000、屬性技能第6頁第8分流MAX、大師技能118、職階全5.5；未逐slot歸屬",
      "來源標示TP5.0+但未指明逐slot歸屬，不得拆填",
      "採本影片世界線B（0:39 Boss UB）；世界線A及TP4.0–4.4版本只作風險備註",
    ],
    notes: "【僅供參考】台服單一玩家實戰：Boss HP=0/270000000且剩0:22；來源聲明半A，故為SEMI_AUTO；單一來源上限D，逐slot需求維持UNKNOWN",
  },
  {
    team_id: "TM-W810-03",
    support_slot: null,
    operation_mode: "AUTO",
    stability: "單一實戰",
    units: ["yukino_orig", "ames_sum", "labyrista_alpha", "sono_orig", "violet_isanami"],
    source_ids: ["yt_w3My0QHcoTA"],
    evidence_ids: ["ev086", "ev091", "ev092", "ev093", "ev094", "ev095", "ev096", "ev103", "ev104", "ev105", "ev106"],
    operation_mode_claims: [{ mode: "AUTO", source_id: "yt_w3My0QHcoTA" }],
    timeline_ref: "AX-W810-03-EV086",
    support: { unit: "UNKNOWN", requirements: "UNKNOWN" },
    failure_conditions: [
      "來源全域養成：全屬性Lv1000、屬性技能第6頁第8分流MAX、大師技能118、職階全5.5；未逐slot歸屬",
      "來源僅明示OXOOX與AUTO ON；O／X不拆成逐slot養成事實",
      "逐slot星級、RANK、UE與TP需求UNKNOWN",
    ],
    notes: "【僅供參考】台服單一玩家實戰：Boss HP=0/270000000且剩0:03；社群俗稱阿法晶正規化為拉比林斯達（始源）；全自動單一來源上限D",
  },
  {
    team_id: "TM-W810-04",
    support_slot: null,
    operation_mode: "AUTO",
    stability: "單一實戰",
    units: ["yukino_orig", "ames_sum", "sono_orig", "nanaka_sum", "violet_isanami"],
    source_ids: ["yt_w3My0QHcoTA"],
    evidence_ids: ["ev087", "ev091", "ev092", "ev093", "ev094", "ev095", "ev096", "ev099", "ev100", "ev103", "ev104"],
    operation_mode_claims: [{ mode: "AUTO", source_id: "yt_w3My0QHcoTA" }],
    timeline_ref: "AX-W810-04-EV087",
    support: { unit: "UNKNOWN", requirements: "UNKNOWN" },
    failure_conditions: [
      "來源全域養成：全屬性Lv1000、屬性技能第6頁第8分流MAX、大師技能118、職階全5.5；未逐slot歸屬",
      "來源僅明示OOOXO與AUTO ON；O／X不拆成逐slot養成事實",
      "逐slot星級、RANK、UE與TP需求UNKNOWN",
    ],
    notes: "【僅供參考】台服單一玩家實戰：Boss HP=0/270000000且剩0:05，隨後Now Loading；全自動單一來源上限D",
  },
  {
    team_id: "TM-W810-05",
    support_slot: null,
    operation_mode: "AUTO",
    stability: "單一實戰",
    units: ["yukino_orig", "ames_sum", "misora_xmas", "sono_orig", "violet_isanami"],
    source_ids: ["yt_w3My0QHcoTA"],
    evidence_ids: ["ev088", "ev091", "ev092", "ev093", "ev094", "ev095", "ev096", "ev101", "ev102", "ev103", "ev104"],
    operation_mode_claims: [{ mode: "AUTO", source_id: "yt_w3My0QHcoTA" }],
    timeline_ref: "AX-W810-05-EV088",
    support: { unit: "UNKNOWN", requirements: "UNKNOWN" },
    failure_conditions: [
      "來源全域養成：全屬性Lv1000、屬性技能第6頁第8分流MAX、大師技能118、職階全5.5；未逐slot歸屬",
      "來源明示全SET；另稱OXOOO亦可，但不將O／X拆成逐slot養成事實",
      "逐slot星級、RANK、UE與TP需求UNKNOWN",
    ],
    notes: "【僅供參考】台服單一玩家實戰：Boss HP=0/270000000且剩0:17；來源聲明全SET全自動，另列OXOOO可行；單一來源上限D",
  },
].map((seed) => ({
  ...seed,
  guide_id: waterGuideId,
  stage_label: "蒼波8-10",
  verified_date: "2026-08-08",
  last_review_due: "2026-09-30",
}));

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
  is_borrowed: seed.support_slot
    ? seed.support_slot === `slot${index + 1}`
    : seed.support.unit === "NONE"
      ? false
      : null,
}));

const teamSummary = (seed) => ({
  team_id: seed.team_id,
  operation_mode: seed.operation_mode,
  clear_status: "VERIFIED",
  stability: seed.stability,
  members: members(seed),
});

const fireStageSummary = {
  guide_id: fireGuideId,
  server: "TW",
  mode: "DEEP",
  area: "紅焰",
  stage: "8-10",
  status: "VERIFIED",
  team_count: 5,
  reproducibility: "CONFIRMED",
  verified_date: "2026-08-08",
};

const waterStageSummary = {
  guide_id: waterGuideId,
  server: "TW",
  mode: "DEEP",
  area: "蒼波",
  stage: "8-10",
  status: "VERIFIED",
  team_count: 5,
  reproducibility: "CONFIRMED",
  verified_date: "2026-08-08",
};

const fireResearchStageSummary = {
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

const meta = (warnings = [], details = {}) => ({
  api_version: "v1",
  generated_at: "2026-08-08T00:00:00Z",
  server: "UNKNOWN",
  environment_version: "UNKNOWN",
  verified_at: null,
  stale_status: "UNKNOWN",
  confidence: "UNKNOWN",
  evidence_ids: [],
  claim_ids: [],
  data_revision: "a".repeat(64),
  ...details,
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

const envelope = (data, warnings = [], details = {}) => ({
  data,
  meta: meta(warnings, details),
});

// Keep typed baseline totals in one place so they can be reconciled with the
// importer output whenever the canonical closure changes.
const typedBaselineCounts = {
  stages: 3,
  teams: 10,
  team_members: 50,
  characters: 35,
  evidence: 73,
  claims: 69,
  operation_timelines: 15,
  timeline_steps: 37,
  arena_defenses: 1,
  arena_defense_members: 5,
  arena_counters: 2,
  arena_counter_members: 10,
  arena_counter_evidence: 4,
  arena_counter_claims: 4,
  gacha_timeline_events: 5,
  gacha_timeline_evidence: 10,
  gacha_timeline_claims: 8,
  gacha_community_sources: 4,
  gacha_timeline_community_sources: 0,
};

const baseline = envelope({
  research_core_version: "v1.5",
  application_version: "3.0.0-b4",
  canonical_source: "research_core_file_ssot",
  generated_at: "2026-08-09T00:00:00Z",
  counts: typedBaselineCounts,
  gates: { gate_a: false, gate_b: false, gate_c: false },
  featured_stage: fireStageSummary,
});

const fireStageDetail = envelope({
  ...fireStageSummary,
  applicable_version: "ch16/Lv373",
  source_tier: "SINGLE_PLAYER_REPORT",
  claim_confidence: "D",
  last_review_due: "2026-09-30",
  notes: "實際開頁與逐幀核對後取得 5 支不同五人的 VERIFIED effective teams；相同五人多來源已去重，未知操作模式與逐 slot 條件仍誠實保留。",
  coverage: { verified_distinct_teams: 5, maturity_target: 5, remaining: 0, is_mature: true },
  teams: fireTeamSeeds.map(teamSummary),
  evidence_ids: ["ev050", "ev051", "ev052", "ev056", "ev057", "ev058", "ev059", "ev060", "ev069", "ev070", "ev071", "ev072", "ev073", "ev074", "ev075", "ev076", "ev077", "ev078", "ev079", "ev080", "ev081", "ev082", "ev083"],
  claim_ids: ["CLM-PVE-F810-STD", "CLM-PVE-F810-SHIZURU", "CLM-PVE-F810-NOLUISE", "CLM-PVE-F810-ANNEGREA", "CLM-PVE-F810-MIO", "CLM-PVE-TL-F810-MIO", "CLM-TW-LUISE-ORIG-REL", "CLM-TW-CROCE-AERIAL-REL", "CLM-TW-LAILAEL-XMAS-REL", "CLM-TW-LIND-REL", "CLM-TW-VURM-REL", "CLM-TW-SHIZURU-VAL-AVAILABLE", "CLM-TW-MAHO-SUMMER-AVAILABLE", "CLM-TW-YUI-XMAS-REL", "CLM-TW-LAILAEL-XMAS-UE1", "CLM-TW-ANNE-GREA-REL", "CLM-LOC-ANNE-GREA", "CLM-TW-MIO-NGS-AVAILABLE", "CLM-LOC-MIO-NGS"].sort(),
});

const waterStageDetail = envelope({
  ...waterStageSummary,
  applicable_version: "TW-2026-06-01／exact ch-Lv UNKNOWN",
  source_tier: "SINGLE_PLAYER_REPORT",
  claim_confidence: "D",
  last_review_due: "2026-09-30",
  notes: "同一台服玩家影片逐隊實播確認5支不同五人與實際清場；相同五人未重複計數；CONFIRMED只表示完整五人、關卡、清場、可用性與追溯閉合，不代表多玩家穩定重現；五個隊伍Claim均為單一來源D並誠實保留Gate C blocking warnings",
  coverage: { verified_distinct_teams: 5, maturity_target: 5, remaining: 0, is_mature: true },
  teams: waterTeamSeeds.map(teamSummary),
  evidence_ids: ["ev084", "ev085", "ev086", "ev087", "ev088", "ev091", "ev092", "ev093", "ev094", "ev095", "ev096", "ev097", "ev098", "ev099", "ev100", "ev101", "ev102", "ev103", "ev104", "ev105", "ev106"],
  claim_ids: [
    "CLM-PVE-W810-MISORA-NANAKA", "CLM-PVE-W810-SONO-NINON", "CLM-PVE-W810-LABYRISTA-SONO", "CLM-PVE-W810-SONO-NANAKA", "CLM-PVE-W810-MISORA-SONO",
    "CLM-PVE-TL-W810-01", "CLM-PVE-TL-W810-02", "CLM-PVE-TL-W810-03", "CLM-PVE-TL-W810-04", "CLM-PVE-TL-W810-05",
    "CLM-TW-YUKINO-REL", "CLM-TW-AMES-SUMMER-REL", "CLM-TW-SONO-REL", "CLM-TW-NINON-SUMMER-REL", "CLM-TW-NANAKA-SUMMER-AVAILABLE", "CLM-TW-MISORA-XMAS-REL", "CLM-TW-VIOLET-ISANAMI-REL", "CLM-TW-LABYRISTA-ALPHA-REL",
    "CLM-LOC-YUKINO", "CLM-LOC-AMES-SUMMER", "CLM-LOC-SONO", "CLM-LOC-NINON-SUMMER", "CLM-LOC-NANAKA-SUMMER", "CLM-LOC-MISORA-XMAS", "CLM-LOC-VIOLET-ISANAMI", "CLM-LOC-LABYRISTA-ALPHA",
  ].sort(),
});

const fireResearchStageDetail = envelope({
  ...fireResearchStageSummary,
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

const stageSummaries = [fireStageSummary, waterStageSummary, fireResearchStageSummary];
const stageDetailsByGuide = new Map([
  [fireGuideId, fireStageDetail],
  [waterGuideId, waterStageDetail],
  [fireResearchStageSummary.guide_id, fireResearchStageDetail],
]);
const teamSeeds = [...fireTeamSeeds, ...waterTeamSeeds];
const teamSeedsById = new Map(teamSeeds.map((seed) => [seed.team_id, seed]));

const pveDatasetSha = "2".repeat(64);
const pveWorkbookOneSha = "a".repeat(64);
const pveWorkbookTwoSha = "b".repeat(64);
const pveStagingOneSha = "c".repeat(64);
const pveStagingTwoSha = "d".repeat(64);
const pveAssetShas = ["1", "3", "4", "5", "6"].map((value) => value.repeat(64));
const pveFixturePng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

const gachaLibraryImageShas = [
  "0b37c66dcb7869511a6c59ba238bd1fe47652c3c9c1d7de190d5d83f2cd9bbc3",
  "b2e32e1184e5c9810837e4dd024de10029e5ba04910567d3165a30b37b73eb66",
  "8bad4463ce79600a45a9b73eafa4c5779063851828a8e984867e2720268acd8e",
  "5e740fd0dde0bf4fff6ed04c142ec6ee952446ada793919ceaf046751f2f79f5",
  "b75260f60e5f16bf43b236c267419858911c0f2cd1dc179e8805aa144580ae25",
  "4b27066b807534427e4db5e445a09630401b962cbbd04bb7f1cda8388e3b7f75",
  "f5e82caa50b5119a4cad82bbb525f368aca6bca1098132390c41eafbf44b68b6",
  "7f1d8061f139907536fa46006bdd221f93531bc7e78de90f4f4b36a530539e2b",
  "7357ea0d26e8038453f13b766834ea710cab62aef14bbb5e8262ad29f889e5bb",
  "727f81eed2c0ef6ea47dd39866c8e4fb70a09136c03c2ab75ad9d387c6cceae4",
  "d72ca660b1926682d16d9fe11327e3c616f2d33115f3b01c56eba313ad2786f2",
  "5db0ce2363a22bf3485c7aa74e3f46ac8a0e1a417720ce5e6ab8a8b70e651592",
  "f3cf1983ba8afbd1057fa24dbe6e0dd91c77ef4abe1fe5d6042272c887ee8a39",
  "67270092cc18790f36e448a6d9398a9e201775f90880674db25f3e5146602d13",
  "6b579d82c11fdd43a55bba0fd10666a707528206e72a79138cf097f85066560a",
  "964b011048860dfbf17b17bc687d438ca362bc4ac4f16aa4f16aaeaa22234b6c",
  "94cf72fb030ed3a0b8a66fd050225f0a5856c8873411d40a3bcccefc264d2f61",
];
const gachaLibraryMissingSha = "7".repeat(64);
const gachaLibraryRedirectSha = "8".repeat(64);
const gachaLibrarySvgSha = "9".repeat(64);
const gachaLibraryHtmlErrorSha = "a".repeat(64);

const gachaLibrarySeeds = [
  ["RERUN", ["步未(怪盜)", "真琴(指揮官)", "可可蘿(遊俠)"], "2026-08-01", "2026-08-16"],
  ["LIMITED_PICKUP", ["鏡華（歌德）"], "2026-08-11", "2026-08-23"],
  ["RERUN", ["克蘿茜(風靈)", "碧(駕駛員)", "鳳凰", "美冬(工作服)", "碧(工作服)"], "2026-08-16", "2026-08-31"],
  ["LIMITED_PICKUP", ["凱留（霸瞳天星）"], "2026-08-23", "2026-08-31"],
  ["LIMITED_PICKUP", ["真穗（少女與戰車）"], "2026-08-31", "2026-09-22"],
  ["LIMITED_PICKUP", ["艾麗卡（少女與戰車）"], "2026-09-11", "2026-09-22"],
  ["PERMANENT_PICKUP", ["露露伊"], "2026-09-22", "2026-10-01"],
  ["RERUN", ["鏡華(春日)", "碧卡拉", "吉塔(魔導士)"], "2026-09-22", "2026-10-01"],
  ["LIMITED_PICKUP", ["莉莉（女武神）"], "2026-10-01", "2026-10-11"],
  ["LIMITED_PICKUP", ["普蕾希亞（女武神）"], "2026-10-11", "2026-10-23"],
  ["RERUN", ["彩羽", "霞（修女）", "華音", "紡希（煉獄）"], "2026-10-11", "2026-10-23"],
  ["LIMITED_PICKUP", ["可璃亞（女武神）"], "2026-10-23", "2026-10-31"],
  ["RERUN", ["咲戀（夏日）", "真步（夢想樂園）", "伊莉亞（祭服）", "鈴奈（夏日）", "鈴莓（夏日）", "珠希（夏日）", "凱留（夏日）", "貪吃佩可（夏日）"], "2026-10-23", "2026-10-31"],
  ["LIMITED_PICKUP", ["雪菲（瓦德拉赫）"], "2026-10-31", "2026-11-03"],
  ["LIMITED_PICKUP", ["露易絲瑪莉（夏日）"], "2026-11-03", "2026-11-15"],
  ["RERUN", ["優依（聖誕節）", "美空（聖誕節）", "普蕾西亞(夏日)", "雪菲(夏日)", "厄莉絲(夏日)"], "2026-11-03", "2026-11-15"],
  ["LIMITED_PICKUP", ["克蕾琪塔（夏日）"], "2026-11-15", "2026-12-01"],
];

const gachaLibraryForecasts = gachaLibrarySeeds.map((seed, index) => ({
  candidate_id: `GACHA-DOCX-${String(index + 1).padStart(24, "0")}`,
  review_order: index + 1,
  source_declared_pool_kind: seed[0],
  raw_character_names: seed[1],
  forecast_start: seed[2],
  forecast_end: seed[3],
  precision: "DAY",
  date_boundary_semantics: "SOURCE_UNSPECIFIED",
  raw_description_lines: [seed[1].join("、")],
  raw_forecast_text: `台服預測${seed[2]}～${seed[3]}`,
  raw_sequence_label: index === 16 ? "第144次" : null,
  identity_status: "UNVERIFIED_COMMUNITY_NAME",
  review_status: "PENDING",
  review_reason: index === 12
    ? "UNDELIMITED_CHARACTER_TEXT_REQUIRES_REVIEW"
    : "EXACT_EVENT_LINK_NOT_REVIEWED",
  promotion_eligible: false,
  proposed_event_id: null,
  parser_warnings: index === 12 ? ["UNQUOTED_CHARACTER_SEQUENCE"] : [],
  image: {
    asset_url: `/api/v1/gacha-library/assets/${gachaLibraryImageShas[index]}`,
    byte_length: 1000 + index,
    mime_type: "image/jpeg",
    sha256: gachaLibraryImageShas[index],
  },
  provenance: {
    description_locators: [`word/document.xml#paragraph=${index * 4 + 1}`],
    source_locator: `word/document.xml#paragraph=${index * 4 + 2}`,
    image_locator: `word/document.xml#paragraph=${index * 4 + 4};image=1`,
    relationship_id: `rId${index + 4}`,
    package_path: `word/media/image${index + 1}.jpeg`,
  },
}));

const gachaLibraryPayload = {
  data: {
    items: gachaLibraryForecasts,
    total: 17,
  },
  meta: {
    api_version: "v1",
    schema_version: "gacha-community-docx-candidates/v1",
    dataset_sha256: "e".repeat(64),
    source_status: "USER_SUPPLIED",
    authority: "COMMUNITY_FORECAST",
    source_id: "GACHA-COMM-002",
    independence_group: "GACHA-COMM-002",
    canonical_write_count: 0,
    source_document: {
      content_addressed_filename: "0600faf911747c6df1a98afddfe1fe8e5af585ff72af11e2d34299f5e70c4cfe.docx",
      sha256: "0600faf911747c6df1a98afddfe1fe8e5af585ff72af11e2d34299f5e70c4cfe",
      byte_length: 2102864,
    },
  },
};

const pveLibraryMeta = {
  api_version: "v1",
  schema_version: "private-pve-local-catalog/v1",
  dataset_sha256: pveDatasetSha,
  source_status: "SOURCE_PROVIDED",
  independent_clear_verification: "NOT_PERFORMED",
  source_workbooks: [
    {
      filename: "深域關卡備戰所有屬性1~7.xlsx",
      sha256: pveWorkbookOneSha,
      byte_length: 123456,
      staging_catalog_sha256: pveStagingOneSha,
    },
    {
      filename: "深域關卡8~10&追憶&露娜塔.xlsx",
      sha256: pveWorkbookTwoSha,
      byte_length: 234567,
      staging_catalog_sha256: pveStagingTwoSha,
    },
  ],
};

const pveLibraryEnvelope = (data) => ({ data, meta: pveLibraryMeta });
const pveProvenance = (sheetName, sourceRange, workbook = 1) => ({
  source_workbook_sha256: workbook === 1 ? pveWorkbookOneSha : pveWorkbookTwoSha,
  source_workbook_filename: workbook === 1
    ? "深域關卡備戰所有屬性1~7.xlsx"
    : "深域關卡8~10&追憶&露娜塔.xlsx",
  staging_catalog_sha256: workbook === 1 ? pveStagingOneSha : pveStagingTwoSha,
  sheet_name: sheetName,
  source_range: sourceRange,
});

const pveStageSummaries = [
  {
    stage_id: "pve-deep-fire-1-1",
    mode: "DEEP",
    element: "FIRE",
    label_raw: "紅焰深域 1-1",
    stage_refs: [{ kind: "DEEP_STAGE", area: 1, stage: 1 }],
    team_count: 1,
    provenance: pveProvenance("紅焰の深域(火屬性)", "A4:H6"),
  },
  {
    stage_id: "pve-deep-fire-1-2",
    mode: "DEEP",
    element: "FIRE",
    label_raw: "紅焰深域 1-2",
    stage_refs: [{ kind: "DEEP_STAGE", area: 1, stage: 2 }],
    team_count: 2,
    provenance: pveProvenance("紅焰の深域(火屬性)", "J4:Q8"),
  },
  {
    stage_id: "pve-remembrance-arachne-1-5",
    mode: "REMEMBRANCE",
    element: "DARK",
    label_raw: "追憶戰域 阿剌克涅 1–5層",
    stage_refs: [
      { kind: "REMEMBRANCE_GROUP", area: 1, stage: 1 },
      { kind: "REMEMBRANCE_GROUP", area: 1, stage: 5 },
    ],
    team_count: 1,
    provenance: pveProvenance("追憶阿剌克涅1-5", "A9:N12", 2),
  },
  {
    stage_id: "pve-luna-top-ex",
    mode: "LUNA_TOWER",
    element: "NONE",
    label_raw: "露娜塔頂層 EX",
    stage_refs: [{ kind: "LUNA_TOWER", area: 0, stage: 1 }],
    team_count: 1,
    provenance: pveProvenance("露娜塔頂層EX", "A4:L8", 2),
  },
];

const pveCurrentDeepNumbers = Array.from({ length: 10 }, (_, index) => index + 1);

function pveAvailableFilters(mode, element) {
  const modes = [...new Set(pveStageSummaries.map((item) => item.mode))].sort();
  const elements = [...new Set(
    pveStageSummaries
      .filter((item) => !mode || item.mode === mode)
      .map((item) => item.element),
  )].sort();

  if (mode === "DEEP" && (!element || element === "FIRE")) {
    return {
      modes,
      elements,
      areas: pveCurrentDeepNumbers,
      stages: pveCurrentDeepNumbers,
    };
  }

  const refs = pveStageSummaries
    .filter((item) => (!mode || item.mode === mode) && (!element || item.element === element))
    .flatMap((item) => item.stage_refs);
  return {
    modes,
    elements,
    areas: [...new Set(refs.map((ref) => ref.area))].sort((left, right) => left - right),
    stages: [...new Set(refs.map((ref) => ref.stage))].sort((left, right) => left - right),
  };
}

const pveYoutubeSource = {
  kind: "HYPERLINK",
  label_raw: "通關影片",
  origin_cell: "I4",
  resolution_status: "RESOLVED",
  alias_id: null,
  alias_label: null,
  applies_to_cell: "H4",
  url: "https://www.youtube.com/watch?v=pveTest1234",
  media: {
    kind: "YOUTUBE",
    external_url: "https://www.youtube.com/watch?v=pveTest1234",
    embed_url: "https://www.youtube-nocookie.com/embed/pveTest1234",
    video_id: "pveTest1234",
  },
};

const pveExternalSource = {
  kind: "HYPERLINK",
  label_raw: "外部解陣參考",
  origin_cell: "I5",
  resolution_status: "RESOLVED",
  alias_id: null,
  alias_label: null,
  applies_to_cell: "H5",
  url: "https://appmedia.jp/priconne-redive/4466131",
  media: {
    kind: "EXTERNAL",
    external_url: "https://appmedia.jp/priconne-redive/4466131",
    embed_url: null,
    video_id: null,
  },
};

const pvePortraits = pveAssetShas.map((assetSha, index) => ({
  display_position: index + 1,
  asset_sha256: assetSha,
  asset_url: `/api/v1/pve-library/assets/${assetSha}`,
  icon_url: index === 0
    ? "https://redive.estertion.win/icon/unit/100161.webp"
    : index === 1
      ? "https://redive.estertion.win.example/icon/unit/100131.webp"
      : null,
  mapping_status: index === 0 ? "RESOLVED" : "UNRESOLVED",
  tw_name: index === 0 ? "日和" : null,
  display_rarity: index === 0 ? "SIX_STAR" : null,
  display_source: index === 0 ? "ESTERTION" : "WORKBOOK_EMBEDDED",
  unit_key: index === 0 ? "hiyori_orig" : null,
  anchor_cell: `${String.fromCharCode(74 + index)}4`,
}));

const pveDeepDetail = {
  ...pveStageSummaries[1],
  teams: [
    {
      team_id: "pve-team-fire-1-2-001",
      display_order: 1,
      notes_raw: "跳跳虎可換情姐；依 Excel 原文保留。",
      flags: ["SOURCE_PROVIDED"],
      source_range: "J4:Q5",
      portraits: pvePortraits,
      axes: [
        {
          axis_id: "pve-axis-fire-1-2-001-a",
          operation_raw: "OXOOX",
          notes_raw: "半自動；來源沒有角色位置對齊聲明。",
          source_cell: "H4",
          operation: {
            kind: "SOURCE_PATTERN",
            order_basis: "WORKBOOK_TEXT_LEFT_TO_RIGHT",
            member_alignment: "UNRESOLVED",
            execution_hints: ["半自動"],
            variants: [
              {
                kind: "SET_PATTERN",
                raw: "OXOOX",
                origin_field: "OPERATION_TEXT",
                origin_cell: "H4",
                source_order_states: ["SET", "NOT_SET", "SET", "SET", "NOT_SET"],
              },
            ],
          },
          source_links: [pveYoutubeSource],
        },
        {
          axis_id: "pve-axis-fire-1-2-001-b",
          operation_raw: "全SET",
          notes_raw: "另一條 Excel 收錄軸。",
          source_cell: "H5",
          operation: {
            kind: "ALL_SET",
            order_basis: "WORKBOOK_TEXT_LEFT_TO_RIGHT",
            member_alignment: "UNRESOLVED",
            execution_hints: [],
            variants: [
              {
                kind: "ALL_SET",
                raw: "全SET",
                origin_field: "OPERATION_TEXT",
                origin_cell: "H5",
                source_order_states: ["SET", "SET", "SET", "SET", "SET"],
              },
            ],
          },
          source_links: [pveExternalSource],
        },
      ],
      source_links: [pveYoutubeSource, pveExternalSource],
      provenance: pveProvenance("紅焰の深域(火屬性)", "J4:Q5"),
    },
    {
      team_id: "pve-team-fire-1-2-002",
      display_order: 2,
      notes_raw: null,
      flags: ["SOURCE_PROVIDED", "NO_OPERATION_AXIS"],
      source_range: "J6:Q6",
      portraits: pvePortraits.map((portrait) => ({ ...portrait, anchor_cell: portrait.anchor_cell.replace("4", "6") })),
      axes: [],
      source_links: [],
      provenance: pveProvenance("紅焰の深域(火屬性)", "J6:Q6"),
    },
  ],
};

const pveLibraryDetails = new Map([
  [pveDeepDetail.stage_id, pveDeepDetail],
  [pveStageSummaries[2].stage_id, { ...pveStageSummaries[2], teams: [] }],
  [pveStageSummaries[3].stage_id, { ...pveStageSummaries[3], teams: [] }],
]);

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
  timelineId,
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
  criticality = "UNKNOWN",
  failure = "UNKNOWN",
}) {
  if (!timelineId) throw new Error(`timelineId is required for ${id}`);
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
    criticality,
    instruction_zh_tw: instruction,
    failure_if_missed: failure,
    source_locator: locator,
  };
}

const fireTeamTwoStep = (step) => timelineStep({
  ...step,
  timelineId: "TL-F810-02-EV073",
});

const tm2StructuredSteps = [
  fireTeamTwoStep({ id: "TLS-F810-02-001", sequence: 1, sourceStep: 1, timeState: "NOT_STATED", milliseconds: null, trigger: "WAVE_START", actor: "luisemarie_orig", action: "SET_ON", autoState: "ON", cue: "戰鬥開始", instruction: "開場將露易絲瑪莉設為 SET。", locator: "2025年9月魔法半自動／手順1" }),
  fireTeamTwoStep({ id: "TLS-F810-02-002", sequence: 2, sourceStep: 1, timeState: "NOT_STATED", milliseconds: null, trigger: "WAVE_START", actor: "lailael_xmas", action: "SET_ON", autoState: "ON", cue: "戰鬥開始", instruction: "開場將萊拉耶爾（聖誕節）設為 SET。", locator: "2025年9月魔法半自動／手順1" }),
  fireTeamTwoStep({ id: "TLS-F810-02-003", sequence: 3, sourceStep: 1, timeState: "NOT_STATED", milliseconds: null, trigger: "WAVE_START", actor: "croce_aerial", action: "SET_ON", autoState: "ON", cue: "戰鬥開始", instruction: "開場將克蘿茜（航空）設為 SET。", locator: "2025年9月魔法半自動／手順1" }),
  fireTeamTwoStep({ id: "TLS-F810-02-004", sequence: 4, sourceStep: 1, timeState: "NOT_STATED", milliseconds: null, trigger: "WAVE_START", actor: "shizuru_valentine", action: "SET_ON", autoState: "ON", cue: "戰鬥開始", instruction: "開場將靜流（情人節）設為 SET；烏爾姆先不設 SET。", locator: "2025年9月魔法半自動／手順1" }),
  fireTeamTwoStep({ id: "TLS-F810-02-005", sequence: 5, sourceStep: 2, timeState: "STATED", milliseconds: 70000, trigger: "ANIMATION_CUE", triggerActor: "vurm_orig", actor: "vurm_orig", action: "SET_ON", autoState: "ON", cue: "烏爾姆 UB 結束後", instruction: "倒數 1:10 左右，在烏爾姆 UB 後開啟烏爾姆 SET。", locator: "2025年9月魔法半自動／手順2" }),
  fireTeamTwoStep({ id: "TLS-F810-02-006", sequence: 6, sourceStep: 3, timeState: "STATED", milliseconds: 62000, trigger: "ANIMATION_CUE", triggerActor: "croce_aerial", actor: "vurm_orig", action: "SET_OFF", autoState: "ON", cue: "克蘿茜（航空）UB 結束後", instruction: "倒數 1:02 左右，在克蘿茜（航空）UB 後關閉烏爾姆 SET。", locator: "2025年9月魔法半自動／手順3" }),
  fireTeamTwoStep({ id: "TLS-F810-02-007", sequence: 7, sourceStep: 3, timeState: "STATED", milliseconds: 62000, trigger: "ANIMATION_CUE", triggerActor: "croce_aerial", actor: "croce_aerial", action: "SET_OFF", autoState: "ON", cue: "克蘿茜（航空）UB 結束後", instruction: "同一時間點關閉克蘿茜（航空）SET。", locator: "2025年9月魔法半自動／手順3" }),
  fireTeamTwoStep({ id: "TLS-F810-02-008", sequence: 8, sourceStep: 4, timeState: "STATED", milliseconds: 53000, trigger: "ANIMATION_CUE", triggerActor: "shizuru_valentine", actor: "vurm_orig", action: "SET_ON", autoState: "ON", cue: "靜流（情人節）UB 結束後", instruction: "倒數 0:53 左右，在靜流（情人節）UB 後開啟烏爾姆 SET。", locator: "2025年9月魔法半自動／手順4" }),
  fireTeamTwoStep({ id: "TLS-F810-02-009", sequence: 9, sourceStep: 4, timeState: "STATED", milliseconds: 53000, trigger: "ANIMATION_CUE", triggerActor: "shizuru_valentine", actor: "croce_aerial", action: "SET_ON", autoState: "ON", cue: "靜流（情人節）UB 結束後", instruction: "同一時間點開啟克蘿茜（航空）SET。", locator: "2025年9月魔法半自動／手順4" }),
  fireTeamTwoStep({ id: "TLS-F810-02-010", sequence: 10, sourceStep: 4, timeState: "STATED", milliseconds: 53000, trigger: "ANIMATION_CUE", triggerActor: "shizuru_valentine", actor: "NONE", action: "AUTO_OFF", autoState: "OFF", cue: "靜流（情人節）UB 結束後", instruction: "完成兩個 SET 切換後關閉 AUTO。", locator: "2025年9月魔法半自動／手順4" }),
  fireTeamTwoStep({ id: "TLS-F810-02-011", sequence: 11, sourceStep: 5, timeState: "STATED", milliseconds: 34000, trigger: "ANIMATION_CUE", triggerActor: "shizuru_valentine", actor: "shizuru_valentine", action: "SET_OFF", autoState: "OFF", cue: "靜流（情人節）UB 結束後", instruction: "倒數 0:34 左右，在靜流（情人節）UB 後關閉其 SET。", locator: "2025年9月魔法半自動／手順5" }),
  fireTeamTwoStep({ id: "TLS-F810-02-012", sequence: 12, sourceStep: 6, timeState: "STATED", milliseconds: 25000, trigger: "ANIMATION_CUE", triggerActor: "lailael_xmas", actor: "shizuru_valentine", action: "SET_ON", autoState: "OFF", cue: "萊拉耶爾（聖誕節）UB 結束後", instruction: "倒數 0:25 左右開啟靜流（情人節）SET，並於途中取消來源所稱「セグメント」技能動作。", locator: "2025年9月魔法半自動／手順6" }),
  fireTeamTwoStep({ id: "TLS-F810-02-013", sequence: 13, sourceStep: 7, timeState: "STATED", milliseconds: 17000, trigger: "ANIMATION_CUE", triggerActor: "shizuru_valentine", actor: "shizuru_valentine", action: "SET_OFF", autoState: "OFF", cue: "靜流（情人節）UB 結束後", instruction: "倒數 0:17 左右，在靜流（情人節）UB 後關閉其 SET。", locator: "2025年9月魔法半自動／手順7" }),
  fireTeamTwoStep({ id: "TLS-F810-02-014", sequence: 14, sourceStep: 8, timeState: "STATED", milliseconds: 5000, trigger: "ANIMATION_CUE", triggerActor: "croce_aerial", actor: "shizuru_valentine", action: "USE_UB", autoState: "OFF", cue: "克蘿茜（航空）UB 結束後", instruction: "倒數 0:05 左右，在克蘿茜（航空）UB 後立即施放靜流（情人節）UB，以取消來源所稱「セグメント」技能動作。", locator: "2025年9月魔法半自動／手順8" }),
];

const tm5SourceTextSteps = [
  timelineStep({ id: "TLS-F810-05-001", timelineId: "TL-F810-05-EV083", sequence: 1, sourceStep: 1, timeState: "STATED", milliseconds: 90000, trigger: "SOURCE_TEXT_ONLY", actor: "NONE", action: "NO_ACTION", autoState: "OFF", cue: "raw_set_pattern=[〇〇〇〇〇]", instruction: "來源原文：1:30 [〇〇〇〇〇](OFF)；actor 未標示，方括號圖樣定義 UNKNOWN。", locator: "影片說明／timeline 1" }),
  timelineStep({ id: "TLS-F810-05-002", timelineId: "TL-F810-05-EV083", sequence: 2, sourceStep: 2, timeState: "STATED", milliseconds: 38000, trigger: "SOURCE_TEXT_ONLY", triggerActor: "anne_grea_orig", actor: "anne_grea_orig", action: "NO_ACTION", autoState: "OFF", cue: "raw_set_pattern=[〇〇〇ー〇]", instruction: "來源原文：0:38 アングレア [〇〇〇ー〇](OFF)；僅保存角色 marker，不推定動作。", locator: "影片說明／timeline 2" }),
  timelineStep({ id: "TLS-F810-05-003", timelineId: "TL-F810-05-EV083", sequence: 3, sourceStep: 3, timeState: "STATED", milliseconds: 27000, trigger: "SOURCE_TEXT_ONLY", triggerActor: "vurm_orig", actor: "vurm_orig", action: "NO_ACTION", autoState: "OFF", cue: "raw_set_pattern=[〇〇〇〇〇]", instruction: "來源原文：0:27 ヴルム [〇〇〇〇〇](OFF)；僅保存角色 marker，不推定動作。", locator: "影片說明／timeline 3" }),
  timelineStep({ id: "TLS-F810-05-004", timelineId: "TL-F810-05-EV083", sequence: 4, sourceStep: 4, timeState: "STATED", milliseconds: 26000, trigger: "SOURCE_TEXT_ONLY", triggerActor: "yui_xmas", actor: "yui_xmas", action: "NO_ACTION", autoState: "OFF", cue: "raw_set_pattern=[〇〇〇〇ー]", instruction: "來源原文：0:26 ユイ [〇〇〇〇ー](OFF)；僅保存角色 marker，不推定動作。", locator: "影片說明／timeline 4" }),
  timelineStep({ id: "TLS-F810-05-005", timelineId: "TL-F810-05-EV083", sequence: 5, sourceStep: 5, timeState: "STATED", milliseconds: 7000, trigger: "SOURCE_TEXT_ONLY", triggerActor: "vurm_orig", actor: "vurm_orig", action: "NO_ACTION", autoState: "ON", cue: "raw_set_pattern=[〇〇〇〇ー]", instruction: "來源原文：0:07 ヴルム [〇〇〇〇ー](ON)；僅保存角色 marker，不推定動作。", locator: "影片說明／timeline 5" }),
];

const waterTeamOneSteps = [
  timelineStep({ id: "TLS-W810-01-001", timelineId: "TL-W810-01-EV084", sequence: 1, sourceStep: 1, timeState: "STATED", milliseconds: 90000, trigger: "WAVE_START", actor: "NONE", action: "NO_ACTION", autoState: "ON", cue: "raw_set_pattern=OOXOO", instruction: "來源原文：1:30 OOXOO，AUTO ON；O／X圖樣不拆成逐slot動作。", locator: "yt_w3My0QHcoTA@00:13-02:13#step-1" }),
  timelineStep({ id: "TLS-W810-01-002", timelineId: "TL-W810-01-EV084", sequence: 2, sourceStep: 2, timeState: "STATED", milliseconds: 67000, trigger: "CLOCK", triggerActor: "nanaka_sum", actor: "nanaka_sum", action: "NO_ACTION", autoState: "ON", cue: "raw_set_pattern=OXOOO", instruction: "來源原文：1:07 七七香（夏日）→ OXOOO；只保存角色marker與圖樣。", locator: "yt_w3My0QHcoTA@00:13-02:13#step-2" }),
  timelineStep({ id: "TLS-W810-01-003", timelineId: "TL-W810-01-EV084", sequence: 3, sourceStep: 3, timeState: "STATED", milliseconds: 59000, trigger: "ANIMATION_CUE", triggerActor: "ames_sum", actor: "ames_sum", action: "USE_UB", autoState: "ON", cue: "愛梅斯1技為美空充TP後最速／開眼後", instruction: "倒數0:59，在愛梅斯1技為美空充TP後最速施放愛梅斯UB。", locator: "yt_w3My0QHcoTA@00:13-02:13#step-3", criticality: "CRITICAL", failure: "若0:53雪野UB早於美空UB，來源指出0:59按得太早。" }),
  timelineStep({ id: "TLS-W810-01-004", timelineId: "TL-W810-01-EV084", sequence: 4, sourceStep: 4, timeState: "STATED", milliseconds: 53000, trigger: "SOURCE_TEXT_ONLY", triggerActor: "misora_xmas", actor: "NONE", action: "NO_ACTION", autoState: "ON", cue: "美空UB後接雪野UB", instruction: "來源觀察：0:53美空UB後接雪野UB；不是額外手動指令。", locator: "yt_w3My0QHcoTA@00:13-02:13#step-4" }),
  timelineStep({ id: "TLS-W810-01-005", timelineId: "TL-W810-01-EV084", sequence: 5, sourceStep: 5, timeState: "STATED", milliseconds: 48000, trigger: "ANIMATION_CUE", triggerActor: "ames_sum", actor: "ames_sum", action: "USE_UB", autoState: "ON", cue: "愛梅斯1技為薇歐莉特充TP後最速", instruction: "倒數0:48，在愛梅斯1技為薇歐莉特充TP後最速施放愛梅斯UB。", locator: "yt_w3My0QHcoTA@00:13-02:13#step-5a", criticality: "CRITICAL" }),
  timelineStep({ id: "TLS-W810-01-006", timelineId: "TL-W810-01-EV084", sequence: 6, sourceStep: 5, timeState: "STATED", milliseconds: 48000, trigger: "CLOCK", actor: "NONE", action: "AUTO_OFF", autoState: "OFF", cue: "raw_set_pattern=OOXOO", instruction: "同一來源步驟切換為OOXOO並關閉AUTO。", locator: "yt_w3My0QHcoTA@00:13-02:13#step-5b" }),
  timelineStep({ id: "TLS-W810-01-007", timelineId: "TL-W810-01-EV084", sequence: 7, sourceStep: 6, timeState: "STATED", milliseconds: 41000, trigger: "BOSS_ACTION", actor: "NONE", action: "NO_ACTION", autoState: "OFF", cue: "Boss UB", instruction: "來源世界線B於0:41發生Boss UB；不新增玩家動作。", locator: "yt_w3My0QHcoTA@00:13-02:13#step-6" }),
  timelineStep({ id: "TLS-W810-01-008", timelineId: "TL-W810-01-EV084", sequence: 8, sourceStep: 7, timeState: "STATED", milliseconds: 38000, trigger: "CLOCK", triggerActor: "yukino_orig", actor: "NONE", action: "AUTO_ON", autoState: "ON", cue: "raw_set_pattern=OOOOX", instruction: "來源原文：0:38雪野→OOOOX並開啟AUTO；只將明示AUTO ON結構化。", locator: "yt_w3My0QHcoTA@00:13-02:13#step-7" }),
  timelineStep({ id: "TLS-W810-01-009", timelineId: "TL-W810-01-EV084", sequence: 9, sourceStep: 8, timeState: "STATED", milliseconds: 17000, trigger: "CLOCK", triggerActor: "violet_isanami", actor: "violet_isanami", action: "NO_ACTION", autoState: "ON", cue: "raw_set_pattern=OXOOO", instruction: "來源原文：0:17薇歐莉特（黃泉鯨命）→OXOOO；只保存角色marker與圖樣。", locator: "yt_w3My0QHcoTA@00:13-02:13#step-8" }),
];

const waterTeamTwoSteps = [
  timelineStep({ id: "TLS-W810-02-001", timelineId: "TL-W810-02-EV085", sequence: 1, sourceStep: 1, timeState: "STATED", milliseconds: 90000, trigger: "WAVE_START", actor: "NONE", action: "NO_ACTION", autoState: "ON", cue: "raw_set_pattern=OXOOO", instruction: "來源原文：1:30 OXOOO，AUTO ON；O／X圖樣不拆成逐slot動作。", locator: "yt_w3My0QHcoTA@02:14-03:48#step-1" }),
  timelineStep({ id: "TLS-W810-02-002", timelineId: "TL-W810-02-EV085", sequence: 2, sourceStep: 2, timeState: "STATED", milliseconds: 71000, trigger: "CLOCK", triggerActor: "ames_sum", actor: "NONE", action: "AUTO_OFF", autoState: "OFF", cue: "愛梅斯marker後關閉AUTO", instruction: "來源原文：1:11愛梅斯→AUTO OFF；不推定箭頭前的角色動作種類。", locator: "yt_w3My0QHcoTA@02:14-03:48#step-2" }),
  timelineStep({ id: "TLS-W810-02-003", timelineId: "TL-W810-02-EV085", sequence: 3, sourceStep: 3, timeState: "STATED", milliseconds: 56000, trigger: "BOSS_ACTION", actor: "NONE", action: "NO_ACTION", autoState: "OFF", cue: "Boss UB", instruction: "來源世界線B於0:56發生Boss UB；不新增玩家動作。", locator: "yt_w3My0QHcoTA@02:14-03:48#step-3" }),
  timelineStep({ id: "TLS-W810-02-004", timelineId: "TL-W810-02-EV085", sequence: 4, sourceStep: 4, timeState: "STATED", milliseconds: 50000, trigger: "CLOCK", triggerActor: "yukino_orig", actor: "NONE", action: "AUTO_ON", autoState: "ON", cue: "雪野marker後開啟AUTO", instruction: "來源原文：0:50雪野→AUTO ON；不推定箭頭前的角色動作種類。", locator: "yt_w3My0QHcoTA@02:14-03:48#step-4" }),
  timelineStep({ id: "TLS-W810-02-005", timelineId: "TL-W810-02-EV085", sequence: 5, sourceStep: 5, timeState: "STATED", milliseconds: 39000, trigger: "BOSS_ACTION", actor: "NONE", action: "NO_ACTION", autoState: "ON", cue: "Boss UB", instruction: "本影片世界線B於0:39發生Boss UB；世界線A的0:36不混入本軸。", locator: "yt_w3My0QHcoTA@02:14-03:48#step-5" }),
  timelineStep({ id: "TLS-W810-02-006", timelineId: "TL-W810-02-EV085", sequence: 6, sourceStep: 6, timeState: "STATED", milliseconds: 24000, trigger: "CLOCK", triggerActor: "ames_sum", actor: "ames_sum", action: "NO_ACTION", autoState: "ON", cue: "raw_set_pattern=OOOOX", instruction: "來源原文：0:24愛梅斯→OOOOX；只保存角色marker與圖樣。", locator: "yt_w3My0QHcoTA@02:14-03:48#step-6" }),
];

const waterAutoSteps = {
  "TM-W810-03": [timelineStep({ id: "TLS-W810-03-001", timelineId: "TL-W810-03-EV086", sequence: 1, sourceStep: 1, timeState: "STATED", milliseconds: 90000, trigger: "WAVE_START", actor: "NONE", action: "NO_ACTION", autoState: "ON", cue: "raw_set_pattern=OXOOX", instruction: "來源原文：1:30 OXOOX，AUTO ON；圖樣語意不再細拆。", locator: "yt_w3My0QHcoTA@03:49-05:27#step-1" })],
  "TM-W810-04": [timelineStep({ id: "TLS-W810-04-001", timelineId: "TL-W810-04-EV087", sequence: 1, sourceStep: 1, timeState: "STATED", milliseconds: 90000, trigger: "WAVE_START", actor: "NONE", action: "NO_ACTION", autoState: "ON", cue: "raw_set_pattern=OOOXO", instruction: "來源原文：1:30 OOOXO，AUTO ON；圖樣語意不再細拆。", locator: "yt_w3My0QHcoTA@05:28-06:51#step-1" })],
  "TM-W810-05": [timelineStep({ id: "TLS-W810-05-001", timelineId: "TL-W810-05-EV088", sequence: 1, sourceStep: 1, timeState: "STATED", milliseconds: 90000, trigger: "WAVE_START", actor: "NONE", action: "NO_ACTION", autoState: "ON", cue: "raw_set_pattern=全SET", instruction: "來源原文：1:30全SET並全自動；OXOOO替代樣式只留於說明。", locator: "yt_w3My0QHcoTA@06:52-07:58#step-1" })],
};

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
  "TM-W810-01": [
    {
      source_axis_id: "AX-W810-01-EV084",
      timeline_id: "TL-W810-01-EV084",
      source_id: "yt_w3My0QHcoTA",
      source_evidence_id: "ev084",
      source_locator: "yt_w3My0QHcoTA@00:13-02:13",
      timeline_variant_name: "本影片世界線B（0:41 Boss UB）",
      operation_mode: "MANUAL_TIMELINE",
      clock_mode: "COUNTDOWN",
      battle_duration_ms: 90000,
      initial_auto_state: "ON",
      status: "STRUCTURED",
      reproducibility: "TW_REPRODUCED",
      gap_reason: null,
      last_verified_at: "2026-08-08",
      notes: "來源明示2目押並列世界線A/B；只結構化本影片實際採用的B，兩個標☆愛梅斯時點保存為UB，其餘O／X與角色箭頭不過度解讀；TW_REPRODUCED只表示此台服來源實戰",
      steps: waterTeamOneSteps,
    },
  ],
  "TM-W810-02": [
    {
      source_axis_id: "AX-W810-02-EV085",
      timeline_id: "TL-W810-02-EV085",
      source_id: "yt_w3My0QHcoTA",
      source_evidence_id: "ev085",
      source_locator: "yt_w3My0QHcoTA@02:14-03:48",
      timeline_variant_name: "本影片世界線B（0:39 Boss UB／TP5.0+）",
      operation_mode: "SEMI_AUTO",
      clock_mode: "COUNTDOWN",
      battle_duration_ms: 90000,
      initial_auto_state: "ON",
      status: "STRUCTURED",
      reproducibility: "TW_REPRODUCED",
      gap_reason: null,
      last_verified_at: "2026-08-08",
      notes: "來源聲明半A；只結構化本影片世界線B的時間與AUTO狀態；世界線A及TP4.0–4.4版本只留風險備註；TP5.0+不拆成逐slot事實",
      steps: waterTeamTwoSteps,
    },
  ],
  "TM-W810-03": [
    {
      source_axis_id: "AX-W810-03-EV086",
      timeline_id: "TL-W810-03-EV086",
      source_id: "yt_w3My0QHcoTA",
      source_evidence_id: "ev086",
      source_locator: "yt_w3My0QHcoTA@03:49-05:27",
      timeline_variant_name: "全自動 OXOOX",
      operation_mode: "AUTO",
      clock_mode: "COUNTDOWN",
      battle_duration_ms: 90000,
      initial_auto_state: "ON",
      status: "STRUCTURED",
      reproducibility: "TW_REPRODUCED",
      gap_reason: null,
      last_verified_at: "2026-08-08",
      notes: "來源明示全自動及1:30開場OXOOX；以WAVE_START／NO_ACTION加raw_set_pattern保存，不推定O／X的逐slot養成或技能語意；阿法晶已正規化為拉比林斯達（始源）",
      steps: waterAutoSteps["TM-W810-03"],
    },
  ],
  "TM-W810-04": [
    {
      source_axis_id: "AX-W810-04-EV087",
      timeline_id: "TL-W810-04-EV087",
      source_id: "yt_w3My0QHcoTA",
      source_evidence_id: "ev087",
      source_locator: "yt_w3My0QHcoTA@05:28-06:51",
      timeline_variant_name: "全自動 OOOXO",
      operation_mode: "AUTO",
      clock_mode: "COUNTDOWN",
      battle_duration_ms: 90000,
      initial_auto_state: "ON",
      status: "STRUCTURED",
      reproducibility: "TW_REPRODUCED",
      gap_reason: null,
      last_verified_at: "2026-08-08",
      notes: "來源明示全自動及1:30開場OOOXO；以WAVE_START／NO_ACTION加raw_set_pattern保存，不推定O／X的逐slot養成或技能語意",
      steps: waterAutoSteps["TM-W810-04"],
    },
  ],
  "TM-W810-05": [
    {
      source_axis_id: "AX-W810-05-EV088",
      timeline_id: "TL-W810-05-EV088",
      source_id: "yt_w3My0QHcoTA",
      source_evidence_id: "ev088",
      source_locator: "yt_w3My0QHcoTA@06:52-07:58",
      timeline_variant_name: "全自動全SET（OXOOO亦可）",
      operation_mode: "AUTO",
      clock_mode: "COUNTDOWN",
      battle_duration_ms: 90000,
      initial_auto_state: "ON",
      status: "STRUCTURED",
      reproducibility: "TW_REPRODUCED",
      gap_reason: null,
      last_verified_at: "2026-08-08",
      notes: "來源明示1:30全SET全自動並稱OXOOO亦可；主要軸以WAVE_START／NO_ACTION加raw_set_pattern=全SET保存，替代圖樣留於說明，不為同一來源建立第二條axis",
      steps: waterAutoSteps["TM-W810-05"],
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
    guide_id: seed.guide_id,
    server: "TW",
    stage: seed.stage_label,
    support_slot: seed.support_slot,
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
    verified_date: seed.verified_date,
    last_review_due: seed.last_review_due,
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

function canonicalEvidence([
  evidenceId,
  claimId,
  module,
  server,
  sourceTier,
  sourceTitle,
  sourceUrl,
  sourceLocator,
  publishedDate,
  claimSummary,
  limitations,
]) {
  return envelope({
    evidence_id: evidenceId,
    declared_claim_id: claimId,
    linked_claim_id: claimId,
    module,
    server,
    source_tier: sourceTier,
    evidence_confidence: sourceTier === "OFFICIAL" ? "A" : "D",
    source_title: sourceTitle,
    source_url: sourceUrl,
    source_locator: sourceLocator,
    published_date: publishedDate,
    published_date_precision: "DAY",
    verified_date: "2026-08-08",
    claim_summary: claimSummary,
    limitations,
    status: "ACTIVE",
  });
}

const waterEvidenceRows = [
  ["ev084", "CLM-PVE-W810-MISORA-NANAKA", "pve", "TW", "SINGLE_PLAYER_REPORT", "YouTube 蒼波 8-10 五隊實戰－第1隊美空七七香", "https://www.youtube.com/watch?v=w3My0QHcoTA", "yt_w3My0QHcoTA@00:13-02:13", "2026-06-01", "影片顯示完整五人＝雪野／愛梅斯（夏日）／美空（聖誕節）／七七香（夏日）／薇歐莉特（黃泉鯨命）；最終攻擊後 Boss HP bar 清空並回到蒼波地圖且 8-10 顯示 CLEAR；來源稱剩13秒與2目押", "單一台服玩家一次成功故通關與操作 Claim 上限 D；世界線及全域養成不代表其他帳號穩定重現"],
  ["ev085", "CLM-PVE-W810-SONO-NINON", "pve", "TW", "SINGLE_PLAYER_REPORT", "YouTube 蒼波 8-10 五隊實戰－第2隊苑妮諾", "https://www.youtube.com/watch?v=w3My0QHcoTA", "yt_w3My0QHcoTA@02:14-03:48", "2026-06-01", "影片顯示完整五人＝雪野／愛梅斯（夏日）／苑／妮諾（夏日）／薇歐莉特（黃泉鯨命）；Boss HP=0/270000000 且剩0:22；來源稱半A", "單一台服玩家一次成功故上限 D；TP5.0+ 與全域養成未逐 slot 歸屬"],
  ["ev086", "CLM-PVE-W810-LABYRISTA-SONO", "pve", "TW", "SINGLE_PLAYER_REPORT", "YouTube 蒼波 8-10 五隊實戰－第3隊拉比林斯達苑", "https://www.youtube.com/watch?v=w3My0QHcoTA", "yt_w3My0QHcoTA@03:49-05:27", "2026-06-01", "影片顯示完整五人＝雪野／愛梅斯（夏日）／拉比林斯達（始源）／苑／薇歐莉特（黃泉鯨命）；Boss HP=0/270000000 且剩0:03；來源稱全自動 OXOOX", "單一台服玩家一次成功故上限 D；阿法晶僅為社群俗稱且 O／X 不拆成逐 slot 養成事實"],
  ["ev087", "CLM-PVE-W810-SONO-NANAKA", "pve", "TW", "SINGLE_PLAYER_REPORT", "YouTube 蒼波 8-10 五隊實戰－第4隊苑七七香", "https://www.youtube.com/watch?v=w3My0QHcoTA", "yt_w3My0QHcoTA@05:28-06:51", "2026-06-01", "影片顯示完整五人＝雪野／愛梅斯（夏日）／苑／七七香（夏日）／薇歐莉特（黃泉鯨命）；Boss HP=0/270000000 且剩0:05後進入 Now Loading；來源稱全自動 OOOXO", "單一台服玩家一次成功故上限 D；O／X 與全域養成不拆成逐 slot 事實"],
  ["ev088", "CLM-PVE-W810-MISORA-SONO", "pve", "TW", "SINGLE_PLAYER_REPORT", "YouTube 蒼波 8-10 五隊實戰－第5隊美空苑", "https://www.youtube.com/watch?v=w3My0QHcoTA", "yt_w3My0QHcoTA@06:52-07:58", "2026-06-01", "影片顯示完整五人＝雪野／愛梅斯（夏日）／美空（聖誕節）／苑／薇歐莉特（黃泉鯨命）；Boss HP=0/270000000 且剩0:17；來源稱全SET全自動並另列 OXOOO 可行", "單一台服玩家一次成功故上限 D；替代 SET 樣式不代表多次重現"],
  ["ev091", "CLM-TW-YUKINO-REL", "availability", "TW", "OFFICIAL", "台服官網雪野精選轉蛋公告", "https://www.princessconnect.so-net.tw/news/newsDetail/3712", "tw_official_notice_3712", "2026-01-31", "官方正文列出「雪野」並公告於2026/02/01 16:00登場", "只證明台服官方名稱與實裝；跨服名稱對照另為B級映射"],
  ["ev092", "CLM-LOC-YUKINO", "availability", "JP", "OFFICIAL", "日服官網ユキノ登場公告", "https://priconne-redive.jp/news/information/33458/", "jp_official_33458", "2025-09-30", "官方正文列出「ユキノ」；與ev091交叉支撐同一角色原版映射", "官方正文未直接聲明台日對照；映射上限B"],
  ["ev093", "CLM-TW-AMES-SUMMER-REL", "availability", "TW", "OFFICIAL", "台服官網愛梅斯（夏日）精選轉蛋公告", "https://www.princessconnect.so-net.tw/news/newsDetail/3132", "tw_official_notice_3132", "2024-11-30", "官方正文列出「愛梅斯（夏日）」並公告於2024/12/01 16:00登場", "只證明台服官方名稱與實裝；跨服名稱對照另為B級映射"],
  ["ev094", "CLM-LOC-AMES-SUMMER", "availability", "JP", "OFFICIAL", "日服官網アメス（サマー）登場公告", "https://priconne-redive.jp/news/information/28051/", "jp_official_28051", "2024-07-31", "官方正文列出「アメス（サマー）」；與ev093交叉支撐同一角色夏日版本映射", "官方正文未直接聲明台日對照；映射上限B"],
  ["ev095", "CLM-TW-SONO-REL", "availability", "TW", "OFFICIAL", "台服官網苑精選轉蛋公告", "https://www.princessconnect.so-net.tw/news/newsDetail/3539", "tw_official_notice_3539", "2025-09-15", "官方正文列出「苑」並公告於2025/09/16 16:00登場", "只證明台服官方名稱與實裝；跨服名稱對照另為B級映射"],
  ["ev096", "CLM-LOC-SONO", "availability", "JP", "OFFICIAL", "日服官網ソノ登場公告", "https://priconne-redive.jp/news/information/31915/", "jp_official_31915", "2025-05-15", "官方正文列出「ソノ」；與ev095交叉支撐同一角色原版映射", "官方正文未直接聲明台日對照；映射上限B"],
  ["ev097", "CLM-TW-NINON-SUMMER-REL", "availability", "TW", "OFFICIAL", "台服官網妮諾（夏日）精選轉蛋公告", "https://www.princessconnect.so-net.tw/news/newsDetail/3648", "tw_official_notice_3648", "2025-12-15", "官方正文列出「妮諾（夏日）」並公告於2025/12/16 16:00登場", "只證明台服官方名稱與實裝；跨服名稱對照另為B級映射"],
  ["ev098", "CLM-LOC-NINON-SUMMER", "availability", "JP", "OFFICIAL", "日服官網ニノン（サマー）登場公告", "https://priconne-redive.jp/news/information/33009/", "jp_official_33009", "2025-08-15", "官方正文列出「ニノン（サマー）」；與ev097交叉支撐同一角色夏日版本映射", "官方正文未直接聲明台日對照；映射上限B"],
  ["ev099", "CLM-TW-NANAKA-SUMMER-AVAILABLE", "availability", "TW", "OFFICIAL", "台服官網七七香（夏日）可取得公告", "https://www.princessconnect.so-net.tw/news/newsDetail/3624", "tw_official_notice_3624", "2025-11-23", "官方正文列出「七七香（夏日）」為可取得角色，證明目前台服AVAILABLE與官方名稱", "不是首次實裝公告故不推定tw_release_date；跨服名稱對照另為B級映射"],
  ["ev100", "CLM-LOC-NANAKA-SUMMER", "availability", "JP", "OFFICIAL", "日服官網ナナカ（サマー）登場公告", "https://priconne-redive.jp/news/information/9122/", "jp_official_9122", "2020-07-15", "官方正文列出「ナナカ（サマー）」；與ev099交叉支撐同一角色夏日版本映射", "台服Evidence不是初次實裝頁且官方正文未直接聲明跨服對照；映射上限B"],
  ["ev101", "CLM-TW-MISORA-XMAS-REL", "availability", "TW", "OFFICIAL", "台服官網美空（聖誕節）精選轉蛋公告", "https://www.princessconnect.so-net.tw/news/newsDetail/3814", "tw_official_notice_3814", "2026-04-15", "官方正文列出「美空（聖誕節）」並公告於2026/04/16 16:00登場", "只證明台服官方名稱與實裝；跨服名稱對照另為B級映射"],
  ["ev102", "CLM-LOC-MISORA-XMAS", "availability", "JP", "OFFICIAL", "日服官網ミソラ（クリスマス）登場公告", "https://priconne-redive.jp/news/information/34409/", "jp_official_34409", "2025-12-15", "官方正文列出「ミソラ（クリスマス）」；與ev101交叉支撐同一角色聖誕版本映射", "官方正文未直接聲明台日對照；映射上限B"],
  ["ev103", "CLM-TW-VIOLET-ISANAMI-REL", "availability", "TW", "OFFICIAL", "台服官網薇歐莉特（黃泉鯨命）精選轉蛋公告", "https://www.princessconnect.so-net.tw/news/newsDetail/3872", "tw_official_notice_3872", "2026-05-31", "官方正文列出「薇歐莉特（黃泉鯨命）」並公告於2026/06/01 16:00登場", "水堇僅為社群俗稱；跨服名稱對照另為B級映射"],
  ["ev104", "CLM-LOC-VIOLET-ISANAMI", "availability", "JP", "OFFICIAL", "日服官方鏡像ヴァイオレット（イサナミ）登場公告", "https://dmg.priconne-redive.jp/news/detail.php?id=34985", "jp_official_mirror_34985", "2026-01-31", "官方正文列出「ヴァイオレット（イサナミ）」；與ev103交叉支撐同一角色同版本映射", "官方正文未直接聲明台日對照且採DMM官方鏡像；映射上限B"],
  ["ev105", "CLM-TW-LABYRISTA-ALPHA-REL", "availability", "TW", "OFFICIAL", "台服官網拉比林斯達（始源）精選轉蛋公告", "https://www.princessconnect.so-net.tw/news/newsDetail/3401", "tw_official_notice_3401", "2025-05-31", "官方正文列出「拉比林斯達（始源）」並公告於2025/06/01 16:00登場；角色劇情解鎖指向同一活動第2話與終幕", "阿法晶僅為社群俗稱且不是克莉絲提娜；跨服名稱對照另為B級映射"],
  ["ev106", "CLM-LOC-LABYRISTA-ALPHA", "availability", "JP", "OFFICIAL", "日服官方鏡像ラビリスタ（アルファ）登場公告", "https://dmg.priconne-redive.jp/news/detail.php?id=30360", "jp_official_mirror_30360", "2025-01-31", "官方正文列出「ラビリスタ（アルファ）」且角色劇情解鎖指向同一活動第2話與エピローグ；與ev105支撐同一角色同版本映射", "官方正文未直接聲明台日對照且採DMM官方鏡像；映射上限B"],
];

const arenaDefenseMembers = [
  [1, "eris_orig", "厄莉絲"],
  [2, "presia_fallen", "普蕾西亞（墮落）"],
  [3, "rei_ny", "怜（新年）"],
  [4, "neya_orig", "涅婭"],
  [5, "matsuri_orig", "茉莉"],
].map(([slot, unit_key, display_name]) => ({
  slot,
  unit_key,
  display_name,
  display_name_source: "TW_OFFICIAL",
}));

const arenaCounterMembers = [
  [
    [1, "kaya_orig", "嘉夜"],
    [2, "aira_orig", "埃拉"],
    [3, "rem_orig", "雷姆"],
    [4, "yuki_orig", "雪"],
    [5, "saren_sum", "咲戀（夏日）"],
  ],
  [
    [1, "kaya_orig", "嘉夜"],
    [2, "aira_orig", "埃拉"],
    [3, "mahiru_orig", "真陽"],
    [4, "yuki_orig", "雪"],
    [5, "saren_sum", "咲戀（夏日）"],
  ],
].map((members) => members.map(([slot, unit_key, display_name]) => ({
  slot,
  unit_key,
  display_name,
  display_name_source: "TW_OFFICIAL",
})));

const arenaCounters = arenaCounterMembers.map((counter_members, index) => ({
  counter_id: `TW_ARENA_20260525_0${index + 1}`,
  defense_id: "TW-2026-05-25:eris_orig;matsuri_orig;neya_orig;presia_fallen;rei_ny",
  server: "TW",
  environment_version: "TW-2026-05-25",
  arena_bracket: "UNKNOWN",
  defense_signature: "eris_orig;matsuri_orig;neya_orig;presia_fallen;rei_ny",
  counter_signature: counter_members.map((member) => member.unit_key).sort().join(";"),
  defense_members: arenaDefenseMembers,
  counter_members,
  status: "SINGLE_REPORT",
  match_type: "EXACT",
  outcome: "WIN",
  verification: "SCREENSHOT_RESULT",
  sample_size: 1,
  wins: 1,
  losses: 0,
  empirical_win_rate: null,
  randomness: "UNKNOWN（原樓主稱網站測試有贏也有輸）",
  rng_risk: "UNKNOWN",
  claim_confidence: "D",
  reproducibility: "UNVERIFIED_REPEATABILITY",
  source_tier: "SINGLE_PLAYER_REPORT",
  source_record_count: 1,
  source_platforms: ["Bahamut"],
  tw_availability_check: "PASS",
  unavailable_unit_ids: [],
  required_upgrade_check: "UNKNOWN",
  operation_mode: "UNKNOWN",
  environment_match: "UNKNOWN",
  speed_conditions: "UNKNOWN",
  initial_action_notes: "UNKNOWN",
  verified_date: "2026-08-08",
  last_review_due: "2026-08-23",
  record_date_min: "2026-05-25",
  record_date_max: "2026-05-25",
  notes: "單一玩家截圖戰果；只作 exact composition 參考。",
  evidence_ids: index === 0 ? ["ev113", "ev114"] : ["ev113", "ev115"],
  claim_ids: index === 0
    ? ["CLM-ARENA-TW-DEF-20260525", "CLM-ARENA-TW-COUNTER-20260525-01"]
    : ["CLM-ARENA-TW-DEF-20260525", "CLM-ARENA-TW-COUNTER-20260525-02"],
}));

const arenaCharacters = [...new Map(
  [
    ...arenaDefenseMembers,
    ...arenaCounterMembers.flat(),
    ...Object.entries(character).map(([unit_key, display_name], index) => ({
      slot: index + 1,
      unit_key,
      display_name,
    })),
  ].map((member) => [
    member.unit_key,
    {
      unit_key: member.unit_key,
      tw_name: member.display_name,
      jp_name: "UNKNOWN",
      tw_availability_status: "AVAILABLE",
    },
  ]),
).values()];

const parenaEnvironments = [
  { server: "TW", environment_version: "TW-MOCK-2026-08", verified_case_count: 1 },
  { server: "TW", environment_version: "TW-MOCK-NO-EXACT", verified_case_count: 1 },
];

function mockParenaCounter(defenseTeam, matchupNo) {
  const base = arenaCounters[0];
  const byKey = new Map(arenaCharacters.map((row) => [row.unit_key, row.tw_name]));
  const defense_members = defenseTeam.map((unit_key, index) => ({
    slot: index + 1,
    unit_key,
    display_name: byKey.get(unit_key) ?? unit_key,
    display_name_source: "TW_OFFICIAL",
  }));
  return {
    ...base,
    counter_id: `TEST-PARENA-COUNTER-${matchupNo}`,
    defense_id: `TEST-PARENA-DEFENSE-${matchupNo}`,
    environment_version: "TW-MOCK-2026-08",
    defense_signature: defenseTeam.slice().sort().join(";"),
    defense_members,
    status: "VERIFIED",
    claim_confidence: "C",
    reproducibility: "CONFIRMED",
    source_record_count: 2,
    sample_size: 2,
    wins: 2,
    required_upgrade_check: "PASS",
    environment_match: "EXACT",
    notes: "TEST_ONLY：完整 exact 三隊案例，不代表 canonical research data。",
    evidence_ids: ["ev113", "ev114"],
    claim_ids: [`CLM-TEST-PARENA-${matchupNo}`],
  };
}

function mockParenaSolve(body) {
  const defenseTeams = body?.defense_teams;
  if (!Array.isArray(defenseTeams) || defenseTeams.length !== 3) return null;
  const allUnits = defenseTeams.flat();
  if (defenseTeams.some((team) => !Array.isArray(team) || team.length !== 5)
      || new Set(allUnits).size !== 15) return null;
  const querySignature = defenseTeams
    .map((team) => team.slice().sort().join(";"))
    .sort()
    .join("||");
  if (body.environment_version === "TW-MOCK-NO-EXACT") {
    return envelope({
      match_type: "EXACT",
      similar_enabled: false,
      query_signature: querySignature,
      defense_teams: defenseTeams,
      cases: [],
    }, ["NO_EXACT_PARENA_PLAN"]);
  }
  const matchups = defenseTeams.map((team, index) => ({
    matchup_no: index + 1,
    defense_input_index: index + 1,
    result_claim_id: `CLM-TEST-PARENA-${index + 1}`,
    counter: mockParenaCounter(team, index + 1),
  }));
  return envelope({
    match_type: "EXACT",
    similar_enabled: false,
    query_signature: querySignature,
    defense_teams: defenseTeams,
    cases: [{
      case_id: "TEST-PARENA-001",
      server: "TW",
      environment_version: "TW-MOCK-2026-08",
      status: "VERIFIED",
      hidden_team_mode: "NONE",
      verified_date: "2026-08-10",
      reproducibility: "CONFIRMED",
      last_review_due: "2026-09-10",
      notes: "TEST_ONLY synthetic positive fixture。",
      case_win_claim_id: "CLM-TEST-PARENA-WIN",
      case_win_confidence: "D",
      sources: [{
        source_id: "SRC-TEST-PARENA",
        title: "TEST_ONLY P-Arena source",
        platform: "TEST_ONLY",
        source_type: "TEST_FIXTURE",
        server: "TW",
        url: "https://example.invalid/test-only-parena",
        last_checked: "2026-08-10",
        freshness_window: "CURRENT",
        access_status: "ACTIVE",
        confidence_cap: "C",
        extraction_method: "TEST_ONLY",
        notes: "Never canonical。",
      }],
      evidence_ids: ["ev113", "ev114"],
      claim_ids: ["CLM-TEST-PARENA-1", "CLM-TEST-PARENA-2", "CLM-TEST-PARENA-3", "CLM-TEST-PARENA-WIN"],
      matchups,
    }],
  }, ["CASE_WIN_SINGLE_SOURCE_REFERENCE", "CASE_WIN_CONFIDENCE_D_BLOCKS_GATE_C"], {
    server: "TW",
    environment_version: "TW-MOCK-2026-08",
    verified_at: "2026-08-10",
    confidence: "D",
    evidence_ids: ["ev113", "ev114"],
    claim_ids: ["CLM-TEST-PARENA-1", "CLM-TEST-PARENA-2", "CLM-TEST-PARENA-3", "CLM-TEST-PARENA-WIN"],
  });
}

function gachaEvent({
  eventId,
  jpDate,
  estimateStart,
  estimateEnd,
  characterName,
  poolType,
  limitedStatus,
  limitedClaimId = null,
  maturity,
  evidenceIds,
  claimIds,
  values = {},
  confidence = "低（研究列；價值未評估）",
  priority = "NOT_EVALUATED",
  track = "ALL_NEW",
  anchorCount = 7,
  notes = "TEST_ONLY Gacha timeline fixture。",
}) {
  return {
    event_id: eventId,
    source_server: "JP",
    target_server: "TW",
    jp_date: jpDate,
    model_estimate_start: estimateStart,
    model_estimate_end: estimateEnd,
    tw_estimate_start: estimateStart,
    tw_estimate_end: estimateEnd,
    forecast_method: "MODEL_ONLY",
    confidence,
    character_name_jp: characterName,
    tw_name: null,
    pool_type: poolType,
    limited_status: limitedStatus,
    limited_claim_id: limitedClaimId,
    arena_value: values.arena ?? "NOT_EVALUATED",
    p_arena_value: values.pArena ?? "NOT_EVALUATED",
    pve_value: values.pve ?? "NOT_EVALUATED",
    clan_value: values.clan ?? "NOT_EVALUATED",
    future_upgrade: values.future ?? "UNKNOWN",
    relative_priority: priority,
    anchor_track: track,
    anchor_count: anchorCount,
    forecast_basis: `${track} track | n=${anchorCount} | median=123 | range=122-124 | mapping_conf=B | source=canonical anchors`,
    last_verified: "2026-08-09",
    status: "ACTIVE",
    maturity,
    last_review_due: "2026-08-31",
    community_estimate_start: null,
    community_estimate_end: null,
    community_order_consensus: "",
    community_source_count: 0,
    community_last_checked: null,
    community_disagreement: "",
    forecast_notes: notes,
    evidence_ids: evidenceIds,
    claim_ids: claimIds,
    community_source_ids: [],
  };
}

const gachaTimeline = [
  gachaEvent({
    eventId: "JP_20260630_shefi_vardrache",
    jpDate: "2026-06-30",
    estimateStart: "2026-10-30",
    estimateEnd: "2026-11-01",
    characterName: "シェフィ（ヴァードラッヘ）",
    poolType: "公主祭限定",
    limitedStatus: "YES",
    limitedClaimId: "CLM-SHEFI-POOL",
    maturity: "MATURE",
    evidenceIds: ["ev010", "ev011", "ev012", "ev032"],
    claimIds: ["CLM-SHEFI-DATE", "CLM-SHEFI-EVAL-PVE", "CLM-SHEFI-POOL"],
    values: { arena: "待查證", pArena: "待查證", pve: "高（D）", clan: "待查證（E）", future: "待查證" },
    confidence: "低～中",
    priority: "相對優先級待補獨立價值證據（限定身分 OFFICIAL／A；現有價值結論最高 D）",
    track: "LIMITED",
    anchorCount: 5,
  }),
  gachaEvent({
    eventId: "JP_20260703_luisemarie_summer",
    jpDate: "2026-07-03",
    estimateStart: "2026-11-02",
    estimateEnd: "2026-11-04",
    characterName: "ルイズマリー（サマー）",
    poolType: "限定（泳裝）",
    limitedStatus: "YES",
    limitedClaimId: "CLM-LUISE-DATE",
    maturity: "MATURE",
    evidenceIds: ["ev013", "ev014", "ev033"],
    claimIds: ["CLM-LUISE-DATE", "CLM-LUISE-EVAL"],
    values: { arena: "待查證", pArena: "待查證", pve: "中", clan: "待查證", future: "待查證" },
    confidence: "低～中",
    priority: "相對優先級待補獨立價值證據（現有價值結論最高 D）",
    track: "LIMITED",
    anchorCount: 5,
  }),
  gachaEvent({
    eventId: "JP_20260731_fubuki_summer",
    jpDate: "2026-07-31",
    estimateStart: "2026-11-30",
    estimateEnd: "2026-12-02",
    characterName: "フブキ（サマー）",
    poolType: "限定（泳裝，官網明載期間限定）",
    limitedStatus: "YES",
    limitedClaimId: "CLM-JP-FUBUKI-DATE",
    maturity: "RESEARCH",
    evidenceIds: ["ev048"],
    claimIds: ["CLM-JP-FUBUKI-DATE"],
    track: "LIMITED",
    anchorCount: 5,
  }),
  gachaEvent({
    eventId: "JP_20260815_vampy_summer",
    jpDate: "2026-08-15",
    estimateStart: "2026-12-15",
    estimateEnd: "2026-12-17",
    characterName: "ヴァンピィ（サマー）",
    poolType: "8.5 Year Anniversary ガチャ（官方直播）",
    limitedStatus: "UNKNOWN",
    maturity: "RESEARCH",
    evidenceIds: ["ev123"],
    claimIds: ["CLM-JP-85-LIVE-GACHA"],
    notes: "官方直播未直接明示期間限定身分；台服名稱與價值維持 UNKNOWN。",
  }),
  gachaEvent({
    eventId: "JP_20260823_tia",
    jpDate: "2026-08-23",
    estimateStart: "2026-12-23",
    estimateEnd: "2026-12-25",
    characterName: "ティア",
    poolType: "プリンセスフェス プライズガチャ（官方直播）",
    limitedStatus: "UNKNOWN",
    maturity: "RESEARCH",
    evidenceIds: ["ev123"],
    claimIds: ["CLM-JP-85-LIVE-GACHA"],
    notes: "只保存 Princess Fes Prize Gacha 事實；不由池名推論 Fes 限定。",
  }),
];

const gachaCommunitySources = [
  {
    source_id: "GACHA-COMM-001",
    title: "卡池整理表更新分享（更新至2026.8月）",
    platform: "巴哈姆特",
    author: "修.安里特（ernieseed123）",
    source_type: "MAINTAINED_TABLE",
    url: "https://forum.gamer.com.tw/C.php?bsn=30861&snA=36559",
    last_seen_update: "2026-08-01",
    coverage_start: "2026-01",
    coverage_end: "2026-12",
    update_status: "CHECKED",
    confidence_cap: "D",
    usage: "台服卡池順序、月份整理、表格型未來視",
    last_checked: "2026-08-09",
    notes: "論壇月更索引／2026-08影片／Google Sheet 均實開；wrapper archive 為 2024-09 至 2026-08。作者明示推薦是個人想法；個人寶石門檻永久排除；JP日期仍須官方正文",
  },
  {
    source_id: "GACHA-COMM-002",
    title: "未來台服卡池開放整理",
    platform: "巴哈姆特",
    author: "檸笙（asd224569）",
    source_type: "FORUM_TIMELINE",
    url: "https://forum.gamer.com.tw/C.php?bsn=30861&snA=37138",
    last_seen_update: "2026-07-29",
    coverage_start: "2025-05-04",
    coverage_end: "2026-12-01",
    update_status: "CHECKED",
    confidence_cap: "D",
    usage: "角色池順序與預測窗口",
    last_checked: "2026-08-09",
    notes: "預測非官方日期；社群中文名不得作 canonical 台服名。",
  },
  {
    source_id: "GACHA-COMM-003",
    title: "稍微整理了一下未來視",
    platform: "巴哈姆特",
    author: "帕帕維爾（xcru2267）",
    source_type: "FORUM_TIMELINE",
    url: "https://forum.gamer.com.tw/C.php?bsn=30861&snA=37522",
    last_seen_update: "2026-04-15",
    coverage_start: null,
    coverage_end: null,
    update_status: "STALE",
    confidence_cap: "D",
    usage: "歷史社群整理／表單",
    last_checked: "2026-08-09",
    notes: "缺近期新池；GameWith 衍生評價不算獨立第二來源。",
  },
  {
    source_id: "GACHA-COMM-004",
    title: "台服未來視影片系列",
    platform: "YouTube",
    author: "播放清單建立者3C木巫／影片作者煌靈LongTimeNoC",
    source_type: "VIDEO_SERIES",
    url: "https://www.youtube.com/playlist?list=PL8baEoP7EWvo00nXMUW8pwlByCRFBvXMd",
    last_seen_update: "2022-10-07",
    coverage_start: "2022-08-05",
    coverage_end: "2022-10-07",
    update_status: "STALE",
    confidence_cap: "D",
    usage: "僅供歷史角色價值研究；不作現行日期證據",
    last_checked: "2026-08-09",
    notes: "播放清單停在 2022 年；未完整播放內容不得作價值 Evidence。",
  },
];

const evidence123 = envelope({
  evidence_id: "ev123",
  declared_claim_id: "CLM-JP-85-LIVE-GACHA",
  linked_claim_id: "CLM-JP-85-LIVE-GACHA",
  module: "gacha",
  server: "JP",
  source_tier: "OFFICIAL",
  evidence_confidence: "A",
  source_title: "日服官方 8.5 周年直前生放送卡池投影片",
  source_url: "https://www.youtube.com/watch?v=wtS78cLTlyo",
  source_locator: "official_youtube_8_5_live@49:17;57:07;59:01;1:42:07;1:42:41;1:43:21",
  published_date: "2026-08-08",
  published_date_precision: "DAY",
  verified_date: "2026-08-09",
  claim_summary: "官方影片投影片明示ヴァンピィ（サマー）與ティア登場及 8/15 Anniversary／Select、8/23 Princess Fes Prize 卡池時程",
  limitations: "投影片未直接明示兩角為期間限定；不推論台服日期、台服中文名或角色價值",
  status: "ACTIVE",
});

function gachaEvidence({
  evidenceId,
  claimId,
  sourceTier,
  sourceTitle,
  sourceUrl,
  sourceLocator = "",
  publishedDate,
  publishedDatePrecision,
  verifiedDate,
  claimSummary,
  limitations,
}) {
  return envelope({
    evidence_id: evidenceId,
    declared_claim_id: claimId,
    linked_claim_id: claimId,
    module: "gacha",
    server: "JP",
    source_tier: sourceTier,
    evidence_confidence: sourceTier === "OFFICIAL" ? "A" : "D",
    source_title: sourceTitle,
    source_url: sourceUrl,
    source_locator: sourceLocator,
    published_date: publishedDate,
    published_date_precision: publishedDatePrecision,
    verified_date: verifiedDate,
    claim_summary: claimSummary,
    limitations,
    status: "ACTIVE",
  });
}

function arenaEvidence(evidenceId, claimId, summary) {
  const isCanonicalEv114 = evidenceId === "ev114";
  return envelope({
    evidence_id: evidenceId,
    declared_claim_id: claimId,
    linked_claim_id: claimId,
    module: "arena",
    server: "TW",
    source_tier: "SINGLE_PLAYER_REPORT",
    evidence_confidence: "D",
    source_title: isCanonicalEv114
      ? "巴哈姆特回覆 B1 台服競技場勝利戰果"
      : "巴哈姆特 Arena 單筆戰果",
    source_url: isCanonicalEv114
      ? "https://forum.gamer.com.tw/Co.php?bsn=30861&sn=504930"
      : `https://forum.gamer.com.tw/test-only/${evidenceId}`,
    source_locator: isCanonicalEv114
      ? "B1 憂姫 2026-05-25 10:41:38＋原圖 https://truth.bahamut.com.tw/s01/202605/forum/30861/acb01f479fdbfae7011c6eb730769599.JPG"
      : `arena_report@${evidenceId}`,
    published_date: "2026-05-25",
    published_date_precision: "DAY",
    verified_date: "2026-08-08",
    claim_summary: isCanonicalEv114
      ? "原始戰果圖明示攻方 Win、防方 Lose、防守五人全為 0%；攻方完整五人為嘉夜／埃拉／雷姆／雪／咲戀（夏日）"
      : summary,
    limitations: isCanonicalEv114
      ? "單一作者單次截圖；只證明一次 exact composition 勝利，不代表穩定率或多次重現；戰果未載版本與練度"
      : "單一來源、單一樣本；不代表可重現性或穩定勝率。",
    status: "ACTIVE",
  });
}

const evidenceFixtures = new Map([
  ["ev029", evidence029],
  ["ev010", gachaEvidence({ evidenceId: "ev010", claimId: "CLM-SHEFI-DATE", sourceTier: "OFFICIAL", sourceTitle: "日服官方X", sourceUrl: "https://x.com/priconne_redive/status/2071792124971110672", sourceLocator: "x_post_2071792124971110672", publishedDate: "2026-06-30", publishedDatePrecision: "DAY", verifiedDate: "2026-07-16", claimSummary: "シェフィ（ヴァードラッヘ）06/30 登場", limitations: "無" })],
  ["ev011", gachaEvidence({ evidenceId: "ev011", claimId: "CLM-SHEFI-EVAL-PVE", sourceTier: "MAJOR_GUIDE", sourceTitle: "GameWith 評價頁565564", sourceUrl: "https://gamewith.jp/pricone-re/article/show/565564", sourceLocator: "gamewith_article_565564", publishedDate: "2026-07", publishedDatePrecision: "MONTH", verifiedDate: "2026-07-16", claimSummary: "單體／複數兩用attacker；UB4回後氷竜超克追傷；單體Boss頂級；深域道中最適候補；自身無防debuff", limitations: "單一攻略站" })],
  ["ev012", gachaEvidence({ evidenceId: "ev012", claimId: "CLM-SHEFI-EVAL-PVE", sourceTier: "SINGLE_PLAYER_REPORT", sourceTitle: "YouTube 性能解說", sourceUrl: "https://youtube.com/watch?v=Fg6zgqwiz6E", publishedDate: "2026-07", publishedDatePrecision: "MONTH", verifiedDate: "2026-07-16", claimSummary: "闇屬性；全攻擊追擊；「最強泛用attacker」評價與ev011方向一致", limitations: "單一影片；屬性標註待官方頁核對" })],
  ["ev013", gachaEvidence({ evidenceId: "ev013", claimId: "CLM-LUISE-DATE", sourceTier: "OFFICIAL", sourceTitle: "日服官網news列表", sourceUrl: "https://priconne-redive.jp/news/information/", publishedDate: "2026-07-03", publishedDatePrecision: "DAY", verifiedDate: "2026-07-16", claimSummary: "期間限定ルイズマリー（サマー）7/3 開池", limitations: "無" })],
  ["ev014", gachaEvidence({ evidenceId: "ev014", claimId: "CLM-LUISE-EVAL", sourceTier: "MAJOR_GUIDE", sourceTitle: "GameWith ガチャ解說111249", sourceUrl: "https://gamewith.jp/pricone-re/article/show/111249", sourceLocator: "gamewith_article_111249", publishedDate: "2026-07", publishedDatePrecision: "MONTH", verifiedDate: "2026-07-16", claimSummary: "單體Boss水魔法buffer；火力／耐久支援平衡；非必須級；持有主要水魔角則餘裕再抽", limitations: "單一攻略站" })],
  ["ev032", gachaEvidence({ evidenceId: "ev032", claimId: "CLM-SHEFI-POOL", sourceTier: "OFFICIAL", sourceTitle: "日服官網36760", sourceUrl: "https://priconne-redive.jp/news/information/36760/", sourceLocator: "official_notice_36760", publishedDate: "2026-06-30", publishedDatePrecision: "DAY", verifiedDate: "2026-07-18", claimSummary: "シェフィ（ヴァードラッヘ）プリンセスフェス限定（官方直接公告）", limitations: "無（2026-07-18 稽核官方直頁確認）" })],
  ["ev033", gachaEvidence({ evidenceId: "ev033", claimId: "CLM-LUISE-DATE", sourceTier: "OFFICIAL", sourceTitle: "日服官方（DMM GAMES版）2026/07/03 公告（期間限定「ルイズマリー（サマー）」ピックアップ）", sourceUrl: "https://dmg.priconne-redive.jp/news/detail.php?id=36850", sourceLocator: "jp_official_information_36850", publishedDate: "2026-07-03", publishedDatePrecision: "DAY", verifiedDate: "2026-08-02", claimSummary: "ルイズマリー（サマー）期間限定ピックアップ 2026/07/03 12:00～2026/07/15 11:59", limitations: "無（2026-08-02官方直頁完整抓取確認；DMM GAMES版官方站同ID鏡像）" })],
  ["ev048", gachaEvidence({ evidenceId: "ev048", claimId: "CLM-JP-FUBUKI-DATE", sourceTier: "OFFICIAL", sourceTitle: "日服官網 2026/07/31 公告（期間限定「フブキ（サマー）」ピックアップ）", sourceUrl: "https://priconne-redive.jp/news/information/37049/", sourceLocator: "jp_official_information_37049", publishedDate: "2026-07-31", publishedDatePrecision: "DAY", verifiedDate: "2026-08-02", claimSummary: "期間限定「フブキ（サマー）」ピックアップ 2026/07/31 12:00～2026/08/15 11:59；劇情活動「ラヴって♡バズさまー！」連動", limitations: "無（2026-08-02官方直頁完整抓取確認）" })],
  ["ev123", evidence123],
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
  ["ev113", arenaEvidence("ev113", "CLM-ARENA-TW-DEF-20260525", "正文顯示完整五人防守編成。")],
  ["ev114", arenaEvidence("ev114", "CLM-ARENA-TW-COUNTER-20260525-01", "正文截圖顯示第一組完整五人與單次勝利結果。")],
  ["ev115", arenaEvidence("ev115", "CLM-ARENA-TW-COUNTER-20260525-02", "正文截圖顯示第二組完整五人與單次勝利結果。")],
  ...waterEvidenceRows.map((row) => [row[0], canonicalEvidence(row)]),
]);

function send(response, status, payload) {
  response.writeHead(status, {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
  });
  response.end(JSON.stringify(payload));
}

function sendPng(response, payload) {
  response.writeHead(200, {
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "no-store",
    "Content-Length": payload.byteLength,
    "Content-Type": "image/png",
    "X-Content-Type-Options": "nosniff",
  });
  response.end(payload);
}

async function readJson(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    return null;
  }
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://${host}:${port}`);
  if (request.method === "OPTIONS") return send(response, 204, {});
  if (request.method === "POST" && url.pathname === "/api/v1/solver/parena") {
    const payload = mockParenaSolve(await readJson(request));
    return payload
      ? send(response, 200, payload)
      : send(response, 422, { detail: { code: "INVALID_PARENA_DEFENSE" } });
  }
  if (request.method !== "GET") return send(response, 405, { detail: { code: "METHOD_NOT_ALLOWED" } });
  if (url.pathname === "/health/live" || url.pathname === "/health/ready") {
    return send(response, 200, { status: "ok", checks: { fixture: "TEST_ONLY" } });
  }
  const pveAssetMatch = url.pathname.match(/^\/api\/v1\/pve-library\/assets\/([0-9a-f]{64})$/);
  if (pveAssetMatch && pveAssetShas.includes(pveAssetMatch[1])) {
    return sendPng(response, pveFixturePng);
  }
  const gachaLibraryAssetMatch = url.pathname.match(/^\/api\/v1\/gacha-library\/assets\/([0-9a-f]{64})$/);
  if (gachaLibraryAssetMatch) {
    const sha = gachaLibraryAssetMatch[1];
    if (gachaLibraryImageShas.includes(sha)) return sendPng(response, pveFixturePng);
    if (sha === gachaLibraryMissingSha) {
      return send(response, 404, {
        error: { code: "GACHA_ASSET_NOT_FOUND", message: "Fixture asset was not found." },
      });
    }
    if (sha === gachaLibraryRedirectSha) {
      response.writeHead(302, {
        Location: `/api/v1/gacha-library/assets/${gachaLibraryImageShas[0]}`,
      });
      return response.end();
    }
    if (sha === gachaLibrarySvgSha) {
      response.writeHead(200, {
        "Cache-Control": "no-store",
        "Content-Type": "image/svg+xml",
      });
      return response.end('<svg xmlns="http://www.w3.org/2000/svg"><text>unsafe fixture</text></svg>');
    }
    if (sha === gachaLibraryHtmlErrorSha) {
      response.writeHead(404, {
        "Cache-Control": "no-store",
        "Content-Type": "text/html; charset=utf-8",
      });
      return response.end("<h1>fixture not found</h1>");
    }
  }
  if (url.pathname === "/api/v1/gacha-library/forecasts") {
    return send(response, 200, gachaLibraryPayload);
  }
  if (url.pathname === "/api/v1/pve-library/stages") {
    const mode = url.searchParams.get("mode")?.trim() || null;
    const element = url.searchParams.get("element")?.trim() || null;
    const parseFilterNumber = (name) => {
      const raw = url.searchParams.get(name)?.trim();
      if (!raw) return null;
      const value = Number(raw);
      return Number.isInteger(value) && value >= 0 ? value : null;
    };
    const area = parseFilterNumber("area");
    const stage = parseFilterNumber("stage");
    const items = pveStageSummaries.filter((item) => (
      (!mode || item.mode === mode)
      && (!element || item.element === element)
      && (area === null || item.stage_refs.some((ref) => ref.area === area))
      && (stage === null || item.stage_refs.some((ref) => ref.stage === stage))
    ));
    return send(response, 200, pveLibraryEnvelope({
      items,
      filters: { mode, element, area, stage },
      available_filters: pveAvailableFilters(mode, element),
      total: items.length,
    }));
  }
  const pveStageMatch = url.pathname.match(/^\/api\/v1\/pve-library\/stages\/([^/]+)$/);
  if (pveStageMatch) {
    const detail = pveLibraryDetails.get(decodeURIComponent(pveStageMatch[1]));
    if (detail) return send(response, 200, pveLibraryEnvelope(detail));
    return send(response, 404, {
      error: {
        code: "PVE_STAGE_NOT_FOUND",
        message: "PVE library stage was not found.",
        details: { stage_id: decodeURIComponent(pveStageMatch[1]) },
      },
    });
  }
  if (url.pathname === "/api/v1/baseline") return send(response, 200, baseline);
  if (url.pathname === "/api/v1/stages") return send(response, 200, envelope(stageSummaries));
  if (url.pathname === "/api/v1/gacha/timeline") {
    if (gachaCanonicalUnavailable) {
      return send(response, 503, {
        detail: { code: "DATABASE_UNAVAILABLE" },
      });
    }
    return send(response, 200, envelope(gachaTimeline, ["GACHA_RESEARCH_ROWS_PRESENT"], {
      server: "MIXED",
      evidence_ids: ["ev010", "ev011", "ev012", "ev013", "ev014", "ev032", "ev033", "ev048", "ev123"],
      claim_ids: [
        "CLM-JP-85-LIVE-GACHA",
        "CLM-JP-FUBUKI-DATE",
        "CLM-LUISE-DATE",
        "CLM-LUISE-EVAL",
        "CLM-SHEFI-DATE",
        "CLM-SHEFI-EVAL-PVE",
        "CLM-SHEFI-POOL",
      ],
    }));
  }
  if (url.pathname === "/api/v1/gacha/community-sources") {
    if (gachaCanonicalUnavailable) {
      return send(response, 503, {
        detail: { code: "DATABASE_UNAVAILABLE" },
      });
    }
    return send(response, 200, envelope(gachaCommunitySources, ["STALE_COMMUNITY_SOURCES_PRESENT"]));
  }
  const stageMatch = url.pathname.match(/^\/api\/v1\/stages\/([^/]+)$/);
  if (stageMatch) {
    const stageDetail = stageDetailsByGuide.get(decodeURIComponent(stageMatch[1]));
    if (stageDetail) return send(response, 200, stageDetail);
  }
  if (url.pathname === "/api/v1/pvp/characters") {
    return send(response, 200, envelope(arenaCharacters, [], {
      server: "TW",
      evidence_ids: ["ev041", "ev107", "ev108", "ev109", "ev110", "ev111", "ev112"],
    }));
  }
  if (url.pathname === "/api/v1/parena/environments") {
    return send(response, 200, envelope(parenaEnvironments, [], {
      server: "TW",
      environment_version: "MIXED",
    }));
  }
  if (url.pathname === "/api/v1/pvp/counters") {
    const requestedSignature = url.searchParams.get("defense_signature");
    const canonicalSignature = requestedSignature
      ? requestedSignature.split(";").map((unitKey) => unitKey.trim()).sort().join(";")
      : null;
    const matchingCounters = canonicalSignature === null
      ? arenaCounters
      : arenaCounters.filter((counter) => counter.defense_signature === canonicalSignature);
    const warnings = matchingCounters.length === 0
      ? ["NO_EXACT_COUNTER", "NO_VERIFIED_COUNTER"]
      : ["NO_VERIFIED_COUNTER", "SINGLE_REPORT_REFERENCE_ONLY"];
    const details = matchingCounters.length === 0
      ? {}
      : {
          server: "TW",
          environment_version: "TW-2026-05-25",
          evidence_ids: ["ev113", "ev114", "ev115"],
          claim_ids: [
            "CLM-ARENA-TW-DEF-20260525",
            "CLM-ARENA-TW-COUNTER-20260525-01",
            "CLM-ARENA-TW-COUNTER-20260525-02",
          ],
        };
    return send(response, 200, envelope(matchingCounters, warnings, details));
  }
  const evidenceMatch = url.pathname.match(/^\/api\/v1\/evidence\/(ev\d+)$/);
  if (evidenceMatch && evidenceFixtures.has(evidenceMatch[1])) {
    return send(response, 200, evidenceFixtures.get(evidenceMatch[1]));
  }
  const timelineMatch = url.pathname.match(/^\/api\/v1\/teams\/([^/]+)\/timelines$/);
  if (timelineMatch) {
    const seed = teamSeedsById.get(decodeURIComponent(timelineMatch[1]));
    if (seed) {
      const timeline = timelineForTeam(seed);
      const warnings = timeline.status === "PARTIAL"
        ? ["STRUCTURED_TIMELINE_PARTIAL"]
        : timeline.status === "SOURCE_GAP"
          ? ["STRUCTURED_TIMELINE_SOURCE_GAP"]
          : [];
      return send(response, 200, envelope(timeline, warnings));
    }
  }
  const teamMatch = url.pathname.match(/^\/api\/v1\/teams\/([^/]+)$/);
  if (teamMatch) {
    const seed = teamSeedsById.get(decodeURIComponent(teamMatch[1]));
    if (seed) return send(response, 200, teamDetail(seed));
  }
  const parts = url.pathname.split("/");
  const id = parts.at(-1) ?? "";
  return send(response, 404, { detail: { code: "NOT_FOUND", resource: "fixture", id } });
});

server.listen(port, host);

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
