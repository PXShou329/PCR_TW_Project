import { expect, test } from "@playwright/test";

test("私人 DOCX 未來視與 canonical timeline 分區呈現", async ({ page }, testInfo) => {
  await page.goto("/gacha");

  const section = page.locator(".private-gacha-section");
  await expect(section).toHaveAttribute("data-load-state", "ready");
  await expect(section.getByRole("heading", { name: "私人文件預測／非官方" })).toBeVisible();
  await expect(section.getByText("私人文件預測", { exact: true })).toBeVisible();
  await expect(section.getByText("非官方", { exact: true }).first()).toBeVisible();
  await expect(section.getByText("17 池", { exact: true })).toBeVisible();
  await expect(section.getByText("文件中的中文名稱尚未等同台服官方角色名稱", { exact: false })).toBeVisible();
  await expect(section.getByText("圖片上的日版日期不會當成台服日期", { exact: false })).toBeVisible();

  const cards = section.locator(".private-gacha-card");
  await expect(cards).toHaveCount(17);
  await expect(cards.locator(".private-gacha-names li")).toHaveCount(39);
  await expect(cards.locator('img[src^="/api/v1/gacha-library/assets/"]')).toHaveCount(17);
  await expect(cards.filter({ hasText: "復刻池" })).toHaveCount(6);
  await expect(cards.filter({ hasText: "常駐角色" })).toHaveCount(1);
  await expect(cards.filter({ hasText: "限定 UP" })).toHaveCount(10);

  const shefi = cards.filter({ hasText: "雪菲（瓦德拉赫）" });
  await expect(shefi.getByText("2026-10-31 – 2026-11-03", { exact: true })).toBeVisible();
  await expect(shefi.getByText("文件原始名稱 · 尚未確認為台服官方名稱", { exact: true })).toBeVisible();

  const unquoted = cards.nth(12);
  await expect(unquoted.getByText("UNQUOTED_CHARACTER_SEQUENCE", { exact: true })).toBeVisible();
  await expect(unquoted.getByText("原文含未加引號的角色序列", { exact: false })).toBeVisible();
  await expect(unquoted.locator(".private-gacha-names li")).toHaveCount(8);

  const finalCard = cards.nth(16);
  await expect(finalCard.getByText("第144次", { exact: true })).toBeVisible();
  await expect(finalCard.getByText("克蕾琪塔（夏日）", { exact: true })).toBeVisible();
  await expect(finalCard.getByText("2026-11-15 – 2026-12-01", { exact: true })).toBeVisible();

  // The pre-existing public materialization remains present and independent.
  await expect(page.locator(".gacha-card")).toHaveCount(5);
  await expect(page.getByRole("heading", { name: "日服事件與台服模型區間" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "社群未來視來源狀態" })).toBeVisible();

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  if (testInfo.project.name === "mobile-chromium") {
    const sectionBox = await section.boundingBox();
    expect(sectionBox?.x ?? -1).toBeGreaterThanOrEqual(0);
    expect((sectionBox?.x ?? 0) + (sectionBox?.width ?? Number.POSITIVE_INFINITY)).toBeLessThanOrEqual(
      await page.evaluate(() => window.innerWidth),
    );
  }
});

test("私人卡池圖片 404 時保留文字資料", async ({ page }) => {
  const missingSha = "7".repeat(64);
  await page.route("**/api/v1/gacha-library/forecasts", async (route) => {
    const response = await route.fetch();
    const payload = await response.json();
    payload.data.items[0].image.sha256 = missingSha;
    payload.data.items[0].image.asset_url = `/api/v1/gacha-library/assets/${missingSha}`;
    await route.fulfill({ response, json: payload });
  });
  await page.goto("/gacha");

  const section = page.locator(".private-gacha-section");
  await expect(section).toHaveAttribute("data-load-state", "ready");
  const firstCard = section.locator(".private-gacha-card").first();
  await expect(firstCard.locator('.private-gacha-card__media[data-image-state="failed"]')).toBeVisible();
  await expect(firstCard.getByText("來源圖片不可用", { exact: true })).toBeVisible();
  await expect(firstCard.getByText("本機圖片載入失敗", { exact: true })).toBeVisible();
  await expect(firstCard.getByText("步未(怪盜)", { exact: true })).toBeVisible();
  await expect(firstCard.getByText("2026-08-01 – 2026-08-16", { exact: true })).toBeVisible();
});

