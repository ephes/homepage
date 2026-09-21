# Portfolio quality checks

This package audits both the canonical static portfolio prototype and an already
running Wagtail parity candidate without changing either target. It covers the
homepage, 501, Impressum, Datenschutz and one representative project page with JavaScript-on and
JavaScript-off navigation, keyboard reachability, page-specific essential content,
axe in default/open-menu states, 320 px reflow with JavaScript both enabled and
disabled, and forced colors. The browser audit additionally records homepage reduced
motion, transfer size and source size; the separate Lighthouse command measures its
category scores. The fault-injection pass forces all seven optional post-Hero
initializers to fail within one controlled page load and requires every failure
to remain caught while every later initializer is still attempted. The source audit also requires each
footer project navigation to use `aria-labelledby` with an existing visible heading,
without replacing that name through `aria-label` or `title`.
The Hero's two low-level fallbacks are exercised independently: one pass rejects the
Saira readiness promise while WebGL remains available and requires the initialized
canvas to survive; another makes WebGL unavailable and requires the static MOIN to
remain visible.

```sh
cd quality/portfolio
npm ci
npx playwright install chromium
npm run baseline       # reports findings, exits successfully
npm run audit:ci       # fails when a functional/a11y check fails
npm run lighthouse:ci  # fails below the configured Lighthouse targets
```

For reproducible runs, use `npm ci` after the lockfile exists; `npm install` is only needed when intentionally updating dependencies. By default, the scripts serve `docs/superpowers/prototypes/` through an isolated local HTTP server. Reports are written to `artifacts/` and intentionally ignored because timestamps and browser versions make them machine-specific.

`audit:ci` covers the functional, accessibility and browser-state contracts described
below; it does not run Lighthouse. Performance and the aggregate Lighthouse category
thresholds are the separate `lighthouse:ci` gate, so a green `audit:ci` run can coexist
with the explicitly open Performance score recorded below.

`contracts.json` is the language-neutral single source for semantic locators and
page requirements. `contracts.mjs` loads and freezes that catalog, then adds the
runtime target profiles. The browser audit and Django's rendered Wagtail contract
tests therefore consume the same selectors instead of maintaining parallel lists. A target
profile supplies each page URL and its expected HTTP status independently; the Wagtail
error page's intentional `501` response is consequently a valid result rather than a
generic load failure. `audit:ci` first exercises profile/contract coverage, the exact
prototype legal-link depths and Wagtail origin/path resolution with Node's built-in
test runner.

`PORTFOLIO_AUDIT_URL` can point the same contracts at another hosted copy. It remains
the exact homepage URL for backwards-compatible prototype runs unless the explicit
`PORTFOLIO_AUDIT_HOMEPAGE_PATH` override is also set; in that case the path wins. To
audit an already running Wagtail instance, set `PORTFOLIO_AUDIT_TARGET=wagtail` as well and supply any
URL on that instance; the Wagtail profile derives its explicit homepage, 501,
representative-project, Impressum and Datenschutz routes from that URL's origin. The Wagtail profile now requires
the complete current homepage section set plus the shared shell, project, contact,
legal and 501 semantics; it is no longer a typography-only or structural-core profile.
It deliberately does not create, migrate or seed a temporary Wagtail server, so the
supplied instance must already contain equivalent published content. Deployments with
another page tree can override
the five paths through `PORTFOLIO_AUDIT_HOMEPAGE_PATH`,
`PORTFOLIO_AUDIT_ERROR_PATH`, `PORTFOLIO_AUDIT_PROJECT_PATH`,
`PORTFOLIO_AUDIT_IMPRINT_PATH` and `PORTFOLIO_AUDIT_PRIVACY_PATH`.
`PORTFOLIO_SOURCE_DIR` can point source-size metrics at a different implementation
directory.

For the standard local tree, run the migrated Wagtail server first and then use:

