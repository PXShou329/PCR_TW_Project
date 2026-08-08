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
    timeline_ref: "yt_jkPXr3aUZZQ@00:45-05:50;yt_tYwLvHHbKXo@00:00-05:05",
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
    timeline_ref: "yt_F39PkRIg0T4@02:34-05:27;yt_OtiJrk3jacg@00:58-04:37;yt_i4pE3GxTMMA@04:11-07:18",
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
    timeline_ref: "yt_ZXUDJm_AsSA@00:12-03:15",
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
  counts: { stages: 1, teams: 3, team_members: 15, characters: 8, evidence: 18, claims: 13 },
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
    timeline: { status: "SOURCE_GAP", references: splitTimeline(seed.timeline_ref), steps: [] },
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
  if (url.pathname === "/api/v1/evidence/ev052") return send(response, 200, evidence052);
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
