"""
Webmention integration for django-cast blog posts.

This module handles automatic sending of webmentions when blog posts are published
through Wagtail's publishing workflow.
"""

from django.dispatch import receiver
from wagtail.signals import page_published


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
    page = kwargs["instance"]

    # Import here to avoid circular imports
    try:
        from cast.models import Episode, Post
    except ImportError:
        # django-cast not installed
        return

    # Only process Post and Episode pages
    if not isinstance(page.specific, (Post, Episode)):
        return

    post = page.specific

    # Import webmention sender
    try:
        from indieweb.senders import WebmentionSender
    except ImportError:
        # django-indieweb not installed
        return

    # Get the full URL of the post
    full_url = post.get_full_url()

    # Get the rendered HTML content from the body StreamField
    # Using __html__() method which doesn't require a request object
    html_content = post.body.__html__()

    # Send webmentions
    sender = WebmentionSender()
    results = sender.send_webmentions(source_url=full_url, html_content=html_content)

    # Log results
    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count

    if results:
        print(f"Webmentions sent for {full_url}: {success_count} successful, {fail_count} failed")

        # Log individual results for debugging
        for result in results:
            if result["success"]:
                print(f"  ✓ Sent webmention to {result['target']}")
            else:
                print(f"  ✗ Failed to send to {result['target']}: {result['error']}")
