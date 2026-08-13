import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

const usesRealCatalog = Boolean(process.env.PLAYWRIGHT_BASE_URL?.trim());
const estertionFixtureUrl = "https://redive.estertion.win/icon/unit/100161.webp";
const onePixelPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

if (!usesRealCatalog) {
test("舊 PVE 網址依模式導向新的獨立頁面", async ({ page }) => {
  await page.goto("/pve");
  await expect(page).toHaveURL(/\/pve\/deep\?element=FIRE&area=1&stage=1$/);

  await page.goto("/pve?mode=REMEMBRANCE&element=DARK&area=1&stage=5");
  await expect(page).toHaveURL(/\/pve\/remembrance\?element=DARK$/);

  await page.goto("/pve?mode=LUNA_TOWER&element=NONE");
  await expect(page).toHaveURL(/\/pve\/luna-tower$/);
});

test("深域只使用 catalog 選單且篩選網址可分享", async ({ page }) => {
  await page.goto("/pve/deep");

  await expect(page).toHaveURL(/\/pve\/deep\?element=FIRE&area=1&stage=1$/);
  await expect(page.getByRole("heading", { name: "深域關卡攻略" })).toBeVisible();
  await expect(page.getByText("Excel 來源整理", { exact: true })).toBeVisible();
  await expect(page.getByText("未獨立驗證通關", { exact: false })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "PVE 攻略分類" }).getByRole("link", { name: /深域/ }))
    .toHaveAttribute("aria-current", "page");
  const deepFilters = page.locator(".pve-library-filters");
  await expect(deepFilters.getByLabel("屬性", { exact: true })).toHaveValue("FIRE");
  await expect(deepFilters.getByLabel("深域區域", { exact: true })).toHaveValue("1");
  await expect(deepFilters.getByLabel("關卡", { exact: true })).toHaveValue("1");
  await expect(page.locator('.pve-library-filters input[type="number"]')).toHaveCount(0);

  const areaValues = await deepFilters.getByLabel("深域區域", { exact: true }).locator("option:not([disabled])").evaluateAll(
    (options) => options.map((option) => (option as HTMLOptionElement).value),
  );
  const stageValues = await deepFilters.getByLabel("關卡", { exact: true }).locator("option:not([disabled])").evaluateAll(
    (options) => options.map((option) => (option as HTMLOptionElement).value),
  );
  expect(areaValues).toEqual(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]);
  expect(stageValues).toEqual(areaValues);

  const initialCard = page.locator(".pve-library-card");
  await expect(initialCard).toHaveCount(1);
  await expect(initialCard).toContainText("紅焰深域 1-1");
  await expect(page.getByText("追憶戰域 阿剌克涅 1–5層")).toHaveCount(0);
  await expect(page.getByText("露娜塔頂層 EX")).toHaveCount(0);

  await deepFilters.getByLabel("深域區域", { exact: true }).selectOption("1");
  await deepFilters.getByLabel("關卡", { exact: true }).selectOption("2");
  await page.getByRole("button", { name: "查看這一關" }).click();
  await expect(page).toHaveURL(/\/pve\/deep\?element=FIRE&area=1&stage=2$/);
  const deepCard = page.locator(".pve-library-card").filter({ hasText: "紅焰深域 1-2" });
  await expect(deepCard).toBeVisible();
  await expect(deepCard).toContainText("收錄 2 隊");
  await expect(page.locator(".pve-library-card")).toHaveCount(1);

  await page.goto("/pve/deep?element=FIRE&area=11&stage=11");
  await expect(page.locator(".pve-library-card")).toHaveCount(0);
  await expect(page.getByText("系統不會推測或建立不存在的關卡", { exact: false })).toBeVisible();
});

