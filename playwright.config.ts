import { defineConfig, devices, type PlaywrightTestConfig } from "@playwright/test";

const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL?.trim() || undefined;
const privateLibrariesProvisioned =
  !externalBaseUrl
  || process.env.PLAYWRIGHT_PRIVATE_LIBRARIES_REAL?.trim() === "1";
// Keep mock-backed E2E isolated from the real Compose web port used by local
// deployment smoke tests, so reuseExistingServer cannot silently test a stale image.
const localBaseUrl = "http://127.0.0.1:3101";
const canonicalFailureBaseUrl = "http://127.0.0.1:3102";
const canonicalFailureTag = /@canonical-api-unavailable/;

const localWebServers: PlaywrightTestConfig["webServer"] = [
  {
    command: "node tests/e2e/mock-api.mjs",
    url: "http://127.0.0.1:4400/health/live",
    reuseExistingServer: false,
    timeout: 30_000,
    env: {
      MOCK_API_PORT: "4400",
    },
  },
  {
    command: "npm run dev --workspace @pcr-tw/web -- --hostname 127.0.0.1 --port 3101",
    url: localBaseUrl,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      API_BASE_URL: "http://127.0.0.1:4400",
    },
  },
  {
    command: "node tests/e2e/mock-api.mjs",
    url: "http://127.0.0.1:4401/health/live",
    reuseExistingServer: false,
    timeout: 30_000,
    env: {
      MOCK_API_PORT: "4401",
      MOCK_GACHA_CANONICAL_UNAVAILABLE: "1",
    },
  },
  {
    command: "npm run dev --workspace @pcr-tw/web -- --hostname 127.0.0.1 --port 3102",
    url: canonicalFailureBaseUrl,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      API_BASE_URL: "http://127.0.0.1:4401",
      PCR_E2E_NEXT_DIST_DIR: ".runtime/next-gacha-canonical-unavailable",
    },
  },
];

const standardProjects: PlaywrightTestConfig["projects"] = [
  {
    name: "desktop-chromium",
    grepInvert: canonicalFailureTag,
    use: { ...devices["Desktop Chrome"] },
  },
  {
    name: "mobile-chromium",
    grepInvert: canonicalFailureTag,
    use: { ...devices["Pixel 7"] },
  },
];

const localFailureProjects: PlaywrightTestConfig["projects"] = externalBaseUrl
  ? []
  : [
      {
        name: "gacha-canonical-unavailable",
        grep: canonicalFailureTag,
        use: {
          ...devices["Desktop Chrome"],
          baseURL: canonicalFailureBaseUrl,
        },
      },
    ];

export default defineConfig({
  testDir: "./tests/e2e",
  // Private-library specs use the local mock catalog by default. An external
  // stack must opt in only after provisioning the ignored XLSX/DOCX artifacts.
  testIgnore: privateLibrariesProvisioned ? [] : [/private-libraries/],
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
  projects: [...standardProjects, ...localFailureProjects],
});
