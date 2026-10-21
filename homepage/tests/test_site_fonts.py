"""The main site's Saira fonts: small subset files, preloaded, without layout shifts."""

import re
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

STATIC = Path(__file__).resolve().parents[1] / "static"
CSS = (STATIC / "css" / "site-overrides.css").read_text()
FONT_FACES = re.findall(r"@font-face\s*{[^}]*}", CSS)
SAIRA_FACES = [face for face in FONT_FACES if '"Saira"' in face]

UPRIGHT_PRELOAD = 'href="/static/fonts/saira-latin.woff2" as="font" type="font/woff2" crossorigin'
ITALIC_PRELOAD = 'href="/static/fonts/saira-italic-latin.woff2" as="font" type="font/woff2" crossorigin'


def test_saira_comes_from_the_main_site_subsets():
    sources = [re.search(r'url\("([^"]+)"\)', face).group(1) for face in SAIRA_FACES]
    assert sources == [
        "../fonts/saira-latin.woff2",
        "../fonts/saira-latin-ext.woff2",
        "../fonts/saira-italic-latin.woff2",
        "../fonts/saira-italic-latin-ext.woff2",
    ]
    for source in sources:
        assert (STATIC / "css" / source).resolve().is_file()
    assert "portfolio/fonts" not in CSS


def test_saira_does_not_swap_after_first_paint():
    for face in SAIRA_FACES:
        assert "font-display: optional;" in face
        assert "unicode-range: U+" in face


def test_core_and_extension_ranges_do_not_overlap():
    def codepoints(face):
        ranges = re.search(r"unicode-range: ([^;]+);", face).group(1)
        result = set()
        for part in ranges.split(", "):
            start, _, end = part.removeprefix("U+").partition("-")
            result |= set(range(int(start, 16), int(end or start, 16) + 1))
        return result

    core, ext, italic_core, italic_ext = (codepoints(face) for face in SAIRA_FACES)
    assert core == italic_core and ext == italic_ext
    assert not core & ext
    # Umlauts, ß, typographic quotes, dashes, ellipsis, euro and the "→" of "Read more →"
    # are in the preloaded core file.
    assert {ord(c) for c in "äöüÄÖÜßẞ„“”‘’–—…€→"} <= core


@pytest.mark.django_db
def test_pages_preload_only_the_upright_core_file(client):
    get_user_model().objects.create_user(username="jochen", name="Jochen Wersdörfer")
    html = client.get(reverse("jochen")).content.decode()
    assert html.count(UPRIGHT_PRELOAD) == 1
    assert ITALIC_PRELOAD not in html
    # The preload comes before the stylesheets that declare the font.
    assert html.index(UPRIGHT_PRELOAD) < html.index("site-overrides.css")


def test_blog_list_also_preloads_the_italic_core_file():
    template = (Path(__file__).resolve().parents[1] / "templates/cast/bootstrap5/blog_list_of_posts.html").read_text()
    assert "{% block font_preloads %}" in template
    assert "{{ block.super }}" in template
    assert "{% static 'fonts/saira-italic-latin.woff2' %}" in template
