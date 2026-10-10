import { readdir, readFile } from "node:fs/promises";
import { gzipSync } from "node:zlib";
const assets = await readdir("dist/assets");
const prohibited = [
  "SAMPLE test experiment",
  "synthetic-v2",
  "research-preview-1",
  "0.39704897741387934",
  "2.381648888888889",
];
let initial = 0;
for (const name of assets.filter((n) => n.endsWith(".js"))) {
  const content = await readFile(`dist/assets/${name}`);
  for (const marker of prohibited)
    if (content.includes(marker))
      throw new Error(
        `Prohibited preview/fixture content in ${name}: ${marker}`,
      );
  const size = gzipSync(content).length;
  if (name.startsWith("index-")) initial += size;
  console.log(`${name}: ${(size / 1024).toFixed(1)} KiB gzipped`);
}
if (initial > 250 * 1024)
  throw new Error("Initial JavaScript exceeds 250 KiB gzip budget");
console.log(
  "Production preview/fixture content guard and initial JS budget passed.",
);
