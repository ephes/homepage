Testing
=======

The project uses pytest as the test framework with Django integration.

Running Tests
-------------

Using Commands.py
~~~~~~~~~~~~~~~~~

Run all tests::

    uv run python commands.py test

Run tests with coverage report::

    uv run python commands.py coverage

The coverage command will:

* Run all tests with coverage tracking
* Generate an HTML coverage report
* Automatically open the report in your browser (macOS/WSL)

``test``, ``mypy`` and ``coverage`` exit zero on success and preserve nonzero
subprocess exit statuses (signal termination becomes 128 + signal number). If a tool cannot start (for example, an executable is
missing), the command prints a diagnostic and exits 1. Install Mypy separately
before using ``uv run python commands.py mypy``.

Coverage stops at the first failed step: failed tests prevent report generation
and opening, and a failed HTML report prevents opening. Stopping before opening
after either failure avoids showing a stale report from a previous run.
A macOS opener failure also makes the command fail. WSL Explorer return codes are best-effort because
Explorer may return nonzero after opening successfully; failure to start Explorer
still exits 1.

The committed ``.coveragerc`` takes precedence over the coverage configuration in
``pyproject.toml`` and requires ``django-coverage-plugin``, which is not included
in the locked development dependencies. Install that plugin separately to use
this configuration. Without it, ``coverage`` fails with exit 1 before tests run.

Using Justfile
~~~~~~~~~~~~~~

Alternatively, use the just commands::

    just test
    just coverage

Test Configuration
------------------

The test configuration is defined in ``pyproject.toml``:

.. code-block:: toml

    [tool.pytest.ini_options]
    testpaths = ["homepage"]
    DJANGO_SETTINGS_MODULE = "config.settings.test"
    addopts = [
        "-ra",
        "--reuse-db",
        "--no-migrations",
    ]

Key settings:

* ``testpaths``: Limits default discovery to application tests, excluding local backup and media trees
  (add any new test roots outside ``homepage`` to this list)
* ``DJANGO_SETTINGS_MODULE``: Uses the test-specific Django settings
* ``--reuse-db``: Reuses the test database between runs for faster testing
* ``--no-migrations``: Skips migrations during test runs for speed
* ``-ra``: Shows a short summary of all test outcomes

Media Storage in Tests
~~~~~~~~~~~~~~~~~~~~~~

Tests never write to the S3 bucket. ``config/settings/test.py`` replaces the ``default`` and
``production`` storages with Django's ``InMemoryStorage`` and sets AWS credentials that S3 rejects,
so an accidental S3 access fails instead of uploading files. ``homepage/tests/test_storage_settings.py``
guards this: it fails if any configured storage backend uses S3.

Coverage Configuration
----------------------

The effective configuration is the committed ``.coveragerc``:

.. code-block:: ini

    [run]
    include = homepage/*
    omit = *migrations*, *tests*
    plugins =
        django_coverage_plugin

This records executed files under ``homepage`` while excluding migrations and
tests, and uses the separately installed Django coverage plugin. The coverage
settings in ``pyproject.toml`` are not used by the default command while
``.coveragerc`` is present.

Test Organization
-----------------

* Test files should be placed in ``homepage/tests/`` or app-specific ``tests/`` directories
* Follow pytest naming conventions:

  * Test files: ``test_*.py`` or ``*_test.py``
  * Test functions: ``test_*``
  * Test classes: ``Test*``

* Use pytest fixtures for test data and setup
* Prefer factory-boy for creating test model instances

Writing Tests
-------------

Example test structure::

    import pytest
    from django.urls import reverse
    from homepage.users.models import User

    @pytest.mark.django_db
    def test_user_creation():
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        assert user.username == 'testuser'
        assert user.check_password('testpass123')

    @pytest.mark.django_db
    def test_homepage_view(client):
        response = client.get(reverse('home'))
        assert response.status_code == 200

Best Practices
--------------

1. **Use pytest fixtures**: Leverage pytest's powerful fixture system for setup and teardown
2. **Mark database tests**: Use ``@pytest.mark.django_db`` for tests that need database access
3. **Use factories**: Use factory-boy to create test data instead of fixtures files
4. **Test isolation**: Each test should be independent and not rely on other tests
5. **Coverage goals**: Aim for high test coverage on new code, especially business logic
6. **Fast tests**: Use ``--reuse-db`` and avoid unnecessary database operations

Continuous Integration
----------------------

Tests are automatically run in CI/CD pipelines. Ensure all tests pass locally before pushing changes.
