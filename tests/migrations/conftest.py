import pytest


@pytest.fixture(scope="session", autouse=True)
def require_migrations(request):
    if request.config.getoption("nomigrations"):
        raise pytest.UsageError("Run migration regressions with --migrations --create-db")


@pytest.fixture(scope="session")
def django_db_modify_db_settings(django_db_modify_db_settings_parallel_suffix, django_test_environment):
    from django.conf import settings

    # Older upstream Wagtail data migrations write through the default manager.
    # Build the secondary test schema from current models, then exercise our
    # migration with a real executor against that schema.
    settings.DATABASES["legacy"].setdefault("TEST", {})["MIGRATE"] = False
