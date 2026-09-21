from pathlib import Path

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from wagtail.rich_text import get_text_for_indexing

from homepage.portfolio.blocks import get_project_block_region

register = template.Library()


@register.simple_tag
def versioned_static(path):
    """Add a source-mtime version locally while preserving production manifests."""

    url = static(path)
    if not settings.DEBUG:
        return url

    source_path = finders.find(path)
    if not source_path:
        return url

    return f"{url}?v={Path(source_path).stat().st_mtime_ns}"


@register.filter
def richtext_plaintext(value):
    """Return RichText as decoded plain text for Django to escape once."""

    return get_text_for_indexing(str(value or ""))


@register.filter
def project_block_region(block):
    """Return the single project-page region responsible for rendering a block."""

    return get_project_block_region(block.block_type)


@register.filter
def responsive_image_srcset(responsive_image):
    """Render a Wagtail ``ResponsiveImage`` with Wagtail's srcset serializer."""

    if not responsive_image:
        return ""

    return responsive_image.get_width_srcset(responsive_image.renditions)
