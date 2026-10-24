Development Setup
=================

This guide covers setting up and running the development environment for the homepage project.

Prerequisites
-------------

* Python 3.12+
* uv (Python package manager)
* PostgreSQL
* just (command runner) - Install with ``brew install just`` on macOS

Quick Start
-----------

1. Install dependencies::

    just install

2. Start development services::

    just dev

This starts PostgreSQL, Django development server, and JupyterLab as defined in the ``Procfile``.

Using the Justfile
------------------

The project uses a ``justfile`` for common development tasks. Here are the available commands:

Starting Services
~~~~~~~~~~~~~~~~~

* ``just dev`` - Start core development services (PostgreSQL and Django only)
* ``just dev-all`` - Start all services from Procfile (PostgreSQL, Django, JupyterLab, Vite)
* ``just dev-force`` - Force restart (kills existing processes first)

The ``dev`` commands will:

1. Check if services are already running on required ports
2. Start the requested services
3. Log all output to ``logs/dev.log``
4. Display colored output in the terminal

You can also start services individually in separate terminals:

* ``just postgres`` - Start only PostgreSQL
* ``just django`` - Start only Django development server
* ``just jupyter`` - Start only JupyterLab

Viewing Logs
~~~~~~~~~~~~

* ``just logs`` - View last 50 lines of the log file
* ``just logs -n 100`` - View last 100 lines
* ``just logs-follow`` - Follow logs in real-time (like ``tail -f``)
* ``just logs-grep ERROR`` - Filter logs for specific patterns

Django Management
~~~~~~~~~~~~~~~~~

* ``just manage <command>`` - Run any Django management command
* ``just shell`` - Open Django shell_plus
* ``just db-migrate`` - Create and apply database migrations
* ``just db-shell`` - Open PostgreSQL shell

Testing
~~~~~~~

* ``just test`` - Run test suite
* ``just coverage`` - Run tests with coverage report

Updating Dependencies
~~~~~~~~~~~~~~~~~~~~~

The committed ``uv.lock`` pins the complete environment, including exact Git
commits for django-cast, django-indieweb, django-resume, and the Cast themes.
django-cast tracks ``develop`` and django-resume tracks ``main``, so an update can
include unreleased changes even when the package version is unchanged. Review upstream release notes as well as the commit change.

Refresh all dependencies within the constraints in ``pyproject.toml``::

    uv lock --upgrade
    uv sync --locked

To update only django-cast and any dependencies required by its new constraints::

    uv lock --upgrade-package django-cast
    uv sync --locked

Run isolated application tests and migration checks without a local database::

    (
        export DATABASE_URL=sqlite:///:memory:
        export LEGACY_DATABASE_URL=sqlite:///:memory:
        export DJANGO_SETTINGS_MODULE=config.settings.test
        uv run --locked pytest --create-db
        uv run --locked python manage.py check
        uv run --locked python manage.py makemigrations --check --dry-run
        uv run --locked python manage.py migrate --noinput
    )

Pytest's ``testpaths`` limits default discovery to ``homepage`` so ``just test``
and direct pytest runs avoid local backup/media directories. Also inspect the
migration plan with the production settings and database before deployment;
SQLite checks do not substitute for PostgreSQL validation. Deploy with the
committed lock, apply migrations, and collect static files through the deployment
workflow.

2026-10-24 Django and Wagtail security update
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The lock advances Django 6.1.1 to 6.1.2 and Wagtail 8.0 to 8.0.1; the
existing version ranges now require these security-patched minima. Project
Python compatibility remains ``>=3.12``. All other locked packages, including
certifi 2026.10.19, pip 26.2.2 and django-cast ``ddcc44d9``, are unchanged.

See the `Django release notes <https://docs.djangoproject.com/en/6.1/releases/6.1.2/>`_
and `Wagtail release notes <https://docs.wagtail.org/en/stable/releases/8.0.1.html>`_
for the security and regression fixes.

One-off validation for this update: 731 application tests passed on Python
3.15.1 with PostgreSQL 17, all configured prek hooks passed, a fresh database
completed migrations, and ``makemigrations --check --dry-run`` found no changes.
The old and new distributions' 49 Django and 325 Wagtail migration source files
were byte-identical. A separate scratch check used production's
CompressedManifestStaticFilesStorage with in-memory test media: all seven
required manifests existed and no Brotli assets were generated. These manual
checks do not introduce a standing checker in this application repository.

