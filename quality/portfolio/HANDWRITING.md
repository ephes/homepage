# Handwriting assets and verification

## Release note — 2026-09-10

The six existing handwriting phrases keep their exact coordinates, compound paths,
mask paths, animation lengths/timing, and editorial apostrophe adjustment. Each SVG
now declares each unique path once in `<defs>` and paints or animates local `<use>`
references. Outline/tint share one compound geometry, and both masks share their
stroke geometries. The edge contour keeps its own geometry because it is not the
same compound path. No contours are split into independently filled shapes.

Animation classes and stroke styles belong to the visible use elements. `motion.js`
resolves their local backing path for `getTotalLength()` and for the apostrophe
correction, applying a correction only once when paint layers share geometry.
If either member of an ink/outline pen pair cannot resolve its geometry, that complete
annotation keeps its original visible SVG text instead of attempting a partial write.
Keep selectors class-based; a use element itself is not an SVG geometry element.

The homepage still loads all six phrases near the first annotation. Pages whose
annotations consist only of `tell me more` load `handwriting-contact.js` instead.
Both use the existing readiness event and visible SVG-text fallback. Reduced
motion requests neither bundle. There is no custom data decoder or path rounding.

| Asset | Raw bytes | gzip level 9 | Brotli quality 11 |
|---|---:|---:|---:|
| Previous full bundle | 2,346,337 | 730,194 | 116,230 |
| Shared-geometry full bundle | 1,535,008 | 484,850 | 116,515 |
| Project contact subset | 244,651 | 77,422 | 22,819 |

Brotli already finds most repetitions, so outline sharing primarily reduces raw
source size and parsing, not the Brotli transfer size of the homepage. The contact
subset substantially reduces both. Its URL is shared by all project pages; both
tested engines reused the cached file on the second project visit (zero transfer).
A project visit after the homepage can require the separate contact file once.
Including `motion.js` and the new subset, the runtime source files shrink by
565,642 raw bytes and 168,548 gzip bytes while growing by 24 lines. Those figures
exclude the separately added verification tooling and documentation.

There are 258 SVG elements for all phrases, compared with 182 previously; 76
geometry paths and 146 use references replace 146 direct paths. The contact-only
SVG has 41 elements. More reuse is not automatically faster. Desktop microbenchmarks
found SVG parsing around 4.9 → 3.2 ms in Chromium and 5 → 3 ms in WebKit, while initial
layout in WebKit increased approximately 5 → 10 ms. These warm, unthrottled measurements are
diagnostic, not mobile performance guarantees or evidence of an overall CPU win.
An outline-only variant used fewer nodes, but produced inconsistent Chromium
intermediate-frame colors in the controlled comparison; it is not the shipped variant.

## Rebuild and test

The full checked-in bundle is the geometry source of truth. The builder expands
existing local references and rebuilds deterministically, including the project
subset. It asserts exact equality of every expanded `d` string. No separate copy
of the large source is needed. Optional `--input /path/to/legacy-bundle.js` supports
importing regenerated geometry; review any intentional geometry change separately.

Before changing an asset, preserve its current bundle as a temporary baseline.
Run from this directory with the baseline path in the last two commands:

```sh
npx playwright install chromium webkit
npm run handwriting:build
npm run handwriting:check
npm run handwriting:behavior
npm run handwriting:visual -- /absolute/path/to/baseline-handwriting-glyphs.js
npm run handwriting:size -- /absolute/path/to/baseline-handwriting-glyphs.js
npm run audit:ci
```

The visual check compares real page screenshots and all six annotations at five
animation times (0, 100, 500, 999, 1000 ms), in Chromium and WebKit at 1280 and 412 px.
It checks that all 128 pen animations exist, verifies the mask lengths, and fails
on any changed pixel. Controlled animation fixtures intentionally use simultaneous
one-second strokes; the page retains its existing sequential timing. Behavior
checks cover direct project anchors, native menus with/without JS, reduced motion,
failed requests, missing referenced glyph geometry, configured asset URLs, and
cross-project resource reuse. Reports and screenshots go to ignored `artifacts/`.

## Wagtail / deployment contract

Wagtail collects the byte-identical Saira and Astagina WOFF2 font files centrally
under `portfolio/static/portfolio/fonts/`. Saira is preloaded and used for the
initial design. Astagina is declared with `font-display: swap` and used by the
server-rendered SVG-text fallback, but it is deliberately not preloaded. Missing or
late font delivery therefore never creates an invisible-text phase.

The canonical prototype directory is registered once as the namespaced Django static
source `portfolio/prototype`. The full and contact-only outline/mask bundles remain in
that source of truth and are collected without a copied Wagtail mirror. Templates pass
their manifest-resolved URLs to the canonical motion script:

```django
{% load static %}
{# Homepage #}
<script src="{% static 'portfolio/prototype/motion.js' %}"
        data-handwriting-src="{% static 'portfolio/prototype/handwriting-glyphs.js' %}"
        defer></script>

{# Project page #}
<script src="{% static 'portfolio/prototype/motion.js' %}"
        data-handwriting-contact-src="{% static 'portfolio/prototype/handwriting-contact.js' %}"
        defer></script>
```

The 501, Impressum and Datenschutz pages have no handwritten phrase and supply neither
bundle URL. The legal pages still load `motion.js` for their non-handwriting motion,
while the shared `site-shell.js` pauses and resumes the decorative organic SVG for
Reduced Motion; absence of a handwriting data attribute prevents a glyph request. The static
prototype's `projekte/projekt.js` is also absent from every Wagtail page: it is a
client-side body generator, not a handwriting dependency or a production renderer.
Wagtail uses its semantic server output plus the narrow `project-wagtail.js` overflow
adapter instead.

This avoids assuming that unhashed aliases survive `collectstatic` or that a future
static origin has a particular hostname. `motion.js` requests the full homepage data
only when a phrase approaches the viewport and the smaller contact subset on project
pages; reduced motion requests neither bundle. No site content relies on either file
loading. A Wagtail-edited phrase without matching outline data stays visible as its
original SVG text rather than being silently substituted.

Production settings already select WhiteNoise's
`CompressedManifestStaticFilesStorage`, and the project dependency is
`whitenoise[brotli]`. The portfolio test suite exercises the real backend, requires
the Brotli encoder, verifies byte-equivalent gzip and Brotli sidecars for a
compressible fixture, and checks that the collected font stylesheet points to the
manifest-hashed, byte-identical WOFF2 files. WOFF2 is already compressed internally;
the test does not claim or require redundant gzip/Brotli sidecars for the font files.

The following check processes these two files through the same storage backend in
an isolated temporary root and requests their hashed URLs through WhiteNoise. It
verifies identity/gzip/br bodies, `Content-Encoding`, `Content-Length`, and
`Vary: Accept-Encoding`, without loading project settings or accessing deployment
credentials, a database, or an assumed host:

```sh
# Run from the repository root with the actual deployment interpreter:
python quality/portfolio/check-handwriting-compression.py --require-brotli
```

It fails explicitly when Brotli generation is unavailable. The current project
environment and the real portfolio collectstatic test require the full Brotli path.
A future proxy/CDN must preserve negotiation and
the `Vary` header; verify the actual deployed response over HTTPS after deployment.
The prototype's Python HTTP server intentionally does not represent that pipeline.
