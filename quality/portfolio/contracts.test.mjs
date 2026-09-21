import assert from "node:assert/strict";
import test from "node:test";

import { contractProfiles, locators, selector, targetProfiles } from "./contracts.mjs";
import { target } from "./support.mjs";

function collectLocatorReferences(profiles) {
  const referencedLocators = new Set();

  for (const [profileName, profile] of Object.entries(profiles)) {
    for (const [pageName, contract] of Object.entries(profile)) {
      const context = `${profileName}.${pageName}`;
      assert.equal(typeof contract.name, "string", `${context}.name must be a string`);
      assert.ok(Array.isArray(contract.essentials), `${context}.essentials must be an array`);
      assert.ok(Array.isArray(contract.keyboardTargets), `${context}.keyboardTargets must be an array`);
      assert.ok(
        contract.menu && typeof contract.menu === "object" && !Array.isArray(contract.menu),
        `${context}.menu must be an object`,
      );

      for (const [index, requirement] of contract.essentials.entries()) {
        assert.ok(
          requirement && typeof requirement === "object" && !Array.isArray(requirement),
          `${context}.essentials[${index}] must be an object`,
        );
        assert.equal(typeof requirement.name, "string", `${context}.essentials[${index}].name must be a string`);
        assert.equal(
          typeof requirement.locator,
          "string",
          `${context}.essentials[${index}].locator must be a string`,
        );
        referencedLocators.add(requirement.locator);
      }

      for (const [index, locatorKey] of contract.keyboardTargets.entries()) {
        assert.equal(typeof locatorKey, "string", `${context}.keyboardTargets[${index}] must be a string`);
        referencedLocators.add(locatorKey);
      }

      for (const [menuKey, locatorKey] of Object.entries(contract.menu)) {
        assert.equal(typeof locatorKey, "string", `${context}.menu.${menuKey} must be a string`);
        referencedLocators.add(locatorKey);
      }
    }
  }

  return referencedLocators;
}

test("every target profile has one contract for every page", () => {
  for (const [profileName, profile] of Object.entries(targetProfiles)) {
    assert.deepEqual(Object.keys(contractProfiles[profileName]).sort(), Object.keys(profile.pages).sort());
  }
});

test("every contract locator key resolves", () => {
  for (const locatorKey of collectLocatorReferences(contractProfiles)) selector(locatorKey);
});

test("every locator is referenced by at least one page contract", () => {
  const locatorKeys = new Set(Object.keys(locators));
  const referencedLocators = collectLocatorReferences(contractProfiles);

  assert.deepEqual(
    [...locatorKeys].filter((locatorKey) => !referencedLocators.has(locatorKey)),
    [],
  );
});

test("descriptive contract strings do not count as locator references", () => {
  const profiles = {
    fixture: {
      page: {
        name: "main",
        menu: {},
        essentials: [{ name: "projects", locator: "contact" }],
        keyboardTargets: [],
      },
    },
  };

  assert.deepEqual([...collectLocatorReferences(profiles)], ["contact"]);
});

test("prototype legal locators preserve the relative depth contract", () => {
  assert.equal(selector("imprintLink"), "footer a[href='impressum.html']");
  assert.equal(selector("privacyLink"), "footer a[href='datenschutz.html']");
  assert.equal(selector("projectImprintLink"), "footer a[href='../impressum.html']");
  assert.equal(selector("projectPrivacyLink"), "footer a[href='../datenschutz.html']");
});

test("Wagtail target derives explicit and overridable paths from the supplied origin", async () => {
  const originalEnvironment = { ...process.env };
  try {
    process.env.PORTFOLIO_AUDIT_TARGET = "wagtail";
    process.env.PORTFOLIO_AUDIT_URL = "https://portfolio.test/arbitrary/entry/";
    process.env.PORTFOLIO_AUDIT_PROJECT_PATH = "/work/example/";

    const resolved = await target();

    assert.equal(resolved.profile, "wagtail");
    assert.equal(resolved.url, "https://portfolio.test/blogs/portfolio/katharina/");
    assert.deepEqual(resolved.pages, {
      homepage: {
        url: "https://portfolio.test/blogs/portfolio/katharina/",
        expectedStatus: 200,
      },
      error: {
        url: "https://portfolio.test/portfolio/501/",
        expectedStatus: 501,
      },
      project: {
        url: "https://portfolio.test/work/example/",
        expectedStatus: 200,
      },
      imprint: {
        url: "https://portfolio.test/impressum/",
        expectedStatus: 200,
      },
      privacy: {
        url: "https://portfolio.test/datenschutz/",
        expectedStatus: 200,
      },
    });
  } finally {
    process.env = originalEnvironment;
  }
});

test("explicit prototype homepage path takes precedence over the backwards-compatible URL", async () => {
  const originalEnvironment = { ...process.env };
  try {
    process.env.PORTFOLIO_AUDIT_TARGET = "prototype";
    process.env.PORTFOLIO_AUDIT_URL = "https://prototype.test/releases/current.html";
    process.env.PORTFOLIO_AUDIT_HOMEPAGE_PATH = "next.html";

    const resolved = await target();

    assert.equal(resolved.url, "https://prototype.test/releases/next.html");
  } finally {
    process.env = originalEnvironment;
  }
});
