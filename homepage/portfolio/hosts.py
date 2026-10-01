"""Hostnames that serve the portfolio as its own site.

On these hosts Wagtail's page tree is served from ``/`` (``config.urls_portfolio``)
instead of ``/blogs/``. Every other host keeps the main URL configuration.
"""

from urllib.parse import urlsplit

from django.conf import settings
from django.urls import reverse

PORTFOLIO_URLCONF = "config.urls_portfolio"


def is_portfolio_host(hostname):
    return bool(hostname) and hostname.lower() in {host.lower() for host in settings.PORTFOLIO_HOSTS}


def portfolio_page_path(root_url, page_path):
    """Rewrite a Wagtail page path for a portfolio host.

    ``page_path`` was reversed with the URL configuration that is active right now
    (``/blogs/...`` on the main host, ``/...`` on a portfolio host). Pages of a site
    on a portfolio host always live below ``/`` there.
    """

    if page_path is None or not is_portfolio_host(urlsplit(root_url or "").hostname):
        return page_path
    current_prefix = reverse("wagtail_serve", args=("",))
    portfolio_prefix = reverse("wagtail_serve", args=("",), urlconf=PORTFOLIO_URLCONF)
    if not page_path.startswith(current_prefix):
        return page_path
    return portfolio_prefix + page_path.removeprefix(current_prefix)


class PortfolioHostMiddleware:
    """Serve requests for a portfolio host with the portfolio URL configuration."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if is_portfolio_host(request.get_host().rsplit(":", 1)[0]):
            request.urlconf = PORTFOLIO_URLCONF
        return self.get_response(request)
