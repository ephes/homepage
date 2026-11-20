"""URL identity only: visibility and authorization belong to the callers."""

from urllib.parse import urlparse

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import connections
from django.test.utils import CaptureQueriesContext
from django.urls import get_urlconf, set_urlconf
from wagtail.models import Locale, Page, PageViewRestriction, Site

from homepage.core.page_lookup import find_page_for_url, get_wagtail_site
from homepage.portfolio.models import PortfolioIndexPage

pytestmark = pytest.mark.django_db


@pytest.fixture
def sites():
    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node() or Page.add_root(instance=Page(title="Root", slug="root"))
    container = root.add_child(instance=Page(title="Container", slug="container"))
    Site.objects.all().delete()
    records = []
    for port in (80, 443, 8000):
        home = container.add_child(instance=Page(title=str(port), slug=f"home-{port}"))
        site = Site.objects.create(hostname="lookup.example", port=port, root_page=home, is_default_site=port == 80)
        page = home.add_child(instance=PortfolioIndexPage(title="Shared", slug="shared"))
        records.append((site, page))
    return records


@pytest.mark.parametrize(
    "index,authority,scheme",
    [
        (0, "lookup.example:80", "http"),
        (1, "lookup.example:443", "https"),
        (2, "lookup.example:8000", "http"),
        (0, "LOOKUP.example", "http"),
        (1, "lookup.example", "https"),
    ],
)
def test_exact_port_and_scheme_defaults(sites, index, authority, scheme):
    site, page = sites[index]
    url = f"{scheme}://{authority}/blogs/shared/"
    assert get_wagtail_site(urlparse(url)).pk == site.pk
    found = find_page_for_url(url)
    assert type(found) is PortfolioIndexPage
    assert found.pk == page.pk


@pytest.mark.parametrize("port", ["invalid", "65536", "-1"])
def test_malformed_port_has_no_page(sites, port):
    url = f"https://lookup.example:{port}/blogs/shared/"
    assert get_wagtail_site(urlparse(url)) is None
    assert find_page_for_url(url) is None


def test_default_site_fallback(sites):
    default, page = sites[0]
    for authority in ("lookup.example:9000", "unknown.example"):
        url = f"https://{authority}/blogs/shared/"
        assert get_wagtail_site(urlparse(url)).pk == default.pk
        assert find_page_for_url(url).pk == page.pk


def test_no_default_site_refuses_unknown_or_ambiguous_host(sites):
    Site.objects.update(is_default_site=False)
    for authority in ("unknown.example", "lookup.example:9000"):
        url = f"https://{authority}/blogs/shared/"
        assert get_wagtail_site(urlparse(url)) is None
        assert find_page_for_url(url) is None
    assert find_page_for_url("https://lookup.example/blogs/shared/").pk == sites[1][1].pk


def test_unique_hostname_fallback_without_default(sites):
    Site.objects.exclude(pk=sites[2][0].pk).delete()
    Site.objects.update(is_default_site=False)
    assert find_page_for_url("https://lookup.example:9000/blogs/shared/").pk == sites[2][1].pk


def test_full_ancestry_unicode_query_and_fragment(sites):
    home = sites[1][0].root_page
    expected = []
    for slug in ("alpha", "beta"):
        parent = home.add_child(instance=Page(title=slug, slug=slug))
        expected.append(parent.add_child(instance=PortfolioIndexPage(title="Grüße", slug="grüße")))
    for slug, page in zip(("alpha", "beta"), expected, strict=True):
        found = find_page_for_url(f"https://lookup.example/blogs/{slug}/gr%C3%BC%C3%9Fe/?q=ignored#fragment")
        assert type(found) is PortfolioIndexPage
        assert found.pk == page.pk
    assert find_page_for_url("https://lookup.example/blogs/gr%C3%BC%C3%9Fe/") is None


def test_draft_and_private_pages_remain_available_to_callers(sites):
    home = sites[1][0].root_page
    for slug, live in (("draft", False), ("private", True)):
        page = home.add_child(instance=PortfolioIndexPage(title=slug, slug=slug, live=live))
        PageViewRestriction.objects.create(page=page, restriction_type="login")
        found = find_page_for_url(f"https://lookup.example/blogs/{slug}/")
        assert type(found) is PortfolioIndexPage
        assert found.pk == page.pk
        assert found.live is live


