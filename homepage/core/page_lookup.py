"""
Helpers for mapping public URLs back to Wagtail pages.

Used by the Webmention URL resolver and the Micropub handler so both resolve
URLs through the Wagtail page tree (site root -> blog -> post) instead of
matching bare slugs across all blogs.
"""

from urllib.parse import ParseResult, unquote, urlparse

from django.urls import Resolver404, resolve
from wagtail.models import Page
from wagtail.models import Site as WagtailSite
from wagtail.models.sites import get_site_for_hostname


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

    Only URLs routed to Wagtail's ``serve`` view are considered. The page is looked
    up by its ``url_path`` below the matching site's root page, so the lookup is
    scoped to the full parent chain rather than the last path segment. Visibility
    (live / public) and permissions are left to the caller.
    """
    parsed = urlparse(url)
    if not parsed.path:
        return None
    try:
        # Wagtail emits percent-encoded URLs for Unicode slugs; Django resolves decoded paths.
        match = resolve(unquote(parsed.path))
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
    page = Page.objects.filter(url_path=url_path).first()
    return page.specific if page is not None else None
