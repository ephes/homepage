Homepage
========

Just my own personal site


:License: MIT

Basic Commands
--------------

Running Tests
^^^^^^^^^^^^^

::

    $ pytest

Developer quality commands
^^^^^^^^^^^^^^^^^^^^^^^^^^

Run ``uv run python commands.py test``, ``mypy``, or ``coverage`` (Mypy must be
installed separately). These commands exit zero on success, preserve nonzero
tool exit statuses (signals become 128 + signal number), and exit 1 with a diagnostic if a tool cannot start.
Coverage generates a report only after its tests pass, and opens it on macOS/WSL
only after report generation succeeds. Report failures and macOS opener failures
also fail the command. WSL Explorer return codes are best-effort because Explorer
can return nonzero after successfully opening; failure to start it still exits 1.
``just test`` and ``just coverage`` use these same commands. The committed coverage
configuration uses ``django-coverage-plugin``, included in the locked development
dependencies. ``uv sync --locked`` installs it (see ``docs/tests.rst``).
Template coverage remains unavailable with the current test settings; coverage
can warn and continue with Python coverage only (see ``docs/tests.rst``).

Lint
^^^^

::

    $ flake8

Continuous Integration
^^^^^^^^^^^^^^^^^^^^^^

GitHub Actions (``.github/workflows/ci.yml``) runs on every push and pull request:

* ``audit``: pinned pip-audit against the frozen runtime/development registry graph (see below)
* ``lint``: the pre-commit hooks via ``uv run prek run --all-files`` (Python 3.15.2)
* ``test``: ``pytest`` against a PostgreSQL 17 service container (Python 3.14
  and 3.15.2, uv 0.13.6, ``uv sync --locked``), with dummy AWS settings; test settings keep uploads in memory

User pages
^^^^^^^^^^

User pages under ``/users/`` are not a public member directory. The list at
``/users/`` is for staff only: anonymous visitors are sent to the login page and
logged-in non-staff users get a 403. A profile at ``/users/<username>/`` is shown
to its owner and to staff. Anonymous visitors are sent to the login page; any
other logged-in user gets a 404, so the page does not reveal whether a username
exists.

Docs
^^^^

::

    $ cd docs
    $ make html

Local development services
^^^^^^^^^^^^^^^^^^^^^^^^^^

``just dev`` starts PostgreSQL and Django; ``just dev-all`` or ``./run_dev.sh``
starts the full Procfile. All use ``dev_runner.py`` to own one supervisor per
checkout, stream terminal output and save a colour-stripped ``logs/dev.log``.
``just cleanup`` signals only the runner recorded in ``logs/dev.json`` after
checking its PID, creation time, command and checkout. The runner stops its own
process group on exit, including INT, TERM, HUP and QUIT. ``just dev-force`` cleans up that checkout before starting
again; unrelated servers and notebooks are left alone. Individually started
services are not owned by this runner.

Cleanup refuses stale, legacy or mismatching records. Inspect the recorded
process first, then remove stale ``logs/dev.json`` (or the old ``logs/dev.pid``)
manually after inspecting/stopping any orphaned service PIDs individually; never
use a command-name kill to recover. Startup refuses to overwrite
an existing record. The runner uses POSIX process groups and the locked ``psutil``
development dependency. Install dependencies with ``uv sync --locked`` first.
Supervisor failures produce a nonzero command status (including through logging),
signals become 128 + signal number, and normal exit removes the ownership record.

Locked dependency audit
^^^^^^^^^^^^^^^^^^^^^^^

Run ``python audit_dependencies.py`` locally, exactly as CI does. It exports the
frozen default runtime and development graph without resolving or changing the
lock, then runs ``pip-audit==2.10.1 --strict --disable-pip --no-deps``. Export,
extraction, dependency collection and auditor failures fail the command. Registry
requirements retain their interpreter/platform markers, so the audit covers the
current environment (CI uses Linux/Python 3.15.2). Optional groups and separately
resolved prek hook environments are outside this export.

The five first-party Git requirements (cast-bootstrap5, cast-vue, django-cast,
django-indieweb and django-resume) are printed with their locked commits and
excluded from registry matching; their registry transitives remain audited.
Unexpected sources fail closed. This is not an advisory audit of the Git source
code. ``PIP_AUDIT_CACHE_DIR`` can override the default ``.cache/pip-audit`` cache.

The development lock refresh raises Black to at least 26.10.1 and Tornado to at
least 6.6 for the reported formatter/notebook advisories. Application dependencies
and all five source commits remain pinned. The independent Black prek hook uses
the same fixed formatter release; no application deployment is needed.
