"""
Webmention integration for django-cast blog posts.

This module handles automatic sending of webmentions when blog posts are published
through Wagtail's publishing workflow.
"""

from urllib.parse import urlsplit, urlunsplit

from django.dispatch import receiver
from wagtail.signals import page_published

# These will be imported inside the function to avoid circular imports
Post = None
Episode = None
WebmentionSender = None


@receiver(page_published)
def send_webmentions_on_publish(sender, **kwargs):
    """
    Send webmentions when a blog post is published.

    This handler:
    1. Listens for Wagtail page_published signals
    2. Checks if the published page is a django-cast Post or Episode
    3. Extracts URLs from the post content
    4. Sends webmentions to all external URLs that support them
    """
    global Post, Episode, WebmentionSender

    page = kwargs["instance"]

    # Import here to avoid circular imports
    if Post is None or Episode is None:
        try:
            from cast.models import Episode as _Episode
            from cast.models import Post as _Post

            Post = _Post
            Episode = _Episode
        except ImportError:
            # django-cast not installed
            return

    # Only process Post and Episode pages
    if not isinstance(page.specific, (Post, Episode)):
        return

    post = page.specific

    # Import webmention sender
    if WebmentionSender is None:
        try:
            from indieweb.senders import WebmentionSender as _WebmentionSender

            WebmentionSender = _WebmentionSender
        except ImportError:
            # django-indieweb not installed
            return

    # Get the full URL of the post
    full_url = post.get_full_url()

    # Create a minimal request object for rendering
    from django.test import RequestFactory

    request_factory = RequestFactory()
    request = request_factory.get(full_url)

    # Use get_description with render_detail=True to get the full content
    html_content = post.get_description(request=request, render_detail=True, escape_html=False, remove_newlines=False)

    # Send webmentions
    sender = WebmentionSender()
    results = sender.send_webmentions(source_url=full_url, html_content=html_content)

    # Log results
    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count

    if results:
        print(f"Webmentions sent for {full_url}: {success_count} successful, {fail_count} failed")

        # Individual results for debugging. Targets come from the post content, so
        # only scheme, host and path are printed: no query string, fragment or
        # credentials, and no free-form error text (it can quote the full URL).
        for result in results:
            target = _loggable_url(result["target"])
            if result["success"]:
                print(f"  ✓ Sent webmention to {target}")
            else:
                reason = "error" if "error" in result else "rejected"
                print(f"  ✗ Failed to send to {target} ({reason})")


def _loggable_url(url) -> str:
    """Return ``url`` reduced to scheme, host, port and path."""
    try:
        parts = urlsplit(str(url))
        host = parts.hostname or ""
        port = parts.port
    except ValueError:
        return "<unparseable URL>"
    if ":" in host:
        host = f"[{host}]"
    if port is not None:
        host = f"{host}:{port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))