```sh
PORTFOLIO_AUDIT_TARGET=wagtail \
PORTFOLIO_AUDIT_URL=http://127.0.0.1:8000 \
PORTFOLIO_AUDIT_HOMEPAGE_PATH=/blogs/portfolio/katharina/ \
PORTFOLIO_AUDIT_ERROR_PATH=/portfolio/501/ \
PORTFOLIO_AUDIT_PROJECT_PATH=/blogs/portfolio/katharina/buchgestaltung/ \
PORTFOLIO_AUDIT_IMPRINT_PATH=/impressum/ \
PORTFOLIO_AUDIT_PRIVACY_PATH=/datenschutz/ \
npm run audit:ci
```

The project template provides the canonical composition from each project's own
semantic StreamField. Migration ``0012`` places statement and challenge/solution copy
in previously empty projects; ``0013`` completes that exact unchanged transitional
placeholder with results and testimonial blocks, seeds otherwise wholly empty streams,
and defines the same four-block editable value for newly created projects. It preserves
the two existing block IDs and leaves every other non-empty stream and all historical
revisions untouched.
Migrations ``0014`` and ``0015`` add the constrained teaser formatting and replace only
the unchanged section-label defaults with ``Mehrwert`` and ``Kundenstimmen``.
Migrations ``0016`` through ``0019`` add the project-specific website-button label,
editable project categories, optional project end year and explicit homepage hero-card
flag. Migration ``0020`` explicitly retires the superseded About/contact compatibility
fields from the editor. Migration ``0021`` hides the retained legal-destination columns
and locks public footer destinations to the built-in named routes; those columns remain
only for migration and revision compatibility. ``0021`` is the current portfolio
migration predecessor. Migration ``0022`` replaces persisted legal-email placeholders
with a structural contact block whose address comes directly from the global site
settings at render time; ``0022`` is the current portfolio migration tip.
The template keeps gallery/media before results and testimonial regardless of editor
block insertion order. Project copy is never a sitewide fallback. The homepage project
links and ordered project cards follow Wagtail's native child-page order. Editors reach its drag-and-drop
view through ``Projekte → Reihenfolge`` and select wide 21:9 desktop cards with the
per-project ``Hero-Kachel auf der Startseite`` field; mobile retains one sorted lead
card followed by the uniform project Reel.
The homepage collections still require a real migrated/published site. No audit result
from a static file, empty site or stale server counts as Wagtail visual parity.

The admin sidebar's ``Startseite`` and expandable ``Projekte`` shortcuts must resolve
to the same Wagtail page records as the normal page explorer. ``Neues Projekt`` opens
the direct ``ProjectPage`` creation form; unpublished projects remain available to
editors but must be absent from every public project collection. Teaser, related-card
and hero image crops use Wagtail ``fill`` renditions and therefore the focal area stored
on the selected source image. Uncropped StreamField and gallery media continue to use
proportional ``width`` renditions.

``ProjectPage.teaser_text`` accepts bold emphasis, inline links and the constrained
``Kein Umbruch`` inline style. Statement, challenge and solution copy provide the same
controls while keeping headings template-owned. The no-break style wraps only the
selected phrase in ``span[data-no-break]`` and must remain effective in the public
JavaScript-off output. Render checks must preserve teaser emphasis and links in the visible
project lead while keeping the meta description free of HTML and retaining the approved
lead spacing. On cream project surfaces editorial links remain warm black at rest and
use the same 600 weight as service values; hover or keyboard focus turns their text
tangerine while the shared tangerine hairline enters from the left. The transition is
disabled under reduced motion. Nested bold markup inside a link inherits that 600 weight
instead of becoming heavier.

Project metadata stacks category, optional client and the derived year or period in its first metadata
column. Ordered services form a semantic unordered list in the next column, one item
per line. They use the reusable ``marker-list`` pattern, whose CSS-generated
warm-black triangle is aligned to the list edge; ``.rich-text`` unordered lists use the
same pattern without author-inserted symbols. The canonical project hero headline must retain manual hyphenation, its
``min(18ch, 100%)`` intrinsic measure and ``1.03`` line-height so wide-screen titles can
span the available grid, whole words are not automatically split, umlauts have room and
320-pixel reflow does not gain document overflow.

