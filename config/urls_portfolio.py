"""URL configuration for hosts in ``PORTFOLIO_HOSTS`` (e.g. design.wersdoerfer.de).

The portfolio is its own Wagtail site there, so Wagtail serves its page tree from
``/``. Admin, blog and all other routes stay on the main host (``config.urls``).
"""

from django.urls import include, path
from wagtail import urls as wagtail_urls

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
    path("", include(wagtail_urls)),
]
