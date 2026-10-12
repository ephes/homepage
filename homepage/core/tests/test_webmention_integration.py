import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from cast.models import Blog, Post
from django.db import transaction
from wagtail.models import Locale, Page, PageViewRestriction, Site

from homepage.core.webmention_integration import (
    _deliver_webmentions,
    _send_webmentions_for,
    send_webmentions_on_publish,
)


@pytest.fixture
def mock_page_with_post():
    """Create a mock Page instance with a Post as specific."""
    # Create the Post mock
    post = Mock(spec=Post)
    post.get_full_url.return_value = "https://example.com/post/test-post"
    post.pk = 23

    # Mock the get_description method
    post.get_description.return_value = "<p>This is a test post with a <a href='https://external.com'>link</a>.</p>"

    # Create the Page mock with specific returning the post
    page = Mock()
    page.specific = post

    return page


@pytest.fixture
def mock_webmention_sender():
    """Mock the WebmentionSender class."""
    with patch("homepage.core.webmention_integration.WebmentionSender") as mock_class:
        mock_instance = Mock()
        mock_instance.send_webmentions.return_value = [
            {"target": "https://external.com", "success": True, "response": "Success"}
        ]
        mock_class.return_value = mock_instance
        yield mock_class


class TestWebmentionIntegration:
    def test_send_webmentions_on_publish_success(self, mock_page_with_post, mock_webmention_sender):
        """Test successful webmention sending for a published post."""
        _send_webmentions_for(mock_page_with_post.specific)

        # Get the post from the page
        post = mock_page_with_post.specific

        # Verify get_full_url was called
        post.get_full_url.assert_called_once()

        # Verify get_description was called with correct parameters
        # We don't check the exact request object, just that the method was called with the right params
        assert post.get_description.called
        call_kwargs = post.get_description.call_args.kwargs
        assert call_kwargs["render_detail"] is True
        assert call_kwargs["escape_html"] is False
        assert call_kwargs["remove_newlines"] is False

        # Verify WebmentionSender was used correctly
        mock_webmention_sender.assert_called_once()
        mock_instance = mock_webmention_sender.return_value
        mock_instance.send_webmentions.assert_called_once_with(
            source_url="https://example.com/post/test-post",
            html_content="<p>This is a test post with a <a href='https://external.com'>link</a>.</p>",
        )

    def test_send_webmentions_on_non_post_instance(self, mock_webmention_sender):
        """Test that non-Post instances are ignored."""
        # Create a Page with non-Post specific
        page = Mock()
        page.specific = Mock()  # Not a Post instance

        # Call the signal handler
        send_webmentions_on_publish(sender=Mock, instance=page, revision=None)

        # Verify WebmentionSender was not called
        mock_webmention_sender.assert_not_called()

    def test_send_webmentions_with_no_links(self, mock_page_with_post, mock_webmention_sender):
        """Test behavior when post has no external links."""
        # Mock get_description to return content with no links
        post = mock_page_with_post.specific
        post.get_description.return_value = "<p>This is a test post with no links.</p>"

        # Mock WebmentionSender to return empty results
        mock_instance = mock_webmention_sender.return_value
        mock_instance.send_webmentions.return_value = []

        _send_webmentions_for(post)

        # Verify the process completed without errors
        mock_instance.send_webmentions.assert_called_once()

    @patch("homepage.core.webmention_integration.print")
    def test_send_webmentions_logs_results(self, mock_print, mock_page_with_post, mock_webmention_sender):
        """Test that results are logged correctly."""
        # Mock WebmentionSender to return mixed results
        mock_instance = mock_webmention_sender.return_value
        mock_instance.send_webmentions.return_value = [
            {"target": "https://external1.com", "success": True, "response": "Success"},
            {"target": "https://external2.com", "success": False, "response": "Failed"},
            {"target": "https://external3.com", "success": True, "response": "Success"},
        ]

        _send_webmentions_for(mock_page_with_post.specific)

        # Verify logging
        mock_print.assert_called()

        # Get all print calls
        print_calls = [call[0][0] for call in mock_print.call_args_list]

        # Check summary message
        summary_call = print_calls[0]
        assert "2 successful, 1 failed" in summary_call
        assert "page 23:" in summary_call
        assert "https://example.com/post/test-post" not in summary_call

        # Check individual messages
        assert any("✓ Sent webmention to https://external1.com" in call for call in print_calls)
        assert any("✗ Failed to send to https://external2.com" in call for call in print_calls)
        assert any("✓ Sent webmention to https://external3.com" in call for call in print_calls)

    def test_indieweb_not_installed(self, mock_page_with_post):
        """Test graceful handling when django-indieweb is not installed."""
        # Patch the import statement itself
        with patch("homepage.core.webmention_integration.WebmentionSender", None):
            with patch("builtins.__import__", side_effect=ImportError("No module named 'indieweb'")):
                # Should not raise an exception
                _send_webmentions_for(mock_page_with_post.specific)


