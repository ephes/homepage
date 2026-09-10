import fs from "node:fs/promises";
import path from "node:path";
import lighthouse from "lighthouse";
import { launch } from "chrome-launcher";
import { chromium } from "playwright";
import { artifactsDir, packageDir, target } from "./support.mjs";

const failOnFindings = process.argv.includes("--fail-on-findings");
const thresholds = { performance: 90, accessibility: 90, "best-practices": 90, seo: 90 };
const server = await target();
let chrome;
let report;
try {
  chrome = await launch({
    chromePath: chromium.executablePath(),
    chromeFlags: ["--headless", "--no-sandbox", "--disable-dev-shm-usage"],
  });
  report = await lighthouse(server.url, {
    port: chrome.port,
    output: ["json", "html"],
    logLevel: "error",
    onlyCategories: Object.keys(thresholds),
    formFactor: "mobile",
    screenEmulation: { mobile: true, width: 412, height: 823, deviceScaleFactor: 1.75, disabled: false },
    throttlingMethod: "simulate",
  });
} finally {
  if (chrome) await chrome.kill();
  await server.stop();
}

if (!report) throw new Error("Lighthouse returned no report");
const { lhr } = report;
const scores = Object.fromEntries(Object.keys(thresholds).map((key) => [key, Math.round((lhr.categories[key].score || 0) * 100)]));
const metrics = Object.fromEntries(
  ["first-contentful-paint", "largest-contentful-paint", "speed-index", "total-blocking-time", "cumulative-layout-shift"]
    .map((key) => [key, { value: lhr.audits[key].numericValue, display: lhr.audits[key].displayValue }]),
);
const summary = {
  generatedAt: lhr.fetchTime,
  target: lhr.finalDisplayedUrl,
  lighthouseVersion: lhr.lighthouseVersion,
  userAgent: lhr.userAgent,
  scores,
  thresholds,
  metrics,
  bytes: {
    total: lhr.audits["total-byte-weight"].numericValue,
    display: lhr.audits["total-byte-weight"].displayValue,
  },
  requests: lhr.audits["network-requests"].details?.items?.length || 0,
  failures: Object.keys(thresholds).filter((key) => scores[key] < thresholds[key]),
};

await fs.mkdir(artifactsDir, { recursive: true });
await fs.writeFile(path.join(artifactsDir, "lighthouse.json"), `${JSON.stringify(summary, null, 2)}\n`);
await fs.writeFile(path.join(artifactsDir, "lighthouse-report.json"), report.report[0]);
await fs.writeFile(path.join(artifactsDir, "lighthouse-report.html"), report.report[1]);
const categoryRows = Object.keys(thresholds).map((key) => `| ${key} | ${scores[key]} | ${thresholds[key]} | ${scores[key] >= thresholds[key] ? "PASS" : "FAIL"} |`).join("\n");
const metricRows = Object.entries(metrics).map(([key, value]) => `| ${key} | ${value.display} |`).join("\n");
const markdown = `# Lighthouse baseline\n\nGenerated: ${summary.generatedAt}  \nTarget: \`${summary.target}\`  \nLighthouse: ${summary.lighthouseVersion}\n\n| Category | Score | Target | Result |\n|---|---:|---:|---:|\n${categoryRows}\n\n| Metric | Value |\n|---|---:|\n${metricRows}\n\n- Network: ${summary.requests} requests, ${summary.bytes.display}.\n- Full interactive report: \`lighthouse-report.html\`.\n`;
await fs.writeFile(path.join(artifactsDir, "lighthouse.md"), markdown);
console.log(markdown);
console.log(`Reports: ${path.relative(packageDir, artifactsDir)}/lighthouse.{json,md}, ${path.relative(packageDir, artifactsDir)}/lighthouse-report.{json,html}`);
if (failOnFindings && summary.failures.length) process.exitCode = 1;
