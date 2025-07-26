"""
Test that blog.author is available in post templates.
"""

from datetime import datetime
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase
from indieweb.models import Profile

User = get_user_model()


class BlogAuthorTemplateTest(TestCase):
    def test_template_renders_blog_author(self):
        """Test that blog.author is rendered correctly in the template"""
        # Create mock objects
        mock_blog = Mock()
        mock_blog.author = "Jochen Wersdörfer"

        mock_page = Mock()
        mock_page.blog = mock_blog
        mock_page.owner = None  # No owner, so fallback is used
        mock_page.page_url = "/test-post/"
        mock_page.title = "Test Post"
        mock_page.visible_date = datetime(2025, 7, 25, 10, 0, 0)
        mock_page.body = []

        # Create context - now blog is passed directly in context
        context = {"page": mock_page, "blog": mock_blog, "render_detail": True, "comments_are_enabled": False}

        # Render the template
        html = render_to_string("cast/bootstrap5/post_body.html", context)

        # Check that the author is in the hidden h-card (fallback case without owner)
        self.assertIn("Jochen Wersdörfer", html)
        self.assertIn('class="h-entry"', html)
        # The h-card should be hidden
        self.assertIn('style="display: none;"', html)
        # Check for author info in the output
        self.assertIn("Jochen Wersdörfer", html)

    def test_template_with_none_author_shows_none(self):
        """Test that None author is included in the hidden h-card"""
        # Create mock objects with None author
        mock_blog = Mock()
        mock_blog.author = None

        mock_page = Mock()
        mock_page.blog = mock_blog
        mock_page.owner = None  # No owner, so fallback is used
        mock_page.page_url = "/test-post/"
        mock_page.title = "Test Post"
        mock_page.visible_date = datetime(2025, 7, 25, 10, 0, 0)
        mock_page.body = []

        # Create context - now blog is passed directly in context
        context = {"page": mock_page, "blog": mock_blog, "render_detail": True, "comments_are_enabled": False}

        # Render the template
        html = render_to_string("cast/bootstrap5/post_body.html", context)

        # This should show "None" in the hidden h-card
        self.assertIn("None", html)
        self.assertIn('style="display: none;"', html)

    def test_template_with_none_page_renders_nothing(self):
        """Test that template handles None page gracefully"""
        # Create context with None page
        context = {"page": None, "render_detail": False, "comments_are_enabled": False}

        # Render the template
        html = render_to_string("cast/bootstrap5/post_body.html", context)

        # Should render nothing or empty
        self.assertEqual(html.strip(), "")

    def test_template_with_page_owner_uses_h_card_tag(self):
        """Test that when page has owner, it uses the h_card template tag"""
        # Create real user
        test_user = User.objects.create_user(username="testuser", email="test@example.com")

        # Create IndieWeb profile for the user
        Profile.objects.create(
            user=test_user,
            name="Test User",
            photo_url="https://example.com/photo.jpg",
            url="https://example.com/",
            h_card={
                "name": ["Test User"],
                "photo": ["https://example.com/photo.jpg"],
                "url": ["https://example.com/"],
            },
        )

        mock_blog = Mock()
        mock_blog.author = "Test Author"

        mock_page = Mock()
        mock_page.blog = mock_blog
        mock_page.owner = test_user
        mock_page.page_url = "/test-post/"
        mock_page.title = "Test Post"
        mock_page.visible_date = datetime(2025, 7, 25, 10, 0, 0)
        mock_page.body = []

        # Create context
        context = {"page": mock_page, "blog": mock_blog, "render_detail": True, "comments_are_enabled": False}

        # Render the template
        html = render_to_string("cast/bootstrap5/post_body.html", context)

        # Check that the h-card is present and hidden
        self.assertIn('class="h-card"', html)
        self.assertIn('style="display: none;"', html)
        # Check that the user's h-card data is rendered
        self.assertIn("Test User", html)
        self.assertIn("https://example.com/photo.jpg", html)