An optional project URL renders a semantic ``a.project-live-link`` using the shared
pill presentation: priority-one color and large-text contrast at the priority-two
header button's compact outer height. Its label is project-editable with a sitewide fallback; an
empty URL must still omit the entire control. The button label remains its accessible
name and the decorative arrow stays hidden from assistive technology.

The Wagtail admin theme is a separate manifest-collected adapter at
``portfolio/admin.css``. Local ``DEBUG`` responses append the source-file modification
time as a query version so browser caching cannot mask a theme change. Its contract is
limited to semantic Wagtail color variables:
the cream/warm-black/tangerine brand palette, contrast-safe text and button variants,
emerald-green confirming actions, light/dark/system schemes and a Forced Colors focus
token. Expandable menu panels use the documented warm-grey surface (``#393734``) with
a cream active entry and muted light-warm inactive entries. It must not redefine the
admin's layout geometry or responsive behavior. Dark Draftail toolbars must render
their controls in cream; their icons may never inherit the warm-black confirming-
button label color used on the green action surface.

Public Wagtail stylesheets use the same local-preview safeguard through the
``versioned_static`` template tag. Only ``DEBUG`` URLs receive the source modification
time; collected production URLs remain the unchanged manifest-hashed/static-domain
URLs. A normal refresh on ``127.0.0.1`` must therefore show the current token, layout
and no-break rules without requiring a hard reload.

``test_wagtail_admin_theme_dependencies_exist_in_the_installed_wagtail_css`` is the
fail-closed upgrade guard. Keep the Wagtail minor-version constraint in
``pyproject.toml``; when intentionally raising it, run this test and visually inspect
the light, dark and system themes plus the open project submenu before merging.

## Latest integrated baseline — 2026-09-21

Both the prototype and Wagtail `audit:ci` profiles pass for all five pages: homepage,
501, representative project, Impressum and Datenschutz. The exercised JavaScript-on/
off navigation, native disclosure, keyboard, 320 px reflow, reduced-motion and forced-
colors states pass with zero axe violations. Reduced-motion Wagtail screenshots of the
two legal pages are pixel-identical to their canonical prototype pages at 1200, 375 and
320 px.

The daemonless portfolio Django run has 201 passing tests and two skipped Docker
build-context integration tests; both integration tests also pass against a temporary
Colima daemon. The complete daemonless Django suite has 259 passing tests plus the same
two Docker skips and the known pre-existing
`homepage/tests/test_webmentions.py::WebmentionIntegrationTest::test_webmention_display_template_tags`
failure, where the unrelated test calls `count()` without an argument on a list.

The latest isolated mobile Lighthouse results are:

| Target | Perf | A11y | Best Practices | SEO | FCP | LCP | Speed Index | TBT | CLS | Requests | Transfer |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Wagtail | 85 | 100 | 100 | 100 | 2.6 s | 3.8 s | 2.6 s | 30 ms | 0.033 | 14 | 478 KiB |
| Prototype | 81 | 100 | 92 | 90 | 3.6 s | 3.8 s | 3.6 s | 0 ms | 0.034 | 12 | 521 KiB |

These measurements show a mixed trade-off: Wagtail transfers 43 KiB less but adds two
requests and 30 ms TBT, while LCP is unchanged. They do not support a general performance-
improvement claim. The Performance target remains 90, so Wagtail's 85 is still an open
release gate. Accessibility, Best Practices and SEO meet their configured thresholds;
the accessibility audit remains stricter than the aggregate score because any axe
violation fails `audit:ci`. The first cleanup lead for that open gate is the superseded
`Sections (Wireframe)` block in `portfolio-startseite.css`: it duplicates selectors
overridden by the later fluid-hero rules and still contains selectors for removed hero
markup. Remove it only in a dedicated screenshot-diff-backed performance pass so the
canonical visual source is not changed without evidence.

The [handwriting asset checks and deployment contract](HANDWRITING.md) cover exact
SVG geometry reuse, the project-only subset, cross-browser pixel/animation parity,
resource size and parsing, and isolated WhiteNoise content-encoding verification.
