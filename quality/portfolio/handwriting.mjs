import fs from "node:fs/promises";
import assert from "node:assert/strict";
import { chromium, webkit } from "playwright";
import path from "node:path";
import { target, prototypeDir, artifactsDir } from "./support.mjs";
if (!process.argv[2])
  throw new Error(
    "Usage: node handwriting.mjs /absolute/path/to/baseline-handwriting-glyphs.js",
  );
const baseline = await fs.readFile(process.argv[2], "utf8");
await fs.mkdir(artifactsDir, { recursive: true });
const motionCSS = await fs.readFile(
  path.join(prototypeDir, "motion.css"),
  "utf8",
);
const server = await target();
const results = [];
try {
  for (const [name, type] of Object.entries({ chromium, webkit })) {
    const browser = await type.launch();
    try {
      for (const width of [1280, 412]) {
        const shots = [];
        for (const legacy of [true, false]) {
          const context = await browser.newContext({
              viewport: { width, height: 900 },
            }),
            page = await context.newPage(),
            errors = [];
          page.on("pageerror", (e) => errors.push(e.message));
          if (legacy)
            await page.route("**/handwriting-*.js", (r) =>
              r.fulfill({
                body: baseline,
                contentType: "application/javascript",
              }),
            );
          await page.goto(server.url);
          await page.locator("#leistungen").scrollIntoViewIfNeeded();
          await page.waitForFunction(
            () => document.querySelectorAll(".hw-label").length === 6,
          );
          await page.waitForTimeout(4000);
          await page.evaluate(() => {
            document
              .querySelectorAll("svg")
              .forEach((svg) => svg.pauseAnimations?.());
            document.getAnimations().forEach((a) => a.pause());
          });
          const bytes = await page.screenshot({
            path: `${artifactsDir}/handwriting-${name}-${width}-${legacy ? "before" : "after"}-page.png`,
          });
          const lengths = await page
            .locator(".hw-pen")
            .evaluateAll((es) =>
              es.map((e) => e.style.getPropertyValue("--L")),
            );
          const proof = await page.evaluate(() => {
            const labels = [...document.querySelectorAll(".hw-label")];
            const preview = document.createElement("div");
            preview.className = "handwriting-proof";
            const style = document.createElement("style");
            style.textContent =
              ":root{--ink:#171410;--creme:#F0ECE2;--hw-outline:#F0ECE2}body{margin:0;background:#F0ECE2!important}.handwriting-proof{display:grid;grid-template-columns:1fr;gap:10px;padding:20px}.handwriting-proof .scr.hw-label{position:relative;display:block;inline-size:100%;block-size:160px;left:auto;bottom:auto;font-size:96px}.handwriting-proof .hw-svg{left:50%!important;bottom:0!important;transform:translateX(-50%)!important;color:#171410!important;--hw-outline:#F0ECE2!important}.handwriting-proof .hw-final{display:none!important}";
            labels.forEach((label) => preview.append(label.cloneNode(true)));
            preview
              .querySelectorAll(".hw-svg")
              .forEach((svg) => svg.classList.add("hw-go"));
            preview.querySelectorAll(".hw-pen,.hw-outline-pen").forEach((p) => {
              p.style.setProperty("--hw-duration", "1s");
              p.style.setProperty("--hw-delay", "0s");
            });
            return { style: style.outerHTML, html: preview.outerHTML };
          });
          assert.deepEqual(errors, []);
          await page.goto("about:blank");
          await page.setContent(
            `<html class="has-js js-hw"><head><style>${motionCSS}</style>${proof.style}</head><body>${proof.html}</body></html>`,
          );
          assert.equal(
            await page.evaluate(() => document.getAnimations().length),
            128,
          );
          const frames = [];
          for (const time of [0, 100, 500, 999, 1000]) {
            await page.evaluate(async (time) => {
              document.getAnimations().forEach((a) => {
                a.pause();
                a.currentTime = time;
              });
              // Let both style and SVG/compositor paint consume the controlled time.
              await new Promise((resolve) =>
                requestAnimationFrame(() => requestAnimationFrame(resolve)),
              );
            }, time);
            frames.push(
              await page.screenshot({
                fullPage: true,
                path: `${artifactsDir}/handwriting-${name}-${width}-${legacy ? "before" : "after"}-${time}.png`,
              }),
            );
          }
          assert.deepEqual(errors, []);
          shots.push({ bytes, frames, lengths });
          await context.close();
        }
        assert.deepEqual(shots[0].lengths, shots[1].lengths);
        const page = await browser.newPage();
        async function diff(before, after) {
          return page.evaluate(
            async ([a, b]) => {
              async function decode(s) {
                const i = new Image();
                i.src = s;
                await i.decode();
                const c = document.createElement("canvas");
                c.width = i.width;
                c.height = i.height;
                const x = c.getContext("2d");
                x.drawImage(i, 0, 0);
                return x.getImageData(0, 0, c.width, c.height).data;
              }
              const aa = await decode(a),
                bb = await decode(b);
              let different = 0,
                max = 0;
              for (let i = 0; i < aa.length; i += 4) {
                let d = 0;
                for (let j = 0; j < 3; j++)
                  d = Math.max(d, Math.abs(aa[i + j] - bb[i + j]));
                if (d) different++;
                max = Math.max(max, d);
              }
              return { pixels: aa.length / 4, different, max };
            },
            [before, after].map(
              (b) => "data:image/png;base64," + b.toString("base64"),
            ),
          );
        }
        const pageDiff = await diff(shots[0].bytes, shots[1].bytes),
          frameDiffs = [];
        for (let i = 0; i < shots[0].frames.length; i++)
          frameDiffs.push(await diff(shots[0].frames[i], shots[1].frames[i]));
        results.push({ name, width, pageDiff, frameDiffs });
        console.log(JSON.stringify(results.at(-1)));
        await page.close();
      }
    } finally {
      await browser.close();
    }
  }
} finally {
  await server.stop();
}
await fs.writeFile(
  path.join(artifactsDir, "handwriting.json"),
  JSON.stringify(results, null, 2) + "\n",
);
assert.ok(
  results.every(
    (result) =>
      result.pageDiff.different === 0 &&
      result.frameDiffs.every((frame) => frame.different === 0),
  ),
  "SVG reuse must be pixel-identical",
);