CI tests the exact Python 3.15.1 stack using uv 0.13.5 and retains Python 3.14.
This does not extend upstream support: the `Django installation FAQ
<https://docs.djangoproject.com/en/6.1/faq/install/>`_ lists Python 3.15 from
Django 6.1.3, and the `Wagtail compatibility table
<https://docs.wagtail.org/en/stable/releases/upgrading.html>`_ currently stops
at Python 3.14. No unreleased Django patch or interpreter downgrade is substituted.
Server runtime provisioning and rollout remain separate ops-control work.

2026-10-21 certifi security update
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``uv.lock`` advances certifi from ``2026.7.22`` to ``2026.10.19`` and pip from
``26.2.1`` to ``26.2.2`` for the eMudhra/emSign CA compromise
(`GHSA-6q48-6c7w-9gw2
<https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2>`_).
``pyproject.toml`` now requires ``certifi>=2026.10.19`` so a later relock cannot
resolve an affected bundle. No other package changed. Deploying an earlier
commit or lock reinstalls the affected certifi and pip versions; restart the
application after syncing so running processes load the new bundle.

2026-10-17 django-cast develop refresh
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``uv.lock`` advances only django-cast from ``704a60aa`` to ``ddcc44d9``
(0.2.68 development). It adds transcript glossary snippets, private correction
sidecars and editor review, preserves approved speaker mappings when transcript
text changes, and omits the speaker-count hint for known-speaker Voxhelm jobs.

Deploy with migrations ``cast.0084`` through ``0086``. Migration ``0084`` reads
existing stored transcript files to backfill source fingerprints; retain a fresh
database backup before deployment. The corrections sidecar uses the private
voice-reference storage backend. Existing transcripts are not automatically
glossary-corrected by the migrations; corrections run on future Voxhelm imports
or through ``apply_transcript_glossary``. Rolling code back does not undo
transcript edits or remove the added schema.

Validation: 712 application tests passed on PostgreSQL 17 with real migrations,
all prek hooks passed, and ``makemigrations --check --dry-run`` found no changes.
An isolated Python 3.15 production environment passed system checks and showed
only the three expected pending Cast migrations before deployment.

2026-09-16 django-cast release pin
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The focused django-cast refresh advances the Git pin from ``b36ddd4b`` to the
released 0.2.65 commit ``1021142d``. PyPI now also publishes 0.2.65. No other
locked dependency changed. See the
`final 0.2.65 release notes <https://github.com/ephes/django-cast/blob/0.2.65/docs/releases/0.2.65.rst>`_.
The 102 application tests passed on Python 3.14.5, the migration graph applied
to empty SQLite, and the settings, model-change, documentation, and hook checks
completed with only the already documented test-manifest warnings.

2026-09-08 dependency refresh
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* django-cast: 0.2.64 at ``90790d9e`` to unreleased 0.2.65 at ``b36ddd4b``
  on ``develop``. The latest published PyPI release at upgrade time is 0.2.64.
* Django: 6.1 to 6.1.1; Wagtail remains 8.0.
* django-indieweb: 0.6.1 to 0.6.2. Both Cast theme Git pins remain unchanged.
* django-debug-toolbar: 7.0.0 to 8.0.0; Gunicorn: 26.0.0 to 26.2.0.
* Refreshed the remaining compatible runtime and development dependencies.

The Cast update includes permission, feed-isolation, comment, and editor
rich-text fixes. Legacy audio/video collection endpoints no longer accept
uploads; clients should use the editor media endpoints. Editor rich-text writes
are normalized against configured Wagtail features. See the
`upstream 0.2.65 notes <https://github.com/ephes/django-cast/blob/b36ddd4b3b3e31b73dd822b749304957c4b3ffe0/docs/releases/0.2.65.rst>`_
for integration changes.

The application, configuration, scripts, and utilities contain no references to
the removed legacy media collection upload paths. A pre-deploy scan of the
available production Traefik access log (27,632,499 entries) found no POSTs to
``/api/audios/`` or ``/api/videos/``. This covers observed usage, not unknown
clients outside the available log history.

