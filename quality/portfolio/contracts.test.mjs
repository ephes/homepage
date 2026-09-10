import assert from "node:assert/strict";
import test from "node:test";

import { contractProfiles, selector, targetProfiles } from "./contracts.mjs";
import { target } from "./support.mjs";

test("every target profile has one contract for every page", () => {
  for (const [profileName, profile] of Object.entries(targetProfiles)) {
    assert.deepEqual(Object.keys(contractProfiles[profileName]).sort(), Object.keys(profile.pages).sort());
  }
});

test("every contract locator key resolves", () => {
  for (const pageContracts of Object.values(contractProfiles)) {
    for (const contract of Object.values(pageContracts)) {
      const referencedLocators = [
        ...contract.essentials.map((requirement) => requirement.locator),
        ...contract.keyboardTargets,
        ...Object.values(contract.menu),
      ];
      for (const locatorKey of referencedLocators) selector(locatorKey);
    }
  }
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
