from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock

from cast.models.pages import ContentBlock
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from wagtail import blocks


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

    def test_card_template_demotes_raw_excerpt_headings_to_labels(self):
        page = self._page()
        page.body = self._body_with_paragraph('<h2 data-block-key="heading">Open Source</h2><p>Text.</p>')
        blog = Mock(author="Jochen Wersdörfer")

        html = render_to_string(
            "cast/bootstrap5/post_body.html",
            {"page": page, "blog": blog, "render_detail": False, "comments_are_enabled": False},
        )

        self.assertIn('<h3 class="post-card-excerpt-label">Open Source</h3>', html)
        self.assertNotIn("<h2>Open Source</h2>", html)
        self.assertNotIn('<h2 data-block-key="heading">Open Source</h2>', html)

    def test_card_template_demotes_raw_excerpt_headings_when_render_detail_is_omitted(self):
        page = self._page()
        page.body = self._body_with_paragraph('<h2 data-block-key="heading">Open Source</h2><p>Text.</p>')
        blog = Mock(author="Jochen Wersdörfer")

        html = render_to_string(
            "cast/bootstrap5/post_body.html",
            {"page": page, "blog": blog, "comments_are_enabled": False},
        )

        self.assertIn('<h3 class="post-card-excerpt-label">Open Source</h3>', html)
        self.assertNotIn('<h2 data-block-key="heading">Open Source</h2>', html)

    def test_detail_template_preserves_raw_body_headings(self):
        page = self._page()
        page.body = self._body_with_paragraph('<h2 data-block-key="heading">Open Source</h2><p>Text.</p>')
        blog = Mock(author="Jochen Wersdörfer")

        html = render_to_string(
            "cast/bootstrap5/post_body.html",
            {"page": page, "blog": blog, "render_detail": True, "comments_are_enabled": False},
        )

        self.assertIn('<h2 data-block-key="heading">Open Source</h2>', html)
        self.assertNotIn("post-card-excerpt-label", html)

    def _page(self):
        page = Mock()
        page.owner = None
        page.page_url = "/test-post/"
        page.title = "Test Post"
        page.visible_date = datetime(2025, 7, 25, 10, 0, 0)
        page.body = []
        return page

    def _body_with_paragraph(self, html):
        body_block = blocks.StreamBlock(
            [
                ("overview", ContentBlock(section="overview")),
                ("detail", ContentBlock(section="detail")),
            ]
        )
        return body_block.to_python(
            [
                {
                    "type": "overview",
                    "value": [
                        {
                            "type": "paragraph",
                            "value": html,
                        }
                    ],
                }
            ]
        )