Validated with Python 3.14.7: 102 application tests and 4 subtests passed,
the full migration graph applied to an empty in-memory SQLite database, and
``makemigrations --check --dry-run`` found no changes. These checks used
``config.settings.test`` with both ``DATABASE_URL`` and
``LEGACY_DATABASE_URL`` set to ``sqlite:///:memory:``. System checks reported the
test settings' missing Vite manifests; the run also emitted dependency
deprecation warnings. The local settings check, including debug-toolbar 8.0,
reported no issues.

Before deployment, the new frozen production dependencies were installed into
an isolated environment on the production host with Python 3.14.7, including
the pillow-heif wheel. Against the production PostgreSQL database, that
environment's ``migrate --plan`` reported no planned operations and its
production settings check reported no issues. Neither Cast nor IndieWeb adds
migration changes between the old and new pins. A fresh custom-format database
dump and copies of the previous dependency files were saved on the host before
deployment; rollback can redeploy the preceding commit and lock without schema
rollback for this refresh. PostgreSQL's existing collation-version mismatch was
resolved on 2026-09-16 by rebuilding all 117 indexes that use the database
default collation concurrently, then refreshing the database metadata from
glibc 2.35 to 2.39. The post-maintenance check found no invalid user indexes;
system catalog indexes were outside the targeted rebuild. A cluster-wide check
found that the unrelated ``lead`` and ``template1`` databases still carry the
old version and are outside this application release follow-up.

Code Quality
~~~~~~~~~~~~

* ``uv run python commands.py mypy`` - Run type checking with mypy

Deployment
~~~~~~~~~~

* ``just deploy-staging`` - Deploy to staging via ops-control (SOPS)
* ``just deploy-production`` - Deploy to production via ops-control (SOPS)
* Deploy bootstraps ops-control collections via ``uvx ansible-galaxy`` and runs playbooks via ``uvx ansible-playbook``

Blog Cover Image
~~~~~~~~~~~~~~~~

The default social cover image for blog posts without their own cover image is
the ``cover_image`` field on the ``ephes_blog`` Wagtail blog page. Regenerate
the screenshot from the production blog overview with::

    just blog-cover-screenshot

After deploying code that includes the ``update_blog_cover_image`` management
command, generate the screenshot and install it on production with::

    just blog-cover-update-production

The recipes use ``shot-scraper`` through ``uvx``. Override
``BLOG_COVER_URL``, ``BLOG_COVER_OUTPUT``, ``BLOG_COVER_REMOTE`` or
``BLOG_COVER_SLUG`` if you need to target a different page, file, host, or
blog. Wagtail revisions are attributed to the ``jochen`` user by default;
override ``BLOG_COVER_USER`` to use a different username. To see all management
command flags, including ``--title``, ``--alt-text``, ``--user`` and
``--no-publish``, run::

    just manage update_blog_cover_image --help

The image is uploaded through the image model, so django-cast strips EXIF GPS
data from it like from any other upload. The command stores the image file
first and then changes the database: it creates the image row and saves (or, by default, publishes a revision of) the
blog page in one transaction. If that fails, for example because the user may
not publish the page, nothing is left half done:

* the image row and the blog change are rolled back, so the blog keeps its
  previous cover image and alt text;
* the file uploaded by this run is deleted from storage again. Only the name
  that the storage returned for this upload is removed, and only if that name
  was free before; the previous cover and any other existing file are never
  deleted;
* the original error is raised and the command exits non-zero. If the uploaded
  file could not be removed, its storage name is printed so it can be deleted
  by hand.

The social rendition is generated after the change is committed. A failure
there leaves the new cover in place and is reported as an error.

Main Site Fonts
~~~~~~~~~~~~~~~

The main site (blog, start page, profile pages) uses Saira from
``homepage/static/fonts/``. These files are derived from the portfolio's variable
fonts in ``homepage/portfolio/static/portfolio/fonts/``, which stay untouched:

* the width axis is pinned at 100 (the site never sets ``font-stretch``); the weight
  axis (100-900) is kept;
* each style is split into a core file (``saira-latin.woff2``,
  ``saira-italic-latin.woff2``: Basic Latin, Latin-1, punctuation, arrows, euro, ẞ) and
  an extension file with every other Saira character (``*-latin-ext.woff2``). The
  ``@font-face`` rules in ``css/site-overrides.css`` carry matching
  ``unicode-range`` values, so browsers only fetch an extension file when a page uses
  one of its characters;
