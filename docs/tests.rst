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
``pyproject.toml`` and requires ``django-coverage-plugin``, which is included
in the locked development dependencies. ``uv sync --locked`` installs the plugin;
no separate installation is needed.

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
  (add ordinary application test roots here; migration regressions deliberately run separately)
* ``DJANGO_SETTINGS_MODULE``: Uses the test-specific Django settings
* ``--reuse-db``: Reuses the test database between runs for faster testing
* ``--no-migrations``: Skips migrations during the application suite for speed
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
tests, and loads the Django coverage plugin from the development dependencies. The coverage
settings in ``pyproject.toml`` are not used by the default command while
``.coveragerc`` is present.

Installing the plugin fixes coverage startup, but does not enable template
coverage with the current test settings. The default coverage core on Python 3.14 and later
(``sysmon``) does not support plugin file tracers and emits a warning. With
``COVERAGE_CORE=ctrace``, the plugin requires template debugging, which
``config.settings.test`` disables. Coverage can warn, disable the plugin, and
continue successfully with Python coverage only; a successful command does not
guarantee template coverage.

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

Migration regressions
---------------------

Run ``uv run --locked pytest --migrations --create-db -p no:sugar tests/migrations``
to exercise real MigrationExecutor/schema changes on a separate, freshly created
test database. CI runs this after the application suite. Keep it separate because
Wagtail's data migrations create default pages/sites that application fixtures
intentionally construct themselves. All migration fixtures contain synthetic content.

The two-alias regression builds the secondary schema from current models and
copies the default test database's applied migration history before using the
real executor for portfolio migrations. This avoids unrelated historical Wagtail
data migrations that write through default managers. Synthetic pages and both
live/latest revision encodings are checked on both aliases in both directions.

Portfolio browser regressions
-----------------------------

Install Chromium with ``uv run --locked playwright install --with-deps chromium``
(on supported local systems, ``playwright install chromium`` is sufficient when
system libraries already exist). Run
``uv run --locked pytest --create-db -p no:sugar tests/browser``.
``PLAYWRIGHT_BROWSERS_PATH`` may select a writable browser cache.

The gate renders only synthetic Wagtail homepage/project fixtures, serves their
production scripts/styles/fonts through intercepted browser requests, and
rejects external resources. Chromium exercises desktop and narrow viewports,
reduced motion, native link gestures, keyboard focus/inert cleanup, hover, and
single/multiple-touch chapter routing. WebGL is disabled in that navigation fixture.

``tests/browser/test_hero_runtime.py`` separately executes the complete shipped
hero script and stylesheet on synthetic HTML. It controls the WebGL API, frame
queue, font promises and clock, while retaining real DOM, Canvas2D and navigation
events. Context/shader/startup/frame faults must reveal readable fallback content
and stop animation; pending/rejected/fulfilled/late fonts must start exactly once
within the 1.5 second fallback deadline. This is lifecycle/error-boundary evidence,
not a GPU rendering or performance test. A reel dependency fault verifies that
later tile, cursor and SVG motion controls survive a failed initializer; native
navigation remains usable. Repeated
visibility/intersection/live reduced-motion transitions check zero-or-one pending
frame ownership, including overlapping pause reasons and initially reduced motion. The Python 3.14 CI
job runs this gate after the application and migration suites. These regressions
stay outside the default application testpaths because Chromium is an explicit
prerequisite.

Page lookup identity contracts
------------------------------

``uv run --locked pytest homepage/core/tests/test_page_lookup.py`` directly
checks the shared Webmention/Micropub helper, independently of wrapper policy.
Synthetic sites sharing a hostname have distinct roots and colliding slugs:
explicit ports select their own root, omitted HTTP/HTTPS ports select 80/443,
and malformed ports fail lookup. Wagtail's default-site and unique-hostname
fallbacks are intentional; ambiguous hosts without a default return no page.

Generic specific page instances are resolved below nested site roots using the
full ancestor path, including decoded Unicode. Query strings and fragments do
not change identity, and application routes are excluded. Draft and restricted
pages remain available to callers; lookup itself grants no visibility or access.
