"""URL configuration for hosts in ``PORTFOLIO_HOSTS`` (e.g. design.wersdoerfer.de).

The portfolio is its own Wagtail site there, so Wagtail serves its page tree from
``/``. The Wagtail admin is available as well and carries the portfolio's admin
theme. Everything else is a 404 (``portfolio_views.not_found_fallback``). The main
site's routes are appended after that fallback: they are never matched on this host,
but templates (admin, error pages) can still reverse them.
"""

from django.conf import settings
from django.urls import include, path, re_path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from config import urls as main_urls
from homepage.core import views as core_views
from homepage.portfolio import views as portfolio_views

# The main site's error pages link to routes that do not exist on this host.
handler400 = portfolio_views.bad_request
handler403 = portfolio_views.permission_denied
handler404 = portfolio_views.page_not_found
handler500 = portfolio_views.server_error

urlpatterns = [
    path("robots.txt", core_views.robots_txt, name="robots_txt"),
    path("favicon.ico", core_views.favicon),
    path("impressum/", portfolio_views.imprint, name="portfolio_imprint"),
    path("datenschutz/", portfolio_views.privacy, name="portfolio_privacy"),
    path("portfolio/", include("homepage.portfolio.urls", namespace="portfolio")),
    path(settings.WAGTAILADMIN_BASE_URL, include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("", include(wagtail_urls)),
    # Wagtail's route only matches slash-terminated word segments; nothing below may match.
    re_path(r"", portfolio_views.not_found_fallback),
] + [
    # The main site's Wagtail mount (/blogs/) would make wagtail_serve reverse to it.
    pattern
    for pattern in main_urls.urlpatterns
    if getattr(pattern, "urlconf_name", None) is not wagtail_urls
]
