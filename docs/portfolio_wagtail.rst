Portfolio in Wagtail
====================

Data contract
-------------

``PortfolioIndexPage`` is the only parent for ``ProjectPage`` records. Public
project navigation filters to live, public ``ProjectPage`` descendants in Wagtail
tree order. On a project page, ``get_other_projects()`` returns the next two
projects and wraps at the end of the list.

Project services are editor-sortable ``ProjectService`` child records. Structured
case-study content lives in the ``content`` StreamField and supports one introductory
statement, challenge/solution copy, full-width images, image pairs, portrait duos,
flexible galleries, results and one optional testimonial. Rich-text controls
deliberately exclude heading levels because templates own the document outline.
The project metadata renders category, year and ordered services, plus the optional
client whenever an editor supplies one.

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
Wagtail's ``Meta.template`` contract. Consequently, ``project_page.html`` only needs
``include_block`` and automatically renders future registered block types without a
second type dispatch. Image pairs share one pair template and all editorial images
share one captioned-image template, so rendition attributes, contextual alt text and
captions cannot drift between block types. The markup composes the existing Stack,
Grid and Frame primitives where they express structure; final prototype-parity CSS
remains a separate reviewed phase.

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

``GalleryValue.mobile_rows`` already preserves the approved rule that only adjacent,
ordinary portrait images form a mobile pair. The structural foundation intentionally
does not consume that presentation grouping yet: wiring it into the gallery markup is
part of the separately reviewed visual-parity phase. Keep its regression test in place
until that template port is complete.

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

501 route and fallback behavior
-------------------------------

The editable placeholder is available at ``/portfolio/501/`` and deliberately
returns HTTP 501. This URL is an explicit Django route; it does not add a catch-all
and does not change the existing Wagtail mount below ``/blogs/``.

Copy is stored per Wagtail site in ``ErrorPageSettings``. The app depends on
``wagtail.contrib.settings`` in ``INSTALLED_APPS`` and registers the model from
``homepage.portfolio.wagtail_hooks``. If Wagtail cannot resolve a site for a request,
the view uses the field defaults instead of failing. If the selected site has no live
portfolio index, the page omits index-dependent navigation, contact and teaser links;
the response, meaningful brand text and home link remain available.
Reading the preview route never creates settings records: an unconfigured site receives
an unsaved default instance until an editor deliberately saves its settings in Wagtail.

Shared navigation and home links use Wagtail's request-aware ``pageurl`` tag.
They therefore resolve against the selected request site, including HTTPS sites on
non-default ports, rather than relying on the first site associated with a page.

CSS cascade contract
--------------------

The Wagtail portfolio loads one structural stylesheet, ``portfolio/portfolio.css``.
It keeps the current foundation and 501 presentation together without importing the
larger static prototype design. Font files and generated handwriting data remain
separate assets. A future motion stylesheet may be loaded separately, but its rules
must join the existing ``motion`` layer instead of creating a new precedence level.

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

The layered presentation requires a browser with ``@layer`` support. A browser without
it ignores the layered presentation, but still receives the complete semantic HTML:
links, native menu disclosure and page content remain visible and keyboard-operable
with user-agent styles. Supporting a pre-layer visual baseline would require a
separately generated unlayered build; duplicating every declaration in the source
stylesheet is deliberately avoided because it would make cascade fixes ambiguous and
increase transfer size.

CSS foundation note (2026-09-10)
--------------------------------

The former ``foundation.css`` and page-specific ``501.css`` were consolidated into
``portfolio.css``. This is a source-organization and request-count change only: all
selectors and computed values remain unchanged. The signature four-column prototype
grid and approved visual design are not ported or altered by this foundation release.
The 501 composition and related-project cards reuse the shared Stack primitive;
logical viewport and padding properties retain equivalent physical fallbacks where
older engines need them. The shared ``--site-header-block-size`` contract keeps the
501 content-height calculation tied to the header instead of repeating its literal
height in page rules. It encodes the current single-line header geometry; any change
to header padding, line height, borders or wrapping requires a 320-pixel 501 fold check.
