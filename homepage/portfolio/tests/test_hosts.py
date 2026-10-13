import pytest
from django.core.exceptions import DisallowedHost
from django.urls import resolve

from homepage.portfolio.hosts import PORTFOLIO_URLCONF, PortfolioHostMiddleware, is_portfolio_host, portfolio_page_path
from homepage.portfolio.views import admin_theme_css


@pytest.mark.parametrize("configured_host", ["design.example.test", "DESIGN.EXAMPLE.TEST."])
@pytest.mark.parametrize("request_host", ["design.example.test", "DESIGN.EXAMPLE.TEST.", "design.example.test.:8000"])
def test_equivalent_hosts_select_portfolio_root_and_admin_theme(settings, rf, configured_host, request_host):
    settings.PORTFOLIO_HOSTS = [configured_host]
    settings.ALLOWED_HOSTS = ["design.example.test"]
    request = rf.get("/", HTTP_HOST=request_host)

    PortfolioHostMiddleware(lambda request: None)(request)

    assert request.urlconf == PORTFOLIO_URLCONF
    assert resolve("/", urlconf=request.urlconf).url_name == "wagtail_serve"
    response = admin_theme_css(request)
    assert response.status_code == 302
    assert response["Location"] == "/static/portfolio/admin.css"


def test_unrelated_host_keeps_main_routes_and_admin_theme(settings, rf):
    settings.PORTFOLIO_HOSTS = ["design.example.test."]
    settings.ALLOWED_HOSTS = ["main.example.test"]
    request = rf.get("/", HTTP_HOST="main.example.test.")

    PortfolioHostMiddleware(lambda request: None)(request)

    assert not hasattr(request, "urlconf")
    response = admin_theme_css(request)
    assert response.status_code == 200
    assert response.content == b""


def test_portfolio_configuration_does_not_bypass_allowed_hosts(settings, rf):
    settings.PORTFOLIO_HOSTS = ["design.example.test"]
    settings.ALLOWED_HOSTS = ["main.example.test"]
    request = rf.get("/", HTTP_HOST="design.example.test.")

    with pytest.raises(DisallowedHost):
        PortfolioHostMiddleware(lambda request: None)(request)


@pytest.mark.parametrize("hostname", [None, "", "design.example.test..", "other.example.test."])
def test_nonmatching_hostnames(settings, hostname):
    settings.PORTFOLIO_HOSTS = ["design.example.test."]

    assert not is_portfolio_host(hostname)


@pytest.mark.parametrize("root_url", ["https://design.example.test", "https://design.example.test.:8000"])
def test_page_paths_use_the_canonical_portfolio_host(settings, root_url):
    settings.PORTFOLIO_HOSTS = ["DESIGN.EXAMPLE.TEST."]

    assert portfolio_page_path(root_url, "/blogs/projekt/") == "/projekt/"
    assert portfolio_page_path("https://other.example.test.", "/blogs/projekt/") == "/blogs/projekt/"
