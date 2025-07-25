"""
Tests for webmention sending integration with django-cast.
"""

from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase

from homepage.core import webmention_integration


class TestWebmentionIntegration(TestCase):
    def test_webmention_sending_uses_body_html_method(self):
        """Test that webmention sending uses body.__html__() instead of get_description()."""

        # Create a mock Post class
        class MockPostClass(type):
            pass

        # Create mock post instance
        mock_post = Mock()
        mock_post.__class__ = MockPostClass
        mock_post.get_full_url.return_value = "https://example.com/post/1/"

        # Mock the body field with __html__ method
        mock_body = MagicMock()
        mock_body.__html__ = Mock(return_value='<p>Test content with <a href="https://external.com">link</a></p>')
        mock_post.body = mock_body

        # Create mock page with specific attribute returning our mock post
        mock_page = Mock()
        mock_page.specific = mock_post

        # Mock the imports and WebmentionSender
        with patch.object(webmention_integration, "Post", MockPostClass):
            with patch.object(webmention_integration, "Episode", Mock):
                with patch.object(webmention_integration, "WebmentionSender") as MockSender:
                    # Mock webmention sender
                    mock_sender = Mock()
                    mock_sender.send_webmentions.return_value = [{"target": "https://external.com", "success": True}]
                    MockSender.return_value = mock_sender

                    # Call the handler directly
                    webmention_integration.send_webmentions_on_publish(None, instance=mock_page)

                    # Verify that body.__html__() was called
                    mock_body.__html__.assert_called_once()

                    # Verify webmentions were sent with correct parameters
                    mock_sender.send_webmentions.assert_called_once_with(
                        source_url="https://example.com/post/1/",
                        html_content='<p>Test content with <a href="https://external.com">link</a></p>',
                    )

    def test_webmention_sending_logs_results(self):
        """Test that webmention sending logs success and failure results."""

        # Create a mock Post class
        class MockPostClass(type):
            pass

        # Create mock post instance
        mock_post = Mock()
        mock_post.__class__ = MockPostClass
        mock_post.get_full_url.return_value = "https://example.com/post/1/"

        # Mock the body field
        mock_body = MagicMock()
        mock_body.__html__ = Mock(
            return_value='<p>Links: <a href="https://success.com">1</a> <a href="https://fail.com">2</a></p>'
        )
        mock_post.body = mock_body

        # Create mock page
        mock_page = Mock()
        mock_page.specific = mock_post

        # Mock the imports and WebmentionSender
        with patch.object(webmention_integration, "Post", MockPostClass):
            with patch.object(webmention_integration, "Episode", Mock):
                with patch.object(webmention_integration, "WebmentionSender") as MockSender:
                    # Mock webmention sender with mixed results
                    mock_sender = Mock()
                    mock_sender.send_webmentions.return_value = [
                        {"target": "https://success.com", "success": True},
                        {"target": "https://fail.com", "success": False, "error": "Connection refused"},
                    ]
                    MockSender.return_value = mock_sender

                    # Capture print output
                    with patch("builtins.print") as mock_print:
                        # Call the handler directly
                        webmention_integration.send_webmentions_on_publish(None, instance=mock_page)

                        # Verify logging output
                        mock_print.assert_any_call(
                            "Webmentions sent for https://example.com/post/1/: 1 successful, 1 failed"
                        )
                        mock_print.assert_any_call("  ✓ Sent webmention to https://success.com")
                        mock_print.assert_any_call("  ✗ Failed to send to https://fail.com: Connection refused")
