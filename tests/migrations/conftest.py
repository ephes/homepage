import pytest


@pytest.fixture(scope="session", autouse=True)
def require_migrations(request):
    if request.config.getoption("nomigrations"):
        raise pytest.UsageError("Run migration regressions with --migrations --create-db")
