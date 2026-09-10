import fs from "node:fs/promises";
import path from "node:path";
import { gzipSync } from "node:zlib";
import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";
import { artifactsDir, formatBytes, markdownTable, packageDir, repoRoot, target } from "./support.mjs";

const failOnFindings = process.argv.includes("--fail-on-findings");
const sourceDir = path.resolve(process.env.PORTFOLIO_SOURCE_DIR || path.join(repoRoot, "docs/superpowers/prototypes"));
const homepageEssentials = [
  ["main", "main#main-content"],
  ["projects", "#projekte"],
  ["services", "#leistungen"],
  ["about", "#about"],
  ["clients", "#kunden"],
  ["contact", "#kontakt"],
  ["project link", "a.tile[href]"],
  ["email link", "a[href^='mailto:']"],
  ["legal link", "a[href='impressum.html']"],
];
const homepageKeyboardTargets = [
  "a.skip-link",
  "a.tile[href]",
  "#kontakt a[href^='mailto:']",
  "footer a[href='impressum.html']",
  "footer a[href='datenschutz.html']",
];
const additionalPages = [
  {
    name: "501",
    path: "501.html",
    essentials: [
      ["main", "main#main-content"],
      ["heading", "h1#error-heading"],
      ["project recommendations", ".error-projects"],
      ["project link", ".error-projects a.more-card[href]"],
      ["home link", "a.error-home-link[href]"],
      ["legal link", "footer a[href='impressum.html']"],
    ],
    keyboardTargets: [
      "a.skip-link",
      ".error-projects a.more-card[href]",
      "a.error-home-link[href]",
      "footer a[href='impressum.html']",
      "footer a[href='datenschutz.html']",
    ],
  },
  {
    name: "project",
    path: "projekte/buchgestaltung.html",
    essentials: [
      ["main", "main#main-content"],
      ["heading", "h1"],
      ["case study", "#case-study"],
      ["contact", "#kontakt"],
      ["email link", "#kontakt a[href^='mailto:']"],
      ["legal link", "footer a[href='../impressum.html']"],
    ],
    keyboardTargets: [
      "a.skip-link",
      "a.brand[href]",
      "#kontakt a[href^='mailto:']",
      "footer a[href='../impressum.html']",
      "footer a[href='../datenschutz.html']",
    ],
  },
];

const result = {
  generatedAt: new Date().toISOString(),
  target: null,
  browser: null,
  checks: [],
  axe: {},
  pageWeight: {},
  source: {},
};

function check(name, pass, detail) {
  result.checks.push({ name, pass: Boolean(pass), detail });
}

async function visibleEssentials(page, label, essentials = homepageEssentials) {
  const missing = [];
  for (const [name, selector] of essentials) {
    const locator = page.locator(selector).first();
    if ((await locator.count()) === 0 || !(await locator.isVisible())) missing.push(name);
  }
  check(`${label}: essential content visible`, missing.length === 0, missing.length ? `missing: ${missing.join(", ")}` : `${essentials.length} landmarks/links`);
}

async function keyboardTargets(page, selectors = homepageKeyboardTargets) {
  return page.evaluate((targets) => {
    return targets.map((selector) => {
      const element = document.querySelector(selector);
      return { selector, href: element?.getAttribute("href") || null };
    });
  }, selectors);
}

async function auditKeyboard(page, label, selectors) {
  const targets = await keyboardTargets(page, selectors);
  const missed = [];
  for (const [index, target] of targets.entries()) {
    if (index === 0) {
      await page.evaluate(() => {
        document.body.tabIndex = -1;
        document.body.focus({ preventScroll: true });
      });
      await page.keyboard.press("Tab");
    } else {
      await page.evaluate((selector) => document.querySelector(selector)?.focus({ preventScroll: true }), target.selector);
      await page.keyboard.press("Shift+Tab");
      await page.keyboard.press("Tab");
    }
    const activeMatches = await page.evaluate((selector) => document.activeElement?.matches(selector) || false, target.selector);
    if (!activeMatches) missed.push(target.selector);
  }
  await page.evaluate(() => document.body.removeAttribute("tabindex"));
  check(`${label}: keyboard reachability`, missed.length === 0, missed.length ? `not reached by Tab: ${missed.join(", ")}` : `${targets.length} representative links reached by native Tab navigation`);
}

