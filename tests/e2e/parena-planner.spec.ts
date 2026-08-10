import { expect, test } from "@playwright/test";

async function selectFifteen(page: import("@playwright/test").Page) {
  const selects = page.locator(".parena-team select");
  await expect(selects).toHaveCount(15);
  for (let index = 0; index < 15; index += 1) {
    await selects.nth(index).selectOption({ index: index + 1 });
  }
}

const realStack = Boolean(process.env.PLAYWRIGHT_BASE_URL?.trim());

if (realStack) {
  test("P-Arena 真實零案例保持 NO_MATURE 且不可送出", async ({ page }) => {
    await page.goto("/parena");

    await expect(page.getByRole("heading", { name: "公主競技場三隊規劃" })).toBeVisible();
    const environment = page.locator(".parena-environment select");
    await expect(environment).toHaveValue("");
    await expect(environment.locator("option")).toHaveCount(1);
    await expect(environment.locator("option")).toHaveText("目前沒有 mature 環境");
    await expect(page.getByText("NO_MATURE_PARENA_CASE", { exact: true })).toBeVisible();
    await expect(page.getByText("目前 typed materialization 中沒有成熟 P-Arena case。")).toBeVisible();

    await selectFifteen(page);
    await expect(page.getByText("15/15 已選擇；15/15 不重複。")).toBeVisible();
    await expect(page.getByRole("button", { name: "查詢三隊 exact 解法" })).toBeDisabled();
    await expect(page.locator(".parena-matchups .arena-counter-card")).toHaveCount(0);
    await expect(page.getByText("推測功能未啟用")).toBeVisible();
  });
} else {
  test("P-Arena 3×5 exact planner 顯示三場與 Evidence", async ({ page }) => {
    await page.goto("/parena");

    await expect(page.getByRole("heading", { name: "公主競技場三隊規劃" })).toBeVisible();
    await expect(page.getByText("推測功能未啟用")).toBeVisible();
    await selectFifteen(page);
    await expect(page.getByText("15/15 已選擇；15/15 不重複。")).toBeVisible();

    await page.getByRole("button", { name: "查詢三隊 exact 解法" }).click();

    await expect(page.getByText("TEST-PARENA-001", { exact: false })).toBeVisible();
    await expect(page.locator(".parena-matchups .arena-counter-card")).toHaveCount(3);
    await expect(page.getByText("EXACT WIN")).toHaveCount(3);
    await expect(page.getByText("SINGLE_REPORT", { exact: true })).toBeVisible();
    await expect(page.getByText("BLOCKS GATE C", { exact: true })).toBeVisible();
    await expect(page.getByText("CASE_WIN_CONFIDENCE_D_BLOCKS_GATE_C", { exact: true })).toBeVisible();
    await expect(page.getByText("SIMILAR / HIDDEN")).toBeVisible();
    const evidenceButton = page.getByRole("button", { name: /開啟本場 Evidence/ }).first();
    await evidenceButton.click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByRole("dialog")).toContainText("巴哈姆特");
    await expect(page.getByRole("dialog")).toContainText(
      "47_PRINCESS_ARENA_CASE_REGISTRY.csv#TEST-PARENA-001",
    );
    await page.getByRole("dialog").getByRole("button", { name: "關閉" }).click();

    const firstUnit = page.locator(".parena-team select").first();
    const originalFirstUnit = await firstUnit.inputValue();
    await firstUnit.selectOption({ index: 16 });
    await expect(page.getByText("TEST-PARENA-001", { exact: false })).toHaveCount(0);
    await expect(page.locator(".parena-matchups .arena-counter-card")).toHaveCount(0);
    await expect(page.getByText("CASE_WIN_CONFIDENCE_D_BLOCKS_GATE_C", { exact: true })).toHaveCount(0);

    await firstUnit.selectOption(originalFirstUnit);
    await page.getByRole("button", { name: "查詢三隊 exact 解法" }).click();
    await expect(page.getByText("TEST-PARENA-001", { exact: false })).toBeVisible();
    await page.locator(".parena-environment select").selectOption("TW-MOCK-NO-EXACT");
    await expect(page.getByText("TEST-PARENA-001", { exact: false })).toHaveCount(0);
    await expect(page.locator(".parena-matchups .arena-counter-card")).toHaveCount(0);
    await expect(page.getByText("CASE_WIN_CONFIDENCE_D_BLOCKS_GATE_C", { exact: true })).toHaveCount(0);
  });

  test("P-Arena exact miss 誠實顯示空結果且不回退 Similar", async ({ page }) => {
    await page.goto("/parena");
    await page.locator(".parena-environment select").selectOption("TW-MOCK-NO-EXACT");
    await selectFifteen(page);

    await page.getByRole("button", { name: "查詢三隊 exact 解法" }).click();

    await expect(page.getByRole("heading", { name: "目前沒有可呈現的三隊實證解法" })).toBeVisible();
    await expect(page.getByText("NO_EXACT_PARENA_PLAN", { exact: true })).toBeVisible();
    await expect(page.locator(".parena-matchups .arena-counter-card")).toHaveCount(0);
    await expect(page.getByText("推測功能未啟用")).toBeVisible();
  });
}
