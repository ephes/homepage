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

Docs
^^^^

::

    $ cd docs
    $ make html
