"""Post images on the blog list load lazily from the second post on."""

import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import cast
from django.template import Context, Template
from django.template.loader import render_to_string

OVERRIDE = Path(__file__).resolve().parents[1] / "templates/cast/image/image.html"
UPSTREAM = Path(cast.__file__).resolve().parent / "templates/cast/image/image.html"


class FakeImageBlock:
    """Stands in for an image block and reports whether it was asked to load lazily."""

    block_type = "image"

    def render_as_block(self, context):
        return "[lazy image]" if context.get("lazy_images") else "[eager image]"


def _post(slug):
    body = [SimpleNamespace(block_type="overview", value=[FakeImageBlock()])]
    return SimpleNamespace(
        owner=None, page_url=f"/{slug}/", title=slug, visible_date=datetime(2026, 10, 21), body=body
    )


def _image_value():
    regular = SimpleNamespace(
        src={"jpeg": "/a.jpg"},
        srcset={"jpeg": "/a.jpg 1110w", "avif": "/a.avif 1110w"},
        sizes="1110px",
        width=1110,
        height=740,
    )
    return SimpleNamespace(regular=regular, default_alt_text="Alt")


def test_list_loads_images_lazily_from_the_second_post_on():
    # Same loop as cast-bootstrap5's blog_list_of_posts.html.
    template = Template(
        '{% for post in posts %}{% include "cast/bootstrap5/post_body.html" with render_detail=False page=post %}'
        "{% endfor %}"
    )
    html = template.render(Context({"posts": [_post("one"), _post("two"), _post("three")], "blog": None}))
    assert re.findall(r"\[(lazy|eager) image\]", html) == ["eager", "lazy", "lazy"]


def test_detail_page_loads_images_eagerly():
    html = render_to_string("cast/bootstrap5/post_body.html", {"page": _post("one"), "render_detail": True})
    assert "[eager image]" in html


def test_image_template_adds_loading_lazy_only_when_asked():
    lazy = render_to_string("cast/image/image.html", {"value": _image_value(), "lazy_images": "lazy"})
    eager = render_to_string("cast/image/image.html", {"value": _image_value()})
    assert 'loading="lazy"' in lazy
    assert "loading=" not in eager


def test_image_template_otherwise_matches_django_cast():
    # Fails when django-cast changes its image markup, so the override can follow.
    override = OVERRIDE.read_text()
    override = re.sub(r"{% comment %}.*?{% endcomment %}\n", "", override, flags=re.S)
    override = override.replace('      {% if lazy_images %}loading="lazy"{% endif %}\n', "")
    assert override == UPSTREAM.read_text()
