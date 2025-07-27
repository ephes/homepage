Development Setup
=================

This guide covers setting up and running the development environment for the homepage project.

Prerequisites
-------------

* Python 3.12+
* uv (Python package manager)
* PostgreSQL (or Docker for running PostgreSQL)
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

Deployment
~~~~~~~~~~

* ``just deploy-staging`` - Deploy to staging environment
* ``just deploy-production`` - Deploy to production environment

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
    postgres -D databases/postgres

    # Just Django
    uv run python manage.py runserver

    # Just JupyterLab
    uv run python commands.py jupyterlab


Add Dependencies to be Editable by Claude
-----------------------------------------

All dev dependencies::

    /add-dir ../django-dast
    /add-dir ../cast-bootstrap5
    /add-dir ../django-indieweb
    /add-dir ../cast-vue
