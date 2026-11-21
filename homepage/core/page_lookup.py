"""
Helpers for mapping public URLs back to Wagtail pages.

Micropub uses the generic route lookup. Webmention shares the site selection
and URL path parsing, and looks up Cast blogs and posts directly.
"""

from urllib.parse import ParseResult, unquote, urlparse

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import Resolver404, resolve
from wagtail.models import Page
from wagtail.models import Site as WagtailSite
from wagtail.models.sites import get_site_for_hostname

from homepage.portfolio.hosts import PORTFOLIO_URLCONF, is_portfolio_host


def get_wagtail_site(parsed_url: ParseResult) -> WagtailSite | None:
    """Return the Wagtail site that serves ``parsed_url``.

    Uses Wagtail's own hostname/port selection (exact hostname+port, then
    hostname on the default site, then the default site), as request routing does.
    """
    try:
        port = parsed_url.port
    except ValueError:
        return None
    if port is None:
        port = 443 if parsed_url.scheme == "https" else 80
    try:
        return get_site_for_hostname((parsed_url.hostname or "").lower(), port)
    except WagtailSite.DoesNotExist:
        # No hostname match and no default site, as in Wagtail's request routing.
        return None


def url_path_parts(parsed_url: ParseResult) -> list[str]:
    """Return the percent-decoded, non-empty path segments of ``parsed_url``."""
    return [part for part in unquote(parsed_url.path).strip("/").split("/") if part]


def find_page_for_url(url: str) -> Page | None:
    """Return the specific Wagtail page that ``url`` would be served from, or ``None``.

    The target hostname selects the URLconf. Only URLs routed to Wagtail's
    ``serve`` view are considered. The page is looked up by its ``url_path`` below the
    matching site's root page, so the lookup uses the full parent chain. Visibility
    (live / public) and permissions are left to the caller.
    """
    parsed = urlparse(url)
    if not parsed.path:
        return None
    urlconf = PORTFOLIO_URLCONF if is_portfolio_host(parsed.hostname) else settings.ROOT_URLCONF
    try:
        # Wagtail emits percent-encoded URLs for Unicode slugs; Django resolves decoded paths.
        match = resolve(unquote(parsed.path), urlconf=urlconf)
    except Resolver404:
        return None
    if match.url_name != "wagtail_serve" or not match.args:
        return None

    site = get_wagtail_site(parsed)
    if site is None:
        return None

    relative_path = match.args[0].strip("/")
    url_path = site.root_page.url_path
    if relative_path:
        url_path = f"{url_path}{relative_path}/"
    alias = site._state.db
    identity = Page.objects.using(alias).filter(url_path=url_path).values_list("pk", "content_type_id").first()
    if identity is None:
        return None

    page_id, content_type_id = identity
    try:
        content_type = ContentType.objects.db_manager(alias).get_for_id(content_type_id)
    except ContentType.DoesNotExist:
        return None
    # Match Wagtail's fallback for a content type whose model is unavailable.
    model = content_type.model_class() or Page
    try:
        return model._default_manager.using(alias).get(pk=page_id)
    except model.DoesNotExist:
        return None
