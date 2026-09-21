from django.http import Http404
from django.shortcuts import redirect, render
from wagtail import views as wagtail_views
from wagtail.models import Page, Site

from .models import (
    ErrorPageSettings,
    LegalPageSettings,
    PortfolioIndexPage,
    PortfolioSiteSettings,
    get_site_setting_or_default,
)


def _portfolio_index_for_site(site):
    """Return the live portfolio landing page owned by ``site``, if any."""

    if site is None:
        return None
    return (
        PortfolioIndexPage.objects.live()
        .public()
        .descendant_of(site.root_page, inclusive=True)
        .order_by("path")
        .first()
    )


def _wagtail_page_for_request(request, path):
    """Return an exact live Wagtail route result for ``path``, if present."""

    route_result = Page.route_for_request(request, path)
    if route_result is None:
        return None
    # Keep the full live route result. Do not apply ``public()`` here: a page may
    # deliberately carry a view restriction, which Wagtail enforces when it
    # serves the mounted route. RoutablePageMixin also uses the arguments to
    # distinguish a sub-route from the owning page's root URL.
    return route_result


def _portfolio_shell_context(
    *, site, portfolio_index=None, include_legal_sections=False
):
    """Build one site's utility-page shell without exposing lookup internals."""

    if portfolio_index is None:
        portfolio_index = _portfolio_index_for_site(site)
    portfolio_projects = (
        list(portfolio_index.get_portfolio_projects().order_by("path"))
        if portfolio_index
        else []
    )
    portfolio_site_settings = get_site_setting_or_default(PortfolioSiteSettings, site)
    legal_defaults = (
        {} if include_legal_sections else {"imprint_sections": [], "privacy_sections": []}
    )
    portfolio_legal_settings = get_site_setting_or_default(
        LegalPageSettings, site, **legal_defaults
    )
    return {
        "portfolio_index": portfolio_index,
        "portfolio_projects": portfolio_projects,
        "portfolio_site_settings": portfolio_site_settings,
        "portfolio_legal_settings": portfolio_legal_settings,
    }


def error_501(request):
    """Render the site-specific, editable placeholder with its real status."""

    site = Site.find_for_request(request)
    context = _portfolio_shell_context(site=site)
    error_settings = get_site_setting_or_default(ErrorPageSettings, site)
    portfolio_projects = context["portfolio_projects"]
    return render(
        request,
        "portfolio/501.html",
        {
            **context,
            "error_settings": error_settings,
            "featured_projects": portfolio_projects[:2],
        },
        status=501,
    )


def _legal_page(request, *, page_kind):
    """Render one request-site legal document from shared editable settings."""

    site = Site.find_for_request(request)
    route_path = request.path_info.removeprefix("/")
    wagtail_route = _wagtail_page_for_request(request, route_path)
    if wagtail_route is not None:
        wagtail_page, route_args, route_kwargs = wagtail_route
        if route_args or route_kwargs:
            # A routable page can own the legal-looking path as a sub-route.
            # Its canonical page URL does not encode that route, so redirecting
            # there would silently discard the matched endpoint and arguments.
            return wagtail_views.serve(request, route_path)

        # These compatibility routes precede Wagtail's catch-all. Preserve an
        # explicitly published page on every request site, including the site
        # that also owns the portfolio landing page. Wagtail derives the URL
        # from its actual mount point and Django's active script prefix.
        canonical_url = wagtail_page.get_url(request=request)
        if canonical_url != request.path:
            return redirect(canonical_url)
        # If Wagtail is mounted at the root, redirecting would loop back into
        # this compatibility route. Delegate to Wagtail's complete serving
        # pipeline instead so the published page still takes precedence.
        return wagtail_views.serve(request, route_path)

    portfolio_index = _portfolio_index_for_site(site)
    if portfolio_index is None:
        # A live collision was already redirected above. Without one, a site
        # that has no portfolio must not receive the portfolio's legal defaults.
        raise Http404

    context = _portfolio_shell_context(
        site=site,
        portfolio_index=portfolio_index,
        include_legal_sections=True,
    )
    legal_settings = context["portfolio_legal_settings"]
    if page_kind == "imprint":
        title = legal_settings.imprint_title
        sections = legal_settings.imprint_sections
    else:
        title = legal_settings.privacy_title
        sections = legal_settings.privacy_sections
    return render(
        request,
        "portfolio/legal_page.html",
        {
            **context,
            "legal_settings": legal_settings,
            "legal_page_kind": page_kind,
            "legal_title": title,
            "legal_sections": sections,
            "top_anchor": "seitenanfang",
        },
    )


def imprint(request):
    return _legal_page(request, page_kind="imprint")


def privacy(request):
    return _legal_page(request, page_kind="privacy")
