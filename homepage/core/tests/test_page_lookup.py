"""URL identity only: visibility and authorization belong to the callers."""

from urllib.parse import urlparse

import pytest
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
