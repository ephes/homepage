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
    testimonial). ``homepage_is_hero`` makes a project a large tile on the landing page.

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
    admin before the portfolio goes live.

``ErrorPageSettings``
    Copy of the 501 placeholder page.

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
* Admin, blog, accounts and all other routes exist only on the main host.

Every other host keeps ``config/urls.py``: the Wagtail page tree stays under
``/blogs/``. The legal and 501 routes exist there as well (the admin preview of a
portfolio page needs them to resolve its links), but return 404 or omit the portfolio
identity on a site without a portfolio root.

A portfolio host needs a Wagtail site with that hostname whose root page is the
portfolio page, the hostname in ``DJANGO_ALLOWED_HOSTS`` and ``DJANGO_PORTFOLIO_HOSTS``,
and a reverse-proxy rule that routes it to the homepage application.

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
* ``fonts.css`` and ``fonts/``: Saira and Astagina as WOFF2.

Templates must reference assets through ``{% static %}`` (or the ``versioned_static``
tag for stylesheets, which appends the file's modification time in ``DEBUG``), so
hashed ``collectstatic`` output works in production. Page stylesheets go into the
``extra_styles`` block of ``portfolio/base.html``, deferred scripts into
``extra_scripts``.

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

``seed_portfolio`` fills empty service, about and client lists of every portfolio page
with Katharina's default copy and creates the project categories. It never overwrites
existing entries and can be run repeatedly. The entries are saved as a new page
revision, so the Wagtail editor shows them; the revision is published only if the page
was live without pending draft changes. ``--create`` creates an unpublished portfolio
page if none exists. With ``--hostname`` it becomes the root page of a new Wagtail site
for that hostname (next to the main site's tree), with ``--port`` as the site's port
(default 443, so Wagtail renders ``https://`` URLs); without it, it is created below the
default site's root page. The command can also prefill a production page once.

To view the portfolio as its own site locally, run the command above, publish the page
in the admin, start Django with ``DJANGO_PORTFOLIO_HOSTS=design.localhost`` (and the
hostname in ``DJANGO_ALLOWED_HOSTS``) and open ``http://design.localhost:8000/``.
