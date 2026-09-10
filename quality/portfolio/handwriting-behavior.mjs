import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { chromium, webkit } from "playwright";
import { target, artifactsDir, prototypeDir } from "./support.mjs";

const server = await target();
const results = [];
try {
  for (const [name, type] of Object.entries({ chromium, webkit })) {
    const browser = await type.launch();
    try {
      for (const javaScriptEnabled of [true, false]) {
        const context = await browser.newContext({ javaScriptEnabled });
        for (const url of [
          server.url,
          new URL("projekte/buchgestaltung.html#kontakt", server.url).href,
        ]) {
          const page = await context.newPage();
          const requests = [];
          page.on("request", (request) => {
            if (/handwriting-(?:glyphs|contact)/.test(request.url()))
              requests.push(request.url());
          });
          await page.goto(url);
          if (javaScriptEnabled && url.includes("projekte")) {
            await page.waitForFunction(
              () => !!document.querySelector(".hw-label"),
            );
            assert.equal(requests.length, 1);
            assert.ok(requests[0].includes("handwriting-contact.js"));
          }
          await page.locator(".site-nav > summary").click();
          assert.equal(
            await page.locator(".site-nav").getAttribute("open"),
            "",
          );
          await page
            .locator(".site-nav nav a")
            .first()
            .waitFor({ state: "visible" });
          if (!javaScriptEnabled) assert.equal(requests.length, 0);
          await page.close();
        }
        await context.close();
        results.push({
          browser: name,
          javaScriptEnabled,
          navigation: "pass",
          directProjectEntry: "pass",
        });
      }
      for (const failedResource of ["project-teasers.js", "projekt.js"]) {
        const context = await browser.newContext();
        const page = await context.newPage();
        await page.route(`**/${failedResource}`, (route) => route.abort());
        await page.goto(
          new URL("projekte/buchgestaltung.html", server.url).href,
        );
        await page.waitForFunction(
          () => !document.documentElement.classList.contains("project-pending"),
        );
        assert.ok(await page.locator("main.no-js-content").isVisible());
        assert.ok(await page.getByText("[Kurze Projektzusammenfassung", { exact: false }).isVisible());
        results.push({ browser: name, failedResource, projectFallback: "pass" });
        await context.close();
      }
      for (const scenario of ["reduce", "failure"]) {
        const context = await browser.newContext({
          reducedMotion: scenario === "reduce" ? "reduce" : "no-preference",
        });
        const page = await context.newPage(),
          requests = [];
        page.on("request", (request) => {
          if (/handwriting-(?:glyphs|contact)/.test(request.url()))
            requests.push(request.url());
        });
        if (scenario === "failure")
          await page.route("**/handwriting-contact.js", (route) =>
            route.abort(),
          );
        await page.goto(
          new URL("projekte/buchgestaltung.html#kontakt", server.url).href,
        );
        await page.waitForTimeout(800);
        assert.equal(await page.locator("html.js-hw").count(), 0);
        assert.ok(await page.locator("svg.scr > text").isVisible());
        if (scenario === "reduce") assert.equal(requests.length, 0);
        results.push({ browser: name, scenario, visibleFallback: "pass" });
        await context.close();
      }
      const malformedContext = await browser.newContext();
      const malformedPage = await malformedContext.newPage();
      const pageErrors = [];
      malformedPage.on("pageerror", (error) => pageErrors.push(error.message));
      await malformedPage.route("**/handwriting-contact.js", async (route) => {
        const response = await route.fetch();
        const source = await response.text();
        const malformed = source.replace('href=\\"#', 'href=\\"#9missing-geometry-');
        assert.notEqual(malformed, source);
        await route.fulfill({ response, body: malformed });
      });
      await malformedPage.goto(
        new URL("projekte/buchgestaltung.html#kontakt", server.url).href,
      );
      await malformedPage.waitForFunction(
        () => !!document.querySelector(".hw-label"),
      );
      await malformedPage.waitForTimeout(100);
      assert.deepEqual(pageErrors, []);
      const fallback = malformedPage.locator(".hw-label.hw-fallback").first();
      assert.ok(await fallback.locator(".hw-final").isVisible());
      assert.equal(await fallback.locator(".hw-svg.hw-go").count(), 0);
      results.push({ browser: name, missingGeometryFallback: "pass" });
      await malformedContext.close();
      const context = await browser.newContext(),
        page = await context.newPage();
      for (const project of ["buchgestaltung", "plakatserie"]) {
        await page.goto(
          new URL(`projekte/${project}.html#kontakt`, server.url).href,
        );
        await page.waitForFunction(() => !!document.querySelector(".hw-label"));
        const resources = await page.evaluate(() =>
          performance
            .getEntriesByType("resource")
            .filter((entry) => /handwriting-/.test(entry.name))
            .map((entry) => ({
              filename: entry.name.split("/").at(-1),
              transfer: entry.transferSize,
              encoded: entry.encodedBodySize,
            })),
        );
        assert.equal(resources.length, 1);
        assert.equal(resources[0].filename, "handwriting-contact.js");
        results.push({ browser: name, project, resources });
      }
      await context.close();
      const hashedContext = await browser.newContext();
      const hashedPage = await hashedContext.newPage();
      await hashedPage.route(
        "**/projekte/buchgestaltung.html",
        async (route) => {
          const response = await route.fetch();
          const html = (await response.text()).replace(
            'src="../motion.js"',
            'src="../motion.js" data-handwriting-contact-src="/handwriting-contact.testhash.js"',
          );
          await route.fulfill({ response, body: html });
        },
      );
      await hashedPage.route("**/handwriting-contact.testhash.js", (route) =>
        route.fulfill({
          path: path.join(prototypeDir, "handwriting-contact.js"),
          contentType: "application/javascript",
        }),
      );
      await hashedPage.goto(
        new URL("projekte/buchgestaltung.html#kontakt", server.url).href,
      );
      await hashedPage.waitForFunction(
        () => !!document.querySelector(".hw-label"),
      );
      assert.equal(
        await hashedPage
          .locator('script[src="/handwriting-contact.testhash.js"]')
          .count(),
        1,
      );
      results.push({ browser: name, configuredHashedAsset: "pass" });
      await hashedContext.close();
    } finally {
      await browser.close();
    }
  }
} finally {
  await server.stop();
}
await fs.mkdir(artifactsDir, { recursive: true });
await fs.writeFile(
  path.join(artifactsDir, "handwriting-behavior.json"),
  JSON.stringify(results, null, 2) + "\n",
);
console.log(JSON.stringify(results, null, 2));
