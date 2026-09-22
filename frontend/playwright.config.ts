import { defineConfig, devices } from "@playwright/test";

const port = 3100;
const apiPort = 8765;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: `http://localhost:${port}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{
    name: "chromium",
    use: {
      ...devices["Desktop Chrome"],
      launchOptions: process.env.E2E_CHROMIUM_PATH
        ? { executablePath: process.env.E2E_CHROMIUM_PATH }
        : undefined,
    },
  }],
  webServer: [
    {
      command: "node e2e/mock-api.mjs",
      url: `http://localhost:${apiPort}/health`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: `mkdir -p .next/standalone/.next/static && cp -R .next/static/. .next/standalone/.next/static/ && PORT=${port} HOSTNAME=localhost node .next/standalone/server.js`,
      url: `http://localhost:${port}/login`,
      env: {
        API_BASE_URL: `http://localhost:${apiPort}/api/v1`,
        NEXT_PUBLIC_API_BASE_URL: `http://localhost:${apiPort}/api/v1`,
      },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
