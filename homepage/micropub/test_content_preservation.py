"""Lossless text conversion, including the handler's explicit format boundary."""

import pytest
from bs4 import BeautifulSoup

from .converters import ContentConverter
from .handler import CastPostMicropubHandler


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        ("before <p>middle</p> after", ["<p>before </p>", "<p>middle</p>", "<p> after</p>"]),
        ("<p>one</p><strong>two</strong><p>three</p>", ["<p>one</p>", "<p><strong>two</strong></p>", "<p>three</p>"]),
        (
            'A &amp; &lt;T&gt; <a href="https://example.com/">link</a><em>!</em><br>end<hr>tail',
            [
                '<p>A &amp; &lt;T&gt; <a href="https://example.com/">link</a><em>!</em><br>end</p>',
                "<hr>",
                "<p>tail</p>",
            ],
        ),
        ("<script>bad()</script>before<p>middle</p>after", ["<p>before</p>", "<p>middle</p>", "<p>after</p>"]),
    ],
)
def test_html_text_and_inline_siblings_keep_order(html, expected):
    handler = CastPostMicropubHandler()
    properties = {"content": [{"html": html}]}
    blocks = handler.converter.convert_content(handler._get_content(properties), properties)
    assert blocks == [("paragraph", value) for value in expected]


@pytest.mark.parametrize(
    ("explicit", "text"),
    [
        (False, "use list[str] and <T> &amp; literally"),
        (True, "use list[str] and <T> &amp; literally"),
        (True, "<p>literal & text</p>\n<br>"),
    ],
)
def test_plain_text_is_literal(explicit, text):
    handler = CastPostMicropubHandler()
    properties = {"content": [{"text": text} if explicit else text]}
    blocks = handler.converter.convert_content(handler._get_content(properties), properties)
    soup = BeautifulSoup(blocks[0][1], "html.parser")
    assert soup.get_text() == text.strip().replace("\n", "")
    assert not soup.find("t")
    assert len(soup.find_all("p")) == 1


def test_explicit_text_keeps_heading_and_fenced_code():
    text = "# Literal <T> &\n\n```python\nx: list[str] = '<T>'\n```"
    properties = {"content": [{"text": text}]}
    assert ContentConverter().convert_content(text, properties) == [
        ("paragraph", "<h2>Literal &lt;T&gt; &amp;</h2>"),
        ("code", {"language": "python", "code": "x: list[str] = '<T>'"}),
    ]


def test_bare_preformatted_html_still_converts_to_code():
    assert ContentConverter().convert_content('<pre><code class="language-python">x &lt; y</code></pre>', {}) == [
        ("code", {"language": "python", "code": "x < y"})
    ]