test("追憶戰域與露娜塔各自只呈現所屬模式", async ({ page }) => {
  await page.goto("/pve/remembrance");
  await expect(page.getByRole("heading", { name: "追憶戰域攻略" })).toBeVisible();
  await expect(page.getByLabel("戰域首領")).toBeVisible();
  await expect(page.getByLabel("深域區域")).toHaveCount(0);
  await expect(page.getByLabel("關卡")).toHaveCount(0);
  const remembranceCard = page.locator(".pve-library-card");
  await expect(remembranceCard).toHaveCount(1);
  await expect(remembranceCard).toContainText("追憶戰域 阿剌克涅 1–5層");
  await expect(page.getByText("紅焰深域 1-2")).toHaveCount(0);
  await expect(page.getByText("露娜塔頂層 EX")).toHaveCount(0);

  await page.getByLabel("戰域首領").selectOption("DARK");
  await page.getByRole("button", { name: "套用篩選" }).click();
  await expect(page).toHaveURL(/\/pve\/remembrance\?element=DARK$/);
  await expect(remembranceCard).toHaveCount(1);
  await expect(remembranceCard).not.toContainText("逐層驗證");

  await page.getByLabel("戰域首領", { exact: true }).selectOption("");
  await page.getByRole("button", { name: "套用篩選" }).click();
  await expect(page).toHaveURL(/\/pve\/remembrance\?element=$/);
  await expect(remembranceCard).toHaveCount(1);
  await expect(page.getByText("網址中的首領不在目前 Excel 清單內", { exact: false })).toHaveCount(0);

  await page.goto(`/pve/remembrance?element=${"X".repeat(65)}`);
  await expect(page.getByText("網址中的首領不在目前 Excel 清單內", { exact: false })).toBeVisible();
  await expect(page.locator(".pve-library-card")).toHaveCount(0);

  await page.goto("/pve/luna-tower");
  await expect(page.getByRole("heading", { name: "露娜塔攻略" })).toBeVisible();
  await expect(page.locator(".pve-library-filters")).toHaveCount(0);
  const lunaCard = page.locator(".pve-library-card");
  await expect(lunaCard).toHaveCount(1);
  await expect(lunaCard).toContainText("露娜塔頂層 EX");
  await expect(page.getByText("紅焰深域 1-2")).toHaveCount(0);
  await expect(page.getByText("追憶戰域 阿剌克涅 1–5層")).toHaveCount(0);
});

