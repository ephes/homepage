Portfolio in Wagtail
====================

The app ``homepage.portfolio`` renders Katharina's design portfolio from Wagtail
pages. It is meant to run as its own Wagtail site (``design.wersdoerfer.de``) whose
root page is a ``PortfolioIndexPage``.

Content model
-------------

``PortfolioIndexPage``
    The landing page. Hero, project, service, about, client and contact sections are
    page fields; services (``PortfolioService``), about items (``PortfolioAboutItem``)
    and clients (``PortfolioClient``) are ordered child records edited inline.

``ProjectPage``
    One project below the index. Teaser, hero image, metadata, category and a
    ``content`` StreamField (statement, challenge/solution, images, gallery, stats,
    testimonial). ``homepage_is_hero`` makes a project a large tile on the landing page:
    two of four columns on a wide grid, the full width on the two-column grid of a
    medium-width projects area. When two tiles no longer fit side by side, all hero
    projects stand on top of each other and the other projects move into the reel below.
    The switch follows the width of the projects area (container queries), not the
    screen; the order is always the order of the pages in Wagtail.

    The project header ("Titelbild" panel) is drawn in two layers. The surface fills the
    whole image area: a background colour (``#RRGGBB``), optionally a second colour with
    a direction for a gradient, and optionally a background image on top that is
    cropped to the area. The motif (``hero_image``, ideally a transparent PNG) lies on
    that surface and is always shown whole, never cropped. Without any of them a
    neutral placeholder is shown. When the article is at least 60rem wide (container
    query) and the window is clearly landscape, at least 5:4 (media query), the title
    image stays fixed on the right while the left column scrolls through headline, lead
    and live link and the case study (statement, challenge, solution). The project
    details (services, client, year, focus, category) stand directly below the
    statement in two columns on the lines of the page grid; without a statement they
    close the case study. Below the side-by-side layout, as soon as the details area
    offers four grid columns of at least 10rem (container query ``project-meta``), they
    use all four: the services split into two columns (first half, then second half, on
    the same lines), then client and year, then focus and category. This works without
    JavaScript; the template passes the number of service rows as ``--service-rows``. The details are framed by a line above
    and below and wrap only between whole words, never hyphenated. While they stand in four columns, statement, challenge and solution are
    separated like page sections (``--space-section``) and the details are set more
    airily; with two columns both gaps and the space around and inside the details are
    smaller (``--case-gap``, ``--meta-space``, switched by the content width without a
    media query). They have no visible heading; "Projekt: Details-Überschrift"
    (site settings) only names the area for screen readers. The eyebrow reads the
    "Case Study" label with the project number. In the side-by-side layout the text column
    has twice the usual inner spacing (``--inset: 2rem``).
    With JavaScript and no reduced-motion preference the case study becomes a pinned
    stage (``startCaseStage`` in ``motion.js``): the page stands still while one
    station at a time - a case-study heading (Das Projekt, Die Aufgabe, Die Lösung) with
    one of its paragraphs - sits in the middle of the view; the project details share
    the station of the statement. After each step the whole station, heading included,
    swaps with a soft lift. Texts with several paragraphs get a small counter
    such as "1 von 3" (connecting word in the site settings, "Projekt: Teilzähler");
    only the script sets it, so it never appears in the text itself. Every heading sits at the same
    height, a little above the middle; marks at the bottom left show the progress
    through the stations and the scroll cue of the landing page sits at the bottom
    right. Each scroll gesture (trackpad gesture, wheel click, swipe, key) moves exactly
    one step from the header through the stations to the gallery and
    back (``startProjectChapters``); the rest of a gesture's momentum is ignored, and a
    swipe that triggered a step stays blocked until the finger lifts.
    Inactive stations are only transparent and not clickable, never ``visibility:
    hidden``, so screen readers can read the whole case study; when keyboard focus
    lands in an inactive station, the page jumps to that station.
    Otherwise the content simply scrolls with normal spacing.

    ``conclusion`` ("Fazit") is the closing statement of a case study. It is shown in
    bold at the end of the solution and always shares a station with the last solution
    paragraph, never alone. Migration ``0011`` moved the closing, fully bold paragraph
    of each solution into this field. Tablets in portrait, nearly square windows and
    phones stack headline and lead, image and case study.

``ProjectCategory``
    Snippet with the categories shown on project tiles.

Site settings (``Settings`` in the Wagtail admin, one set per site):

``PortfolioSiteSettings``
    Brand, availability, profile text, the single public contact address, social links
    and all repeated labels in header, footer and project pages.

``LegalPageSettings``
    Title and sections of Impressum and Datenschutz. The ``Globale Kontaktadresse``
    block always renders the contact address from ``PortfolioSiteSettings``. The default
    sections contain placeholders instead of the postal address (``[Name]``,
    ``[Straße und Hausnummer]``, ``[PLZ Ort]``); enter the real address in the Wagtail
    admin before the portfolio goes live. Opening the settings form saves these defaults
    for the site. Paragraph and address blocks accept stored ``<br>`` line breaks and
    hand them to the editor as ``<br/>``.

``ErrorPageSettings``
    Copy of the 501 placeholder page.

A fixed field in the bottom-left corner, the mirror image of the back-to-top arrow,
switches the appearance between System, Hell and Dunkel (labels in the site settings,
"Darstellung"). It shows the icon of the current choice. A click first raises the field's top
edge like a window over the stacked icons, then slides the menu out to the right to
reveal the words (word left, icon right); closing runs backwards. On phones only the icon
in the narrow margin is visible, the tap area stays 44 px; ``theme-switch.js`` stores the choice in the browser (``portfolio-theme``) and an
inline script in ``base.html`` applies it before the first paint (``data-theme-choice``,
``data-theme``). Without JavaScript the switch is hidden and the page follows the system.
Over the landing-page hero the corner fields and the scroll cue invert themselves
(``mix-blend-mode: difference``) so they stay visible on the revealed image.

Dark mode applies with ``data-theme="dark"`` or, for "System" and without JavaScript,
with ``prefers-color-scheme: dark``. The switch itself sits once in the token layer of
``portfolio.css``: it sets ``color-scheme: dark``, ``--weight-shift: -30`` and the linen
tokens (``--linen-filter: invert(1)``, ``--linen-blend: screen``). Every colour role token
(``--bg``, ``--ink``, ``--muted``, ``--rule*``, ``--ph*``, ``--dark-bg``) carries both values
via ``light-dark()``, so creme and black swap roles while Tangerine stays. Dark mode
uses only black and creme, no other hue: ``--dark-ground`` is the black page, and the
areas that are dark in light mode (clients, results, contact bar, footer) as well as the
landing-page "MOIN" turn to a soft vanilla sand (``--dark-soft``, a darkened creme) with
dark text, so nothing glares like full creme. The header contact button uses the same
sand, a touch lighter so it reads equal on black. Handwriting and asterisks stay
Tangerine; only footer link hovers use a deeper burnt Tangerine (``#952c03``, 4.5:1 on the
sand). Printing
always uses the light scheme (``@media print`` in the token layer), because browsers
usually drop backgrounds and creme text would land on white paper. The landing-page "MOIN" uses its own token
``--hero-word`` (``portfolio-startseite.css``), on dark ``--dark-hero`` (the sand).
On dark, strong lines (``--rule-strong`` and ``--edge`` for the corner fields) are creme at
50 % opacity, while the finer lines (``--rule``, ``--rule-soft``, ``--dark-rule``) are a
little stronger than on light.
Buttons turn around (creme with dark text). Every ``font-weight`` in the portfolio
stylesheets is written as ``calc(<weight> + var(--weight-shift))`` so all type is a touch
lighter on dark; the Astagina handwriting keeps its weight. ``homepage.js`` and
``motion.js`` redraw the hero and the headline alignment when the theme changes at
runtime. The light appearance is unchanged; the Wagtail admin theme is not affected.

Words that belong together can be kept together softly. In rich-text fields mark them
with "Kein Umbruch"; in plain-text project titles join them with a no-break space
(Option+Space on a Mac, e.g. ``Eine Marke``). Such a group moves to the next line as a
whole and only breaks inside when it is wider than the line on its own.

Statement, challenge, solution, the stats entries and the testimonial quote, name and
role may be left empty. A text that is empty or consists only of a bracketed starter
placeholder (``[Name]``, ``[Optionales Kundenstatement zum Projekt.]`` …) is not
rendered, together with its row or section; the case-study section disappears when none
of its blocks is filled.

Fixed presentation elements such as ``Moin`` and the handwritten phrases are not
editable, because their SVG path data is generated for exactly those words
(``static/portfolio/prototype/handwriting-*.js``). Each subpath in that data starts with
an absolute ``M`` point followed by relative ``l`` steps in units of 0.1; ``motion.js``
relies on this when it shifts the apostrophe of "that's me" by changing only the ``M``
coordinate. ``handwriting-glyphs.js`` is larger than the repository's 500 KB file limit
and is therefore excluded from the ``check-added-large-files`` hook.

Routes
------

The portfolio runs on its own hostname. ``DJANGO_PORTFOLIO_HOSTS`` (comma separated,
setting ``PORTFOLIO_HOSTS``) lists these hostnames, e.g. ``design.wersdoerfer.de``.
``homepage.portfolio.hosts.PortfolioHostMiddleware`` serves requests for them with
``config/urls_portfolio.py``:

* Wagtail serves the page tree from ``/``, so the portfolio landing page is ``/`` and a
  project is ``/<slug>/``. Portfolio pages compute their URLs for these hosts without
  the ``/blogs/`` prefix, also when the URL is rendered on the main host (admin links).
* ``/impressum/`` and ``/datenschutz/`` render ``LegalPageSettings`` only when the
  request's Wagtail site has a live, public ``PortfolioIndexPage`` **as its root
  page**; otherwise they return 404. A live Wagtail page with the same relative path
  takes precedence and is redirected to. The portfolio footer only links to these
  pages when the portfolio is the site's root page.
* ``/portfolio/501/`` renders the editable placeholder with HTTP status 501.
* ``robots.txt`` and ``favicon.ico`` as on the main host. Errors (400, 403, 404, 500)
  use the plain ``portfolio/http_error.html`` instead of the blog's error pages.
* The Wagtail admin (``/cms/``) and ``/documents/`` are available too. On a portfolio
  host the admin uses the portfolio's brand theme (``static/portfolio/admin.css``); the
  main host keeps Wagtail's standard look. The theme is linked through
  ``/portfolio/admin-theme.css``, which redirects to the stylesheet on portfolio hosts and
  returns an empty stylesheet elsewhere. Sessions are per host, so editors log in
  separately on each domain.
  The admin login (``/cms/login/``) is throttled as on the main host and shares its
  counters, see :doc:`admin_login_throttle`.
* Every other path is a 404; a path without trailing slash still redirects when the
  slashed path exists. Blog, accounts, fediverse and all other routes are only served on
  the main host. They are appended after that 404 fallback in
  ``config/urls_portfolio.py`` so that templates can still reverse them, but they never
  match there.

Every other host keeps ``config/urls.py``: the Wagtail page tree stays under
``/blogs/``. The legal and 501 routes exist there as well (the admin preview of a
portfolio page needs them to resolve its links), but return 404 or omit the portfolio
identity on a site without a portfolio root.

A portfolio host needs a Wagtail site with that hostname whose root page is the
portfolio page, the hostname in ``DJANGO_ALLOWED_HOSTS`` and ``DJANGO_PORTFOLIO_HOSTS``,
and a reverse-proxy rule that routes it to the homepage application.
Use the hostname without a terminal DNS dot in ``DJANGO_ALLOWED_HOSTS`` and the
Wagtail site. Portfolio comparisons ignore case and a single terminal DNS dot
on both ``PORTFOLIO_HOSTS`` entries and request hostnames, including requests
with a port. Django's ``ALLOWED_HOSTS`` validation still applies.

Navigation and home links use Wagtail's request-aware ``pageurl`` tag, so they resolve
against the site of the current request.

Static assets
-------------

All CSS, JavaScript and fonts live in ``homepage/portfolio/static/portfolio/`` and are
collected like any other app static files:

* ``prototype/``: the design's stylesheets and scripts (``portfolio-startseite.css``,
  ``projekte/projekt.css``, ``motion.css``, ``legal.css``, ``501.css``,
  ``homepage.js``, ``motion.js``, ``site-shell.js``, ``project-teasers.js``,
  ``handwriting-glyphs.js``, ``handwriting-contact.js``);
