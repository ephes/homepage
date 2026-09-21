Portfolio in Wagtail
====================

Data contract
-------------

Shared shell content is stored per Wagtail site in ``PortfolioSiteSettings``:
brand, availability, profile copy, the single public contact address, social
destinations, repeated navigation/project labels and footer-line
copy. Header, native disclosure menu, landing-page calls to action, project pages and
structural ``Globale Kontaktadresse`` blocks in the legal StreamFields render
``PortfolioSiteSettings.contact_email``; separately authored mail addresses remain
untouched. No dummy or copied email value is stored in those contact blocks. LinkedIn, GitHub
and Mastodon likewise have exactly one public source in this setting. The old
``PortfolioIndexPage.contact_email`` column remains only as a hidden migration and
revision compatibility field and is never a rendering fallback.

The words ``Moin`` and the approved handwriting phrases are fixed presentation
elements. They are intentionally absent from the page editor because their canvas/SVG
geometry and the shipped glyph subsets are coupled to the exact phrases. All other
visitor-facing editorial copy is either page content, an ordered child record, a
semantic project StreamField block, a sitewide shared label or one of the dedicated
501/legal settings. Functional accessibility labels and temporary image-ratio
placeholders remain template-owned interface text. The retained ``imprint_url`` and
``privacy_url`` database columns validate root-relative paths or complete HTTP(S) URLs,
but are hidden compatibility data rather than editor-facing destinations. Public footer
links use the named, built-in legal routes directly.

Migration ``0006`` adds the current landing-page hero copy as semantic editor fields:
the emphasized opening, its continuation and second paragraph, plus the compact
experience note. The non-breaking spaces in the default note preserve the approved
320-pixel line grouping but remain ordinary editable text rather than layout markup.
Migrations ``0007`` through ``0010`` complete the current editable homepage contract:
the projects, services, about, clients and contact section copy, ordered service/about/
client records, the split contact headline and the ``Digital`` project category.
``0007`` seeds the approved lists only when the corresponding relation is empty, so it
does not overwrite existing editorial records. ``0010`` splits only the unchanged
default ``Schreib mir.`` value and has an explicit reverse migration.
Migration ``0011`` adds per-site ``LegalPageSettings`` for the two legal pages.
Its semantic StreamFields model titled sections containing paragraphs, addresses and
dated notes; headings remain template-owned and editors cannot inject layout classes.
The canonical Impressum and Datenschutz copy is present as editable defaults.
Migration ``0012`` moves repeated navigation, footer, project and 501 labels into the
existing settings models, seeds the former project example copy into empty project
StreamFields, and creates a missing site setting from the legacy landing-page address
without overwriting an existing setting. Migration ``0013`` installs the four-block
starter as the default for newly created projects. On the real ``0012`` → ``0013``
upgrade path it recognises only the exact, unchanged two-block transitional placeholder,
preserves those block IDs and appends the missing results and testimonial blocks. It also
seeds a still-wholly-empty StreamField, but never changes any other non-empty editorial
content or historical revision. Its reverse data operation is intentionally a no-op
because generated placeholders cannot be distinguished safely from subsequently edited
copy.
Project copy is deliberately not stored in ``PortfolioSiteSettings``. Migration
``0014`` upgrades the teaser to the constrained rich-text contract; ``0015`` changes
only the unchanged editorial defaults from ``Ergebnisse``/``Rückmeldung`` to
``Mehrwert``/``Kundenstimmen`` and preserves custom labels.
Migration ``0016`` adds the optional per-project website-button label. Migration
``0017`` replaces the fixed category choices with centrally managed
``ProjectCategory`` snippets. It seeds and assigns the existing Web, Digital, Print
and Illustration values, preserves the corresponding values in page revisions and
retains a hidden legacy field for a reversible transition. Unexpected historic values
are converted to readable categories instead of leaving a required project relation
empty. Migration ``0018`` adds an optional project end year without changing existing
single-year records. Editors enter the first year in ``Jahr / Startjahr`` and fill
``Endjahr`` only for multi-year work; all public project surfaces then render the
inclusive period with an en dash, for example ``2021–2024``. Migration ``0019`` turns
the former positional homepage hero rhythm into an explicit per-project checkbox and
seeds the existing first, sixth and seventh cards as heroes, preserving the approved
desktop composition and existing revisions. ``0019`` is the current migration tip for
the visual grid change. Migration ``0020`` marks the superseded single-field About and
contact copy as explicit, non-editable compatibility data; the visible, editable
structured About rows and split contact fields remain the public source. Migration
``0021`` likewise locks the superseded legal-destination columns to the built-in named
routes and removes them from the editor while retaining them for migration and revision
compatibility. Migration ``0022`` replaces the parity candidate's persisted dummy-mail
marker and render-time string substitution with a semantic legal contact block. Its
data migration converts only the former marker or the site's matching legacy contact
link, retains surrounding copy and optional link labels, and removes every migrated
mail value from the legal StreamField JSON. When a legacy address contained the contact,
the migration marks the generated address/contact pair with deterministic block IDs;
its reverse operation can therefore restore the single address-block structure without
collapsing an independently authored adjacent pair. The template resolves the block against
``PortfolioSiteSettings.contact_email`` at render time; ordinary editorial mail links
remain independent. ``0022`` is the current migration tip for the portfolio app.

