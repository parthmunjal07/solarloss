import { readdir, readFile } from "node:fs/promises";
import { gzipSync } from "node:zlib";
const assets = await readdir("dist/assets");
const html = await readFile("dist/index.html", "utf8");
const initialAssets = new Set(
  [...html.matchAll(/(?:src|href)="\/assets\/([^"\s]+\.js)"/g)].map(
    (m) => m[1],
  ),
);
if ([...initialAssets].some((n) => /SolarArrayScene|^v2-/.test(n)))
  throw new Error(
    "3D/scientific-contract runtimes must not be preloaded on the landing page",
  );
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
  if (initialAssets.has(name)) initial += size;
  console.log(`${name}: ${(size / 1024).toFixed(1)} KiB gzipped`);
}
if (initial > 250 * 1024)
  throw new Error("Initial JavaScript exceeds 250 KiB gzip budget");
console.log(
  `Production preview/fixture content guard passed. Initial JS including preloads: ${(initial / 1024).toFixed(1)} KiB gzip (250 KiB budget).`,
);