test("三個 PVE 頁面在桌機與手機都不造成頁面水平溢位", async ({ page }, testInfo) => {
  const reviewDirectory = process.env.PVE_UI_REVIEW_DIR?.trim();
  if (reviewDirectory) await mkdir(resolve(reviewDirectory), { recursive: true });
  const routes = [
    { heading: "火屬性 · 區域 1 · 第 2 關", name: "deep", path: "/pve/deep?element=FIRE&area=1&stage=2" },
    { heading: "全部追憶戰域區段", name: "remembrance", path: "/pve/remembrance" },
    { heading: "目前收錄的露娜塔區段", name: "luna-tower", path: "/pve/luna-tower" },
  ];
  for (const route of routes) {
    await page.goto(route.path);
    await expect(page.getByRole("heading", { name: route.heading })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    const shouldCapture = reviewDirectory && (
      testInfo.project.name === "desktop-chromium"
      || (testInfo.project.name === "mobile-chromium" && route.name === "deep")
    );
    if (shouldCapture) {
      const viewport = testInfo.project.name === "mobile-chromium" ? "mobile" : "desktop";
      await page.screenshot({
        fullPage: true,
        path: resolve(reviewDirectory, `pve-${route.name}-${viewport}.png`),
      });
    }
  }
});

test("PVE detail 麵包屑依資料模式返回正確獨立頁", async ({ page }) => {
  await page.goto("/pve/library/pve-deep-fire-1-2");
  await expect(page.getByRole("navigation", { name: "麵包屑" }).getByRole("link", { name: "深域攻略" }))
    .toHaveAttribute("href", "/pve/deep?element=FIRE&area=1&stage=2");

  await page.goto("/pve/library/pve-remembrance-arachne-1-5");
  await expect(page.getByRole("navigation", { name: "麵包屑" }).getByRole("link", { name: "追憶戰域攻略" }))
    .toHaveAttribute("href", "/pve/remembrance?element=DARK");

  await page.goto("/pve/library/pve-luna-top-ex");
  await expect(page.getByRole("navigation", { name: "麵包屑" }).getByRole("link", { name: "露娜塔攻略" }))
    .toHaveAttribute("href", "/pve/luna-tower");
});

test("PVE 關卡以五頭像呈現多軸，O/X 不綁角色且影片點擊後才載入", async ({ page }, testInfo) => {
  await page.route(estertionFixtureUrl, (route) => route.fulfill({
    body: onePixelPng,
    contentType: "image/png",
    status: 200,
  }));
  await page.goto("/pve/library/pve-deep-fire-1-2");

  await expect(page.getByRole("heading", { name: "紅焰深域 1-2" })).toBeVisible();
  await expect(page.getByText("Excel來源整理", { exact: true })).toBeVisible();
  await expect(page.getByText("未獨立驗證通關", { exact: true })).toBeVisible();
  await expect(page.locator(".pve-library-team")).toHaveCount(2);

  const firstTeam = page.locator('[data-team-id="pve-team-fire-1-2-001"]');
  const portraits = firstTeam.locator(".pve-portrait");
  await expect(portraits).toHaveCount(5);
  await expect(portraits.first()).toHaveAttribute("data-image-source", "external");
  await expect(portraits.first().locator("img")).toHaveAttribute("src", estertionFixtureUrl);
  await expect(portraits.first().locator("img")).toHaveAttribute("referrerpolicy", "no-referrer");
  await expect(portraits.nth(1)).toHaveAttribute("data-image-source", "workbook");
  await expect(portraits.nth(1).locator("img")).toHaveAttribute(
    "src",
    `/api/v1/pve-library/assets/${"3".repeat(64)}`,
  );
  await expect(firstTeam.getByRole("list", { name: "隊伍 1 的五位角色" }).getByRole("listitem")).toHaveCount(5);
  await expect(firstTeam.getByAltText("位置 2", { exact: true })).toBeVisible();
  await expect(firstTeam.locator(".pve-axis")).toHaveCount(2);
  await expect(firstTeam.getByText("O／X 只按 Excel 來源文字由左到右呈現", { exact: false })).toHaveCount(2);
  await expect(firstTeam.locator(".pve-portrait [data-state]")).toHaveCount(0);

  const firstPattern = firstTeam.locator(".pve-set-pattern").first();
  await expect(firstPattern).toHaveAttribute("data-member-alignment", "UNRESOLVED");
  await expect(firstPattern).toHaveAttribute("data-order-basis", "WORKBOOK_TEXT_LEFT_TO_RIGHT");
  await expect(firstPattern.locator("li")).toHaveText([
    "O · SET",
    "X · 不SET",
    "O · SET",
    "O · SET",
    "X · 不SET",
  ]);

  const video = firstTeam.locator(".pve-video").first();
  await expect(video.locator("iframe")).toHaveCount(0);
  await video.getByRole("button", { name: /載入 YouTube 影片/ }).click();
  await expect(video.locator("iframe")).toHaveAttribute(
    "src",
    "https://www.youtube-nocookie.com/embed/pveTest1234",
  );

  const assetResponse = await page.request.get(`/api/v1/pve-library/assets/${"1".repeat(64)}`);
  expect(assetResponse.ok()).toBe(true);
  expect(assetResponse.headers()["content-type"]).toContain("image/png");

  const zeroAxisTeam = page.locator('[data-team-id="pve-team-fire-1-2-002"]');
  await expect(zeroAxisTeam.locator(".pve-portrait")).toHaveCount(5);
  await expect(zeroAxisTeam.getByText("NO_OPERATION_AXIS", { exact: true })).toBeVisible();
  await expect(zeroAxisTeam.getByText("Excel 未提供操作軸；不補寫 SET 狀態。", { exact: true })).toBeVisible();

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  if (testInfo.project.name === "mobile-chromium") {
    const boxes = await portraits.evaluateAll((nodes) => nodes.map((node) => node.getBoundingClientRect()));
    expect(new Set(boxes.map((box) => Math.round(box.top))).size).toBe(1);
    expect(boxes.at(-1)?.right ?? Number.POSITIVE_INFINITY).toBeLessThanOrEqual(
      await page.evaluate(() => window.innerWidth),
    );
  }
});

test("EsterTion 頭像載入失敗時退回原始 Excel 頭像", async ({ page }) => {
  await page.route(estertionFixtureUrl, (route) => route.abort("failed"));
  await page.goto("/pve/library/pve-deep-fire-1-2");

  const portrait = page
    .locator('[data-team-id="pve-team-fire-1-2-001"] .pve-portrait')
    .first();
  await portrait.locator("img").scrollIntoViewIfNeeded();
  await portrait.locator("img").evaluate((image) => {
    image.dispatchEvent(new Event("error"));
  });
  await expect(portrait).toHaveAttribute("data-image-source", "workbook");
  await expect(portrait.locator("img")).toHaveAttribute(
    "src",
    `/api/v1/pve-library/assets/${"1".repeat(64)}`,
  );
  await expect(portrait.locator(".pve-portrait__fallback")).toHaveCount(0);
});

test("不存在的本機 PVE 關卡 fail closed", async ({ page }) => {
  await page.goto("/pve/library/not-a-real-stage");
  await expect(page.getByRole("heading", { name: "找不到這筆攻略資料" })).toBeVisible();
});
} else {
  test("真實 Excel catalog 可按屬性與關卡篩選且不冒充通關驗證", async ({ page }) => {
    await page.goto("/pve/deep?element=FIRE&area=8&stage=1");

    await expect(page.getByRole("heading", { name: "深域關卡攻略" })).toBeVisible();
    await expect(page.getByText("Excel 來源整理", { exact: true })).toBeVisible();
    await expect(page.getByText("未獨立驗證通關", { exact: false })).toBeVisible();
    const deepFilters = page.locator(".pve-library-filters");
    await expect(deepFilters.getByLabel("屬性", { exact: true })).toHaveValue("FIRE");
    await expect(deepFilters.getByLabel("深域區域", { exact: true })).toHaveValue("8");
    await expect(deepFilters.getByLabel("關卡", { exact: true })).toHaveValue("1");
    await expect(page.locator('.pve-library-filters input[type="number"]')).toHaveCount(0);

    const cards = page.locator(".pve-library-card");
    await expect(cards).toHaveCount(1);
    await expect(cards.first()).toContainText("深域");
    await expect(cards.first()).toContainText("火");
    await expect(cards.first()).toContainText("8 - 1");
    await expect(cards.first()).toContainText("收錄 22 隊");
  });

  test("真實 PVE 顯示五頭像、原始 O/X、多來源、影片及 reviewed-unknown fallback", async ({ page }, testInfo) => {
    await page.goto("/pve/library/deep%3Afire%3A08-03");

    await expect(page.getByRole("heading", { name: "8 - 3" })).toBeVisible();
    await expect(page.getByText("深域", { exact: true })).toBeVisible();
    await expect(page.getByText("火屬性", { exact: true })).toBeVisible();
    await expect(page.locator(".pve-library-team")).toHaveCount(22);

    const team = page.locator('[data-team-id="deep:fire:08-03:l:028"]');
    const portraits = team.locator(".pve-portrait");
    await expect(portraits).toHaveCount(5);
    await expect(team.locator(".pve-axis")).toHaveCount(1);
    await expect(team.getByText("O／X 只按 Excel 來源文字由左到右呈現", { exact: false })).toBeVisible();
    await expect(team.locator(".pve-portrait [data-state]")).toHaveCount(0);

    const pattern = team.locator(".pve-set-pattern").first();
    await expect(pattern).toHaveAttribute("data-member-alignment", "UNRESOLVED");
    await expect(pattern).toHaveAttribute("data-order-basis", "WORKBOOK_TEXT_LEFT_TO_RIGHT");
    await expect(pattern.locator("li")).toHaveText([
      "X · 不SET",
      "O · SET",
      "X · 不SET",
      "O · SET",
      "O · SET",
    ]);
    await expect(team.getByRole("link", { name: /開啟外部來源/ })).toHaveAttribute(
      "href",
      "https://x.com/bariconneReDive/status/1945293604227891321",
    );

    const video = team.locator(".pve-video");
    await expect(video.locator("iframe")).toHaveCount(0);
    await video.getByRole("button", { name: /載入 YouTube 影片/ }).click();
    await expect(video.locator("iframe")).toHaveAttribute(
      "src",
      "https://www.youtube-nocookie.com/embed/w-HUkuf_Gvc",
    );

    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if (testInfo.project.name === "mobile-chromium") {
      const boxes = await portraits.evaluateAll((nodes) => nodes.map((node) => node.getBoundingClientRect()));
      expect(new Set(boxes.map((box) => Math.round(box.top))).size).toBe(1);
    }

    await page.goto("/pve/library/deep%3Afire%3A10-03");
    const reviewedUnknownTeam = page.locator('[data-team-id="deep:fire:10-03:r:045"]');
    const workbookPortrait = reviewedUnknownTeam
      .locator('.pve-portrait[data-image-source="workbook"]')
      .filter({ has: page.locator('img[src*="1af1491ff99fa75087947056971e3a11dd3ea310dd409991f3e89962d1bc9569"]') })
      .first();
    await expect(workbookPortrait).toBeVisible();
    const assetPath = await workbookPortrait.locator("img").getAttribute("src");
    expect(assetPath).toBe(
      "/api/v1/pve-library/assets/1af1491ff99fa75087947056971e3a11dd3ea310dd409991f3e89962d1bc9569",
    );
    const assetResponse = await page.request.get(assetPath!);
    expect(assetResponse.ok()).toBe(true);
    expect(assetResponse.headers()["content-type"]).toMatch(/^image\/(png|jpeg|gif)/);
  });

  test("真實水 9-2 的 Excel 零操作軸隊伍保留五頭像且不猜 SET", async ({ page }) => {
    await page.goto("/pve/library/deep%3Awater%3A09-02");

    const team = page.locator('[data-team-id="deep:water:09-02:r:016"]');
    await expect(team.locator(".pve-portrait")).toHaveCount(5);
    await expect(team.getByText("NO_OPERATION_AXIS", { exact: true })).toBeVisible();
    await expect(team.getByText("Excel 未提供操作軸；不補寫 SET 狀態。", { exact: true })).toBeVisible();
    await expect(team.locator(".pve-set-pattern")).toHaveCount(0);
  });
}
