"""
The converter must sanitize content with production dependencies only.

bleach is only installed as a transitive dev dependency, so these tests block it
and check that script tags, event handlers and javascript: URLs never survive.
"""

import importlib
import sys
import tomllib
from pathlib import Path

import pytest

from homepage.micropub import converters

PAYLOADS = {
    "html": (
        '<p>ok <script>alert(1)</script><img src="x" onerror="alert(2)">'
        '<a href="javascript:alert(3)" onclick="alert(4)">link</a></p>'
        '<ul><li onmouseover="alert(5)">item</li></ul><blockquote><script>alert(6)</script></blockquote>'
    ),
    "plain": 'hello <script>alert(1)</script>\n<img src=x onerror=alert(2)> <a href="javascript:alert(3)">x</a>',
    "heading-plain": "# title\n\n<b onclick=alert(4)>bold</b><script>alert(5)</script>",
}


@pytest.fixture
def converter_without_bleach(monkeypatch):
    monkeypatch.setitem(sys.modules, "bleach", None)  # any "import bleach" now raises ImportError
    module = importlib.reload(converters)
    yield module.ContentConverter()
    monkeypatch.undo()
    importlib.reload(converters)


def assert_no_active_content(blocks):
    html = " ".join(str(value) for block_type, value in blocks if block_type == "paragraph")
    lowered = html.lower()
    assert "<script" not in lowered
    assert "onerror" not in lowered
    assert "onclick" not in lowered
    assert "onmouseover" not in lowered
    assert "javascript:" not in lowered


@pytest.mark.parametrize("name", PAYLOADS)
def test_content_is_sanitized_without_bleach(converter_without_bleach, name):
    assert_no_active_content(converter_without_bleach.convert_content(PAYLOADS[name], {}))


def test_photo_and_location_are_sanitized(converter_without_bleach):
    properties = {
        "photo": ['javascript:alert(1)" onerror="alert(2)'],
        "location": ['<script>alert(3)</script><img src=x onerror="alert(4)">'],
    }

    assert_no_active_content(converter_without_bleach.convert_content("text", properties))


def test_safe_markup_is_kept(converter_without_bleach):
    blocks = converter_without_bleach.convert_content(
        '<p>Hi <strong>there</strong> <a href="https://example.com/">link</a></p>',
        {"photo": ["https://example.com/p.jpg"]},
    )

    html = " ".join(value for _, value in blocks)
    assert "<strong>there</strong>" in html
    assert 'href="https://example.com/"' in html
    assert 'src="https://example.com/p.jpg"' in html


def test_sanitizer_is_a_runtime_dependency():
    pyproject = tomllib.loads((Path(__file__).resolve().parents[2] / "pyproject.toml").read_text())
    runtime = {
        dep.split("[")[0].split("<")[0].split(">")[0].split("=")[0].strip()
        for dep in pyproject["project"]["dependencies"]
    }
    assert "nh3" in runtime