* ``portfolio.css``, ``homepage.css``, ``project-wagtail.css``/``.js``: small adapters
  between the design and the Wagtail markup;
* ``fonts.css`` and ``fonts/``: Saira (upright and italic, variable) and Astagina as
  WOFF2. The main site uses smaller Saira files derived from these (see "Main Site
  Fonts" in ``development.rst``); its ``css/site-overrides.css`` also lays the
  portfolio's linen texture over its pages (``.linen``, z-index
  1035: above the navbar, below the search dialog, offcanvas and modals; hidden in
  print).

Templates must reference assets through ``{% static %}`` (or the ``versioned_static``
tag for stylesheets, which appends the file's modification time in ``DEBUG``), so
hashed ``collectstatic`` output works in production. Page stylesheets go into the
``extra_styles`` block of ``portfolio/base.html``, deferred scripts into
``extra_scripts``.

The hero's horizontal grid lines follow one rule without media queries
(``--hero-row1``/``--hero-row2`` in ``portfolio-startseite.css``): the top row is a
quarter of the screen height, the middle row is at least half of it and grows with
``Moin``, whose height depends only on the page width, so the word always sits between
the lines. The lead below shrinks the bottom row down to its own height; if that is not
enough, the hero becomes taller than the screen. Narrow and very low screens keep their
own layout with the lead below ``Moin``.

The landing-page hero draws its reveal image into a WebGL texture and requests it with
``crossorigin="anonymous"``. The media storage (S3/CloudFront) must therefore answer
anonymous ``GET`` requests with an ``Access-Control-Allow-Origin`` header for the
portfolio's origin; for CloudFront, include ``Origin`` in the cache key or add the
header with a response-headers policy. Without it the hero keeps its generated
fallback image.

Local development
-----------------

Create the page in the Wagtail admin, or let the seed command create it::

    uv run python manage.py seed_portfolio --create --hostname design.localhost --port 8000

``seed_portfolio`` creates the project categories and, with ``--create``, an empty,
unpublished portfolio page if none exists. It never changes an existing page and can be
run repeatedly. With ``--hostname`` the page becomes the root page of a new Wagtail site
for that hostname (next to the main site's tree), with ``--port`` as the site's port
(default 443, so Wagtail renders ``https://`` URLs); without it, it is created below the
default site's root page.

The code holds no editorial content. Texts, services, about items, clients, projects,
legal texts and images are entered in the Wagtail admin and live in the database (images
in the media storage). Field defaults are neutral placeholders such as ``[Name]`` or empty
values; only plain interface labels ("Kontakt", "Zur Startseite") keep a default. Site
settings that were never saved render these defaults, so save ``Portfolio-Site``,
``Portfolio-Rechtsseiten`` and ``501-Seite`` once for every portfolio site. To get real
content into a local database, restore a production dump.

To view the portfolio as its own site locally, run the command above, publish the page
in the admin, start Django with ``DJANGO_PORTFOLIO_HOSTS=design.localhost`` (and the
hostname in ``DJANGO_ALLOWED_HOSTS``) and open ``http://design.localhost:8000/``.