``PortfolioIndexPage`` is the only parent for ``ProjectPage`` records. Public
project navigation filters to live, public ``ProjectPage`` descendants in Wagtail
tree order. The ``Projekte → Reihenfolge`` admin shortcut opens Wagtail's native
drag-and-drop child ordering; that single order drives the homepage grid, menu, footer
and related-project sequence. Each project owns a ``Hero-Kachel auf der Startseite``
checkbox for the two-column 21:9 desktop treatment. The first sorted project retains
the approved 16:9 mobile lead position while the remaining mobile cards stay in the
uniform Reel. On a project page, ``get_other_projects()`` returns the next two
projects and wraps at the end of the list.

The full-width project-inquiry row below the homepage grid keeps the canonical growing
Tangerine hover/focus fill and its 6.4-second geometry. Its normal-sized action label and
arrow switch to warm black while that fill is active; ``#171410`` on ``#eb3d00`` measures
4.55:1, so the interactive state meets WCAG AA without changing the approved animation.
When hover or keyboard focus ends, the fill becomes transparent immediately. Its width
still resets through the declared 640-millisecond transition, but that retraction is
deliberately not visible after the synchronous opacity change.

Each portfolio entry is therefore an independent editable child page. Editors create
a project below the portfolio index and maintain its title, teaser, category, year or period,
client, ordered services, teaser/hero images and semantic project blocks in that one
record. Publishing makes the page appear automatically in homepage teasers, the menu,
footer and related-project rotation; unpublishing removes it from all of those public
collections without deleting its editorial data. The homepage teaser reads the title,
category, year/period and teaser image directly from the project page, so there is no second
teaser copy to keep synchronized.

The project teaser is a deliberately constrained rich-text field. Editors may bold
individual words or phrases, add inline links and protect a selected brand name or
other phrase with the ``Kein Umbruch`` control. The latter is stored as a semantic
``span[data-no-break]`` inline style and remains effective without JavaScript; it does
not make whole paragraphs unbreakable. Editors still cannot insert headings, lists or
arbitrary layout markup. The same value supplies the visible project introduction and
its plain-text meta description; template-owned wrappers keep the approved spacing
unchanged. Statement, challenge and solution blocks provide the same inline controls.
On the
cream content surface these links remain warm black at rest and use the same 600 weight
as project service values; hover and keyboard focus turn the text tangerine while the
shared tangerine hairline enters from left to right. Reduced-motion mode removes that
transition without removing the link distinction or focus outline.
An overlapping bold mark does not increase an inline link beyond that deliberate 600
weight; the link treatment remains visually consistent.

The Wagtail sidebar exposes ``Startseite`` as a direct editor link and ``Projekte`` as
an expandable list containing ``Neues Projekt``, ``Kategorien`` and every editable
project, including unpublished drafts. ``Kategorien`` opens the central category list;
editors can also create a category from the chooser in a project form. Renaming a
category updates every assigned project, while Wagtail prevents deletion of a category
that is still in use. These are shortcuts over Wagtail's normal page and snippet
interfaces rather than a second content source; permissions still decide which entries
an editor sees.

