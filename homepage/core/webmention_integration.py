"""
Webmention integration for django-cast blog posts.

This module handles automatic sending of webmentions when blog posts are published
through Wagtail's publishing workflow.

Only publicly accessible publications emit webmentions, and only after the
publication has been committed:

* a page with a Wagtail view restriction (its own or one inherited from an
  ancestor) is neither rendered nor announced, because a webmention tells
  third-party endpoints the source URL and which links the page contains;
* the outbound work runs in an ``on_commit`` callback, so a publication inside
  a transaction that is rolled back announces nothing. Without an open
  transaction Django calls the callback at once, inside the signal receiver;
* delivery is best effort: a failure is logged and never undoes or fails the
  committed publication.
"""

import logging
from functools import partial
from urllib.parse import urlsplit, urlunsplit

from django.db import transaction
from django.dispatch import receiver
from wagtail.signals import page_published

logger = logging.getLogger(__name__)

# These will be imported inside the function to avoid circular imports
Post = None
Episode = None
WebmentionSender = None


@receiver(page_published)
def send_webmentions_on_publish(sender, **kwargs):
    """
    Schedule webmentions for a published blog post.

    This handler:
    1. Listens for Wagtail page_published signals
    2. Checks if the published page is a django-cast Post or Episode
    3. Ignores pages that are not publicly accessible
    4. Schedules the delivery for after the surrounding transaction commits

    Inside a transaction nothing is rendered and no request leaves the process
    before the commit. Without one, ``on_commit`` runs the delivery immediately.
    """
    page = kwargs["instance"]

    if not _load_post_models():
        # django-cast not installed
        return

    # Only process Post and Episode pages
    post = page.specific
    if not isinstance(post, (Post, Episode)):
        return

    if not _is_publicly_accessible(post):
        return

    # Only ids cross the commit boundary: the page is read again afterwards, so
    # the delivery sees what was committed rather than this in-memory instance.
    deliver = partial(_deliver_webmentions, post.pk, post.live_revision_id)
    transaction.on_commit(deliver)


def _load_post_models() -> bool:
    global Post, Episode

    if Post is None or Episode is None:
        try:
            from cast.models import Episode as _Episode
            from cast.models import Post as _Post
        except ImportError:
            return False
        Post = _Post
        Episode = _Episode
    return True


def _is_publicly_accessible(page) -> bool:
    """Return whether anonymous visitors may view ``page``.

    Wagtail view restrictions (login, password, groups) apply to a page and to
    everything below it, so the page's ancestors are checked as well.
    """
    return not page.get_view_restrictions().exists()


def _deliver_webmentions(page_id, live_revision_id) -> None:
    """Send the webmentions of a committed publication; never raises.

    Runs after the publishing transaction committed. The publication is done at
    this point, so a failure here is reported and swallowed: it must not turn a
    successful publication into an error response. Only the exception class is
    logged, because the message can quote URLs from the post content.
    """
    try:
        post = _committed_public_post(page_id, live_revision_id)
        if post is not None:
            _send_webmentions_for(post)
    except Exception as exc:
        logger.warning("Webmention delivery failed for page %s: %s", page_id, type(exc).__name__)


def _committed_public_post(page_id, live_revision_id):
    """Return the committed post to announce, or ``None`` when there is none.

    The page is skipped when it no longer exists or is no longer live, when a
    different revision went live in the meantime (that publication schedules its
    own delivery) and when it is not publicly accessible now.
    """
    from wagtail.models import Page

    page = Page.objects.filter(pk=page_id).first()
    if page is None:
        return None
    # Loading the specific page reads the database again. Every decision below is
    # made on that one instance, which is also the one that gets rendered, so the
    # checks cannot pass on an older read of the page than the content comes from.
    post = page.specific
    if not isinstance(post, (Post, Episode)):
        return None
    if not post.live or post.live_revision_id != live_revision_id:
        return None
    if not _is_publicly_accessible(post):
        return None
    return post


def _send_webmentions_for(post) -> None:
    """Render ``post`` and send webmentions to the external URLs it links to."""
    global WebmentionSender

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
    if not full_url:
        # Not reachable through any site, so there is no source URL to announce.
        return

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
        # The page is named by id: its URL holds a slug taken from the title/content.
        print(f"Webmentions sent for page {post.pk}: {success_count} successful, {fail_count} failed")

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
