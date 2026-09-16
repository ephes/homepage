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
commits for django-cast, django-indieweb, and the Cast themes. django-cast tracks
``develop``, so an update can include unreleased changes even when its package
version is unchanged. Review upstream release notes as well as the commit change.

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
rollback for this refresh. PostgreSQL reported an existing collation-version
mismatch during backup, which needs separate maintenance.

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


Add Dependencies to be Editable by Claude
-----------------------------------------

All dev dependencies::

    /add-dir ../django-cast
    /add-dir ../cast-bootstrap5
    /add-dir ../django-indieweb
    /add-dir ../cast-vue