* ``font-display: optional``: if a font is not there by the first paint, that page
  view keeps the fallback font instead of swapping later and shifting the layout.
  To make the font arrive in time, ``cast/bootstrap5/base.html`` preloads the upright
  core file on every page (block ``font_preloads``), and the blog list also preloads
  the italic core file because its hero intro is italic.

Regenerate the files and the generated ``@font-face`` block (between the
``saira-fonts`` markers in ``site-overrides.css``) after changing the source fonts or
the core range in ``scripts/subset_saira_fonts.py``::

    just site-fonts

The script is deterministic and copies ``SAIRA-LICENSE.txt`` next to the files.

Troubleshooting
~~~~~~~~~~~~~~~

* ``just cleanup`` - Kill any leftover processes from previous runs
* ``just troubleshoot`` - Show common issues and solutions

Common Issues
-------------

Port Already in Use
~~~~~~~~~~~~~~~~~~~

If you see "Port 8000 already in use" or similar::

    just cleanup  # Kill leftover processes
    just dev      # Try again

Or force restart everything::

    just dev-force

Checking What's Using a Port
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    lsof -i :8000  # Check Django port
    lsof -i :5432  # Check PostgreSQL port

Development Logging
-------------------

All services log to ``logs/dev.log`` with:

* Color codes stripped for readability
* Process prefixes (``[django]``, ``[postgres]``, etc.)
* Timestamps from each service

The log file is git-ignored and perfect for debugging or for AI assistants to read when helping with development.

Browser Console Access
~~~~~~~~~~~~~~~~~~~~~~

When using browser automation tools (like Playwright MCP), browser console messages can be captured through the automation tool's console message API.

Working with Honcho
-------------------

The project uses ``honcho`` (installed via ``uvx``) to manage multiple processes defined in the ``Procfile``. This ensures:

* All services start and stop together
* Proper signal handling for clean shutdowns
* Color-coded output for different services
* Process output is properly interleaved

You can also run services individually if needed::

    # Just PostgreSQL
    just postgres

    # Just Django
    uv run python manage.py runserver

    # Just JupyterLab
    uv run python commands.py jupyterlab

Code Style and Linting
----------------------

The project uses several tools to maintain code quality and consistency:

Code Formatters
~~~~~~~~~~~~~~~

* **Black**: Automatic code formatting with 119 character line length
* **isort**: Import sorting with Black-compatible profile

Both are configured in ``pyproject.toml``::

    [tool.black]
    line-length = 119

    [tool.isort]
    profile = "black"

To format code manually::

    uv run black .
    uv run isort .

Linting Tools
~~~~~~~~~~~~~

* **flake8**: Style guide enforcement (included in dev dependencies)
* **mypy**: Static type checking

Run type checking::

    uv run python commands.py mypy

Best Practices
~~~~~~~~~~~~~~

1. Run formatters before committing code
2. Use type hints where appropriate, especially for function signatures
3. Follow existing code patterns and conventions
4. Keep line length under 119 characters (enforced by Black)


Work on Local Package Checkouts
-------------------------------

``django-cast``, ``cast-bootstrap5``, ``cast-vue``, ``django-indieweb`` and
``django-resume`` are installed from Git by default. Two commands rewrite their
entries in ``[tool.uv.sources]`` of ``pyproject.toml`` and then run ``uv sync``::

    uv run commands.py switch-to-dev-environment   # editable ../<package> checkouts
    uv run commands.py switch-to-git-sources       # back to the Git sources

``switch-to-dev-environment`` only switches packages whose checkout exists next to
this repository.

If ``uv sync`` exits with an error or cannot be started, the command exits with
status 1 and does not report success. ``pyproject.toml`` is **not** rolled back: it
keeps the new source entries while the installed environment is still the old one.
Fix the cause (a missing checkout, an unreachable Git remote, an incompatible
dependency) and run the same command again, or run the opposite switch command to go
back.

``uv run`` syncs the environment from ``pyproject.toml`` before it starts
``commands.py``. With sources that cannot be installed it fails in the same way and the
command never starts. Recover with ``--no-sync``, which runs the command in the
environment as it is::

    uv run --no-sync commands.py switch-to-git-sources

Add Dependencies to be Editable by Claude
-----------------------------------------

All dev dependencies::

    /add-dir ../django-cast
    /add-dir ../cast-bootstrap5
    /add-dir ../django-indieweb
    /add-dir ../django-resume
    /add-dir ../cast-vue