test("私人 API 503 時 canonical timeline 仍保留", async ({ page }) => {
  await page.route("**/api/v1/gacha-library/forecasts", (route) => route.fulfill({
    body: JSON.stringify({
      error: { code: "GACHA_LIBRARY_UNAVAILABLE", message: "Fixture unavailable." },
    }),
    contentType: "application/json",
    status: 503,
  }));

  await page.goto("/gacha");

  const section = page.locator(".private-gacha-section");
  await expect(section).toHaveAttribute("data-load-state", "error");
  await expect(section.getByRole("heading", { name: "私人文件預測暫時無法取得" })).toBeVisible();
  await expect(section.getByText("公共 canonical timeline 仍可使用", { exact: false })).toBeVisible();
  await expect(page.locator(".gacha-card")).toHaveCount(5);
  await expect(page.getByRole("heading", { name: "日服事件與台服模型區間" })).toBeVisible();
});

test("canonical API 503 時私人 DOCX 17 池仍保留 @canonical-api-unavailable", async ({ page }) => {
  await page.goto("/gacha");

  const privateSection = page.locator(".private-gacha-section");
  await expect(privateSection).toHaveAttribute("data-load-state", "ready");
  await expect(privateSection.getByText("17 池", { exact: true })).toBeVisible();
  await expect(privateSection.locator(".private-gacha-card")).toHaveCount(17);

  const canonicalUnavailable = page.getByRole("heading", {
    name: "公共時間線目前無法取得",
  });
  await expect(canonicalUnavailable).toBeVisible();
  await expect(privateSection.getByRole("heading", {
    name: "公共時間線目前無法取得",
  })).toHaveCount(0);
  await expect(page.getByRole("heading", {
    name: "目前無法取得攻略資料",
  })).toHaveCount(0);
  await expect(page.locator(".gacha-card")).toHaveCount(0);
});

test("私人卡池拒絕非 same-origin 圖片路徑", async ({ page }) => {
  let externalImageRequested = false;
  await page.route("https://example.invalid/**", (route) => {
    externalImageRequested = true;
    return route.abort("blockedbyclient");
  });
  await page.route("**/api/v1/gacha-library/forecasts", async (route) => {
    const response = await route.fetch();
    const payload = await response.json();
    payload.data.items[0].image.asset_url = "https://example.invalid/untrusted.jpg";
    await route.fulfill({ response, json: payload });
  });

  await page.goto("/gacha");

  const firstCard = page.locator(".private-gacha-card").first();
  await expect(firstCard.locator('.private-gacha-card__media[data-image-state="rejected"]')).toBeVisible();
  await expect(firstCard.getByText("已拒絕非 same-origin 圖片路徑", { exact: true })).toBeVisible();
  await expect(firstCard.getByText("步未(怪盜)", { exact: true })).toBeVisible();
  expect(externalImageRequested).toBe(false);
});

test("Gacha asset proxy 拒絕 redirect、SVG 與非 JSON error", async ({ page }) => {
  const redirectResponse = await page.request.get(
    `/api/v1/gacha-library/assets/${"8".repeat(64)}`,
  );
  expect(redirectResponse.status()).toBe(502);
  expect((await redirectResponse.json()).error.code).toBe("UPSTREAM_REDIRECT_REJECTED");

  const svgResponse = await page.request.get(
    `/api/v1/gacha-library/assets/${"9".repeat(64)}`,
  );
  expect(svgResponse.status()).toBe(502);
  expect(svgResponse.headers()["content-type"]).toContain("application/json");
  expect((await svgResponse.json()).error.code).toBe("INVALID_GACHA_LIBRARY_RESPONSE");

  const htmlErrorResponse = await page.request.get(
    `/api/v1/gacha-library/assets/${"a".repeat(64)}`,
  );
  expect(htmlErrorResponse.status()).toBe(502);
  expect(htmlErrorResponse.headers()["content-type"]).toContain("application/json");
  expect((await htmlErrorResponse.json()).error.code).toBe(
    "INVALID_GACHA_LIBRARY_ERROR_RESPONSE",
  );
  expect(await htmlErrorResponse.text()).not.toContain("fixture not found");
});
