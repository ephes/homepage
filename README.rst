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
