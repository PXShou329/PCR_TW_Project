import { expect, test } from "@playwright/test";

const teamTwoPath = "/pve/TW_DEEP_FIRE_08_10_20260802/teams/TM-F810-02";
const teamOnePath = "/pve/TW_DEEP_FIRE_08_10_20260802/teams/TM-F810-01";

test("TM-F810-02 逐來源呈現 PARTIAL 操作軸且不合併缺口來源", async ({ page }) => {
  await page.goto(teamTwoPath);

  await expect(page.getByRole("heading", { name: "部分來源已有結構化操作軸" })).toBeVisible();
  await expect(page.getByLabel("操作軸來源涵蓋率")).toContainText(/1\s*\/\s*4 個來源已結構化/);
  await expect(page.getByText(/平台不會跨來源合併/)).toBeVisible();

  const structuredSource = page.locator('[data-source-id="gamewith_fire_8_10"]');
  await expect(structuredSource).toBeVisible();
  await expect(structuredSource.locator(".timeline-step")).toHaveCount(14);
  await expect(structuredSource.getByText("尚未在台服逐步重現", { exact: true })).toBeVisible();
  await expect(structuredSource.getByText("來源未載", { exact: true }).first()).toBeVisible();

  const openingStep = structuredSource.locator('[data-step-id="TLS-F810-02-001"]');
  await expect(openingStep).toContainText("時間未確認");
  await expect(openingStep).not.toContainText("1:30");
  await expect(openingStep).toContainText("露易絲瑪莉");

  const timedStep = structuredSource.locator('[data-step-id="TLS-F810-02-005"]');
  await expect(timedStep).toContainText("倒數 1:10");
  await expect(timedStep).toContainText("烏爾姆 UB 結束後");
  await expect(timedStep).toContainText("開啟 SET");

  const gapSource = page.locator('[data-source-id="yt_F39PkRIg0T4"]');
  await expect(gapSource).toContainText("尚未建立可驗證步驟");
  await expect(gapSource.locator(".timeline-step")).toHaveCount(0);
  await expect(gapSource).not.toContainText("倒數 1:10");

  const stepEvidenceButton = structuredSource.getByRole("button", { name: /核對本步 Evidence/ }).first();
  await stepEvidenceButton.click();
  const drawer = page.getByRole("dialog", { name: "ev073" });
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("GameWith 深域クエスト「火8-10」攻略");
  await expect(drawer).toContainText("尚未逐步於台服重現");
  await expect(drawer.getByText("本次核對定位：2025年9月魔法半自動／手順1")).toBeVisible();
  await expect(drawer.getByRole("button", { name: "關閉" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  expect(await page.evaluate(() => {
    const dialog = document.querySelector('[role="dialog"]');
    return Boolean(dialog?.contains(document.activeElement));
  })).toBe(true);
  await page.keyboard.press("Escape");
  await expect(drawer).not.toBeVisible();
  await expect(stepEvidenceButton).toBeFocused();

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("TM-F810-01 純 SOURCE_GAP 保留三個來源且不生成步驟", async ({ page }) => {
  await page.goto(teamOnePath);

  await expect(page.getByRole("heading", { name: "尚未建立可驗證的結構化操作軸" })).toBeVisible();
  await expect(page.getByLabel("操作軸來源涵蓋率")).toContainText(/0\s*\/\s*3 個來源已結構化/);
  await expect(page.locator(".timeline-source--gap")).toHaveCount(3);
  await expect(page.locator(".timeline-step")).toHaveCount(0);
  await expect(page.locator('[data-source-id="appmatch_fire_guide"]')).toContainText("全自動聲明");
  await expect(page.locator('[data-source-id="yt_jkPXr3aUZZQ"]')).toContainText("半自動");
  await expect(page.locator('[data-source-id="yt_tYwLvHHbKXo"]')).toContainText("半自動");

  await page.locator('[data-source-id="appmatch_fire_guide"]')
    .getByRole("button", { name: /查看缺口來源 Evidence/ })
    .click();
  const gapDrawer = page.getByRole("dialog", { name: "ev050" });
  await expect(gapDrawer).toContainText("スマホゲームNavi 紅焔の深域完全攻略");
  await expect(gapDrawer.getByText("本次核對定位：appmatch_fire_deep_guide")).toBeVisible();
  await gapDrawer.getByRole("button", { name: "關閉" }).click();

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
