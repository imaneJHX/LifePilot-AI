import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const require = createRequire(path.join(root, "frontend/package.json"));
// Sharp is already installed with Next.js. Derive icons from the existing compass brand.
const sharp = require("sharp");
const icons = path.join(root, "frontend/public/icons");
const source = path.join(icons, "lifepilot.svg");
for (const [name, size] of [
  ["icon-192.png", 192], ["icon-512.png", 512],
  ["icon-maskable-512.png", 512], ["apple-touch-icon.png", 180],
]) {
  await sharp(source).resize(size, size).png().toFile(path.join(icons, name));
  console.log(`Generated ${name}: ${size}x${size}`);
}
