from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class PostBodyHeadingTemplateTest(SimpleTestCase):
    def test_detail_template_renders_post_title_as_h1(self):
        page = self._page()
        blog = Mock(author="Jochen Wersdörfer")

        html = render_to_string(
            "cast/bootstrap5/post_body.html",
            {"page": page, "blog": blog, "render_detail": True, "comments_are_enabled": False},
        )

        self.assertIn('<h1 class="p-name post-title">', html)
        self.assertIn('<a class="u-url" href="/test-post/">Test Post</a>', html)
        self.assertNotIn('<h2 class="p-name post-title">', html)

    def test_card_template_renders_post_title_as_h2(self):
        page = self._page()
        blog = Mock(author="Jochen Wersdörfer")

        html = render_to_string(
            "cast/bootstrap5/post_body.html",
            {"page": page, "blog": blog, "render_detail": False, "comments_are_enabled": False},
        )

        self.assertIn('<h2 class="p-name post-card-title">', html)
        self.assertIn('<a class="u-url" href="/test-post/" data-cast-prefetch>Test Post</a>', html)
        self.assertNotIn("<h1", html)

    def _page(self):
        page = Mock()
        page.owner = None
        page.page_url = "/test-post/"
        page.title = "Test Post"
        page.visible_date = datetime(2025, 7, 25, 10, 0, 0)
        page.body = []
        return page
