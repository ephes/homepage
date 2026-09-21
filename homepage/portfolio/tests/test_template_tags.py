from types import SimpleNamespace
from unittest.mock import patch

from django.test import override_settings
from wagtail.images.models import ResponsiveImage

from homepage.portfolio.templatetags.portfolio_content import (
    responsive_image_srcset,
    richtext_plaintext,
    versioned_static,
)


def test_versioned_static_uses_source_mtime_in_debug(tmp_path):
    stylesheet = tmp_path / "portfolio.css"
    stylesheet.write_text("body {}", encoding="utf-8")

    with (
        override_settings(DEBUG=True),
        patch(
            "homepage.portfolio.templatetags.portfolio_content.static",
            return_value="/static/portfolio/portfolio.css",
        ),
        patch(
            "homepage.portfolio.templatetags.portfolio_content.finders.find",
            return_value=str(stylesheet),
        ),
    ):
        result = versioned_static("portfolio/portfolio.css")

    assert result == (
        f"/static/portfolio/portfolio.css?v={stylesheet.stat().st_mtime_ns}"
    )


def test_versioned_static_keeps_manifest_url_unchanged_outside_debug():
    with (
        override_settings(DEBUG=False),
        patch(
            "homepage.portfolio.templatetags.portfolio_content.static",
            return_value="https://static.example/portfolio.abc123.css",
        ),
        patch(
            "homepage.portfolio.templatetags.portfolio_content.finders.find"
        ) as find,
    ):
        result = versioned_static("portfolio/portfolio.css")

    assert result == "https://static.example/portfolio.abc123.css"
    find.assert_not_called()


def test_richtext_plaintext_decodes_entities_and_preserves_block_separation():
    rendered = richtext_plaintext(
        '<p>Strategie &amp; Design</p><p><a href="https://example.com">Mehr</a></p>'
    )

    assert rendered == "Strategie & Design Mehr"


def test_responsive_image_srcset_uses_wagtails_width_srcset_serializer():
    responsive_image = ResponsiveImage(
        {
            "small": SimpleNamespace(url="/media/small.jpg", width=400),
            "large": SimpleNamespace(url="/media/large.jpg", width=1200),
        }
    )

    assert responsive_image_srcset(responsive_image) == (
        "/media/small.jpg 400w, /media/large.jpg 1200w"
    )
    assert responsive_image_srcset(None) == ""
