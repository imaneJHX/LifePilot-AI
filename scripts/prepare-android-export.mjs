import { copyFileSync, existsSync, readdirSync } from "node:fs";
import path from "node:path";

// Next.js 16.4's Windows exporter leaves backslash-separated RSC segment names
// as nested directories. Its browser router requests dot-separated filenames.
// Add aliases to the export only; retain Next's original generated files.
export function prepareAndroidExport(outputDir) {
  let aliases = 0;
  function visit(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const source = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        visit(source);
      } else if (entry.isFile() && entry.name.endsWith(".txt")) {
        const parts = path.relative(outputDir, source).split(path.sep);
        const segmentIndex = parts.findIndex((part) => part.startsWith("__next."));
        if (segmentIndex < 0 || segmentIndex === parts.length - 1) continue;
        const destination = path.join(
          outputDir, ...parts.slice(0, segmentIndex), parts.slice(segmentIndex).join("."),
        );
        if (!existsSync(destination)) {
          copyFileSync(source, destination);
          aliases++;
        }
      }
    }
  }
  visit(outputDir);
  console.log(`Android export prepared (${aliases} Windows navigation-data aliases added).`);
}