# Publication through Wagtail, with real pages


HOST = "webmention.test"
LINKING_BODY = json.dumps(
    [
        {
            "type": "overview",
            "value": [{"type": "paragraph", "value": '<p>See <a href="https://external.test/article">this</a>.</p>'}],
        }
    ]
)


@pytest.fixture
def blog(db):
    root = Page.get_first_root_node()
    if root is None:
        Locale.objects.get_or_create(language_code="en")
        root = Page.add_root(instance=Page(title="Root", slug="root"))
    home = root.add_child(instance=Page(title="Home", slug="webmention-home"))
    Site.objects.all().delete()
    Site.objects.create(hostname=HOST, port=80, root_page=home, is_default_site=True)
    return home.add_child(instance=Blog(title="Blog", slug="blog"))


@pytest.fixture
def outbound():
    """Record rendering and sending; nothing reaches the network."""
    calls = SimpleNamespace(rendered=[], sent=[], error=None)
    render = Post.get_description

    def get_description(self, *args, **kwargs):
        calls.rendered.append(self.pk)
        return render(self, *args, **kwargs)

    def send_webmentions(self, source_url, html_content):
        calls.sent.append((source_url, html_content))
        if calls.error is not None:
            raise calls.error
        return []

    with (
        patch.object(Post, "get_description", get_description),
        patch("indieweb.senders.WebmentionSender.send_webmentions", send_webmentions),
        patch("homepage.core.webmention_integration.WebmentionSender", None),
    ):
        yield calls


def draft_post(blog, slug="linking-post"):
    return blog.add_child(instance=Post(title=slug, slug=slug, body=LINKING_BODY, live=False))


def restrict(page):
    return PageViewRestriction.objects.create(page=page, restriction_type=PageViewRestriction.LOGIN)


def deliveries(callbacks):
    """The scheduled webmention deliveries among the captured on-commit callbacks."""
    return [callback for callback in callbacks if getattr(callback, "func", None) is _deliver_webmentions]


