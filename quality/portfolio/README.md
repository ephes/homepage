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

For reproducible runs, use `npm ci` after the lockfile exists; `npm install` is only needed when intentionally updating dependencies. The scripts serve only `docs/superpowers/prototypes/` through an isolated local HTTP server. Reports are written to `artifacts/` and intentionally ignored because timestamps and browser versions make them machine-specific.

`PORTFOLIO_AUDIT_URL` can point the same prototype-specific assertions at another hosted copy. Before applying the harness to the future Wagtail implementation, update the selector contract in `audit.mjs`; `PORTFOLIO_SOURCE_DIR` can then point source-size metrics at its implementation directory.

Lighthouse targets are Performance 90, Accessibility 90, Best Practices 90, and SEO 90. The accessibility audit remains stricter than the aggregate Lighthouse score: any serious or critical axe violation fails the CI command.

The [handwriting asset checks and deployment contract](HANDWRITING.md) cover exact
SVG geometry reuse, the project-only subset, cross-browser pixel/animation parity,
resource size and parsing, and isolated WhiteNoise content-encoding verification.
