import { expect, test } from "@playwright/test";

test("首頁如實顯示紅焰 8-10 的 VERIFIED 5/5", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: /找得到證據的攻略/ })).toBeVisible();
  const stageCard = page.locator(".stage-card")
    .filter({ hasText: "紅焰深域" })
    .filter({ hasText: "8-10" });
  await expect(stageCard).toContainText("已驗證通關");
  await expect(stageCard).toContainText("5/5");
  await expect(page.getByText("research_core_file_ssot")).toBeVisible();
  await expect(page.locator(".baseline-card dl")).toContainText(/Evidence\s*64/);
  await expect(page.locator(".baseline-card dl")).toContainText(/Claims\s*62/);
  await expect(page.locator(".baseline-card dl")).toContainText(/來源軸\s*15/);
  await expect(page.locator(".baseline-card dl")).toContainText(/操作步驟\s*37/);
  await expect(page.getByRole("link", { name: "查看紅焰深域 8-10" })).toBeVisible();

  await stageCard.click();
  await expect(page).toHaveURL(/\/pve\/TW_DEEP_FIRE_08_10_20260802$/);
});

test("關卡到隊伍再到 Evidence Drawer 的完整路徑", async ({ page }) => {
  await page.goto("/pve/TW_DEEP_FIRE_08_10_20260802");

  await expect(page.getByRole("heading", { name: "紅焰深域 8-10" })).toBeVisible();
  await expect(page.getByText("已達 5 支不同五人實證隊伍的成熟結構門檻。")).toBeVisible();
  await expect(page.getByRole("heading", { name: "已確認 5 隊，達成成熟結構門檻" })).toBeVisible();
  for (const teamId of ["TM-F810-01", "TM-F810-02", "TM-F810-03", "TM-F810-04", "TM-F810-05"]) {
    await expect(page.getByText(teamId, { exact: true })).toBeVisible();
  }

  await page.getByRole("link", { name: /查看條件與 Evidence/ }).first().click();
  await expect(page).toHaveURL(/\/teams\/TM-F810-01$/);
  await expect(page.getByRole("heading", { name: /AUTO／SEMI_AUTO 聲明互相衝突/ })).toBeVisible();
  await expect(page.getByText("未確認", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "尚未建立可驗證的結構化操作軸" })).toBeVisible();

  await page.getByRole("button", { name: "ev052", exact: true }).click();
  const drawer = page.getByRole("dialog", { name: "ev052" });
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("YouTube 深域クエスト火8-10攻略編成動画");
  await expect(drawer).toContainText("逐 slot 強化條件仍 UNKNOWN");
  await drawer.getByRole("button", { name: "關閉" }).click();
  await expect(drawer).toBeHidden();
});

