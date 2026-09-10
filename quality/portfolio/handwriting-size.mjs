import fs from "node:fs/promises";
import path from "node:path";
import { gzipSync, brotliCompressSync } from "node:zlib";
import { chromium, webkit } from "playwright";
import { prototypeDir, artifactsDir } from "./support.mjs";

if (!process.argv[2])
  throw new Error("Pass the baseline handwriting bundle path");
const sources = {
  before: await fs.readFile(process.argv[2], "utf8"),
  after: await fs.readFile(
    path.join(prototypeDir, "handwriting-glyphs.js"),
    "utf8",
  ),
  contact: await fs.readFile(
    path.join(prototypeDir, "handwriting-contact.js"),
    "utf8",
  ),
};
const report = {};
for (const [name, source] of Object.entries(sources))
  report[name] = {
    raw: Buffer.byteLength(source),
    gzip6: gzipSync(source).length,
    gzip9: gzipSync(source, { level: 9 }).length,
    brotli11: brotliCompressSync(source).length,
  };
for (const [engine, type] of Object.entries({ chromium, webkit })) {
  const browser = await type.launch();
  try {
    const page = await browser.newPage();
    report[engine] = {};
    for (const [name, source] of Object.entries(sources))
      report[engine][name] = await page.evaluate((source) => {
        const parsing = [],
          layout = [],
          script = [];
        let nodes, paths, uses;
        for (let run = 0; run < 12; run++) {
          let start = performance.now();
          new Function(source)();
          script.push(performance.now() - start);
          start = performance.now();
          const element = document.createElement("div");
          element.innerHTML = Object.values(window.PORTFOLIO_HANDWRITING).join(
            "",
          );
          parsing.push(performance.now() - start);
          start = performance.now();
          document.body.append(element);
          // Diagnostic only: intentionally flush layout to measure this phase separately.
          element.getBoundingClientRect();
          layout.push(performance.now() - start);
          nodes = element.querySelectorAll("*").length;
          paths = element.querySelectorAll("path").length;
          uses = element.querySelectorAll("use").length;
          element.remove();
        }
        const median = (values) => values.slice(2).sort((a, b) => a - b)[5];
        return {
          nodes,
          paths,
          uses,
          scriptMs: median(script),
          parseMs: median(parsing),
          initialLayoutMs: median(layout),
        };
      }, source);
  } finally {
    await browser.close();
  }
}
await fs.mkdir(artifactsDir, { recursive: true });
await fs.writeFile(
  path.join(artifactsDir, "handwriting-size.json"),
  JSON.stringify(report, null, 2) + "\n",
);
console.log(JSON.stringify(report, null, 2));
