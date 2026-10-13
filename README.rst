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
configuration requires the separately installed ``django-coverage-plugin``;
without it, coverage fails before running tests (see ``docs/tests.rst``).

Lint
^^^^

::

    $ flake8

Continuous Integration
^^^^^^^^^^^^^^^^^^^^^^

GitHub Actions (``.github/workflows/ci.yml``) runs on every push and pull request:

* ``lint``: the pre-commit hooks via ``uv run prek run --all-files``
* ``test``: ``pytest`` against a PostgreSQL 17 service container (Python 3.14,
  ``uv sync --locked``), with dummy AWS settings; test settings keep uploads in memory

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
