from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from homepage.handwriting.compose import compose_label

register = template.Library()


@register.simple_tag
def handwriting_label(text):
    """Render a CV label as a self-writing handwriting SVG, with graceful fallback.

    Supported text -> visually-hidden real text (a11y) + aria-hidden animated SVG.
    Unsupported/empty text -> plain escaped text only.
    The SVG is fully revealed by default (CSS); handwriting.js hides+animates it
    on scroll only when JS is present and motion is allowed.
    """
    text = "" if text is None else str(text)
    safe = escape(text)
    svg = compose_label(text)
    if svg is None:
        return mark_safe(f'<span class="hw-label hw-fallback">{safe}</span>')
    return mark_safe(
        f'<span class="hw-label" data-hw>'
        f'<span class="hw-text">{safe}</span>{svg}</span>'
    )
