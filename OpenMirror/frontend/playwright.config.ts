import { defineConfig } from "@playwright/test";
import os from "node:os";
import path from "node:path";

// The e2e suite starts its own backend (with a throwaway data directory) and
// a production build of the frontend. Run `npm run build` first.
const dataDir = path.join(os.tmpdir(), `openmirror-e2e-${process.pid}`);

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  use: { baseURL: "http://127.0.0.1:3100", trace: "off" },
  webServer: [
    {
      command: "../backend/.venv/bin/python -m openmirror",
      cwd: "../backend",
      url: "http://127.0.0.1:8100/api/health",
      env: {
        OPENMIRROR_DATA_DIR: dataDir,
        OPENMIRROR_PORT: "8100",
        OPENMIRROR_CORS_ORIGINS: "http://127.0.0.1:3100",
      },
      reuseExistingServer: false,
    },
    {
      command: "npx next start -p 3100 -H 127.0.0.1",
      url: "http://127.0.0.1:3100",
      env: { NEXT_PUBLIC_API_BASE: "http://127.0.0.1:8100", NEXT_DIST_DIR: process.env.NEXT_DIST_DIR ?? ".next-e2e" },
      reuseExistingServer: false,
    },
  ],
});