async function axe(page, label, includeSelector = null) {
  const builder = new AxeBuilder({ page });
  if (includeSelector) builder.include(includeSelector);
  const findings = await builder.analyze();
  const serious = findings.violations.filter((item) => ["serious", "critical"].includes(item.impact));
  result.axe[label] = findings.violations.map(({ id, impact, description, nodes }) => ({ id, impact, description, nodes: nodes.length }));
  check(`axe: ${label}`, findings.violations.length === 0, `${findings.violations.length} violations, ${serious.length} serious/critical`);
}

async function loadPage(context, url) {
  const page = await context.newPage();
  const response = await page.goto(url, { waitUntil: "networkidle" });
  if (!response?.ok()) throw new Error(`Page load failed: ${response?.status()}`);
  return page;
}

async function auditContext(browser, url, options, label, contract = {}) {
  const {
    essentials = homepageEssentials,
    keyboardTargets: keyboardSelectors = homepageKeyboardTargets,
    runAxe = true,
  } = contract;
  console.log(`Auditing ${label}…`);
  const context = await browser.newContext(options);
  const page = await loadPage(context, url);
  console.log(`  ${label}: loaded`);
  await visibleEssentials(page, label, essentials);
  await auditKeyboard(page, label, keyboardSelectors);
  console.log(`  ${label}: keyboard checked`);
  if (runAxe) {
    await axe(page, `${label}, menu closed`);
    console.log(`  ${label}: closed-menu axe checked`);
  }

  const menu = page.locator("details.site-nav");
  await menu.locator(":scope > summary").focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(700);
  const open = await menu.evaluate((element) => element.open);
  const navVisible = await menu.locator("nav").isVisible();
  const firstNavLink = menu.locator("nav a").first();
  const firstLinkVisible = await firstNavLink.isVisible();
  check(`${label}: native menu opens`, open && navVisible && firstLinkVisible, `open=${open}; nav visible=${navVisible}; first link visible=${firstLinkVisible}`);
  console.log(`  ${label}: menu opened`);
  if (runAxe) {
    await axe(page, `${label}, menu open`, ".site-nav");
    console.log(`  ${label}: open-menu axe checked`);
  }
  const projectMenu = menu.locator(".project-menu");
  await projectMenu.locator(":scope > summary").focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(700);
  const overviewLink = projectMenu.locator("a.project-overview-link");
  const overviewHref = await overviewLink.getAttribute("href");
  check(
    `${label}: project overview remains reachable`,
    await overviewLink.isVisible() && overviewHref?.endsWith("#projekte"),
    `visible=${await overviewLink.isVisible()}; href=${overviewHref}`,
  );
  await context.close();
  console.log(`Audited ${label}.`);
}

async function auditReflow(browser, url, label, javaScriptEnabled, essentials = homepageEssentials) {
  console.log(`Auditing ${label}…`);
  const context = await browser.newContext({ javaScriptEnabled, viewport: { width: 320, height: 800 } });
  try {
    const page = await loadPage(context, url);
    await visibleEssentials(page, label, essentials);
    const reflow = await page.evaluate(() => {
      const viewport = document.documentElement.clientWidth;
      const outsideViewport = [...document.querySelectorAll("body *")].filter((element) => {
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return style.display !== "none" && style.visibility !== "hidden" && rect.width > 1 && (rect.right > viewport + 1 || rect.left < -1);
      });
      const hasHorizontalScroller = (element) => {
        for (let parent = element.parentElement; parent; parent = parent.parentElement) {
          if (["auto", "scroll"].includes(getComputedStyle(parent).overflowX)) return true;
        }
        return false;
      };
      const describe = (element) => ({ tag: element.tagName.toLowerCase(), className: String(element.className).slice(0, 80), rect: element.getBoundingClientRect().toJSON() });
      return {
        viewport,
        scrollWidth: document.documentElement.scrollWidth,
        offenders: outsideViewport.filter((element) => !hasHorizontalScroller(element)).slice(0, 12).map(describe),
        containedOffscreenElements: outsideViewport.filter(hasHorizontalScroller).length,
      };
    });
    check(`${label}: reflow`, reflow.scrollWidth <= reflow.viewport + 1, `${reflow.scrollWidth}px document; ${reflow.offenders.length} clipped/offscreen and ${reflow.containedOffscreenElements} scroller-contained elements recorded for inspection`);
    console.log(`Audited ${label}.`);
    return reflow;
  } finally {
    await context.close();
  }
}

