"""
Test that blog.author is available in post templates.
"""

from datetime import datetime
from unittest.mock import Mock

from django.template.loader import render_to_string
from django.test import TestCase


class BlogAuthorTemplateTest(TestCase):
    def test_template_renders_blog_author(self):
        """Test that page.blog.author is rendered correctly in the template"""
        # Create mock objects
        mock_blog = Mock()
        mock_blog.author = "Jochen Wersdörfer"

        mock_page = Mock()
        mock_page.blog = mock_blog
        mock_page.page_url = "/test-post/"
        mock_page.title = "Test Post"
        mock_page.visible_date = datetime(2025, 7, 25, 10, 0, 0)
        mock_page.body = []

        # Create context
        context = {"page": mock_page, "render_detail": True, "comments_are_enabled": False}

        # Render the template
        html = render_to_string("cast/bootstrap5/post_body.html", context)

        # Check that the author is rendered
        self.assertIn("Jochen Wersdörfer", html)
        self.assertIn('class="h-entry"', html)
        self.assertIn('class="author p-author h-card"', html)
        self.assertIn('<a class="p-name u-url" href="/jochen/">Jochen Wersdörfer</a>', html)

    def test_template_with_none_author_shows_none(self):
        """Test that None author is visible (should fail if template is correct)"""
        # Create mock objects with None author
        mock_blog = Mock()
        mock_blog.author = None

        mock_page = Mock()
        mock_page.blog = mock_blog
        mock_page.page_url = "/test-post/"
        mock_page.title = "Test Post"
        mock_page.visible_date = datetime(2025, 7, 25, 10, 0, 0)
        mock_page.body = []

        # Create context
        context = {"page": mock_page, "render_detail": True, "comments_are_enabled": False}

        # Render the template
        html = render_to_string("cast/bootstrap5/post_body.html", context)

        # This should show "None" which is the bug we're catching
        self.assertIn(">None<", html)
        self.assertIn('<a class="p-name u-url" href="/jochen/">None</a>', html)
