import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.utils.html import escape
from django.utils.safestring import mark_safe

from homepage.handwriting.compose import compose_label

register = template.Library()


@register.simple_tag
def handwriting_static(path):
    """Static URL with a `?v=<mtime>` cache-buster so browsers always refetch the
    handwriting CSS/JS after a change (no stale cache during iteration)."""
    url = static(path)
    try:
        abs_path = finders.find(path)
        if abs_path:
            url += ("&" if "?" in url else "?") + "v=" + str(int(os.path.getmtime(abs_path)))
    except Exception:
        pass
    return url


@register.simple_tag
def handwriting_label(text, orientation="horizontal"):
    """Render a CV label as a self-writing handwriting SVG, with graceful fallback.

    Supported text -> visually-hidden real text (a11y) + aria-hidden animated SVG.
    Unsupported/empty text -> plain escaped text only.
    orientation="vertical" rotates the SVG for the rotated rail labels.
    The SVG is fully revealed by default (CSS); handwriting.js hides+animates it
    on scroll only when JS is present and motion is allowed.
    """
    text = "" if text is None else str(text)
    safe = escape(text)
    svg = compose_label(text, orientation)
    if svg is None:
        return mark_safe(f'<span class="hw-label hw-fallback">{safe}</span>')
    cls = "hw-label hw-label--rail" if orientation == "vertical" else "hw-label"
    return mark_safe(
        f'<span class="{cls}" data-hw>'
        f'<span class="hw-text">{safe}</span>{svg}</span>'
    )
