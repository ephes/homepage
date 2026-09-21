import fs from "node:fs";

const contractData = JSON.parse(fs.readFileSync(new URL("./contracts.json", import.meta.url), "utf8"));

function freezeContract(contract) {
  return Object.freeze({
    ...contract,
    menu: Object.freeze({ ...contract.menu }),
    essentials: Object.freeze(contract.essentials.map((requirement) => Object.freeze({ ...requirement }))),
    keyboardTargets: Object.freeze([...contract.keyboardTargets]),
  });
}

function freezeProfile(profile) {
  return Object.freeze(
    Object.fromEntries(Object.entries(profile).map(([pageName, contract]) => [pageName, freezeContract(contract)])),
  );
}

export const locators = Object.freeze({ ...contractData.locators });

export const contractProfiles = Object.freeze(
  Object.fromEntries(
    Object.entries(contractData.profiles).map(([profileName, profile]) => [profileName, freezeProfile(profile)]),
  ),
);

export const targetProfiles = Object.freeze({
  prototype: Object.freeze({
    name: "prototype",
    pages: Object.freeze({
      homepage: Object.freeze({ path: "portfolio-startseite.html", expectedStatus: 200 }),
      error: Object.freeze({ path: "501.html", expectedStatus: 200 }),
      project: Object.freeze({ path: "projekte/buchgestaltung.html", expectedStatus: 200 }),
      imprint: Object.freeze({ path: "impressum.html", expectedStatus: 200 }),
      privacy: Object.freeze({ path: "datenschutz.html", expectedStatus: 200 }),
    }),
  }),
  wagtail: Object.freeze({
    name: "wagtail",
    pages: Object.freeze({
      homepage: Object.freeze({ path: "/blogs/portfolio/katharina/", expectedStatus: 200 }),
      error: Object.freeze({ path: "/portfolio/501/", expectedStatus: 501 }),
      project: Object.freeze({ path: "/blogs/portfolio/katharina/buchgestaltung/", expectedStatus: 200 }),
      imprint: Object.freeze({ path: "/impressum/", expectedStatus: 200 }),
      privacy: Object.freeze({ path: "/datenschutz/", expectedStatus: 200 }),
    }),
  }),
});

export function selector(locatorKey) {
  const value = locators[locatorKey];
  if (!value) throw new Error(`Unknown portfolio locator: ${locatorKey}`);
  return value;
}
