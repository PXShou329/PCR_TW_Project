import { expect, test } from "@playwright/test";

test("首頁如實顯示紅焰 8-10 的 VERIFIED 5/5", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: /找得到證據的攻略/ })).toBeVisible();
  const stageCard = page.locator(".stage-card").filter({ hasText: "8-10" });
  await expect(stageCard).toContainText("已驗證通關");
  await expect(stageCard).toContainText("5/5");
  await expect(page.getByText("research_core_file_ssot")).toBeVisible();
  await expect(page.locator(".baseline-card dl")).toContainText(/Evidence\s*34/);
  await expect(page.locator(".baseline-card dl")).toContainText(/Claims\s*27/);
  await expect(page.locator(".baseline-card dl")).toContainText(/來源軸\s*10/);
  await expect(page.locator(".baseline-card dl")).toContainText(/操作步驟\s*19/);
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

test("首頁第二關卡可進入且誠實顯示 0/5 研究缺口", async ({ page }) => {
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

test("PVP Registry 為空時顯示 no-result 而非虛構隊伍", async ({ page }) => {
  await page.goto("/pvp");

  await expect(page.getByRole("heading", { name: "競技場解陣" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "目前沒有可公開的實證反制" })).toBeVisible();
  await expect(page.getByText("NO_VERIFIED_COUNTER", { exact: true })).toBeVisible();
  await expect(page.getByText("0 筆正式案例", { exact: true })).toBeVisible();
});
