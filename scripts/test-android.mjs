import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { prepareAndroidExport } from "./prepare-android-export.mjs";

const root = fileURLToPath(new URL("../", import.meta.url));
const frontend = path.join(root, "frontend");
function run(args, env = process.env) {
  const result = spawnSync(process.execPath, args, { cwd: frontend, env, stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
// Browser tests reach the host via loopback. Actual emulator builds use 10.0.2.2.
run([path.join(frontend, "node_modules/next/dist/bin/next"), "build"], {
  ...process.env,
  CAPACITOR_BUILD: "true",
  BUILD_STANDALONE: "false",
  NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8001",
});
prepareAndroidExport(path.join(frontend, "out"));
console.log("Testing the browser export. Run android:sync afterward to package a device-reachable API address.");
run([path.join(frontend, "node_modules/@playwright/test/cli.js"), "test", "--config", "playwright.android.config.ts"]);
