import { spawnSync } from "node:child_process";
import { existsSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { prepareAndroidExport } from "./prepare-android-export.mjs";

const root = fileURLToPath(new URL("../", import.meta.url));
const release = process.argv.includes("--release");
const configuredUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
if (release && !configuredUrl) {
  throw new Error("Set NEXT_PUBLIC_API_BASE_URL to your deployed HTTPS FastAPI address before a release export.");
}
const apiBaseUrl = new URL(configuredUrl || "http://10.0.2.2:8000");
if (
  !["http:", "https:"].includes(apiBaseUrl.protocol) ||
  apiBaseUrl.username || apiBaseUrl.password || apiBaseUrl.search || apiBaseUrl.hash ||
  ["localhost", "127.0.0.1", "[::1]"].includes(apiBaseUrl.hostname) ||
  (release && apiBaseUrl.protocol !== "https:")
) {
  throw new Error("Use a device-reachable HTTP(S) FastAPI base URL without credentials, query or fragment. Releases require HTTPS. Android localhost refers to the phone, not your PC.");
}
const frontend = path.join(root, "frontend");
const next = path.join(frontend, "node_modules/next/dist/bin/next");
if (!existsSync(next)) throw new Error("Install frontend dependencies first: npm --prefix frontend ci");

const base = apiBaseUrl.toString().replace(/\/+$/, "");
console.log(`Exporting LifePilot AI for Android; API: ${base}/api (${release ? "release" : "development"})`);
const result = spawnSync(process.execPath, [next, "build"], {
  cwd: frontend,
  env: {
    ...process.env,
    CAPACITOR_BUILD: "true",
    BUILD_STANDALONE: "false",
    NEXT_PUBLIC_API_BASE_URL: base,
  },
  stdio: "inherit",
});
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);
if (!existsSync(path.join(frontend, "out/index.html"))) {
  throw new Error("Next.js did not produce frontend/out/index.html; Capacitor sync was not run.");
}
prepareAndroidExport(path.join(frontend, "out"));
writeFileSync(path.join(frontend, "out/lifepilot-build.json"), JSON.stringify({
  target: "android",
  release,
  apiBaseUrl: base,
}, null, 2) + "\n");
