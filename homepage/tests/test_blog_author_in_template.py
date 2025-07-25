"""
Test that blog.author is available in post templates.
"""

from datetime import datetime
from unittest.mock import Mock

from django.template.loader import render_to_string
from django.test import TestCase


class BlogAuthorTemplateTest(TestCase):
    def test_template_renders_blog_author(self):
        """Test that blog.author is rendered correctly in the template"""
        # Create mock objects
        mock_blog = Mock()
        mock_blog.author = "Jochen Wersdörfer"

        mock_page = Mock()
        mock_page.blog = mock_blog
        mock_page.page_url = "/test-post/"
        mock_page.title = "Test Post"
        mock_page.visible_date = datetime(2025, 7, 25, 10, 0, 0)
        mock_page.body = []

        # Create context - now blog is passed directly in context
        context = {"page": mock_page, "blog": mock_blog, "render_detail": True, "comments_are_enabled": False}

        # Render the template
        html = render_to_string("cast/bootstrap5/post_body.html", context)

        # Check that the author is in the hidden h-card
        self.assertIn("Jochen Wersdörfer", html)
        self.assertIn('class="h-entry"', html)
        self.assertIn('class="author p-author h-card" style="display: none;"', html)
        self.assertIn('<span class="p-name">Jochen Wersdörfer</span>', html)
        self.assertIn('class="u-photo"', html)
        self.assertIn('<a class="u-url" href="/jochen/"></a>', html)

    def test_template_with_none_author_shows_none(self):
        """Test that None author is included in the hidden h-card"""
        # Create mock objects with None author
        mock_blog = Mock()
        mock_blog.author = None

        mock_page = Mock()
        mock_page.blog = mock_blog
        mock_page.page_url = "/test-post/"
        mock_page.title = "Test Post"
        mock_page.visible_date = datetime(2025, 7, 25, 10, 0, 0)
        mock_page.body = []

        # Create context - now blog is passed directly in context
        context = {"page": mock_page, "blog": mock_blog, "render_detail": True, "comments_are_enabled": False}

        # Render the template
        html = render_to_string("cast/bootstrap5/post_body.html", context)

        # This should show "None" in the hidden h-card
        self.assertIn('<span class="p-name">None</span>', html)
        self.assertIn('alt="None"', html)  # Check avatar alt text

    def test_template_with_none_page_renders_nothing(self):
        """Test that template handles None page gracefully"""
        # Create context with None page
        context = {"page": None, "render_detail": False, "comments_are_enabled": False}

        # Render the template
        html = render_to_string("cast/bootstrap5/post_body.html", context)

        # Should render nothing or empty
        self.assertEqual(html.strip(), "")
