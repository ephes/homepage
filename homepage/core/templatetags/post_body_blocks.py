from bs4 import BeautifulSoup
from django import template
from django.utils.encoding import force_str
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def render_post_body_child(context, block):
    """Render a body block, demoting rich-text headings inside post-card excerpts."""
    if hasattr(block, "render_as_block"):
        html = block.render_as_block(context=context.flatten())
    else:
        html = block

    if context.autoescape:
        html = conditional_escape(html)
    else:
        html = force_str(html)

    if not context.get("render_detail") and getattr(block, "block_type", None) == "paragraph":
        html = mark_safe(_demote_card_excerpt_headings(html))
    return html


def _demote_card_excerpt_headings(html):
    if "<h" not in str(html).lower():
        return html

    soup = BeautifulSoup(str(html), "html.parser")
    changed = False
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        label = soup.new_tag("h3")
        label["class"] = "post-card-excerpt-label"
        for child in list(heading.contents):
            label.append(child.extract())
        heading.replace_with(label)
        changed = True
    if not changed:
        return html
    return str(soup)
