from django.shortcuts import render
from wagtail.models import Site

from .models import ErrorPageSettings, PortfolioIndexPage


def error_501(request):
    """Render the site-specific, editable placeholder with its real status."""

    site = Site.find_for_request(request)
    if site:
        error_settings = ErrorPageSettings.objects.filter(site=site).first() or ErrorPageSettings(site=site)
    else:
        error_settings = ErrorPageSettings()
    portfolio_index = None
    if site:
        portfolio_index = (
            PortfolioIndexPage.objects.live()
            .public()
            .descendant_of(site.root_page, inclusive=True)
            .first()
        )
    portfolio_projects = list(portfolio_index.get_portfolio_projects().order_by("path")) if portfolio_index else []
    return render(
        request,
        "portfolio/501.html",
        {
            "error_settings": error_settings,
            "portfolio_index": portfolio_index,
            "portfolio_projects": portfolio_projects,
            "featured_projects": portfolio_projects[:2],
        },
        status=501,
    )
