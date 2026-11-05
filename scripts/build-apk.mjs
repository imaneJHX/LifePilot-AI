import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
if (!existsSync(path.join(root, "android/app/src/main/assets/public/index.html"))) {
  throw new Error("Run npm run android:sync before building an APK.");
}
// Android Studio supplies JDK 21. The CLI also needs JAVA_HOME (or java on PATH).
const result = spawnSync(process.platform === "win32" ? "gradlew.bat" : "./gradlew", ["assembleDebug"], {
  cwd: path.join(root, "android"),
  stdio: "inherit",
  shell: process.platform === "win32",
});
if (result.error) throw result.error;
process.exit(result.status ?? 1);
