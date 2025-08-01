import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import RequestFactory
from wagtail.models import Site
from wagtail.signals import page_published
from cast.models import Post
from homepage.core.webmention_integration import send_webmentions_on_publish


@pytest.fixture
def mock_page_with_post():
    """Create a mock Page instance with a Post as specific."""
    # Create the Post mock
    post = Mock(spec=Post)
    post.get_full_url.return_value = "https://example.com/post/test-post"
    
    # Mock the get_description method
    post.get_description.return_value = "<p>This is a test post with a <a href='https://external.com'>link</a>.</p>"
    
    # Create the Page mock with specific returning the post
    page = Mock()
    page.specific = post
    
    return page


@pytest.fixture
def mock_webmention_sender():
    """Mock the WebmentionSender class."""
    with patch('homepage.core.webmention_integration.WebmentionSender') as mock_class:
        mock_instance = Mock()
        mock_instance.send_webmentions.return_value = [
            {"target": "https://external.com", "success": True, "response": "Success"}
        ]
        mock_class.return_value = mock_instance
        yield mock_class


class TestWebmentionIntegration:
    def test_send_webmentions_on_publish_success(self, mock_page_with_post, mock_webmention_sender):
        """Test successful webmention sending when a post is published."""
        # Call the signal handler
        send_webmentions_on_publish(sender=Post, instance=mock_page_with_post, revision=None)
        
        # Get the post from the page
        post = mock_page_with_post.specific
        
        # Verify get_full_url was called
        post.get_full_url.assert_called_once()
        
        # Verify get_description was called with correct parameters
        # We don't check the exact request object, just that the method was called with the right params
        assert post.get_description.called
        call_kwargs = post.get_description.call_args.kwargs
        assert call_kwargs['render_detail'] is True
        assert call_kwargs['escape_html'] is False
        assert call_kwargs['remove_newlines'] is False
        
        # Verify WebmentionSender was used correctly
        mock_webmention_sender.assert_called_once()
        mock_instance = mock_webmention_sender.return_value
        mock_instance.send_webmentions.assert_called_once_with(
            source_url="https://example.com/post/test-post",
            html_content="<p>This is a test post with a <a href='https://external.com'>link</a>.</p>"
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
        
        # Call the signal handler
        send_webmentions_on_publish(sender=Post, instance=mock_page_with_post, revision=None)
        
        # Verify the process completed without errors
        mock_instance.send_webmentions.assert_called_once()
    
    @patch('homepage.core.webmention_integration.print')
    def test_send_webmentions_logs_results(self, mock_print, mock_page_with_post, mock_webmention_sender):
        """Test that results are logged correctly."""
        # Mock WebmentionSender to return mixed results
        mock_instance = mock_webmention_sender.return_value
        mock_instance.send_webmentions.return_value = [
            {"target": "https://external1.com", "success": True, "response": "Success"},
            {"target": "https://external2.com", "success": False, "response": "Failed"},
            {"target": "https://external3.com", "success": True, "response": "Success"},
        ]
        
        # Call the signal handler
        send_webmentions_on_publish(sender=Post, instance=mock_page_with_post, revision=None)
        
        # Verify logging
        mock_print.assert_called()
        
        # Get all print calls
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Check summary message
        summary_call = print_calls[0]
        assert "2 successful, 1 failed" in summary_call
        assert "https://example.com/post/test-post" in summary_call
        
        # Check individual messages
        assert any("✓ Sent webmention to https://external1.com" in call for call in print_calls)
        assert any("✗ Failed to send to https://external2.com" in call for call in print_calls)
        assert any("✓ Sent webmention to https://external3.com" in call for call in print_calls)
    
    def test_indieweb_not_installed(self, mock_page_with_post):
        """Test graceful handling when django-indieweb is not installed."""
        # Patch the import statement itself
        with patch('homepage.core.webmention_integration.WebmentionSender', None):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'indieweb'")):
                # Should not raise an exception
                send_webmentions_on_publish(sender=Post, instance=mock_page_with_post, revision=None)