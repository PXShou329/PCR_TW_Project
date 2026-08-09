import { defineConfig, devices, type PlaywrightTestConfig } from "@playwright/test";

const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL?.trim() || undefined;
// Keep mock-backed E2E isolated from the real Compose web port used by local
// deployment smoke tests, so reuseExistingServer cannot silently test a stale image.
const localBaseUrl = "http://127.0.0.1:3101";

const localWebServers: PlaywrightTestConfig["webServer"] = [
  {
    command: "node tests/e2e/mock-api.mjs",
    url: "http://127.0.0.1:4100/health/live",
    reuseExistingServer: false,
    timeout: 30_000,
  },
  {
    command: "npm run dev --workspace @pcr-tw/web -- --hostname 127.0.0.1 --port 3101",
    url: localBaseUrl,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      API_BASE_URL: "http://127.0.0.1:4100",
    },
  },
];

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: externalBaseUrl ?? localBaseUrl,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: externalBaseUrl ? undefined : localWebServers,
  projects: [
    {
      name: "desktop-chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "mobile-chromium",
      use: { ...devices["Pixel 7"] },
    },
  ],
});
