# Portfolio quality checks

This package audits the static portfolio prototype without changing it. It covers the homepage, 501 and one representative project shell with JavaScript-on and JavaScript-off navigation, keyboard reachability, page-specific essential content, axe in default/open-menu states, 320 px reflow with JavaScript both enabled and disabled, and forced colors. The homepage additionally covers reduced motion, transfer size, source size, and Lighthouse. The source audit also requires each footer project navigation to use `aria-labelledby` with an existing visible heading, without replacing that name through `aria-label` or `title`.

```sh
cd quality/portfolio
npm ci
npx playwright install chromium
npm run baseline       # reports findings, exits successfully
npm run audit:ci       # fails when a functional/a11y check fails
npm run lighthouse:ci  # fails below the configured Lighthouse targets
```

For reproducible runs, use `npm ci` after the lockfile exists; `npm install` is only needed when intentionally updating dependencies. By default, the scripts serve `docs/superpowers/prototypes/` through an isolated local HTTP server. Reports are written to `artifacts/` and intentionally ignored because timestamps and browser versions make them machine-specific.

`contracts.json` is the language-neutral single source for semantic locators and
page requirements. `contracts.mjs` loads and freezes that catalog, then adds the
runtime target profiles. The browser audit and Django's rendered Wagtail-core test
therefore consume the same selectors instead of maintaining parallel lists. A target
profile supplies each page URL and its expected HTTP status independently; the Wagtail
error page's intentional `501` response is consequently a valid result rather than a
generic load failure. `audit:ci` first exercises profile/contract coverage, the exact
prototype legal-link depths and Wagtail origin/path resolution with Node's built-in
test runner.

`PORTFOLIO_AUDIT_URL` can point the same contracts at another hosted copy. It remains
the exact homepage URL for backwards-compatible prototype runs unless the explicit
`PORTFOLIO_AUDIT_HOMEPAGE_PATH` override is also set; in that case the path wins. To
audit an already running Wagtail instance, set `PORTFOLIO_AUDIT_TARGET=wagtail` as well and supply any
URL on that instance; the Wagtail profile derives its explicit homepage, 501 and
representative-project routes from that URL's origin. This first integration slice
uses a Wagtail-core contract matching the current structural templates; the prototype
contract remains the later full-parity target. It deliberately does not create,
migrate or seed a temporary Wagtail server, so the supplied instance must already
contain equivalent published content. Deployments with another page tree can override
the three paths through `PORTFOLIO_AUDIT_HOMEPAGE_PATH`,
`PORTFOLIO_AUDIT_ERROR_PATH` and `PORTFOLIO_AUDIT_PROJECT_PATH`.
`PORTFOLIO_SOURCE_DIR` can point source-size metrics at a different implementation
directory.

Lighthouse targets are Performance 90, Accessibility 90, Best Practices 90, and SEO 90. The accessibility audit remains stricter than the aggregate Lighthouse score: any serious or critical axe violation fails the CI command.

The [handwriting asset checks and deployment contract](HANDWRITING.md) cover exact
SVG geometry reuse, the project-only subset, cross-browser pixel/animation parity,
resource size and parsing, and isolated WhiteNoise content-encoding verification.