The editor loads ``portfolio/admin.css`` through Wagtail's global admin-CSS hook. It
maps the approved cream (``#F0ECE2``), warm black (``#171410``) and tangerine
(``#EB3D00``) palette onto Wagtail's semantic color properties without changing the
admin layout. A darker tangerine is reserved for small link text where the original
accent would not reach WCAG text contrast. Expandable sidebar panels use the approved
warm-grey surface (``#393734``), which remains distinct from the warm-black main
navigation; the active entry is cream, while inactive entries use a muted light warm
tone that still exceeds normal-text contrast requirements. Confirming primary actions
such as saving, publishing and adding use
the approved emerald green (``#1C995C``) with warm-black text; the lighter green hover
state retains text contrast. Explicit light/dark choices, the system color scheme and
Forced Colors remain supported. The stylesheet is resolved with Django's ``static``
helper and is therefore compatible with hashed production manifests and a separate
static domain. In local ``DEBUG`` mode, its source-file modification time is appended
as a query version so theme changes cannot be masked by a stale browser cache.
Dark Draftail toolbars receive a scoped cream control color so rich-text buttons remain
visible without changing the warm-black labels on green confirming actions.

Wagtail is constrained to the ``7.4`` minor series in ``pyproject.toml``. The admin
theme uses the supported ``insert_global_admin_css`` hook and does not copy or replace
Wagtail templates. A compatibility test reads the installed Wagtail core stylesheet
and fails with an upgrade-specific message if any consumed semantic color property or
submenu selector disappears. A future ``7.5`` or major-version update therefore needs
an explicit dependency change, passing tests and a visual admin check rather than
silently shipping a partially broken theme.

Project placeholders are replaced through the project's teaser and hero image choosers
or by inserting the semantic full-width image, image-pair, portrait-duo and gallery
blocks. Wagtail's image editor owns one selectable focal area per source image. The
cropped teaser, related-card and hero ``fill`` renditions honour that focal area and
fall back to a centred crop when none is set. Editorial content and gallery images use
proportional ``width`` renditions without cropping, so their complete source image stays
visible. Editors set or change the focal area from ``Bilder`` by opening the image and
using Wagtail's focal-area control before selecting it on a project page.

The shared ``Weitersehen.`` heading keeps the prototype's approved narrow-screen
break through a semantic soft-hyphen opportunity in the template. The project adapter
uses manual hyphenation only for that heading, so its accessible text and desktop
rendering remain unchanged while Chromium no longer chooses a different automatic
German break in standards mode.

Project services are editor-sortable ``ProjectService`` child records. Structured
case-study content lives in the ``content`` StreamField and supports one introductory
statement, challenge/solution copy, full-width images, image pairs, portrait duos,
flexible galleries, a ``Mehrwert`` results block and one optional ``Kundenstimmen``
block. Rich-text controls
deliberately exclude heading levels because templates own the document outline.
Case-study rows align the visible top edge of the label and the first copy line.
Wagtail's RichText wrapper margins are neutralised at the adapter boundary;
following rows use the local intrinsic rhythm ``clamp(2rem, 3.5vw, 3rem)`` instead of
the former oversized section-scale gap. No breakpoint is added.
The project metadata stacks category, optional client and the derived year or period in one column. Ordered
services occupy the following column as a semantic unordered list, one service per
line. The reusable ``marker-list`` pattern supplies a larger warm-black triangular
marker without decorative markup; authored ``.rich-text`` unordered lists receive the
same treatment. Ordered, navigation and structural lists are unaffected. The project hero
headline uses an intrinsic ``min(18ch, 100%)`` measure and manual rather than automatic
hyphenation. This lets longer titles use more of the existing grid on wide screens,
keeps words such as ``Leistungen`` intact and still caps the text at the available width
on small screens. Its ``1.03`` line-height balances the visible space above and below
umlaut marks in consecutive display lines.
No additional viewport breakpoint is involved.

The project introduction uses nested intrinsic Switchers: the outer relationship pairs
the lead with a semantic project-details ``aside`` and the inner relationship divides
facts from services. Both respond to their available component width rather than a
viewport breakpoint. Only while the outer pair fits side by side does the lead reserve
``2rem`` of breathing room before the details; in the stacked tablet/mobile arrangement
it returns to the full available measure. Its summary wrapper is a vertical flex stack
with a ``1.875rem`` minimum gap.
The live-project pill consumes remaining block space above itself, so its lower edge
follows the last service row when space is available; longer lead copy takes precedence
and pushes the pill down while retaining at least 30 CSS pixels of separation.
The small metadata labels receive a visual one-pixel cap-edge correction so they align
with the first lead line without moving the shared layout boxes or the pill's lower edge.

The external project URL remains optional. When present, it renders as a semantic link
with the existing shared pill-button presentation instead of the homepage's former
full-row inquiry treatment. It combines the priority-one tangerine face with the outer
height and horizontal padding of the priority-two header contact button. Its
``1.2rem``/700 label keeps light text above the large-text contrast threshold while
reduced block padding holds the compact height. The existing arrow gets the same
``.7rem`` component gap as the other primary pill. ``ProjectPage.live_link_label`` provides an optional
per-project button label; an empty value inherits the sitewide
``PortfolioSiteSettings.project_live_link_label`` default so existing installations do
not lose their configured wording. Migration ``0016`` adds that override without
changing existing project URLs or publication state.

All StreamField images use Wagtail's accessible image block: editors must either
enter contextual alternative text or explicitly mark an image decorative. Teaser
and hero images have separate project-specific alt-text fields. Their image
choosers remain optional only during the migration period so existing revisions
can still be loaded; make both images required after all production projects have
been populated and validated.

Migration and compatibility note (2026-09-10)
---------------------------------------------

Migrations ``0003`` and ``0004`` introduce the structured schema and copy existing
comma-separated services into ordered child records. Existing rich-text bodies
are preserved verbatim and copied into a statement block. The templates render the
ordered names returned by ``get_service_names()`` and the structured ``content``
StreamField; they no longer read the legacy columns. Hero and teaser renditions use
their separate image fields and project-specific alternative text.

The legacy ``services`` and ``body`` columns remain in the database as a reversible
migration safety net, but are hidden from the editor. After deployed content has
been checked, remove both columns in a separate cleanup release. Do not remove them
in the same deployment that first switches public rendering to structured fields.

Migration ``0004`` also upgrades every existing ``ProjectPage`` revision. Each
revision's own historical ``services`` and ``body`` values are copied into its
``service_items`` and ``content`` revision data; the migration does not substitute
the currently published page values. Consequently, publishing or reverting an old
revision cannot accidentally clear the structured fields. Revisions that already
contain either structured key keep that value unchanged, including an intentionally
empty value, so the operation is idempotent and does not overwrite later edits.

StreamField rendering contract
------------------------------

Each approved block class owns its focused template in ``portfolio/blocks`` through
Wagtail's ``Meta.template`` contract. ``project_page.html`` groups the semantic block
types into the prototype's protected visual sequence: statement and challenge/solution,
then project imagery/gallery, results and testimonial. Editors control each project's
content and the order within the image group, but cannot accidentally move results ahead
of the gallery or change the document hierarchy. Image pairs share one pair template and
all editorial images share one captioned-image template, so rendition attributes,
contextual alt text and captions cannot drift between block types. The markup composes
the existing Stack, Grid and Frame primitives where they express structure. The current
canonical project presentation is applied through a small Wagtail adapter; editors never
control layout classes or heading levels.

Public images use Wagtail's installed ``srcset_image`` tag. Hero and card renditions
keep their approved 16:9 and 21:9 crops respectively; editorial images keep their
source aspect ratio. Every generated ``img`` has intrinsic width and height, an
explicit alt decision, a loading policy and a ``sizes`` hint matching its current
full-width, pair or intrinsic-grid slot. Standalone images use their editor-supplied
contextual text; an image inside a fully text-labelled related-project link uses an empty
alt because the title and metadata already name that destination. Responsive sources are
a delivery optimization only and do not change the rendered crop or layout geometry. The
base image rule keeps the block size automatic when a responsive source is narrower
than its intrinsic HTML dimensions; framed crops override both axes deliberately. The
desktop rendition is listed first so browsers without ``srcset`` support retain the
original high-resolution fallback; current browsers select the smallest suitable
source from the same crop or aspect ratio. The shared related-project card accepts a
contextual ``sizes`` hint: capped project pages use their 45-rem slot, while the
currently full-width 501 composition describes its one- or two-column viewport slot.
Isolated card includes receive the current request explicitly so Wagtail's ``pageurl``
tag keeps links request-relative in HTTPS multi-site deployments.

``GalleryValue.mobile_rows`` preserves the approved rule that only adjacent, ordinary
portrait images form a mobile pair. The gallery template now consumes those rows:
single, odd-last and explicitly large images remain full width, while only a directly
adjacent ordinary portrait pair shares a mobile row. Keep the structural regression
test in place when changing either the value object or its template.

Validation checklist
--------------------

Before removing the compatibility columns:

* every legacy service appears once and in its original order;
* every legacy body has a corresponding StreamField statement;
* publishing a pre-migration revision restores its historical services and body in
  the structured fields instead of blanking them;
* every project has distinct teaser and hero imagery where required by the design;
* every selected teaser/hero image has project-specific alternative text;
* every content image has contextual alt text or is intentionally decorative;
* the first, middle and last project return the correct wrapped successors.

Legal routes and editable copy
------------------------------

The root routes ``/impressum/`` and ``/datenschutz/`` first look for a live Wagtail page
at the equivalent site-root-relative path, including on a site that also owns a
portfolio. A collision redirects temporarily to the canonical mounted Wagtail route
instead of serving the same page from a second root URL. The temporary response avoids
caching a stale destination when an editor later unpublishes that page, so the legal
settings fallback remains reachable. This includes view-restricted pages: after the
redirect, Wagtail's normal serving chain remains responsible for their login, password
or group restriction instead of exposing the portfolio fallback.
Only when no such page exists do they render ``LegalPageSettings``, and only when the
request site owns a live, public ``PortfolioIndexPage``. On every other Wagtail site the
compatibility route returns 404 after the collision lookup, so it neither publishes the
portfolio's default personal data nor advertises unreachable legal links in the shared
footer. An independently managed page with the same relative slug is redirected to its
mounted Wagtail URL before this ownership check. Portfolio legal pages use one shared
``legal_page.html`` template and the same
server-rendered header, native disclosure, footer, grid, linen layer and top anchor as
project pages. Footer destinations are derived from the named Django routes rather than
editable path fields, so navigation and the rendered legal endpoints cannot drift apart.
The retained legal URL columns are hidden compatibility fields. The Impressum keeps the
approved animated organic illustration placeholder;
``prefers-reduced-motion`` freezes that decorative motion. Addresses render as semantic
``address`` elements, each legal section receives a template-owned ``h2``, and the footer
marks the current legal destination with ``aria-current="page"``.
Editors insert ``Globale Kontaktadresse`` as a dedicated legal-copy block. They may edit
the surrounding sentence and an optional visible link label, but the block deliberately
has no email field: its ``mailto:`` target and default visible label always come from the
single validated site contact setting.

The legal pages load canonical ``projekte/projekt.css``, ``motion.css`` and ``legal.css``
through the ``portfolio/prototype`` namespace, followed by the Wagtail project adapter.
The canonical static Impressum and Datenschutz markup contains no paragraph nested below
an address, list item or other element inside ``.legal-copy``: every matching paragraph
is a direct child. A source-level regression test enforces that invariant, so narrowing
the canonical privacy selector to ``.legal-copy > p`` preserves the approved static
prototype rhythm while allowing the Wagtail adapter to own its server-rendered address
paragraphs.
They load ``motion.js`` and ``site-shell.js`` for the shared non-essential enhancements,
but provide no handwriting data attribute and request no glyph bundle. With JavaScript
disabled, the complete legal copy, links, native menu and static illustration remain
visible and operable.

501 route and fallback behavior
-------------------------------

The editable placeholder is available at ``/portfolio/501/`` and deliberately
returns HTTP 501. This URL is an explicit Django route; it does not add a catch-all
and does not change the existing Wagtail mount below ``/blogs/``.

Copy is stored per Wagtail site in ``ErrorPageSettings``. The app depends on
``wagtail.contrib.settings`` in ``INSTALLED_APPS`` and registers the model from
``homepage.portfolio.wagtail_hooks``. If Wagtail cannot resolve a site for a request,
the view uses the field defaults instead of failing. If the selected site has no live
portfolio index, the page omits the complete portfolio header and footer as well as
index-dependent navigation, contact and teaser links. This prevents the global route
from publishing either default or saved portfolio identity, availability, profile and
social data on an unrelated Wagtail site; the neutral 501 copy and root home link remain
available. A real portfolio site's 501 shell and composition stay unchanged.
Reading the preview route never creates settings records: an unconfigured site receives
an unsaved default instance until an editor deliberately saves its settings in Wagtail.

Shared navigation and home links use Wagtail's request-aware ``pageurl`` tag.
They therefore resolve against the selected request site, including HTTPS sites on
non-default ports, rather than relying on the first site associated with a page.

Navigation anchor contract
--------------------------

The landing page renders the complete current anchor set: ``stage``, ``projekte``,
``leistungen``, ``about``, ``kunden`` and ``kontakt``. Project pages always expose
``projektstart``, ``galerie`` and ``kontakt``. The optional ``case-study`` and
``ergebnisse`` destinations and their navigation links are emitted only when that
project contains content for the respective region. A gallery fallback preserves
``galerie`` when no editorial media block exists. Render tests keep emitted hash destinations tied to
existing IDs. Navigation remains a native ``details``/``summary`` disclosure without
JavaScript; the script only adds focus return, Escape handling, scroll locking and the
approved transitions.

Asset pipeline and static delivery
----------------------------------

Wagtail resolves the canonical prototype runtime assets through a dedicated finder
with an explicit CSS/JavaScript allowlist. Prototype HTML, working Markdown and the
prototype-only base64 font stylesheet are neither exposed by the development static
server nor copied by ``collectstatic``. A missing allowlisted source emits the
system-check warning ``portfolio.W001`` for diagnosis, while ``collectstatic`` fails
closed so an incomplete portfolio cannot be deployed. Every deployment that serves
the portfolio must include ``docs/superpowers/prototypes``. The static-pipeline tests
fail if a required runtime asset cannot be resolved or collected.
That directory is intentionally both the visual reference and the production source;
creating a second runtime copy would violate the single-source parity contract. Docker,
sdist and other packaging manifests must therefore include it explicitly. The fail-closed
``collectstatic`` check is the packaging guard for that otherwise easy-to-miss dependency.
The repository's Docker ignore rules and Ansible synchronisation options both name the
prototype tree explicitly, and a static-pipeline test protects those deployment contracts
from being removed accidentally. Newly extracted runtime files must be committed before
the production collection step runs.

The homepage visual baseline has one deliberate compatibility caveat. The directly served
``portfolio-startseite.html`` is an Artifact fragment without a doctype or explicit
``html``/``head`` elements, so Chromium reports ``document.compatMode`` as ``BackCompat``
and uses quirks-mode inline line boxes. The other standalone prototype pages declare a
doctype. Production Wagtail always renders the standards-mode ``base.html``
(``CSS1Compat``); it does not emulate quirks mode globally. The homepage adapter pins only
the two observed footer differences: ``.foot-profile > .brand`` becomes a block with a
``1.5`` line height, and ``.foot-projects li > a`` becomes a ``fit-content`` block with
``max-inline-size: 100%``, the same line height and
``max(0px, calc(1.5rem - 1.5em))`` block-end padding. The latter preserves the prototype's
``1.5rem`` parent strut and wrapped-link height while keeping the animated underline no
wider than the link. CSS contract assertions guard both compensations. Changing the
reference fragment to standards mode would require a separate full pixel re-baseline and
visual approval, because line wrapping and section heights may change; the approved
prototype HTML and geometry remain untouched in this parity slice.

The base template exposes ``extra_styles``, ``extra_head`` and ``extra_scripts``
blocks for the manifest-resolved asset pipeline. Page
stylesheets belong in ``extra_styles`` so their order remains directly after the
shared stylesheet. ``extra_head`` is reserved for non-stylesheet head metadata,
preloads and any tiny capability script that must run before paint;
``extra_scripts`` holds deferred enhancement scripts at the end of ``body``. Page templates must
resolve every local asset through Django's static storage; relative runtime fallbacks
are not valid after hashed ``collectstatic`` output. Public CSS uses the
``versioned_static`` template tag: in local ``DEBUG`` mode it appends the source-file
modification time so an old browser cache cannot mask a parity change, while production
receives the unchanged manifest-resolved hashed URL. Font binaries and scripts continue
to use Django's ordinary ``static`` tag.

The shared shell preloads the exact approved Saira variable WOFF2 through the
``static`` tag, then loads the small ``portfolio/fonts.css`` font-face resource
before the layered presentation stylesheet. ``font-display: swap`` keeps system
fallback text visible while Saira arrives. The font-face stylesheet also declares
the exact approved Astagina WOFF2. Astagina is used by the server-rendered handwriting
fallback text but is deliberately not preloaded. The relative URLs
inside this collected stylesheet are source references, not runtime fallbacks:
``CompressedManifestStaticFilesStorage`` rewrites both to their hashed font URLs.
The portfolio static-pipeline test verifies that rewrite and byte equality.

The prototype directory is exposed once as the namespaced static source
``portfolio/prototype``. Wagtail therefore loads the approved canonical CSS, motion,
shell, teaser and handwriting files through manifest-resolved ``{% static %}`` URLs
without copying them into a second production source. The homepage uses
``portfolio-startseite.css``, ``motion.css``, ``homepage.js`` and ``motion.js``;
project pages use ``projekte/projekt.css``, ``motion.css``, ``motion.js``,
``project-teasers.js`` and ``site-shell.js``. The 501 page adds its canonical
``501.css``; Impressum and Datenschutz add canonical ``legal.css`` and share the project
shell scripts without a handwriting URL. Page-local ``homepage.css`` and
``project-wagtail.css`` adapters contain only markup- or data-model-specific bridges.

The static prototype's ``projekte/projekt.js`` is intentionally never loaded by
Wagtail. It replaces ``document.body`` to create a client-rendered reference page,
which would destroy the semantic Wagtail output. ``project-wagtail.js`` performs only
the result-grid overflow measurement needed by the approved layout; the shared
``project-teasers.js`` owns related-card measurement. Handwriting URLs
are passed to ``motion.js`` as ``data-handwriting-src`` on the homepage and
``data-handwriting-contact-src`` on project pages; the generated path data remains a
lazy progressive enhancement. The 501 page has no handwriting annotation and therefore
does not request either glyph bundle; the same applies to both legal pages.

Production installs WhiteNoise with its Brotli extra. The portfolio test suite runs
an isolated ``collectstatic`` pass and verifies that the manifest-hashed fixture is
emitted as byte-equivalent gzip and Brotli sidecars, so compression support cannot
silently disappear from a deployment environment.

CSS cascade contract
--------------------

The Wagtail portfolio loads the layered structural stylesheet
``portfolio/portfolio.css`` after the font-face-only ``portfolio/fonts.css``. Canonical
page and motion styles load through each template's ``extra_styles`` hook, followed by
the narrow Wagtail adapter for that page. These approved prototype files are deliberately
unlayered and therefore sit after the layered foundation; the public layer order inside
``portfolio.css`` remains unchanged. Font files and generated handwriting data remain
separate assets.

Unlayered author declarations outrank normal declarations in every named layer,
regardless of source order or selector specificity. A Wagtail adapter must therefore
not rely on a plain layered declaration to override a colliding canonical rule. The two
sanctioned escape hatches are a canonical custom-property seam (as used for legal-copy
paragraph spacing) or, only when no seam is viable, a narrowly scoped ``!important``
declaration inside the adapter layer (currently the manual hyphenation correction for
the related-project heading). Tests pin these exceptional contracts so future adapter
rules do not silently become dead code.

The layer order is a public contract and must remain exactly::

    @layer reset, tokens, base, layout, components, pages, motion, utilities;

Each layer has one responsibility:

* ``reset`` removes browser defaults only where the portfolio supplies replacements;
* ``tokens`` owns global design decisions and the modular spacing scale;
* ``base`` styles document elements without component classes;
* ``layout`` contains composable structural primitives such as Stack, Cluster and Grid;
* ``components`` owns reusable header, footer, card and contact presentation;
* ``pages`` contains narrowly scoped page exceptions, currently the 501 composition;
* ``motion`` owns animation, transition and reduced-motion behavior;
* ``utilities`` is reserved for explicit single-purpose overrides and should stay small.

Global custom properties belong in ``tokens`` only when their meaning and value are
shared across pages or components, for example colors, spacing steps, measures and
border widths. A component's public input or runtime measurement stays on that
component: ``--space``, ``--minimum``, ``--n`` and ``--d`` are intentionally local.
Do not promote a local value merely to avoid repeating a literal; promote the shared
design decision instead. Page-specific custom properties remain scoped to the page.
The ``base`` layer deliberately gives ordered and unordered ``.rich-text`` lists the
same indentation and vertical rhythm, restoring their respective markers because Wagtail
editors can author both. The ``reset`` layer separately neutralises browser-specific inline
margins on figures, quotations and definition values so shared Grid and Stack geometry
does not vary between engines.

Project-page unordered lists then opt into the approved ``marker-list`` component
presentation: a CSS-generated warm-black triangle aligned to the list's own inline
edge. ``ProjectService`` values use that same semantic pattern, with no marker span in
the template. Ordered lists keep their numeric markers and navigation lists remain
unstyled structural lists.

The layered presentation requires a browser with ``@layer`` support. A browser without
it ignores the layered presentation, but still receives the complete semantic HTML:
links, native menu disclosure and page content remain visible and keyboard-operable
with user-agent styles. Supporting a pre-layer visual baseline would require a
separately generated unlayered build; duplicating every declaration in the source
stylesheet is deliberately avoided because it would make cascade fixes ambiguous and
increase transfer size.

Current-prototype parity slice (2026-09-21)
-------------------------------------------

The current parity slice maps the approved shared prototype decisions into the
Wagtail ``tokens`` layer:

* palette roles: ``--creme``, ``--warm-black``, ``--tangerine``, ``--limette``,
  ``--pine``, ``--smaragd``, ``--bg``, ``--ink``, ``--accent``, muted/rule roles,
  ``--ph``/``--ph-ink`` and their dark-surface counterparts;
* typography roles: ``--headline-xl`` through ``--headline-s``,
  ``--type-eyebrow``, ``--type-subline``, ``--type-lead``,
  ``--type-case-large`` and the reserved ``--scr-size``;
* shared rhythm and tracking: ``--space-section``,
  ``--space-eyebrow-title``, ``--space-title-content``,
  ``--tracking-display``, ``--tracking-action`` and ``--tracking-label``.

The older ``--portfolio-*`` color names remain aliases, so the migration does not
force unrelated component rewrites. Current Wagtail headings, leads, metadata, labels,
cards, captions and footer copy receive semantic component classes or selectors for
those roles. Saira weights 300, 400, 600, 700 and 800 are taken from one 100–900 variable
file; no synthetic per-weight files or external font service are introduced.
Project titles restore the prototype's language-aware automatic hyphenation for
long German words.

The file served at ``/portfolio-startseite.html`` is the explicit visual source of
truth. The Wagtail candidate now contains its full landing-page composition: header,
native disclosure menu, availability strip, viewport-height hero, page grid, linen
overlay, projects, services, about, clients, contact, footer, custom cursor, top anchor,
organic shapes and motion/handwriting enhancements. Project and 501 pages use the same
shared shell and related-project component while preserving editable Wagtail fields,
responsive renditions, the intentional HTTP 501 response and canonical empty-content
placeholders where editorial media or StreamField blocks have not yet been supplied.
The root Impressum and Datenschutz routes complete the same shell with editable,
semantically structured legal copy.

The server-rendered ``MOIN`` keeps its distinct 800-weight role and remains readable
without JavaScript or WebGL. When available, the canonical homepage script layers the
approved WebGL fluid reveal, idle/touch motion and custom cursor over that fallback.
Desktop uses the prototype's measured 2.5168 Saira ratio; the narrow intrinsic fallback
uses the measured 2.56 DOM ratio so the ink fits the approved 320-pixel box. The
page-local canonical homepage stylesheet owns ``--hero-inset`` and follows the current canvas formula as
``clamp(0.5rem, 1.2vw, 1.25rem)``.

Not every prototype property is global. The composition values ``--pad``,
``--hero-inset``, ``--header-h``, ``--hero-floor`` and the mobile availability-strip
height remain owned by the canonical page styles rather than being promoted into the
layered global token set. Their ``:root`` declarations are page-local in practice because
only the relevant canonical stylesheet is loaded; do not redeclare them on
``.portfolio-site``, where the higher selector specificity would shadow the canonical
responsive values.
Runtime measurements such as ``--gap-start`` and ``--gap-end`` remain deferred and
script-owned. Every Layout inputs ``--space``,
``--minimum``, ``--n`` and ``--d`` remain local to their primitive or component. The
public primitives retain their contracts. All responsive and feature queries imported
from the canonical files remain the approved composition queries; the Wagtail adapters
do not introduce an alternative breakpoint system.

Handwritten phrases remain real SVG ``text`` in the server output. ``motion.js`` replaces
that visible fallback with the exact path geometry only after the relevant lazy bundle
loads. The homepage uses the full bundle; project pages use the shared smaller contact
subset; reduced motion requests neither path bundle. Failure to load JavaScript,
Astagina, a glyph bundle or WebGL therefore never hides or removes meaningful content.
Keyboard access, native disclosure semantics, focus restoration, forced-colors styles
and the reduced-motion branch remain part of the browser contract.

The 2026-09-21 integrated browser audits pass for both the prototype and Wagtail
profiles, covering homepage, project, 501, Impressum and Datenschutz. The audited
JavaScript-on/off, native-menu, 320-pixel reflow, reduced-motion and forced-colors
states pass with zero axe violations. Reduced-motion screenshots of both Wagtail legal
pages are pixel-identical to the canonical prototype at 1200, 375 and 320 pixels.
The same reduced-motion pixel comparison covers all nine project routes at those
three widths with zero differing pixels, identical full-page geometry and no
320-pixel document overflow.
The shared layered shell deliberately leaves the final menu geometry to the canonical
page and motion styles. In particular it does not impose a header minimum height, a
second social divider, a competing Social-Grid column definition or a 4.5-rem minimum
height on the circular social links. Those legacy declarations made Wagtail's open menu
one pixel taller at the divider and stretched the 46-pixel social circles to 72-pixel
ovals. After removing them, the complete open header and menu panel are pixel-identical
to the current prototype at 1400 by 1800 pixels; measured header and hero bounds also
match at 1400, 1454, 1200, 375 and 320 pixels.
The standards-mode footer adapter keeps project links block-level only for their approved
line-box height, but constrains their inline size with ``fit-content``. Consequently the
animated underline follows the project title instead of filling its entire grid column;
the other footer link groups are unaffected.

The daemonless portfolio Django run has 201 passing tests and two skipped Docker
build-context integration tests; both integration tests also pass against a temporary
Colima daemon. The complete daemonless Django suite has 259 passing tests, the same two
Docker skips, and exactly one known pre-existing failure,
``homepage/tests/test_webmentions.py::WebmentionIntegrationTest::test_webmention_display_template_tags``;
that unrelated test calls ``count()`` without an argument on a list.

The latest isolated mobile Lighthouse run measures Wagtail at
85/100/100/100 for Performance/Accessibility/Best Practices/SEO: FCP 2.6 s,
LCP 3.8 s, Speed Index 2.6 s, TBT 30 ms, CLS 0.033, 14 requests and 478 KiB.
The matching canonical prototype run measures 81/100/92/90: FCP 3.6 s,
LCP 3.8 s, Speed Index 3.6 s, TBT 0 ms, CLS 0.034, 12 requests and 521 KiB.
These figures show the observed trade-off only; they do not establish a general
performance improvement. In particular, Wagtail's Performance score still misses the
required threshold of 90 and remains an explicit pre-release task. The first measured
cleanup candidate is the superseded ``Sections (Wireframe)`` block in the canonical
homepage stylesheet: it repeats selectors now overridden by the later fluid-hero rules
and retains selectors for markup that no longer exists. Because that stylesheet is the
approved visual source for both prototype and Wagtail, removing the block belongs in a
separate screenshot-diff-backed performance pass rather than this parity change.

The release procedure keeps visible parity changes uncommitted while the real Wagtail
screens are being approved. The separately orchestrated, read-only Claude gate must
return ``REVIEW: CLEAN`` and all resulting fixes must pass the same Django and browser
contracts before publication.

Historical CSS foundation note (2026-09-10; superseded by parity candidate)
---------------------------------------------------------------------------

The former ``foundation.css`` and page-specific ``501.css`` were consolidated into
``portfolio.css``. This is a source-organization and request-count change only: all
selectors and computed values remain unchanged. The signature four-column prototype
grid and approved visual design were not ported by that historical foundation release;
the 2026-09-21 parity slice above now applies them through the canonical assets.
The 501 composition and related-project cards reuse the shared Stack primitive;
logical viewport and padding properties retain equivalent physical fallbacks where
older engines need them. The shared ``--site-header-block-size`` contract keeps the
501 content-height calculation tied to the header instead of repeating its literal
height in page rules. It encodes the current single-line header geometry; any change
to header padding, line height, borders or wrapping requires a 320-pixel 501 fold check.
