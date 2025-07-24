"""
Tests for webmention sending integration with django-cast.
"""

from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase
from wagtail.models import Page
from wagtail.signals import page_published


class TestWebmentionIntegration(TestCase):
    @patch("homepage.core.webmention_integration.WebmentionSender")
    def test_webmention_sending_uses_body_html_method(self, mock_sender_class):
        """Test that webmention sending uses body.__html__() instead of get_description()."""
        # Create mock post
        mock_post = Mock()
        mock_post.get_full_url.return_value = "https://example.com/post/1/"

        # Mock the body field with __html__ method
        mock_body = MagicMock()
        mock_body.__html__ = Mock(return_value='<p>Test content with <a href="https://external.com">link</a></p>')
        mock_post.body = mock_body

        # Create mock page with specific attribute returning our mock post
        mock_page = Mock(spec=Page)
        mock_page.specific = mock_post

        # Mock webmention sender
        mock_sender = Mock()
        mock_sender.send_webmentions.return_value = [{"target": "https://external.com", "success": True}]
        mock_sender_class.return_value = mock_sender

        # Mock the Post class check
        with patch("homepage.core.webmention_integration.Post"):
            # Make isinstance check return True
            with patch("homepage.core.webmention_integration.isinstance", return_value=True):
                # Trigger the signal
                page_published.send(sender=Page, instance=mock_page)

                # Verify that body.__html__() was called
                mock_body.__html__.assert_called_once()

                # Verify webmentions were sent with correct parameters
                mock_sender.send_webmentions.assert_called_once_with(
                    source_url="https://example.com/post/1/",
                    html_content='<p>Test content with <a href="https://external.com">link</a></p>',
                )

    @patch("homepage.core.webmention_integration.WebmentionSender")
    def test_webmention_sending_logs_results(self, mock_sender_class):
        """Test that webmention sending logs success and failure results."""
        # Create mock post
        mock_post = Mock()
        mock_post.get_full_url.return_value = "https://example.com/post/1/"

        # Mock the body field
        mock_body = MagicMock()
        mock_body.__html__.return_value = (
            '<p>Links: <a href="https://success.com">1</a> <a href="https://fail.com">2</a></p>'
        )
        mock_post.body = mock_body

        # Create mock page
        mock_page = Mock(spec=Page)
        mock_page.specific = mock_post

        # Mock webmention sender with mixed results
        mock_sender = Mock()
        mock_sender.send_webmentions.return_value = [
            {"target": "https://success.com", "success": True},
            {"target": "https://fail.com", "success": False, "error": "Connection refused"},
        ]
        mock_sender_class.return_value = mock_sender

        # Capture print output
        with patch("builtins.print") as mock_print:
            with patch("homepage.core.webmention_integration.Post"):
                with patch("homepage.core.webmention_integration.isinstance", return_value=True):
                    # Trigger the signal
                    page_published.send(sender=Page, instance=mock_page)

                    # Verify logging output
                    mock_print.assert_any_call(
                        "Webmentions sent for https://example.com/post/1/: 1 successful, 1 failed"
                    )
                    mock_print.assert_any_call("  ✓ Sent webmention to https://success.com")
                    mock_print.assert_any_call("  ✗ Failed to send to https://fail.com: Connection refused")
