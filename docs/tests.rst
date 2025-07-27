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
    DJANGO_SETTINGS_MODULE = "config.settings.test"
    addopts = [
        "-ra",
        "--reuse-db",
        "--no-migrations",
    ]

Key settings:

* ``DJANGO_SETTINGS_MODULE``: Uses the test-specific Django settings
* ``--reuse-db``: Reuses the test database between runs for faster testing
* ``--no-migrations``: Skips migrations during test runs for speed
* ``-ra``: Shows a short summary of all test outcomes

Coverage Configuration
----------------------

Coverage is configured in ``pyproject.toml``:

.. code-block:: toml

    [tool.coverage.run]
    branch = true
    source = ["apps"]
    omit = ["apps/*/tests/*", "apps/*/migrations/*"]
    command_line = "-m pytest"

This configuration:

* Tracks branch coverage for more detailed analysis
* Focuses on the ``apps`` directory
* Excludes test files and migrations from coverage

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