class TestPublicVisibility:
    def test_public_post_sends_once_after_commit(self, blog, outbound, django_capture_on_commit_callbacks):
        post = draft_post(blog)

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            post.save_revision().publish()
            # Nothing is rendered or sent inside the publication itself.
            assert (outbound.rendered, outbound.sent) == ([], [])

        assert len(deliveries(callbacks)) == 1
        assert outbound.rendered == [post.pk]
        ((source_url, html_content),) = outbound.sent
        assert source_url == f"http://{HOST}/blogs/blog/linking-post/"
        assert "https://external.test/article" in html_content

    @pytest.mark.parametrize("restricted", ["post", "blog"])
    def test_restricted_post_is_neither_rendered_nor_announced(
        self, blog, outbound, django_capture_on_commit_callbacks, restricted
    ):
        post = draft_post(blog)
        restrict(post if restricted == "post" else blog)

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            post.save_revision().publish()

        assert Post.objects.get(pk=post.pk).live is True
        assert deliveries(callbacks) == []
        assert (outbound.rendered, outbound.sent) == ([], [])

    @pytest.mark.parametrize("restricted", ["post", "blog"])
    def test_publishing_after_the_restriction_is_removed_sends_once(
        self, blog, outbound, django_capture_on_commit_callbacks, restricted
    ):
        post = draft_post(blog)
        restriction = restrict(post if restricted == "post" else blog)
        with django_capture_on_commit_callbacks(execute=True):
            post.save_revision().publish()
        restriction.delete()

        with django_capture_on_commit_callbacks(execute=True):
            Post.objects.get(pk=post.pk).save_revision().publish()

        assert outbound.rendered == [post.pk]
        assert len(outbound.sent) == 1

    def test_restriction_added_before_commit_stops_the_delivery(
        self, blog, outbound, django_capture_on_commit_callbacks
    ):
        post = draft_post(blog)

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            post.save_revision().publish()
            restrict(blog)

        assert len(deliveries(callbacks)) == 1
        assert (outbound.rendered, outbound.sent) == ([], [])

    def test_post_unpublished_before_commit_is_not_announced(self, blog, outbound, django_capture_on_commit_callbacks):
        post = draft_post(blog)

        with django_capture_on_commit_callbacks(execute=True):
            post.save_revision().publish()
            Post.objects.get(pk=post.pk).unpublish()

        assert (outbound.rendered, outbound.sent) == ([], [])

    def test_only_the_revision_that_is_live_at_commit_is_announced(
        self, blog, outbound, django_capture_on_commit_callbacks
    ):
        post = draft_post(blog)

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            post.save_revision().publish()
            Post.objects.get(pk=post.pk).save_revision().publish()

        assert len(deliveries(callbacks)) == 2
        assert len(outbound.sent) == 1


@pytest.mark.django_db(transaction=True)
class TestCommitBoundary:
    """These tests really commit and roll back; no test transaction wraps them."""

    def test_rolled_back_publication_sends_nothing(self, blog, outbound):
        post = draft_post(blog)

        with pytest.raises(RuntimeError, match="abort"):
            with transaction.atomic():
                post.save_revision().publish()
                assert Post.objects.get(pk=post.pk).live is True
                raise RuntimeError("abort")

        assert Post.objects.get(pk=post.pk).live is False
        assert (outbound.rendered, outbound.sent) == ([], [])

    def test_committed_publication_sends_once(self, blog, outbound):
        post = draft_post(blog)

        with transaction.atomic():
            with transaction.atomic():
                post.save_revision().publish()
            assert outbound.sent == []

        assert Post.objects.get(pk=post.pk).live is True
        assert outbound.rendered == [post.pk]
        assert len(outbound.sent) == 1

    def test_restricted_publication_sends_nothing_after_commit(self, blog, outbound):
        post = draft_post(blog)
        restrict(blog)

        with transaction.atomic():
            post.save_revision().publish()

        assert Post.objects.get(pk=post.pk).live is True
        assert (outbound.rendered, outbound.sent) == ([], [])

    def test_sender_failure_keeps_the_committed_publication(self, blog, outbound, caplog):
        post = draft_post(blog)
        outbound.error = RuntimeError("cannot reach https://external.test/article?token=SECRET-MARKER")

        with transaction.atomic():
            post.save_revision().publish()

        assert len(outbound.sent) == 1
        assert Post.objects.get(pk=post.pk).live is True
        messages = [record.getMessage() for record in caplog.records if record.name.startswith("homepage")]
        assert messages == [f"Webmention delivery failed for page {post.pk}: RuntimeError"]
        assert "SECRET-MARKER" not in caplog.text

    def test_publication_outside_a_transaction_survives_a_sender_failure(self, blog, outbound):
        post = draft_post(blog)
        outbound.error = RuntimeError("down")

        post.save_revision().publish()

        assert len(outbound.sent) == 1
        assert Post.objects.get(pk=post.pk).live is True