test("蒼波 8-10 從關卡、五隊到手動軸 Evidence Drawer 的完整路徑", async ({ page }) => {
  await page.goto("/");

  const stageCard = page.locator(".stage-card")
    .filter({ hasText: "蒼波深域" })
    .filter({ hasText: "8-10" });
  await expect(stageCard).toContainText("已驗證通關");
  await expect(stageCard).toContainText("5/5");
  await stageCard.click();

  await expect(page).toHaveURL(/\/pve\/TW_DEEP_WATER_08_10_20260808$/);
  await expect(page.getByRole("heading", { name: "蒼波深域 8-10" })).toBeVisible();
  await expect(page.getByText("已達 5 支不同五人實證隊伍的成熟結構門檻。")).toBeVisible();

  const expectedTeams = [
    ["TM-W810-01", "手動操作軸"],
    ["TM-W810-02", "半自動"],
    ["TM-W810-03", "全自動"],
    ["TM-W810-04", "全自動"],
    ["TM-W810-05", "全自動"],
  ] as const;
  for (const [teamId, mode] of expectedTeams) {
    const teamCard = page.locator(".team-card").filter({ hasText: teamId });
    await expect(teamCard.getByText(teamId, { exact: true })).toBeVisible();
    await expect(teamCard.getByRole("heading", { name: mode, exact: true })).toBeVisible();
  }

  const manualTeam = page.locator(".team-card").filter({ hasText: "TM-W810-01" });
  await manualTeam.getByRole("link", { name: /查看條件與 Evidence/ }).click();

  await expect(page).toHaveURL(/\/pve\/TW_DEEP_WATER_08_10_20260808\/teams\/TM-W810-01$/);
  await expect(page.getByRole("heading", { name: "蒼波8-10 · 手動操作軸" })).toBeVisible();
  await expect(page.locator(".roster").getByText("借角未確認", { exact: true })).toHaveCount(5);
  await expect(page.getByRole("heading", { name: "已取得逐來源結構化操作軸" })).toBeVisible();
  await expect(page.getByLabel("操作軸來源涵蓋率")).toContainText(/1\s*\/\s*1 個來源已結構化/);

  const source = page.locator('[data-source-id="yt_w3My0QHcoTA"]');
  await expect(source).toContainText("本影片世界線B（0:41 Boss UB）");
  await expect(source.locator(".timeline-step")).toHaveCount(9);
  const criticalStep = source.locator('[data-step-id="TLS-W810-01-003"]');
  await expect(criticalStep).toContainText("倒數 0:59");
  await expect(criticalStep).toContainText("施放 UB");
  await expect(criticalStep).toContainText("愛梅斯1技為美空充TP後最速");

  const sourceEvidenceButton = source.getByRole("button", { name: "查看此來源 Evidence" });
  await sourceEvidenceButton.click();
  const drawer = page.getByRole("dialog", { name: "ev084" });
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("YouTube 蒼波 8-10 五隊實戰－第1隊美空七七香");
  await expect(drawer).toContainText("yt_w3My0QHcoTA@00:13-02:13");
  await expect(drawer).toContainText("單一台服玩家一次成功");
  await drawer.getByRole("button", { name: "關閉" }).click();

  for (const [teamId, mode, stepCount] of [
    ["TM-W810-02", "半自動", 6],
    ["TM-W810-03", "全自動", 1],
    ["TM-W810-04", "全自動", 1],
    ["TM-W810-05", "全自動", 1],
  ] as const) {
    await page.goto(`/pve/TW_DEEP_WATER_08_10_20260808/teams/${teamId}`);
    await expect(page.getByRole("heading", { name: `蒼波8-10 · ${mode}` })).toBeVisible();
    await expect(page.getByRole("heading", { name: "已取得逐來源結構化操作軸" })).toBeVisible();
    await expect(page.locator('[data-source-id="yt_w3My0QHcoTA"] .timeline-step')).toHaveCount(stepCount);
  }

  for (const evidenceId of [
    "ev084", "ev085", "ev086", "ev087", "ev088", "ev091", "ev092", "ev093", "ev094", "ev095", "ev096",
    "ev097", "ev098", "ev099", "ev100", "ev101", "ev102", "ev103", "ev104", "ev105", "ev106",
  ]) {
    const response = await page.request.get(`/api/v1/evidence/${evidenceId}`);
    expect(response.ok()).toBe(true);
    expect((await response.json()).data.evidence_id).toBe(evidenceId);
  }
  for (const rejectedEvidenceId of ["ev089", "ev090"]) {
    expect((await page.request.get(`/api/v1/evidence/${rejectedEvidenceId}`)).status()).toBe(404);
  }

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("首頁紅焰 10-10 可進入且誠實顯示 0/5 研究缺口", async ({ page }) => {
  await page.goto("/");

  const stageCard = page.locator(".stage-card").filter({ hasText: "10-10" });
  await expect(stageCard).toContainText("研究中");
  await expect(stageCard).toContainText("0/5");
  await stageCard.click();

  await expect(page).toHaveURL(/\/pve\/TW_DEEP_FIRE_10_10_20260802$/);
  await expect(page.getByRole("heading", { name: "紅焰深域 10-10" })).toBeVisible();
  await expect(page.getByText("距成熟門檻仍差 5 隊，因此本關仍是「研究中」狀態。")).toBeVisible();
  await expect(page.getByRole("heading", { name: "已確認 0 隊，不等於成熟攻略" })).toBeVisible();
  await expect(page.getByText("目前沒有符合完整五人、明確關卡與實際通關證據的有效隊伍。")).toBeVisible();

  for (const evidenceId of ["ev029", "ev054", "ev055"]) {
    const response = await page.request.get(`/api/v1/evidence/${evidenceId}`);
    expect(response.ok()).toBe(true);
    expect((await response.json()).data.evidence_id).toBe(evidenceId);
  }
});

test("隊伍頁拒絕與 guide_id 不符的路徑", async ({ page }) => {
  await page.goto("/pve/NOT_THE_TEAM_GUIDE/teams/TM-F810-01");

  await expect(page.getByRole("heading", { name: "找不到這筆攻略資料" })).toBeVisible();
  await expect(page.getByText("平台不會自動建立不存在的隊伍或 Evidence")).toBeVisible();
});

test("PVP 顯示 exact 單筆戰果且完整揭露限制與 Evidence", async ({ page }) => {
  await page.goto("/pvp");

  await expect(page.getByRole("heading", { name: "競技場精確解陣" })).toBeVisible();
  await expect(page.getByText("NO_VERIFIED_COUNTER", { exact: true })).toBeVisible();
  await expect(page.getByText("SINGLE_REPORT_REFERENCE_ONLY", { exact: true })).toBeVisible();
  await expect(page.getByText("目前沒有 VERIFIED counter；現有資料不會被提升為成熟結論。", { exact: true })).toBeVisible();
  await expect(page.getByText("目前顯示的案例只有單筆來源戰果，僅供參考且不代表可重現性。", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "精確防守五人" })).toBeVisible();
  await expect(page.getByRole("list", { name: "精確防守五人" }).getByRole("listitem")).toHaveCount(5);
  await expect(page.getByRole("list", { name: "精確防守五人" }).getByText("台服官方名", { exact: true })).toHaveCount(5);

  for (const counterId of ["TW_ARENA_20260525_01", "TW_ARENA_20260525_02"]) {
    const card = page.locator(".arena-counter-card").filter({ hasText: counterId });
    await expect(card.getByText("【僅供參考】", { exact: true })).toBeVisible();
    await expect(card.getByText("SINGLE_REPORT", { exact: true })).toBeVisible();
    await expect(card.getByText("Confidence D", { exact: true })).toBeVisible();
    await expect(card.getByText("TW Availability PASS", { exact: true })).toBeVisible();
    await expect(card.getByRole("listitem")).toHaveCount(5);
    await expect(card.getByText("台服官方名", { exact: true })).toHaveCount(5);
  }

  await expect(page.getByRole("heading", { name: "Similar 未啟用" })).toBeVisible();

  const firstCounter = page.locator(".arena-counter-card").filter({ hasText: "TW_ARENA_20260525_01" });
  for (const [term, value] of [
    ["台服可用性", "PASS"],
    ["不可用角色", "無"],
    ["來源等級", "SINGLE_PLAYER_REPORT"],
    ["來源平台", "巴哈姆特"],
    ["結果證據", "SCREENSHOT_RESULT"],
    ["實測勝率", "樣本不足，未計算"],
    ["RNG 風險", "UNKNOWN"],
    ["速度條件", "UNKNOWN"],
    ["初動備註", "UNKNOWN"],
    ["強化條件檢查", "UNKNOWN"],
    ["資料核對日", "2026-08-08"],
    ["下次複核", "2026-08-23"],
  ]) {
    await expect(firstCounter.locator(".definition").filter({ hasText: term })).toContainText(value);
  }
  await firstCounter.getByRole("button").filter({ hasText: "ev114" }).click();
  const drawer = page.getByRole("dialog", { name: "ev114" });
  await expect(drawer.getByText("巴哈姆特回覆 B1 台服競技場勝利戰果", { exact: true })).toBeVisible();
  await expect(drawer.getByText("單一作者單次截圖；只證明一次 exact composition 勝利，不代表穩定率或多次重現；戰果未載版本與練度", { exact: true })).toBeVisible();
  await expect(drawer.getByText("Evidence 登錄定位：B1 憂姫 2026-05-25 10:41:38＋原圖 https://truth.bahamut.com.tw/s01/202605/forum/30861/acb01f479fdbfae7011c6eb730769599.JPG", { exact: true })).toBeVisible();
});