@pytest.mark.parametrize("path", ["/accounts/login/", "/users/", "/outside-wagtail/", "/blogs/missing/", ""])
def test_application_and_missing_routes_have_no_page(sites, path):
    # A matching page name must not turn an application route into a CMS route.
    sites[1][0].root_page.add_child(instance=Page(title="Users", slug="users"))
    assert find_page_for_url(f"https://lookup.example{path}") is None


def test_resolves_each_target_from_the_other_hosts_request_urlconf(sites, settings):
    portfolio_host = "portfolio.lookup.example"
    settings.PORTFOLIO_HOSTS = [portfolio_host]
    portfolio_site, portfolio_page = sites[2]
    portfolio_site.hostname = portfolio_host
    portfolio_site.port = 443
    portfolio_site.save(update_fields=["hostname", "port"])
    main_page = sites[1][1]

    original_urlconf = get_urlconf()
    try:
        for active_urlconf, url, expected in (
            (settings.ROOT_URLCONF, f"https://{portfolio_host}/shared/", portfolio_page),
            ("config.urls_portfolio", "https://lookup.example/blogs/shared/", main_page),
        ):
            set_urlconf(active_urlconf)
            found = find_page_for_url(url)
            assert found is not None and found.pk == expected.pk
            assert get_urlconf() == active_urlconf
    finally:
        set_urlconf(original_urlconf)


@pytest.mark.django_db(databases=["default", "legacy"])
def test_route_lookup_projects_identity_and_loads_full_page_on_the_site_alias(settings):
    class SiteRouter:
        def db_for_read(self, model, **hints):
            if model is Site:
                return "legacy"
            return None

    class FixtureRouter:
        def db_for_read(self, model, **hints):
            return "legacy"

        def db_for_write(self, model, **hints):
            return "legacy"

    settings.DATABASE_ROUTERS = [FixtureRouter()]
    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node() or Page.add_root(instance=Page(title="Root", slug="root"))
    home = root.add_child(instance=Page(title="Home", slug="legacy-home"))
    specific = home.add_child(
        instance=PortfolioIndexPage(title="Synthetic portfolio", slug="portfolio", hero_intro="Synthetic introduction")
    )
    Site.objects.create(hostname="secondary.example", port=443, root_page=home)

    settings.DATABASE_ROUTERS = [SiteRouter()]
    ContentType.objects.clear_cache()
    legacy = connections["legacy"]
    with CaptureQueriesContext(connections["default"]) as default_queries, CaptureQueriesContext(legacy) as queries:
        found = find_page_for_url("https://secondary.example/blogs/portfolio/")

        assert type(found) is PortfolioIndexPage
        assert found.pk == specific.pk
        assert found._state.db == "legacy"
        assert not found.get_deferred_fields()
        assert found.title == "Synthetic portfolio"
        assert found.hero_intro == "Synthetic introduction"

    assert len(default_queries) == 0
    page_queries = [q["sql"] for q in queries if ' FROM "wagtailcore_page" ' in q["sql"]]
    [probe] = page_queries
    columns = probe.removeprefix("SELECT ").split(" FROM ", 1)[0].split(", ")
    assert [column.split(" AS ", 1)[0] for column in columns] == [
        '"wagtailcore_page"."id"',
        '"wagtailcore_page"."content_type_id"',
    ]
    assert len(queries) == 4  # site, page identity, cold content type, specific model


def test_route_lookup_keeps_full_base_pages_for_unavailable_types(sites, request):
    request.addfinalizer(ContentType.objects.clear_cache)
    home = sites[1][0].root_page
    page = home.add_child(instance=Page(title="Plain page", slug="plain"))
    url = "https://lookup.example/blogs/plain/"

    for content_type in (
        ContentType.objects.get_for_model(Page),
        ContentType.objects.create(app_label="synthetic", model="removedpage"),
    ):
        Page.objects.filter(pk=page.pk).update(content_type=content_type)
        found = find_page_for_url(url)

        assert type(found) is Page
        assert found.pk == page.pk
        assert found.title == "Plain page"
        assert not found.get_deferred_fields()
