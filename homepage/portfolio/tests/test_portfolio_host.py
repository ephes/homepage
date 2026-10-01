import pytest
from django.core.management import call_command
from wagtail.models import Locale, Page, Site

from homepage.portfolio.models import PortfolioIndexPage

from .test_pages import add_project

pytestmark = pytest.mark.django_db

PORTFOLIO_HOST = "design.example.test"


@pytest.fixture
def portfolio_site(settings):
    """Mirror production: the main site's root is /home/, the portfolio is a sibling tree."""

    settings.PORTFOLIO_HOSTS = [PORTFOLIO_HOST]
    settings.ALLOWED_HOSTS = ["testserver", PORTFOLIO_HOST]
    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node() or Page.add_root(instance=Page(title="Root", slug="root"))
    home = root.add_child(instance=Page(title="Home", slug="home"))
    Site.objects.update_or_create(
        hostname="testserver",
        defaults={"root_page": home, "is_default_site": True, "site_name": "Main"},
    )
    call_command("seed_portfolio", create=True, hostname=PORTFOLIO_HOST)
    index = PortfolioIndexPage.objects.get()
    index.save_revision().publish()
    return index


def test_seed_creates_the_portfolio_as_root_page_of_its_own_site(portfolio_site):
    site = Site.objects.get(hostname=PORTFOLIO_HOST)

    assert site.root_page_id == portfolio_site.pk
    assert portfolio_site.get_parent().pk == Page.get_first_root_node().pk
    assert not site.is_default_site


def test_portfolio_pages_are_served_below_root_on_the_portfolio_host(client, portfolio_site):
    project = add_project(portfolio_site)

    assert portfolio_site.get_url_parts()[2] == "/"
    assert portfolio_site.full_url == f"https://{PORTFOLIO_HOST}/"
    assert project.full_url == f"https://{PORTFOLIO_HOST}/{project.slug}/"
    assert client.get("/", HTTP_HOST=PORTFOLIO_HOST).status_code == 200
    assert client.get(f"/{project.slug}/", HTTP_HOST=PORTFOLIO_HOST).status_code == 200
    assert client.get("/blogs/", HTTP_HOST=PORTFOLIO_HOST).status_code == 404


def test_legal_and_error_pages_work_on_the_portfolio_host(client, portfolio_site):
    assert client.get("/impressum/", HTTP_HOST=PORTFOLIO_HOST).status_code == 200
    assert client.get("/datenschutz/", HTTP_HOST=PORTFOLIO_HOST).status_code == 200
    assert client.get("/portfolio/501/", HTTP_HOST=PORTFOLIO_HOST).status_code == 501


def test_main_host_keeps_its_routes_and_does_not_serve_the_portfolio(client, portfolio_site):
    assert client.get("/impressum/").status_code == 404
    assert client.get("/blogs/portfolio/").status_code == 404
    assert client.get("/robots.txt").status_code == 200


def test_portfolio_urls_are_rendered_for_the_portfolio_host_from_the_main_host(rf, portfolio_site):
    project = add_project(portfolio_site)
    request = rf.get("/cms/", HTTP_HOST="testserver")

    assert project.get_url(request=request) == f"https://{PORTFOLIO_HOST}/{project.slug}/"


def test_unknown_paths_on_the_portfolio_host_get_the_portfolio_404(client, portfolio_site):
    response = client.get("/gibt-es-nicht/", HTTP_HOST=PORTFOLIO_HOST)

    assert response.status_code == 404
    assert "Seite nicht gefunden" in response.content.decode()


def test_seed_site_port_is_configurable_for_local_development(settings):
    settings.PORTFOLIO_HOSTS = ["design.localhost"]
    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node() or Page.add_root(instance=Page(title="Root", slug="root"))
    root.add_child(instance=Page(title="Home", slug="home"))

    call_command("seed_portfolio", create=True, hostname="design.localhost", port=8000)

    site = Site.objects.get(hostname="design.localhost")
    assert site.port == 8000
    assert site.root_url == "http://design.localhost:8000"


def test_wagtail_admin_is_available_on_the_portfolio_host(client, portfolio_site, django_user_model):
    admin = django_user_model.objects.create_superuser("admin", "admin@example.com", "pw")
    client.force_login(admin)

    response = client.get("/cms/", HTTP_HOST=PORTFOLIO_HOST)

    assert response.status_code == 200
    assert 'href="/portfolio/admin-theme.css"' in response.content.decode()


@pytest.mark.parametrize(
    "path",
    ["/@jochen", "/.well-known/webfinger", "/blogs/ephes_blog/feed/rss.xml", "/accounts/login/", "/users/"],
)
def test_main_site_routes_are_not_served_on_the_portfolio_host(client, portfolio_site, path):
    response = client.get(path, HTTP_HOST=PORTFOLIO_HOST)

    assert response.status_code == 404


def test_missing_trailing_slash_still_redirects_on_the_portfolio_host(client, portfolio_site):
    response = client.get("/impressum", HTTP_HOST=PORTFOLIO_HOST)

    assert response.status_code == 301
    assert response["Location"] == "/impressum/"