async function collectSourceFiles() {
  const extensions = new Set([".html", ".css", ".js", ".svg"]);
  const files = [];
  async function walk(directory) {
    for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
      const fullPath = path.join(directory, entry.name);
      if (entry.isDirectory()) await walk(fullPath);
      else if (extensions.has(path.extname(entry.name))) files.push(fullPath);
    }
  }
  await walk(sourceDir);
  return files;
}

async function footerProjectNameOverrides(files) {
  const matches = [];
  const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  for (const file of files.filter((candidate) => [".html", ".js"].includes(path.extname(candidate)))) {
    const source = await fs.readFile(file, "utf8");
    const footerProjectNavigations = source.match(/<nav\b[^>]*\bfoot-projects\b[^>]*>/g) || [];
    const invalid = footerProjectNavigations.some((navigation) => {
      if (/\s(?:aria-label|title)\s*=/i.test(navigation)) return true;
      const labelledBy = navigation.match(/\saria-labelledby\s*=\s*(["'])([^"']+)\1/i)?.[2];
      if (!labelledBy) return true;
      return labelledBy.split(/\s+/).some((id) => {
        const heading = new RegExp(`<h[1-6]\\b(?=[^>]*\\bid=["']${escapeRegExp(id)}["'])[^>]*>`, "i");
        return !heading.test(source);
      });
    });
    if (invalid) {
      matches.push(path.relative(repoRoot, file));
    }
  }
  return matches;
}

async function sourceMetrics(files) {
  const byType = {};
  let bytes = 0;
  let gzipBytes = 0;
  let lines = 0;
  for (const file of files) {
    const content = await fs.readFile(file);
    const extension = path.extname(file).slice(1);
    const metric = byType[extension] ||= { files: 0, bytes: 0, gzipBytes: 0, lines: 0 };
    const fileLines = content.length ? content.toString().split("\n").length : 0;
    const fileGzip = gzipSync(content).length;
    metric.files += 1;
    metric.bytes += content.length;
    metric.gzipBytes += fileGzip;
    metric.lines += fileLines;
    bytes += content.length;
    gzipBytes += fileGzip;
    lines += fileLines;
  }
  return { directory: path.relative(repoRoot, sourceDir), files: files.length, bytes, gzipBytes, lines, byType };
}

const server = await target();
result.target = server.url;
let browser;
try {
  browser = await chromium.launch({ headless: true });
  result.browser = await browser.version();

  await auditContext(browser, server.url, { javaScriptEnabled: true, viewport: { width: 1280, height: 900 } }, "homepage, JS on");
  await auditContext(browser, server.url, { javaScriptEnabled: false, viewport: { width: 1280, height: 900 } }, "homepage, JS off", { runAxe: false });

  result.reflow = {
    homepage: {
      jsOn: await auditReflow(browser, server.url, "homepage, JS on at 320px", true),
      jsOff: await auditReflow(browser, server.url, "homepage, JS off at 320px", false),
    },
  };

  for (const contract of additionalPages) {
    const url = new URL(contract.path, server.url).href;
    await auditContext(browser, url, { javaScriptEnabled: true, viewport: { width: 1280, height: 900 } }, `${contract.name}, JS on`, contract);
    await auditContext(browser, url, { javaScriptEnabled: false, viewport: { width: 1280, height: 900 } }, `${contract.name}, JS off`, { ...contract, runAxe: false });
    result.reflow[contract.name] = {
      jsOn: await auditReflow(browser, url, `${contract.name}, JS on at 320px`, true, contract.essentials),
      jsOff: await auditReflow(browser, url, `${contract.name}, JS off at 320px`, false, contract.essentials),
    };
  }

  const reduced = await browser.newContext({ reducedMotion: "reduce", viewport: { width: 1280, height: 900 } });
  const reducedPage = await loadPage(reduced, server.url);
  const motion = await reducedPage.evaluate(() => {
    const active = [...document.querySelectorAll("body *")].filter((element) => {
      const style = getComputedStyle(element);
      const animationActive = style.animationName !== "none" && style.animationDuration.split(",").some((value) => (parseFloat(value) || 0) > 0.01);
      const motionProperties = new Set(["all", "transform", "translate", "rotate", "scale", "opacity", "width", "height", "inset", "left", "right", "top", "bottom"]);
      const transitionActive = style.transitionDuration.split(",").some((value) => (parseFloat(value) || 0) > 0.01)
        && style.transitionProperty.split(",").some((value) => motionProperties.has(value.trim()));
      return animationActive || transitionActive;
    });
    return active.slice(0, 12).map((element) => {
      const style = getComputedStyle(element);
      return { selector: `${element.tagName.toLowerCase()}.${String(element.className).replaceAll(" ", ".")}`, animation: `${style.animationName} ${style.animationDuration}`, transition: `${style.transitionProperty} ${style.transitionDuration}` };
    });
  });
  check("prefers-reduced-motion", motion.length === 0, motion.length ? `${motion.length}+ elements retain motion` : "no duration above 10ms");
  result.reducedMotionOffenders = motion;
  await reduced.close();

  const forced = await browser.newContext({ forcedColors: "active", viewport: { width: 1280, height: 900 } });
  const forcedPage = await loadPage(forced, server.url);
  await visibleEssentials(forcedPage, "homepage, forced colors");
  await forced.close();
  for (const contract of additionalPages) {
    const forcedContext = await browser.newContext({ forcedColors: "active", viewport: { width: 1280, height: 900 } });
    const forcedPage = await loadPage(forcedContext, new URL(contract.path, server.url).href);
    await visibleEssentials(forcedPage, `${contract.name}, forced colors`, contract.essentials);
    await forcedContext.close();
  }

  const weightContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const weightPage = await loadPage(weightContext, server.url);
  result.pageWeight = await weightPage.evaluate(() => {
    const resources = performance.getEntriesByType("resource");
    const total = (key) => resources.reduce((sum, entry) => sum + (entry[key] || 0), 0);
    return { requests: resources.length + 1, transferBytes: total("transferSize"), encodedBytes: total("encodedBodySize"), decodedBytes: total("decodedBodySize") };
  });
  await weightContext.close();
  const sourceFiles = await collectSourceFiles();
  const footerLabelOverrides = await footerProjectNameOverrides(sourceFiles);
  check(
    "footer project navigation uses its visible heading",
    footerLabelOverrides.length === 0,
    footerLabelOverrides.length ? `missing visible-heading name or text override: ${footerLabelOverrides.join(", ")}` : "every navigation is labelled by its visible heading",
  );
  result.source = await sourceMetrics(sourceFiles);
} finally {
  if (browser) await browser.close();
  await server.stop();
}

await fs.mkdir(artifactsDir, { recursive: true });
await fs.writeFile(path.join(artifactsDir, "audit.json"), `${JSON.stringify(result, null, 2)}\n`);
const failures = result.checks.filter((item) => !item.pass);
const markdown = `# Portfolio quality baseline\n\nGenerated: ${result.generatedAt}  \nTarget: \`${result.target}\`  \nBrowser: ${result.browser}\n\n${markdownTable(result.checks)}\n\n## Weight and code size\n\n- Browser resources: ${result.pageWeight.requests} requests, ${formatBytes(result.pageWeight.transferBytes)} transferred, ${formatBytes(result.pageWeight.decodedBytes)} decoded.\n- Prototype source: ${result.source.files} files, ${result.source.lines.toLocaleString("en-US")} lines, ${formatBytes(result.source.bytes)} raw, ${formatBytes(result.source.gzipBytes)} gzip.\n\nMachine-readable details, including axe nodes and overflow offenders, are in \`audit.json\`.\n`;
await fs.writeFile(path.join(artifactsDir, "audit.md"), markdown);
console.log(markdown);
console.log(`Reports: ${path.relative(packageDir, path.join(artifactsDir, "audit.json"))}, ${path.relative(packageDir, path.join(artifactsDir, "audit.md"))}`);
if (failOnFindings && failures.length) process.exitCode = 1;
