import re
from pathlib import Path

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from wagtail.images.models import Filter
from wagtail.images.rect import Rect
from wagtail.rich_text import get_text_for_indexing

from homepage.portfolio.blocks import get_project_block_region, is_filled

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


NO_BREAK_GROUP = re.compile("[^ \t\n\u00a0]+(?:\u00a0[^ \t\n\u00a0]+)+")


@register.filter
def keep_together(value):
    """Hold word groups joined by no-break spaces together, but only softly.

    Plain-text titles have no rich-text "Kein Umbruch"; editors join words with a no-break
    space (Option+Space) instead. Each such group becomes the same soft no-break span, so it
    wraps as a whole and only breaks inside when it is wider than the line on its own.
    """

    escaped = str(conditional_escape(value))
    return mark_safe(
        NO_BREAK_GROUP.sub(
            lambda match: '<span data-no-break="">' + match.group(0).replace("\u00a0", " ") + "</span>",
            escaped,
        )
    )


@register.filter
def half_rounded_up(value):
    """Half of a count, rounded up: the rows of a list that is split into two columns."""

    return -(-len(value) // 2)


@register.filter
def filled(value):
    """Whether an editorial text is filled in (not empty, not a "[…]" placeholder)."""

    return is_filled(value)


@register.filter
def filled_stats(items):
    """The stats entries whose label is filled in."""

    return [item for item in items if is_filled(item["label"])]


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


@register.simple_tag
def fill_focal_position(image, target_width, target_height):
    """Return the focal centre inside Wagtail's rounded ``fill`` crop.

    The Hero canvas performs one final cover crop after the browser selects a
    responsive rendition. Supplying the focal centre in rendition coordinates
    lets that crop preserve the editor's real focal point instead of assuming
    that Wagtail centred the preceding crop.
    """

    target_width = int(target_width)
    target_height = int(target_height)
    focal_point = image.get_focal_point()
    if focal_point is None:
        focal_point = Rect.from_point(image.width / 2, image.height / 2, 0, 0)

    transform = Filter(spec=f"fill-{target_width}x{target_height}").get_transform(image)
    transformed_focal_x, transformed_focal_y = focal_point.transform(transform).centroid

    return {
        "x": f"{min(1, max(0, transformed_focal_x / transform.size[0])):.6f}",
        "y": f"{min(1, max(0, transformed_focal_y / transform.size[1])):.6f}",
    }
