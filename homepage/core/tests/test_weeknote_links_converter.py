from __future__ import annotations

import io
import json
import re
import threading
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup
from django.core.management import call_command
from django.core.management.base import CommandError as DjangoCommandError

from homepage.core.management.commands.convert_weeknote_links import Command
from homepage.core.weeknotes import converter
from homepage.core.weeknotes.blocks import WeeknoteLinksBlock
from homepage.core.weeknotes.converter import BodyConversion, convert_body, convert_paragraph_html


def _paragraph(value):
    return {"type": "paragraph", "value": value, "id": "paragraph-id"}


def _overview(*blocks):
    return [{"type": "overview", "value": list(blocks), "id": "overview-id"}]


def _weeknote_values(block):
    return [item["value"] for item in block["value"]]


def test_convert_paragraph_html_keeps_one_block_per_consecutive_link_section_and_surrounding_prose():
    conversion = convert_paragraph_html(
        "<p>Intro.</p><h2>Articles</h2><ul>"
        '<li><a href="https://example.com/a">Article A</a> | Useful</li>'
        "</ul><h2>Software</h2><ul>"
        '<li><a href="https://example.com/tool">Tool</a> (Example) | Handy</li>'
        "</ul><p>Outro.</p>"
    )

    assert conversion.changed is True
    assert conversion.converted_sections == 2
    assert [block["type"] for block in conversion.blocks] == [
        "paragraph",
        "weeknote_links",
        "weeknote_links",
        "paragraph",
    ]
    assert conversion.blocks[0]["value"] == "<p>Intro.</p>"
    assert conversion.blocks[3]["value"] == "<p>Outro.</p>"
    articles = _weeknote_values(conversion.blocks[1])
    software = _weeknote_values(conversion.blocks[2])
    assert [(item["category"], item["kind"]) for item in articles] == [("articles", "article")]
    assert [(item["category"], item["kind"]) for item in software] == [("software", "link")]
    assert articles[0]["title"] == "Article A"
    assert articles[0]["description"] == "<p>Useful</p>"
    assert software[0]["source"] == "Example"


def _rendered_sections(blocks):
    """Category headings and link URLs of the rendered stream, in reading order."""
    block = WeeknoteLinksBlock()
    rendered_html = "".join(
        block.render(block.to_python(item["value"])) if item["type"] == "weeknote_links" else item["value"]
        for item in blocks
    )
    soup = BeautifulSoup(rendered_html, "html.parser")
    return [
        element.get_text(strip=True) if element.name == "h2" else element["href"]
        for element in soup.find_all(["h2", "a"])
    ]


@pytest.mark.parametrize(
    "headings",
    [
        ["Software", "Articles", "Software"],  # a category repeated after another one
        ["Videos", "Articles"],  # adjacent sections against the display order
        ["Links", "Open Source", "Software"],  # an alias next to its own category
    ],
)
def test_convert_paragraph_html_renders_adjacent_sections_in_source_order(headings):
    source = "".join(
        f'<h2>{heading}</h2><ul><li><a href="https://example.test/{position}">Item {position}</a></li></ul>'
        for position, heading in enumerate(headings)
    )
    labels = {"Open Source": "Software"}

    conversion = convert_paragraph_html(source)

    assert conversion.converted_sections == len(headings)
    assert conversion.warnings == []
    assert _rendered_sections(conversion.blocks) == [
        part
        for position, heading in enumerate(headings)
        for part in (labels.get(heading, heading), f"https://example.test/{position}")
    ]


def test_convert_paragraph_html_keeps_refused_section_between_converted_runs_in_place():
    source = (
        '<h2>Software</h2><ul><li><a href="https://example.test/one">One</a></li></ul>'
        '<h2>Articles</h2><ul>KEEP<li><a href="https://example.test/two">Two</a></li></ul>'
        '<h2>Software</h2><ul><li><a href="https://example.test/three">Three</a></li></ul>'
    )

    conversion = convert_paragraph_html(source)

    assert [block["type"] for block in conversion.blocks] == ["weeknote_links", "paragraph", "weeknote_links"]
    assert _rendered_sections(conversion.blocks) == [
        "Software",
        "https://example.test/one",
        "Articles",
        "https://example.test/two",
        "Software",
        "https://example.test/three",
    ]


@pytest.mark.parametrize(
    ("prose", "expected"),
    [
        ("&nbsp;Indented text", "\xa0Indented text"),
        ("&nbsp;", "\xa0"),
        ("Trailing space&nbsp;", "Trailing space\xa0"),
    ],
)
def test_convert_paragraph_html_keeps_nonbreaking_spaces_in_top_level_prose(prose, expected):
    conversion = convert_paragraph_html(
        f'{prose}<h2>Articles</h2><ul><li><a href="https://example.com/a">Article A</a></li></ul>'
    )

    assert [block["type"] for block in conversion.blocks] == ["paragraph", "weeknote_links"]
    assert conversion.blocks[0]["value"] == expected


def test_convert_paragraph_html_keeps_section_with_nonbreaking_space_before_list_as_prose():
    source = '<h2>Articles</h2>&nbsp;<ul><li><a href="https://example.com/a">Article A</a></li></ul>'

    conversion = convert_paragraph_html(source)

    assert conversion.changed is False
    assert conversion.converted_sections == 0


def test_convert_paragraph_html_does_not_collapse_across_intervening_prose():
    conversion = convert_paragraph_html(
        '<h2>Articles</h2><ul><li><a href="https://example.com/a">Article A</a></li></ul>'
        "<p>Middle.</p>"
        '<h2>Software</h2><ul><li><a href="https://example.com/tool">Tool</a></li></ul>'
    )

    assert [block["type"] for block in conversion.blocks] == ["weeknote_links", "paragraph", "weeknote_links"]
    assert conversion.blocks[1]["value"] == "<p>Middle.</p>"


def test_convert_paragraph_html_extracts_linked_source_and_limited_rich_description():
    conversion = convert_paragraph_html(
        '<h2>Podcasts</h2><ul><li><a href="https://example.com/episode">Episode</a> '
        '(<a href="https://example.com/show">Show</a>) | Listen with '
        '<a href="https://example.com/notes">notes</a></li></ul>'
    )

    item = _weeknote_values(conversion.blocks[0])[0]

    assert item["category"] == "podcasts"
    assert item["kind"] == "podcast_episode"
    assert item["source"] == "Show"
    assert item["source_url"] == "https://example.com/show"
    assert item["description"] == '<p>Listen with <a href="https://example.com/notes">notes</a></p>'


@pytest.mark.parametrize(
    "source_html",
    [
        "(&lt;em&gt;Source&lt;/em&gt; &amp;copy;)",
        '(<a href="https://example.com/show">&lt;em&gt;Source&lt;/em&gt; &amp;copy;</a>)',
    ],
    ids=["plain-source", "linked-source"],
)
def test_convert_paragraph_html_preserves_escaped_text_in_rendered_links(source_html):
    legacy = (
        '<h2>Podcasts</h2><ul><li><a href="https://example.com/episode">Episode</a> '
        f"{source_html} | &lt;em&gt;Description&lt;/em&gt; &amp;copy; <em>real emphasis</em>"
        " &lt;em&gt;Tail&lt;/em&gt;</li></ul>"
    )

    conversion = convert_paragraph_html(legacy)

    assert not conversion.warnings
    (converted,) = conversion.blocks
    assert converted["type"] == "weeknote_links"
    block = WeeknoteLinksBlock()
    rendered = BeautifulSoup(block.render(block.to_python(converted["value"])), "html.parser")
    assert rendered.select_one(".weeknote-link-title").get_text() == "Episode"
    assert rendered.select_one(".weeknote-link-source").get_text(strip=True) == "<em>Source</em> &copy;"
    description = rendered.select_one(".weeknote-link-description p")
    assert description.get_text() == "<em>Description</em> &copy; real emphasis <em>Tail</em>"
    assert [element.get_text() for element in description.find_all("em")] == ["real emphasis"]


def test_convert_paragraph_html_extracts_source_link_with_parenthesis_in_url():
    conversion = convert_paragraph_html(
        '<h2>Podcasts</h2><ul><li><a href="https://example.com/episode">Episode</a> '
        '(<a href="https://example.com/show(foo)">Show</a>) | Listen</li></ul>'
    )

    item = _weeknote_values(conversion.blocks[0])[0]

    assert item["source"] == "Show"
    assert item["source_url"] == "https://example.com/show(foo)"
    assert item["description"] == "<p>Listen</p>"


def test_convert_paragraph_html_keeps_parentheses_after_source_in_description():
    conversion = convert_paragraph_html(
        '<h2>Podcasts</h2><ul><li><a href="https://example.com/episode">Episode</a> '
        '(<a href="https://example.com/show">Show</a>) | See '
        '<a href="https://example.com/notes">notes</a> (now)</li></ul>'
    )

    item = _weeknote_values(conversion.blocks[0])[0]

    assert item["source"] == "Show"
    assert item["description"] == '<p>See <a href="https://example.com/notes">notes</a> (now)</p>'


@pytest.mark.parametrize(
    ("source_markup", "source_label", "source_url"),
    [
        ("Example (English)", "Example (English)", ""),
        ("Example (English (UK))", "Example (English (UK))", ""),
        (
            '<a href="https://example.test/show(uk)">Show (English (UK))</a>',
            "Show (English (UK))",
            "https://example.test/show(uk)",
        ),
    ],
    ids=["plain", "nested", "linked"],
)
def test_convert_paragraph_html_keeps_balanced_parentheses_in_source(source_markup, source_label, source_url):
    conversion = convert_paragraph_html(
        '<h2>Podcasts</h2><ul><li><a href="https://example.test/episode">Episode</a> '
        f'({source_markup}) | See <a href="https://example.test/notes">notes</a> (now)</li></ul>'
    )

    assert not conversion.warnings
    (block,) = conversion.blocks
    assert block["type"] == "weeknote_links"
    (item,) = _weeknote_values(block)
    assert (item["source"], item["source_url"]) == (source_label, source_url)
    assert item["description"] == '<p>See <a href="https://example.test/notes">notes</a> (now)</p>'


@pytest.mark.parametrize(
    "source_markup",
    ["Example (English) | Listen (now)", '<a href="https://example.test/show">Show (English)</a> | Listen'],
    ids=["plain", "linked"],
)
def test_convert_paragraph_html_preserves_section_with_unclosed_source(source_markup):
    section = (
        '<h2>Podcasts</h2><ul><li><a href="https://example.test/episode">Episode</a> ' f"({source_markup}</li></ul>"
    )
    conversion = convert_paragraph_html(
        section + '<h2>Software</h2><ul><li><a href="https://example.test/tool">Tool</a></li></ul>'
    )

    assert [block["type"] for block in conversion.blocks] == ["paragraph", "weeknote_links"]
    assert conversion.blocks[0]["value"] == section
    (warning,) = conversion.warnings
    assert (warning.heading, warning.message) == ("Podcasts", "List item source has unbalanced parentheses.")


@pytest.mark.parametrize(
    "source_markup",
    [
        '(<a href="https://example.test/show">Show (English</a>)) | Listen',
        '(<a href="https://example.test/show">Show English)</a> | Listen',
    ],
    ids=["open-inside-link", "close-inside-link"],
)
def test_convert_paragraph_html_preserves_section_when_source_parentheses_cross_a_link(source_markup):
    section = (
        '<h2>Podcasts</h2><ul><li><a href="https://example.test/episode">Episode</a> ' f"{source_markup}</li></ul>"
    )
    conversion = convert_paragraph_html(
        section + '<h2>Software</h2><ul><li><a href="https://example.test/tool">Tool</a></li></ul>'
    )

    assert [block["type"] for block in conversion.blocks] == ["paragraph", "weeknote_links"]
    assert conversion.blocks[0]["value"] == section
    (warning,) = conversion.warnings
    assert (warning.heading, warning.message) == (
        "Podcasts",
        "List item source has parentheses that cross a link or markup boundary.",
    )


def test_convert_paragraph_html_preserves_blank_text_between_preserved_inline_nodes():
    conversion = convert_paragraph_html(
        'Read <a href="https://example.com/a">A</a> <a href="https://example.com/b">B</a>'
        '<h2>Articles</h2><ul><li><a href="https://example.com/c">C</a></li></ul>'
    )

    assert conversion.blocks[0]["type"] == "paragraph"
    assert (
        conversion.blocks[0]["value"]
        == 'Read <a href="https://example.com/a">A</a> <a href="https://example.com/b">B</a>'
    )


def test_convert_paragraph_html_warns_and_preserves_ambiguous_heading():
    conversion = convert_paragraph_html(
        '<h2>Podcasts / Videos</h2><ul><li><a href="https://example.com/item">Item</a></li></ul>'
    )

    assert conversion.changed is False
    assert conversion.blocks == []
    assert conversion.warnings[0].heading == "Podcasts / Videos"


def test_convert_paragraph_html_warns_and_preserves_section_that_fails_block_validation():
    conversion = convert_paragraph_html(
        '<h2>Articles</h2><ul><li><a href="/internal/path/">Internal article</a></li></ul>'
        '<h2>Software</h2><ul><li><a href="https://example.com/tool">Tool</a></li></ul>'
    )

    assert conversion.changed is True
    assert [block["type"] for block in conversion.blocks] == ["paragraph", "weeknote_links"]
    assert conversion.blocks[0]["value"] == (
        '<h2>Articles</h2><ul><li><a href="/internal/path/">Internal article</a></li></ul>'
    )
    assert _weeknote_values(conversion.blocks[1])[0]["title"] == "Tool"
    assert conversion.warnings[0].heading == "Articles"
    assert conversion.warnings[0].message == "List section failed structured block validation."


def test_convert_paragraph_html_prepares_each_section_once(monkeypatch):
    cleaned_sizes = []
    original_clean = WeeknoteLinksBlock.clean

    def record_clean(block, value):
        cleaned_sizes.append(len(value))
        return original_clean(block, value)

    monkeypatch.setattr(WeeknoteLinksBlock, "clean", record_clean)
    invalid_section = '<h2>Software</h2><ul><li><a href="/relative">Tool</a></li></ul>'
    items = "".join(f'<li><a href="https://example.test/{i}">Article {i}</a></li>' for i in range(100))

    conversion = convert_paragraph_html(f"<h2>Articles</h2><ul>{items}</ul>{invalid_section}")

    assert [block["type"] for block in conversion.blocks] == ["weeknote_links", "paragraph"]
    prepared = conversion.blocks[0]["value"]
    assert all(item["type"] == "item" and item["id"] for item in prepared)
    assert [item["title"] for item in _weeknote_values(conversion.blocks[0])] == [f"Article {i}" for i in range(100)]
    assert conversion.blocks[1]["value"] == invalid_section
    (warning,) = conversion.warnings
    assert (warning.heading, warning.message) == ("Software", "List section failed structured block validation.")
    assert cleaned_sizes == [100, 1]


@pytest.mark.parametrize(
    ("heading_attrs", "list_attrs"),
    [(' id="saved-section"', ""), ("", ' id="saved-section"')],
    ids=["heading-id", "list-id"],
)
def test_convert_paragraph_html_preserves_section_fragment_targets(heading_attrs, list_attrs):
    legacy = (
        '<p><a href="#saved-section">Jump to articles</a></p>'
        f"<h2{heading_attrs}>Articles</h2><ul{list_attrs}>"
        '<li><a href="https://example.com/a">Article</a></li></ul>'
        "<h3>Software</h3><ul>"
        '<li><a href="https://example.com/tool">Tool</a></li></ul>'
    )

    conversion = convert_body(_overview(_paragraph(legacy)))

    assert conversion.converted_sections == 1
    paragraph, links = conversion.body[0]["value"]
    assert paragraph["type"] == "paragraph"
    preserved = BeautifulSoup(paragraph["value"], "html.parser")
    jump = preserved.find("a", href="#saved-section")
    assert preserved.find(id=jump["href"][1:]).name == ("h2" if heading_attrs else "ul")
    assert links["type"] == "weeknote_links"
    assert [item["title"] for item in _weeknote_values(links)] == ["Tool"]
    assert [(warning.heading, warning.message) for warning in conversion.warnings] == [
        ("Articles", "Link section has a fragment anchor that the structured block cannot keep.")
    ]


@pytest.mark.parametrize(
    "item_html",
    [
        '<li id="saved-section"><a href="https://example.com/a">Article</a></li>',
        '<li><a id="saved-section" href="https://example.com/a">Article</a></li>',
        '<li><a name="saved-section" href="https://example.com/a">Article</a></li>',
        '<li><a href="https://example.com/a">Article</a>'
        ' (via <a id="saved-section" href="https://example.com/">Src</a>)</li>',
    ],
    ids=["item-id", "link-id", "link-name", "source-link-id"],
)
def test_convert_paragraph_html_preserves_fragment_targets_inside_the_list(item_html):
    legacy = (
        '<p><a href="#saved-section">Jump to article</a></p>'
        f"<h2>Articles</h2><ul>{item_html}</ul>"
        '<h3>Software</h3><ul><li><a href="https://example.com/tool">Tool</a></li></ul>'
    )

    conversion = convert_body(_overview(_paragraph(legacy)))

    assert conversion.converted_sections == 1
    paragraph, links = conversion.body[0]["value"]
    assert paragraph["type"] == "paragraph"
    preserved = BeautifulSoup(paragraph["value"], "html.parser")
    assert preserved.find(id="saved-section") or preserved.find("a", attrs={"name": "saved-section"})
    assert [item["title"] for item in _weeknote_values(links)] == ["Tool"]
    assert [(warning.heading, warning.message) for warning in conversion.warnings] == [
        ("Articles", "Link section has a fragment anchor that the structured block cannot keep.")
    ]


@pytest.mark.parametrize(
    ("tag", "attrs"),
    [
        ("h2", ' lang="de"'),
        ("ul", ' dir="rtl"'),
        ("ul", ' class="custom-list"'),
        ("li", ' value="3"'),
        ("primary", ' title="Article title"'),
        ("source", ' hreflang="fr"'),
    ],
    ids=["heading-lang", "list-dir", "list-class", "item-value", "primary-title", "source-hreflang"],
)
def test_convert_paragraph_html_keeps_attributed_section_as_prose(tag, attrs):
    attributes = {tag: attrs}
    section = (
        f'<h2{attributes.get("h2", "")}>Articles</h2><ul{attributes.get("ul", "")}>'
        f'<li{attributes.get("li", "")}><a href="https://example.test/a"{attributes.get("primary", "")}>A</a>'
        f' (<a href="https://example.test/source"{attributes.get("source", "")}>Source</a>)</li></ul>'
    )
    plain = '<h3>Software</h3><ul><li><a href="https://example.test/tool">Tool</a></li></ul>'

    conversion = convert_body(_overview(_paragraph(plain + section + plain)))

    assert conversion.converted_sections == 2
    before, preserved, after = conversion.body[0]["value"]
    assert [before["type"], preserved["type"], after["type"]] == ["weeknote_links", "paragraph", "weeknote_links"]
    assert preserved["value"] == str(BeautifulSoup(section, "html.parser"))
    assert [_weeknote_values(block)[0]["title"] for block in (before, after)] == ["Tool", "Tool"]
    assert [warning.heading for warning in conversion.warnings] == ["Articles"]


def test_convert_paragraph_html_keeps_whitespace_inside_refused_section():
    refused = '<h2 lang="de">Articles</h2> <ul dir="rtl"><li><a href="https://example.test/a">A</a></li></ul>'
    plain = '<h3>Software</h3><ul><li><a href="https://example.test/tool">Tool</a></li></ul>'

    conversion = convert_paragraph_html(refused + plain)

    assert [block["type"] for block in conversion.blocks] == ["paragraph", "weeknote_links"]
    assert conversion.blocks[0]["value"] == refused


def test_convert_paragraph_html_extracts_source_after_blank_comment():
    conversion = convert_paragraph_html(
        '<h2>Articles</h2><ul><li><a href="https://example.test/a">A</a><!-- -->'
        ' (<a href="https://example.test/source">Source</a>)</li></ul>'
    )

    item = _weeknote_values(conversion.blocks[0])[0]
    assert (item["source"], item["source_url"]) == ("Source", "https://example.test/source")


def test_convert_paragraph_html_keeps_attributed_source_after_blank_comment_as_prose():
    section = (
        '<h2>Articles</h2><ul><li><a href="https://example.test/a">A</a><!-- -->'
        ' (<a href="https://example.test/source" hreflang="fr">Source</a>)</li></ul>'
    )

    conversion = convert_paragraph_html(section)

    assert conversion.changed is False
    assert conversion.converted_sections == 0


def test_convert_paragraph_html_only_looks_ahead_from_headings_without_slicing(monkeypatch):
    class TrackedNodes(list):
        reads = 0
        slices = 0

        def __getitem__(self, index):
            if isinstance(index, slice):
                self.slices += 1
            else:
                self.reads += 1
            return super().__getitem__(index)

    lookahead = converter._next_meaningful_node
    tracked = None
    lookahead_calls = 0

    def track_lookahead(nodes, start):
        nonlocal tracked, lookahead_calls
        if tracked is None:
            tracked = TrackedNodes(nodes)
        lookahead_calls += 1
        return lookahead(tracked, start)

    monkeypatch.setattr(converter, "_next_meaningful_node", track_lookahead)
    intro = "<p>Prose</p><h4>Other heading</h4>" * 500
    article_list = '<ul><li><a href="https://example.com/a">Article</a></li></ul>'
    tool_list = '<ul><li><a href="https://example.com/tool">Tool</a></li></ul>'
    ambiguous_heading = "<h2>Podcasts / Videos</h2>"
    trailing_heading = "<h3>Links</h3>"

    conversion = convert_paragraph_html(
        f"{intro}<h2>Articles</h2>\n  {article_list}<h3>Software</h3>\n\t{tool_list}"
        f"{ambiguous_heading}\n  {article_list}{trailing_heading}"
    )

    assert conversion.converted_sections == 2
    before, articles, software, after = conversion.blocks
    assert (before["type"], before["value"]) == ("paragraph", intro)
    assert [articles["type"], software["type"]] == ["weeknote_links", "weeknote_links"]
    assert [item["title"] for item in _weeknote_values(articles)] == ["Article"]
    assert [item["title"] for item in _weeknote_values(software)] == ["Tool"]
    assert (after["type"], after["value"]) == ("paragraph", ambiguous_heading + "\n" + article_list + trailing_heading)
    assert [(warning.heading, warning.message) for warning in conversion.warnings] == [
        ("Podcasts / Videos", "Ambiguous link heading preserved.")
    ]
    assert tracked.slices == 0
    assert lookahead_calls == 4
    assert tracked.reads <= 8


def test_convert_body_only_rewrites_overview_paragraphs():
    body = _overview(
        _paragraph('<p>Intro.</p><h2>Weeknotes</h2><ul><li><a href="https://example.com/w">Weeklog</a></li></ul>'),
        {"type": "image", "value": 1, "id": "image-id"},
    )

    conversion = convert_body(body)

    assert conversion.changed is True
    overview_value = conversion.body[0]["value"]
    assert [block["type"] for block in overview_value] == ["paragraph", "weeknote_links", "image"]
    assert _weeknote_values(overview_value[1])[0]["category"] == "weeknotes"


ARTICLE_ITEM = '<li><a href="https://example.test/a">A</a> (Example Blog) | Worth reading</li>'


@pytest.mark.parametrize(
    ("stray", "message"),
    [
        ("KEEP THIS", "List section has text outside list items."),
        ("<div>KEEP THIS</div>", "List section has a <div> element outside list items."),
        ('<a href="https://example.test/stray">KEEP THIS</a>', "List section has a <a> element outside list items."),
        ("<p>KEEP THIS</p>", "List section has a <p> element outside list items."),
        ("<!-- KEEP THIS -->", "List section has a comment outside list items."),
    ],
)
@pytest.mark.parametrize("position", ["before", "between", "after"])
def test_convert_paragraph_html_preserves_list_with_stray_direct_content(stray, message, position):
    second_item = '<li><a href="https://example.test/b">B</a></li>'
    inner = {
        "before": stray + ARTICLE_ITEM + second_item,
        "between": ARTICLE_ITEM + stray + second_item,
        "after": ARTICLE_ITEM + second_item + stray,
    }[position]
    source = f"<p>Intro.</p><h2>Articles</h2><ul>{inner}</ul><p>Outro.</p>"

    conversion = convert_paragraph_html(source)

    # Nothing converted: the caller keeps the original paragraph block as is.
    assert conversion.changed is False
    assert conversion.blocks == []
    assert [(warning.heading, warning.message) for warning in conversion.warnings] == [("Articles", message)]


def test_convert_paragraph_html_keeps_stray_list_content_next_to_converted_sections():
    stray_section = (
        "<h2>Articles</h2><ul>KEEP THIS"
        '<li><a href="https://example.test/a">A</a></li>'
        "<div>AND THIS</div><!-- and this --></ul>"
    )
    source = (
        "<p>Intro.</p>"
        + stray_section
        + '<h2>Software</h2><ul><li><a href="https://example.test/tool">Tool</a></li></ul>'
        + "<p>Outro.</p>"
    )

    conversion = convert_paragraph_html(source)

    assert [block["type"] for block in conversion.blocks] == ["paragraph", "weeknote_links", "paragraph"]
    assert conversion.blocks[0]["value"] == "<p>Intro.</p>" + stray_section
    assert [item["title"] for item in _weeknote_values(conversion.blocks[1])] == ["Tool"]
    assert conversion.blocks[2]["value"] == "<p>Outro.</p>"
    assert conversion.converted_sections == 1


def test_convert_paragraph_html_allows_whitespace_between_list_items():
    conversion = convert_paragraph_html(
        "<h2>Articles</h2>\n<ul>\n  "
        '<li><a href="https://example.test/a">A</a></li>\n\t\r\f '
        '<li><a href="https://example.test/b">B</a></li>\n</ul>'
    )

    assert conversion.changed is True
    assert conversion.warnings == []
    assert [item["title"] for item in _weeknote_values(conversion.blocks[0])] == ["A", "B"]


@pytest.mark.parametrize(
    ("visible_space", "character"),
    [("&nbsp;", "\xa0"), ("&emsp;", "\u2003"), ("\u3000", "\u3000"), ("\n&nbsp;\n", "\xa0")],
)
def test_convert_paragraph_html_keeps_list_with_visible_space_between_items_as_prose(visible_space, character):
    visible_list = (
        "<h2>Articles</h2><ul>"
        '<li><a href="https://example.test/a">A</a></li>'
        f"{visible_space}"
        '<li><a href="https://example.test/b">B</a></li></ul>'
    )
    source = visible_list + '<h2>Software</h2><ul><li><a href="https://example.test/tool">Tool</a></li></ul>'

    conversion = convert_paragraph_html(source)

    assert [block["type"] for block in conversion.blocks] == ["paragraph", "weeknote_links"]
    preserved = conversion.blocks[0]["value"]
    assert preserved == str(BeautifulSoup(visible_list, "html.parser"))
    assert character in BeautifulSoup(preserved, "html.parser").ul.get_text()
    assert [item["title"] for item in _weeknote_values(conversion.blocks[1])] == ["Tool"]
    assert conversion.converted_sections == 1
    assert [(warning.heading, warning.message) for warning in conversion.warnings] == [
        ("Articles", "List section has text outside list items.")
    ]


@pytest.mark.parametrize(
    "source_markup",
    [
        '<a href="https://example.test/a-src">A</a> / <a href="https://example.test/b-src">B</a>',
        '<a href="https://example.test/a-src">A</a><a href="https://example.test/b-src">B</a>',
        'via <a href="https://example.test/show">Show</a>',
        '<a href="https://example.test/show">Show</a>, Episode 12',
        "<em>Example</em> Blog",
        '<a href="https://example.test/show"><strong>Show</strong></a>',
        '<a href="https://example.test/show">Show</a><!-- sponsored -->',
    ],
)
def test_convert_paragraph_html_preserves_section_with_unrepresentable_source(source_markup):
    section = (
        "<h2>Podcasts</h2><ul>"
        f'<li><a href="https://example.test/episode">Episode</a> ({source_markup}) description</li>'
        '<li><a href="https://example.test/other">Other</a> (Plain Source)</li>'
        "</ul>"
    )

    conversion = convert_paragraph_html("<p>Intro.</p>" + section)

    assert conversion.changed is False
    assert conversion.blocks == []
    assert [(warning.heading, warning.message) for warning in conversion.warnings] == [
        (
            "Podcasts",
            "List item source has several links, rich markup or attributes that the source fields cannot keep.",
        )
    ]


def test_convert_paragraph_html_still_converts_plain_and_single_link_sources():
    conversion = convert_paragraph_html(
        "<h2>Podcasts</h2><ul>"
        '<li><a href="https://example.test/one">One</a> (<a href="https://example.test/show">Show</a>) | Listen</li>'
        '<li><a href="https://example.test/two">Two</a> ( <a href="https://example.test/show2">Show 2</a> )</li>'
        '<li><a href="https://example.test/three">Three</a> (Plain &amp; Simple) - Notes</li>'
        '<li><a href="https://example.test/four">Four</a> | No source</li>'
        "</ul>"
    )

    assert conversion.warnings == []
    items = _weeknote_values(conversion.blocks[0])
    assert [(item["title"], item["source"], item["source_url"], item["description"]) for item in items] == [
        ("One", "Show", "https://example.test/show", "<p>Listen</p>"),
        ("Two", "Show 2", "https://example.test/show2", ""),
        ("Three", "Plain & Simple", "", "<p>Notes</p>"),
        ("Four", "", "", "<p>No source</p>"),
    ]


REALISTIC_WEEKNOTE_OVERVIEW = (
    '<p>Diese Woche ging es vor allem um den <a href="https://example.test/umzug">Umzug</a> der Infrastruktur.</p>'
    "<h2>Articles</h2>"
    "<ul>"
    '<li><a href="https://example.test/postgres">Postgres 18 Released</a> (PostgreSQL News) | '
    "Asynchrones I/O und <code>uuidv7()</code></li>"
    '<li><a href="https://example.test/django">Django 6.0 Tasks</a> '
    '(<a href="https://example.test/djangoproject">Django Weblog</a>)</li>'
    "</ul>"
    "<h2>Podcasts</h2>"
    "<ul>"
    '<li><a href="https://example.test/episode">Lokale Modelle</a> '
    '(<a href="https://example.test/show-a">Show A</a> / <a href="https://example.test/show-b">Show B</a>) '
    "| Crossover-Folge</li>"
    "</ul>"
    "<h2>Software</h2>"
    "<ul>Notiz an mich: sortieren"
    '<li><a href="https://example.test/uv">uv</a> | schneller Paketmanager</li>'
    "</ul>"
    "<h2>Videos</h2>"
    "<ul>"
    '<li><a href="https://example.test/talk">Keynote</a> (DjangoCon) | Sehr sehenswert</li>'
    "</ul>"
    "<p>Bis nächste Woche.</p>"
)


def _links_in_order(blocks):
    """Every link a reader can click after conversion, in document order."""
    links = []
    for block in blocks:
        if block["type"] == "paragraph":
            soup = BeautifulSoup(block["value"], "html.parser")
            links.extend(a["href"] for a in soup.find_all("a"))
            continue
        for item in _weeknote_values(block):
            links.append(item["url"])
            if item["source_url"]:
                links.append(item["source_url"])
            soup = BeautifulSoup(item["description"], "html.parser")
            links.extend(a["href"] for a in soup.find_all("a"))
    return links


def _text_in_order(blocks):
    """The words a reader can see after conversion, without category headings."""
    words = []
    for block in blocks:
        if block["type"] == "paragraph":
            words.append(BeautifulSoup(block["value"], "html.parser").get_text(" "))
            continue
        for item in _weeknote_values(block):
            description = BeautifulSoup(item["description"], "html.parser").get_text(" ")
            words.append(" ".join([item["title"], item["source"], description]))
    return re.sub(r"[\s()|]+", " ", " ".join(words)).strip()


def test_realistic_weeknote_round_trip_keeps_every_link_and_word():
    conversion = convert_paragraph_html(REALISTIC_WEEKNOTE_OVERVIEW)

    assert [block["type"] for block in conversion.blocks] == [
        "paragraph",  # intro
        "weeknote_links",  # Articles
        "paragraph",  # Podcasts (two source links) + Software (stray text), unchanged
        "weeknote_links",  # Videos
        "paragraph",  # outro
    ]
    assert conversion.converted_sections == 2
    assert [(warning.heading, warning.message) for warning in conversion.warnings] == [
        (
            "Podcasts",
            "List item source has several links, rich markup or attributes that the source fields cannot keep.",
        ),
        ("Software", "List section has text outside list items."),
    ]
    preserved = conversion.blocks[2]["value"]
    assert preserved.startswith("<h2>Podcasts</h2><ul>")
    assert '(<a href="https://example.test/show-a">Show A</a> / <a href="https://example.test/show-b">Show B</a>)' in (
        preserved
    )
    assert "<ul>Notiz an mich: sortieren<li>" in preserved

    source_soup = BeautifulSoup(REALISTIC_WEEKNOTE_OVERVIEW, "html.parser")
    assert _links_in_order(conversion.blocks) == [a["href"] for a in source_soup.find_all("a")]
    for heading in source_soup.find_all("h2"):
        if heading.get_text() in {"Articles", "Videos"}:
            heading.decompose()  # converted headings become the category
    expected_text = re.sub(r"[\s()|]+", " ", source_soup.get_text(" ")).strip()
    assert _text_in_order(conversion.blocks) == expected_text
    assert "<code>uuidv7()</code>" in _weeknote_values(conversion.blocks[1])[0]["description"]


@pytest.mark.parametrize(
    "heading_html",
    [
        '<h2><img alt="" src="https://example.test/icon.png"/>Articles</h2>',
        '<h2><a href="https://example.test/all-articles">Articles</a></h2>',
        "<h2><em>Articles</em></h2>",
        "<h3>Articles<!-- curated --></h3>",
    ],
)
def test_convert_paragraph_html_preserves_section_whose_heading_has_markup(heading_html):
    section = heading_html + '<ul><li><a href="https://example.test/a">A</a> (Source) | Notes</li></ul>'
    videos = '<h2>Videos</h2><ul><li><a href="https://example.test/v">V</a></li></ul>'

    conversion = convert_paragraph_html("<p>Intro.</p>" + section + videos)

    assert [block["type"] for block in conversion.blocks] == ["paragraph", "weeknote_links"]
    # The refused section round-trips byte for byte, markup included ...
    assert conversion.blocks[0]["value"] == "<p>Intro.</p>" + section
    assert [(warning.heading, warning.message) for warning in conversion.warnings] == [
        ("Articles", "Link heading has markup that the category heading cannot keep.")
    ]
    # ... and the plain section next to it is still converted.
    assert [item["title"] for item in _weeknote_values(conversion.blocks[1])] == ["V"]
    assert conversion.converted_sections == 1


@pytest.mark.parametrize(
    "link_html",
    [
        '<a href="https://example.test/a"><img alt="Logo" src="https://example.test/logo.png"/> Project</a>',
        '<a href="https://example.test/a"><code>uv</code> 1.0</a>',
        '<a href="https://example.test/a">An <em>important</em> release</a>',
        '<a href="https://example.test/a">Release<!-- draft --></a>',
    ],
)
def test_convert_paragraph_html_preserves_section_whose_primary_link_has_markup(link_html):
    section = (
        "<h2>Software</h2><ul>"
        f"<li>{link_html} (Source) | Notes</li>"
        '<li><a href="https://example.test/plain">Plain</a></li>'
        "</ul>"
    )

    conversion = convert_paragraph_html(section)

    assert conversion.changed is False
    assert conversion.blocks == []
    assert [(warning.heading, warning.message) for warning in conversion.warnings] == [
        ("Software", "List item primary link has markup that the title field cannot keep.")
    ]
    # Unchanged conversions leave the stored paragraph alone, so nothing is lost.
    body = _overview(_paragraph(section))
    assert convert_body(body).body == body


def test_convert_paragraph_html_keeps_plain_heading_and_title_text_exactly():
    conversion = convert_paragraph_html(
        "<h2> Open Source </h2><ul>"
        '<li><a href="https://example.test/a">Tom &amp; Jerry &lt;3 Python</a></li>'
        "</ul>"
    )

    assert conversion.warnings == []
    [item] = _weeknote_values(conversion.blocks[0])
    assert (item["category"], item["title"]) == ("software", "Tom & Jerry <3 Python")


def test_round_trip_with_heading_and_title_markup_keeps_every_link_image_and_word():
    source = (
        "<p>Intro.</p>"
        '<h2><img alt="Icon" src="https://example.test/icon.png"/>Articles</h2>'
        '<ul><li><a href="https://example.test/one">One</a> (Source) | First</li></ul>'
        "<h2>Software</h2>"
        '<ul><li><a href="https://example.test/two"><code>two</code> tool</a> | Second</li></ul>'
        "<h2>Videos</h2>"
        '<ul><li><a href="https://example.test/three">Three</a> (Channel) | Third</li></ul>'
    )

    conversion = convert_paragraph_html(source)

    assert [block["type"] for block in conversion.blocks] == ["paragraph", "weeknote_links"]
    assert conversion.converted_sections == 1
    preserved = BeautifulSoup(conversion.blocks[0]["value"], "html.parser")
    source_soup = BeautifulSoup(source, "html.parser")
    assert [str(img) for img in preserved.find_all("img")] == [str(img) for img in source_soup.find_all("img")]
    assert [str(code) for code in preserved.find_all("code")] == ["<code>two</code>"]
    assert _links_in_order(conversion.blocks) == [a["href"] for a in source_soup.find_all("a")]
    for heading in source_soup.find_all("h2"):
        if heading.get_text() == "Videos":
            heading.decompose()  # the only converted heading becomes the category
    expected_text = re.sub(r"[\s()|]+", " ", source_soup.get_text(" ")).strip()
    assert _text_in_order(conversion.blocks) == expected_text


class FakeRevision:
    id = 42

    def __init__(self):
        self.published = False

    def publish(self):
        self.published = True


class FakePost:
    def __init__(self, *, body, slug="weeknotes-2026-04-27", live=True, has_unpublished_changes=False):
        self.pk = 7
        self.slug = slug
        self.body = SimpleNamespace(raw_data=body)
        self.live = live
        self.latest_revision_id = 41
        self.live_revision_id = 41 if live else None
        self.has_unpublished_changes = has_unpublished_changes
        self.saved_revision = None
        self.save_changed = None

    def save_revision(self, *, changed):
        self.save_changed = changed
        self.saved_revision = FakeRevision()
        return self.saved_revision


class FakeQuerySet:
    hydrated = []

    def __init__(self, posts):
        self.posts = posts

    def using(self, alias):
        return self

    def filter(self, **kwargs):
        posts = self.posts
        for field, expected in kwargs.items():
            name, _, lookup = field.partition("__")

            def matches(post):
                actual = getattr(post, name)
                if lookup == "startswith":
                    return actual.startswith(expected)
                if lookup == "gt":
                    return actual > expected
                if lookup == "lte":
                    return actual <= expected
                return actual == expected

            posts = [post for post in posts if matches(post)]
        return FakeQuerySet(posts)

    def annotate(self, **kwargs):
        for post in self.posts:
            post._body_bytes = len(json.dumps(getattr(post.body, "raw_data", post.body)).encode("utf-8"))
        return self

    def order_by(self, field):
        if field.lstrip("-") == "pk":
            return FakeQuerySet(sorted(self.posts, key=lambda post: post.pk, reverse=field.startswith("-")))
        return self

    def values_list(self, field, *, flat):
        return SimpleNamespace(first=lambda: getattr(self.posts[0], field) if self.posts else None)

    def first(self):
        if not self.posts:
            return None
        self.hydrated.append(self.posts[0].pk)
        return self.posts[0]

    def __iter__(self):
        return iter(self.posts)


def test_convert_weeknote_links_command_dry_run_does_not_save(monkeypatch):
    post = FakePost(
        body=_overview(_paragraph('<h2>Articles</h2><ul><li><a href="https://example.com/a">A</a></li></ul>'))
    )
    _patch_post_model(monkeypatch, [post])
    stdout = io.StringIO()

    call_command("convert_weeknote_links", stdout=stdout)

    assert post.saved_revision is None
    assert "would convert 1 post(s)" in stdout.getvalue()


def test_convert_weeknote_links_command_write_and_publish(monkeypatch):
    post = FakePost(
        body=_overview(_paragraph('<h2>Articles</h2><ul><li><a href="https://example.com/a">A</a></li></ul>'))
    )
    _patch_post_model(monkeypatch, [post])
    stdout = io.StringIO()

    call_command("convert_weeknote_links", "--write", "--publish", stdout=stdout)

    assert post.save_changed is True
    assert post.saved_revision.published is True
    assert "converted 1 post(s), published 1" in stdout.getvalue()


def test_convert_weeknote_links_command_suppress_webmentions_requires_publish(monkeypatch):
    _patch_post_model(monkeypatch, [])

    with pytest.raises(DjangoCommandError, match="--suppress-webmentions requires --publish"):
        call_command("convert_weeknote_links", "--suppress-webmentions", stdout=io.StringIO())


def test_convert_weeknote_links_command_suppresses_webmentions_while_publishing(monkeypatch):
    post = FakePost(
        body=_overview(_paragraph('<h2>Articles</h2><ul><li><a href="https://example.com/a">A</a></li></ul>'))
    )
    _patch_post_model(monkeypatch, [post])
    enter = Mock()
    exit_ = Mock()

    class FakeSuppression:
        def __enter__(self):
            enter()

        def __exit__(self, *_args):
            exit_()

    monkeypatch.setattr(Command, "_suppress_webmentions", lambda self: FakeSuppression())

    call_command("convert_weeknote_links", "--write", "--publish", "--suppress-webmentions", stdout=io.StringIO())

    assert post.saved_revision.published is True
    enter.assert_called_once_with()
    exit_.assert_called_once_with()


def test_convert_weeknote_links_command_write_skips_existing_unpublished_changes(monkeypatch):
    post = FakePost(
        body=_overview(_paragraph('<h2>Articles</h2><ul><li><a href="https://example.com/a">A</a></li></ul>')),
        has_unpublished_changes=True,
    )
    _patch_post_model(monkeypatch, [post])
    stdout = io.StringIO()

    call_command("convert_weeknote_links", "--write", stdout=stdout)

    assert post.saved_revision is None
    assert "converted 0 post(s), published 0, skipped 1" in stdout.getvalue()


def test_convert_weeknote_links_command_fail_on_warnings(monkeypatch):
    post = FakePost(
        body=_overview(_paragraph('<h2>Podcasts / Videos</h2><ul><li><a href="https://example.com/a">A</a></li></ul>'))
    )
    _patch_post_model(monkeypatch, [post])

    with pytest.raises(DjangoCommandError):
        call_command("convert_weeknote_links", "--fail-on-warnings", stdout=io.StringIO())


def test_save_conversion_skips_pages_with_existing_unpublished_changes(monkeypatch):
    post = FakePost(body=[], live=True, has_unpublished_changes=True)
    conversion = BodyConversion(body=[{"type": "overview", "value": []}], changed=True)

    _patch_locked_current_post(monkeypatch)

    result = Command()._save_conversion(post, conversion, publish=True)

    assert post.body.raw_data == []
    assert post.saved_revision is None
    assert result == {"revision_id": None, "published": False, "skipped": "has_unpublished_changes"}


def test_suppress_webmentions_disconnects_and_reconnects_signal(monkeypatch):
    signal = Mock()
    signal.disconnect.return_value = True
    receiver = Mock()
    monkeypatch.setattr("wagtail.signals.page_published", signal)
    monkeypatch.setattr("homepage.core.webmention_integration.send_webmentions_on_publish", receiver)

    with Command()._suppress_webmentions():
        signal.disconnect.assert_called_once_with(receiver)
        signal.connect.assert_not_called()

    signal.connect.assert_called_once_with(receiver)


def _patch_post_model(monkeypatch, posts):
    import cast.models

    monkeypatch.setattr(cast.models.Post, "objects", FakeQuerySet(posts))
    _patch_locked_current_post(monkeypatch)


def _patch_locked_current_post(monkeypatch):
    """Fake posts have no database row to lock: the current post is the fake itself."""

    @contextmanager
    def locked_current_post(self, post):
        yield post

    monkeypatch.setattr(Command, "_locked_current_post", locked_current_post)


def _weeknote_post(*, slug, overview_html, pk=None):
    from cast.models import Blog, Post
    from wagtail.models import Locale, Page

    root = Page.get_first_root_node()
    if root is None:
        Locale.objects.get_or_create(language_code="en")
        root = Page.add_root(instance=Page(title="Root", slug="root"))
    blog = root.add_child(instance=Blog(title="Weeknote blog", slug=f"blog-{slug}"))
    body = json.dumps([{"type": "overview", "value": [{"type": "paragraph", "value": overview_html}]}])
    return blog.add_child(instance=Post(pk=pk, title=slug, slug=slug, body=body))


def _overview_blocks(page):
    return [(child["type"], child["value"]) for child in page.body.raw_data[0]["value"]]


@pytest.mark.django_db
def test_convert_weeknote_links_command_persists_unconvertible_sections_unchanged(tmp_path):
    from cast.models import Post

    post = _weeknote_post(slug="weeknotes-2026-10-05", overview_html=REALISTIC_WEEKNOTE_OVERVIEW)
    report_path = tmp_path / "report.json"

    call_command("convert_weeknote_links", "--write", "--report", str(report_path), stdout=io.StringIO())

    revised = Post.objects.get(pk=post.pk).get_latest_revision_as_object()
    blocks = _overview_blocks(revised)
    assert [block_type for block_type, _value in blocks] == [
        "paragraph",
        "weeknote_links",
        "paragraph",
        "weeknote_links",
        "paragraph",
    ]
    # The persisted HTML of the two refused sections is the source HTML.
    assert blocks[2][1] == (
        "<h2>Podcasts</h2>"
        "<ul>"
        '<li><a href="https://example.test/episode">Lokale Modelle</a> '
        '(<a href="https://example.test/show-a">Show A</a> / <a href="https://example.test/show-b">Show B</a>) '
        "| Crossover-Folge</li>"
        "</ul>"
        "<h2>Software</h2>"
        "<ul>Notiz an mich: sortieren"
        '<li><a href="https://example.test/uv">uv</a> | schneller Paketmanager</li>'
        "</ul>"
    )
    assert blocks[0][1].startswith("<p>Diese Woche")
    assert blocks[4][1] == "<p>Bis nächste Woche.</p>"
    report = json.loads(report_path.read_text())
    assert report[0]["converted_sections"] == 2
    assert [warning["heading"] for warning in report[0]["warnings"]] == ["Podcasts", "Software"]


@pytest.mark.django_db
def test_convert_weeknote_links_command_writes_nothing_when_every_section_is_refused():
    from cast.models import Post

    html = '<h2>Articles</h2><ul>KEEP THIS<li><a href="https://example.test">A</a></li></ul>'
    post = _weeknote_post(slug="weeknotes-2026-10-12", overview_html=html)
    stdout = io.StringIO()

    call_command("convert_weeknote_links", "--write", stdout=stdout)

    stored = Post.objects.get(pk=post.pk)
    assert stored.revisions.count() == 0
    assert _overview_blocks(stored) == [("paragraph", html)]
    assert "converted 0 post(s), published 0, skipped 0, warnings 1." in stdout.getvalue()


LEGACY_ARTICLES = '<h2>Articles</h2><ul><li><a href="https://example.test/a">A</a></li></ul>'


def _editor_saves_during_conversion(monkeypatch, edit):
    """Run ``edit`` after the command computed a conversion and before it saves it."""
    from homepage.core.management.commands import convert_weeknote_links

    def convert_then_edit(raw_data):
        conversion = convert_body(raw_data)
        edit()
        return conversion

    monkeypatch.setattr(convert_weeknote_links, "convert_body", convert_then_edit)


def _editor_body(text):
    return json.dumps([{"type": "overview", "value": [{"type": "paragraph", "value": text}]}])


@pytest.mark.django_db
@pytest.mark.parametrize("flags", [("--write",), ("--write", "--publish")])
def test_convert_weeknote_links_command_keeps_editor_revision_saved_during_conversion(monkeypatch, tmp_path, flags):
    from cast.models import Post

    post = _weeknote_post(slug="weeknotes-2026-10-19", overview_html=LEGACY_ARTICLES)
    post.save_revision().publish()
    live_revision_id = Post.objects.get(pk=post.pk).live_revision_id
    editor_revisions = []

    def editor_saves_draft():
        editor_copy = Post.objects.get(pk=post.pk)
        editor_copy.title = "Edited title"
        editor_copy.body = _editor_body("<p>Editor rewrite.</p>")
        editor_revisions.append(editor_copy.save_revision())

    _editor_saves_during_conversion(monkeypatch, editor_saves_draft)
    report_path = tmp_path / "report.json"
    stdout, stderr = io.StringIO(), io.StringIO()

    call_command("convert_weeknote_links", *flags, "--report", str(report_path), stdout=stdout, stderr=stderr)

    stored = Post.objects.get(pk=post.pk)
    (editor_revision,) = editor_revisions
    assert stored.latest_revision_id == editor_revision.pk
    assert stored.revisions.count() == 2
    assert stored.get_latest_revision_as_object().title == "Edited title"
    assert _overview_blocks(stored.get_latest_revision_as_object()) == [("paragraph", "<p>Editor rewrite.</p>")]
    # Nothing was published: the live page still shows the unconverted source.
    assert stored.live_revision_id == live_revision_id
    assert _overview_blocks(stored) == [("paragraph", LEGACY_ARTICLES)]
    (entry,) = json.loads(report_path.read_text())
    assert (entry["revision_id"], entry["published"], entry["skipped"]) == (None, False, "changed_since_read")
    assert "converted 0 post(s), published 0, skipped 1" in stdout.getvalue()
    assert "1 post(s) changed or were being saved while they were being converted" in stderr.getvalue()


@pytest.mark.django_db
def test_convert_weeknote_links_command_refuses_page_republished_during_conversion(monkeypatch, tmp_path):
    from cast.models import Post

    post = _weeknote_post(slug="weeknotes-2026-10-26", overview_html=LEGACY_ARTICLES)
    post.save_revision().publish()

    def editor_publishes():
        editor_copy = Post.objects.get(pk=post.pk)
        editor_copy.body = _editor_body("<p>Published rewrite.</p>")
        editor_copy.save_revision().publish()

    _editor_saves_during_conversion(monkeypatch, editor_publishes)
    report_path = tmp_path / "report.json"

    call_command(
        "convert_weeknote_links",
        "--write",
        "--publish",
        "--report",
        str(report_path),
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )

    stored = Post.objects.get(pk=post.pk)
    assert stored.revisions.count() == 2
    assert _overview_blocks(stored) == [("paragraph", "<p>Published rewrite.</p>")]
    assert json.loads(report_path.read_text())[0]["skipped"] == "changed_since_read"


@pytest.mark.django_db
def test_convert_weeknote_links_command_reports_page_deleted_during_conversion(monkeypatch, tmp_path):
    from cast.models import Post

    post = _weeknote_post(slug="weeknotes-2026-11-02", overview_html=LEGACY_ARTICLES)
    _editor_saves_during_conversion(monkeypatch, lambda: Post.objects.get(pk=post.pk).delete())
    report_path = tmp_path / "report.json"

    call_command(
        "convert_weeknote_links", "--write", "--report", str(report_path), stdout=io.StringIO(), stderr=io.StringIO()
    )

    assert not Post.objects.filter(pk=post.pk).exists()
    assert json.loads(report_path.read_text())[0]["skipped"] == "changed_since_read"


@pytest.mark.django_db
def test_convert_weeknote_links_command_converts_and_publishes_unchanged_page():
    from cast.models import Post

    post = _weeknote_post(slug="weeknotes-2026-11-09", overview_html=LEGACY_ARTICLES)
    post.save_revision().publish()
    stdout, stderr = io.StringIO(), io.StringIO()

    call_command(
        "convert_weeknote_links", "--write", "--publish", "--suppress-webmentions", stdout=stdout, stderr=stderr
    )

    stored = Post.objects.get(pk=post.pk)
    assert stored.live_revision_id == stored.latest_revision_id
    assert [block_type for block_type, _value in _overview_blocks(stored)] == ["weeknote_links"]
    assert "converted 1 post(s), published 1, skipped 0" in stdout.getvalue()
    assert stderr.getvalue() == ""


@pytest.mark.django_db
@pytest.mark.parametrize("comment", ["<!-- hidden note -->", "<!-- -->"], ids=["comment", "blank-comment"])
def test_convert_weeknote_links_command_preserves_top_level_prose_on_publish(comment):
    from cast.models import Post

    prose = f"Literal &lt;em&gt;text&lt;/em&gt; &amp; copy. {comment}"
    post = _weeknote_post(slug="weeknotes-top-level-prose", overview_html=prose + LEGACY_ARTICLES)
    post.save_revision().publish()

    call_command("convert_weeknote_links", "--write", "--publish", "--suppress-webmentions", stdout=io.StringIO())

    stored = Post.objects.get(pk=post.pk)
    assert stored.live_revision_id == stored.latest_revision_id
    paragraph, links = stored.body[0].value
    assert (paragraph.block_type, links.block_type) == ("paragraph", "weeknote_links")
    rendered = paragraph.render()
    assert comment in rendered
    soup = BeautifulSoup(rendered, "html.parser")
    assert soup.get_text(strip=True) == "Literal <em>text</em> & copy."
    assert soup.find("em") is None


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("flags", [("--write",), ("--write", "--publish", "--suppress-webmentions")])
def test_convert_weeknote_links_command_does_not_block_or_roll_back_an_editor_overwrite(tmp_path, flags):
    """Two real transactions: the command must not wait for the editor's revision lock.

    The editor overwrites the latest draft revision (an autosave): it writes the
    revision row first and the page row second. While it sits between the two,
    the command runs.
    """
    from cast.models import Post
    from django.db import connection, transaction

    post = _weeknote_post(slug="weeknotes-2026-11-16", overview_html=LEGACY_ARTICLES)
    post.save_revision().publish()
    latest_revision_id = Post.objects.get(pk=post.pk).latest_revision_id
    revision_locked, release, errors = threading.Event(), threading.Event(), []
    save_page = Post.save

    def pause_after_the_revision_is_written(self, *args, **kwargs):
        if threading.current_thread() is editor:
            revision_locked.set()
            release.wait(timeout=5)
        return save_page(self, *args, **kwargs)

    def editor_overwrites_latest_revision():
        try:
            with patch.object(Post, "save", pause_after_the_revision_is_written):
                with transaction.atomic():
                    stored = Post.objects.get(pk=post.pk)
                    stored.title = "Editor autosave"
                    stored.save_revision(overwrite_revision=stored.latest_revision, clean=False)
        except Exception as exc:  # noqa: BLE001 - reported to the test
            errors.append(exc)
        finally:
            revision_locked.set()
            connection.close()

    editor = threading.Thread(target=editor_overwrites_latest_revision)
    report_path = tmp_path / "report.json"
    editor.start()
    try:
        assert revision_locked.wait(timeout=10)
        assert errors == []

        call_command(
            "convert_weeknote_links", *flags, "--report", str(report_path), stdout=io.StringIO(), stderr=io.StringIO()
        )
    finally:
        release.set()
        editor.join(timeout=20)

    assert not editor.is_alive()
    # The editor's save went through: no deadlock victim, no lost edit.
    assert errors == []
    stored = Post.objects.get(pk=post.pk)
    assert stored.revisions.count() == 1
    assert stored.latest_revision_id == latest_revision_id
    assert stored.get_latest_revision_as_object().title == "Editor autosave"
    # The command wrote nothing and published nothing.
    assert _overview_blocks(stored) == [("paragraph", LEGACY_ARTICLES)]
    (entry,) = json.loads(report_path.read_text())
    assert (entry["revision_id"], entry["published"], entry["skipped"]) == (None, False, "changed_since_read")


@pytest.mark.django_db(transaction=True)
def test_editor_save_waits_for_the_weeknote_conversion_and_then_completes():
    """The other direction: the command holds the locks, an editor save arrives meanwhile."""
    from cast.models import Post
    from django.db import connection

    post = _weeknote_post(slug="weeknotes-2026-11-23", overview_html=LEGACY_ARTICLES)
    errors, started = [], threading.Event()

    def editor_saves_draft():
        try:
            started.set()
            draft = Post.objects.get(pk=post.pk)
            draft.title = "Saved after the conversion"
            draft.save_revision(clean=False)
        except Exception as exc:  # noqa: BLE001 - reported to the test
            errors.append(exc)
        finally:
            connection.close()

    editor = threading.Thread(target=editor_saves_draft)
    with Command()._locked_current_post(post) as current:
        assert current is not None
        editor.start()
        assert started.wait(timeout=10)
        editor.join(timeout=1)
        # The editor's page update is waiting for the lock held here.
        assert editor.is_alive()
    editor.join(timeout=20)

    assert not editor.is_alive()
    assert errors == []
    assert Post.objects.get(pk=post.pk).get_latest_revision_as_object().title == "Saved after the conversion"


@pytest.mark.django_db
@pytest.mark.parametrize("failure", ["write", "replace"])
def test_report_failure_preserves_old_report_and_committed_revision(monkeypatch, tmp_path, failure):
    import os

    post = _weeknote_post(slug="weeknotes-receipt", overview_html=REALISTIC_WEEKNOTE_OVERVIEW)
    path = tmp_path / "report.json"
    path.write_bytes(b"previous successful report\n")

    def fail(*args, **kwargs):
        raise OSError("report disk failure")

    if failure == "replace":
        monkeypatch.setattr(os, "replace", fail)
    else:
        # Initial preflight must succeed; fail the checkpoint after a real revision.
        def late_failure(self, stream, entry):
            assert entry["revision_id"] is not None
            fail()

        monkeypatch.setattr(Command, "_checkpoint_report", late_failure)
    stderr = io.StringIO()
    with pytest.raises(DjangoCommandError, match="report|receipt"):
        call_command("convert_weeknote_links", "--write", "--report", str(path), stdout=io.StringIO(), stderr=stderr)
    assert path.read_bytes() == b"previous successful report\n"
    post.refresh_from_db()
    revision_id = post.latest_revision_id
    assert revision_id is not None
    assert str(revision_id) in stderr.getvalue()
    assert post.slug in stderr.getvalue()
    assert "retained" in stderr.getvalue()
    before = post.revisions.count()
    monkeypatch.undo()
    call_command("convert_weeknote_links", "--write", "--report", str(path), stdout=io.StringIO())
    assert post.revisions.count() == before


@pytest.mark.django_db
def test_report_preflight_fails_before_creating_revisions(tmp_path):
    post = _weeknote_post(slug="weeknotes-preflight", overview_html=REALISTIC_WEEKNOTE_OVERVIEW)
    before = post.revisions.count()
    with pytest.raises(DjangoCommandError, match="report|receipt"):
        call_command("convert_weeknote_links", "--write", "--report", str(tmp_path / "missing" / "report.json"))
    assert post.revisions.count() == before


@pytest.mark.django_db
def test_conversion_failure_retains_completed_checkpoint(monkeypatch, tmp_path):
    first = _weeknote_post(slug="weeknotes-receipt-first", overview_html=LEGACY_ARTICLES)
    second = _weeknote_post(slug="weeknotes-receipt-second", overview_html=LEGACY_ARTICLES)
    path = tmp_path / "report.json"
    path.write_text("previous report")
    save = Command._save_conversion

    def fail_second(self, post, *args, **kwargs):
        if post.pk == second.pk:
            raise RuntimeError("second conversion failed")
        return save(self, post, *args, **kwargs)

    monkeypatch.setattr(Command, "_save_conversion", fail_second)
    stderr = io.StringIO()
    with pytest.raises(DjangoCommandError, match="second conversion failed"):
        call_command("convert_weeknote_links", "--write", "--report", str(path), stderr=stderr)
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.latest_revision_id is not None
    assert second.latest_revision_id is None
    assert path.read_text() == "previous report"
    (receipt,) = tmp_path.glob(".report.json.*.journal")
    recovered, run, _ = Command._read_receipt(receipt, 100, 4 * 1024 * 1024)
    assert recovered[0]["revision_id"] == first.latest_revision_id
    assert run == {"after_pk": first.pk, "through_pk": second.pk, "status": "partial"}
    assert str(first.latest_revision_id) in stderr.getvalue()


@pytest.mark.django_db
def test_published_report_keeps_umask_mode_or_replaced_report_mode(tmp_path):
    import os
    import stat

    _weeknote_post(slug="weeknotes-report-mode", overview_html=LEGACY_ARTICLES)
    fresh = tmp_path / "fresh.json"
    previous = os.umask(0o022)
    try:
        call_command("convert_weeknote_links", "--report", str(fresh), stdout=io.StringIO())
    finally:
        os.umask(previous)
    assert stat.S_IMODE(fresh.stat().st_mode) == 0o644

    existing = tmp_path / "existing.json"
    existing.write_text("previous report")
    existing.chmod(0o640)
    call_command("convert_weeknote_links", "--report", str(existing), stdout=io.StringIO())
    assert stat.S_IMODE(existing.stat().st_mode) == 0o640
    assert existing.read_text() != "previous report"


@pytest.mark.parametrize("budget", ["posts", "body", "report"])
def test_inventory_budget_stops_before_next_save_and_resumes_exactly(monkeypatch, tmp_path, budget):
    # Thousands of eligible rows, each with a large body and a warning.
    posts = [
        FakePost(body=_overview(_paragraph(REALISTIC_WEEKNOTE_OVERVIEW + "x" * 4096)), slug=f"weeknotes-synthetic-{i}")
        for i in range(1000)
    ]
    for i, post in enumerate(posts, 1):
        post.pk = i
    _patch_post_model(monkeypatch, posts)
    FakeQuerySet.hydrated = []
    report = tmp_path / "report.json"
    options = (
        {"max_posts": 2}
        if budget == "posts"
        else (
            {"max_body_bytes": 2 * len(json.dumps(posts[0].body.raw_data).encode("utf-8"))}
            if budget == "body"
            else {"max_report_bytes": 1400}
        )
    )
    stderr = io.StringIO()
    with pytest.raises(DjangoCommandError, match="Partial run"):
        call_command(
            "convert_weeknote_links",
            write=True,
            publish=True,
            report=str(report),
            stdout=io.StringIO(),
            stderr=stderr,
            **options,
        )
    entries = json.loads(report.read_text())
    assert 1 <= len(entries) <= 2
    last = entries[-1]["page_id"]
    assert FakeQuerySet.hydrated == list(range(1, last + 1)) + ([last + 1] if budget == "report" else [])
    assert all(entry["revision_id"] == 42 and entry["published"] for entry in entries)
    assert f"--after-pk {last} --through-pk 1000" in stderr.getvalue()
    old_revisions = [post.saved_revision for post in posts[:last]]
    # A new row is outside this invocation's frozen upper boundary.
    new_post = FakePost(body=_overview(_paragraph(LEGACY_ARTICLES)), slug="weeknotes-new")
    new_post.pk = 1001
    posts.append(new_post)
    with pytest.raises(DjangoCommandError, match="Partial run"):
        call_command(
            "convert_weeknote_links",
            write=True,
            publish=True,
            after_pk=last,
            through_pk=1000,
            max_posts=2,
            report=str(report),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )
    assert [entry["page_id"] for entry in json.loads(report.read_text())] == [last + 1, last + 2]
    assert [post.saved_revision for post in posts[:last]] == old_revisions
    assert new_post.saved_revision is None


def test_oversize_body_is_not_hydrated_or_saved(monkeypatch, tmp_path):
    post = FakePost(body=_overview(_paragraph("x" * 10000)))
    _patch_post_model(monkeypatch, [post])
    FakeQuerySet.hydrated = []
    with pytest.raises(DjangoCommandError, match="Partial run"):
        call_command(
            "convert_weeknote_links",
            max_body_bytes=100,
            write=True,
            report=str(tmp_path / "report.json"),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )
    assert FakeQuerySet.hydrated == []
    assert post.saved_revision is None


@pytest.mark.django_db
def test_database_body_admission_and_pk_continuation(tmp_path):
    first = _weeknote_post(slug="weeknotes-budget-first", overview_html=LEGACY_ARTICLES)
    second = _weeknote_post(slug="weeknotes-budget-second", overview_html=LEGACY_ARTICLES + "x" * 10000)
    report = tmp_path / "report.json"
    with pytest.raises(DjangoCommandError, match="Partial run"):
        call_command(
            "convert_weeknote_links",
            write=True,
            max_body_bytes=5000,
            report=str(report),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )
    assert [entry["page_id"] for entry in json.loads(report.read_text())] == [first.pk]
    second.refresh_from_db()
    assert second.latest_revision_id is None
    call_command(
        "convert_weeknote_links",
        write=True,
        after_pk=first.pk,
        through_pk=second.pk,
        report=str(report),
        stdout=io.StringIO(),
    )
    assert [entry["page_id"] for entry in json.loads(report.read_text())] == [second.pk]


@pytest.mark.parametrize("count", [100, 200, 400])
def test_receipt_serialization_work_is_linear(monkeypatch, tmp_path, count):
    posts = [FakePost(body=[], slug=f"weeknotes-{i}") for i in range(count)]
    for pk, post in enumerate(posts, 1):
        post.pk = pk
    _patch_post_model(monkeypatch, posts)
    dumps = json.dumps
    work = 0

    def measured(value, *args, **kwargs):
        nonlocal work
        # Count serialized page entries, including entries inside a full prefix.
        work += len(value) if isinstance(value, list) else 1
        return dumps(value, *args, **kwargs)

    monkeypatch.setattr("homepage.core.management.commands.convert_weeknote_links.json.dumps", measured)
    report = tmp_path / "report.json"
    call_command("convert_weeknote_links", max_posts=count, report=str(report), stdout=io.StringIO())
    assert len(json.loads(report.read_text())) == count
    assert work <= 5 * count + 10


@pytest.mark.parametrize("failure", [None, "preflight", "publication"])
def test_receipt_directory_sync_brackets_save_and_journal_unlink(monkeypatch, tmp_path, failure):
    import os
    import stat

    post = FakePost(body=_overview(_paragraph(LEGACY_ARTICLES)))
    _patch_post_model(monkeypatch, [post])
    target = tmp_path / "report.json"
    target.write_text("previous report")
    fsync, unlink = os.fsync, os.unlink
    save = Command._save_conversion
    events = []

    def sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            (journal,) = tmp_path.glob("*.journal")
            assert journal.read_bytes().endswith(b"\n")
            phase = "publication" if target.read_text() != "previous report" else "preflight"
            events.append(phase)
            if failure == phase:
                raise OSError(f"{phase} directory sync failed")
        return fsync(fd)

    def record_save(self, *args, **kwargs):
        events.append("save")
        return save(self, *args, **kwargs)

    def record_unlink(path, *args, **kwargs):
        if str(path).endswith(".journal"):
            events.append("unlink")
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(os, "unlink", record_unlink)
    monkeypatch.setattr(Command, "_save_conversion", record_save)
    stderr = io.StringIO()
    options = dict(write=True, report=str(target), stdout=io.StringIO(), stderr=stderr)
    if failure:
        with pytest.raises(DjangoCommandError, match=f"{failure} directory sync failed"):
            call_command("convert_weeknote_links", **options)
        (journal,) = tmp_path.glob("*.journal")
        assert journal.name in stderr.getvalue()
    else:
        call_command("convert_weeknote_links", **options)

    if failure == "preflight":
        assert events == ["preflight"]
        assert post.saved_revision is None
        assert target.read_text() == "previous report"
    elif failure == "publication":
        assert events == ["preflight", "save", "publication"]
        receipts, run, _ = Command._read_receipt(journal, 100, 4096)
        assert run["status"] == "complete"
        assert receipts == json.loads(target.read_text())
        assert receipts[0]["revision_id"] == post.saved_revision.id
        assert "durability uncertain" in stderr.getvalue()
    else:
        assert events == ["preflight", "save", "publication", "unlink"]
        assert list(tmp_path.glob("*.journal")) == []


@pytest.mark.parametrize("failure", ["short_write", "flush", "fsync", "close", "replace"])
def test_journal_failure_preserves_previous_report_and_committed_ids(monkeypatch, tmp_path, failure):
    import os

    post = FakePost(body=_overview(_paragraph(LEGACY_ARTICLES)))
    _patch_post_model(monkeypatch, [post])
    target = tmp_path / "report.json"
    target.write_text("previous report")
    append = Command._append_frame

    def fail(*args, **kwargs):
        raise OSError(f"injected {failure}")

    def fault_at_commit(stream, frame):
        if "entry" in frame:
            if failure == "short_write":
                write = stream.write

                def short_write(payload):
                    return write(payload[: len(payload) // 2])

                monkeypatch.setattr(stream, "write", short_write)
            elif failure == "flush":
                monkeypatch.setattr(stream, "flush", fail)
            elif failure == "fsync":
                monkeypatch.setattr(os, "fsync", fail)
            elif failure == "close":
                close = stream._closer.cleanup

                def fail_close():
                    monkeypatch.setattr(stream._closer, "cleanup", close)
                    fail()

                monkeypatch.setattr(stream._closer, "cleanup", fail_close)
            elif failure == "replace":
                monkeypatch.setattr(os, "replace", fail)
        append(stream, frame)

    monkeypatch.setattr(Command, "_append_frame", staticmethod(fault_at_commit))
    stderr = io.StringIO()
    with pytest.raises(DjangoCommandError, match="remain committed"):
        call_command(
            "convert_weeknote_links", write=True, publish=True, report=str(target), stdout=io.StringIO(), stderr=stderr
        )
    assert target.read_text() == "previous report"
    assert post.saved_revision.published
    assert f"{post.slug} revision_id=42 published=True" in stderr.getvalue()
    (journal,) = tmp_path.glob("*.journal")
    assert journal.stat().st_mode & 0o777 == 0o600
    if failure == "short_write":
        entries, run, _ = Command._read_receipt(journal, 100, 4 * 1024 * 1024)
        assert entries == []
        assert run == {"after_pk": 0, "through_pk": post.pk, "status": "partial"}


def test_recover_completed_prefix_without_replaying_conversions(monkeypatch, tmp_path):
    posts = [FakePost(body=_overview(_paragraph(LEGACY_ARTICLES)), slug=f"weeknotes-{i}") for i in (1, 2)]
    for i, post in enumerate(posts, 1):
        post.pk = i
    _patch_post_model(monkeypatch, posts)
    save = Command._save_conversion

    def fail_second(self, post, *args, **kwargs):
        if post.pk == 2:
            raise RuntimeError("conversion failed")
        return save(self, post, *args, **kwargs)

    monkeypatch.setattr(Command, "_save_conversion", fail_second)
    target = tmp_path / "report.json"
    with pytest.raises(DjangoCommandError, match="conversion failed"):
        call_command("convert_weeknote_links", write=True, publish=True, report=str(target), stdout=io.StringIO())
    (journal,) = tmp_path.glob("*.journal")
    original = journal.read_bytes()
    stdout = io.StringIO()
    # Recovery must not query, hydrate or save any page.
    import cast.models

    monkeypatch.setattr(cast.models, "Post", None)
    call_command("convert_weeknote_links", recover_receipt=str(journal), report=str(target), stdout=stdout)
    entries = json.loads(target.read_text())
    assert [(entry["page_id"], entry["revision_id"], entry["published"]) for entry in entries] == [(1, 42, True)]
    assert "status=partial" in stdout.getvalue()
    assert "--after-pk 1 --through-pk 2" in stdout.getvalue()
    assert journal.read_bytes() == original
    assert posts[1].saved_revision is None


@pytest.mark.parametrize("malformed_interior", [False, True])
def test_recovery_salvages_complete_entries_before_torn_tail(tmp_path, malformed_interior):
    header = {"format": "homepage-weeknote-receipt-v1", "after_pk": 1, "through_pk": 9, "scope": {}}
    entries = [
        {
            "page_id": pk,
            "through_pk": 9,
            "slug": f"weeknotes-{pk}",
            "revision_id": 40 + pk,
            "published": True,
            "changed": True,
            "warnings": [],
            "skipped": "",
            "converted_sections": 1,
        }
        for pk in (3, 7)
    ]
    frames = [header, *({"entry": entry} for entry in entries)]
    lines = [json.dumps(frame).encode() + b"\n" for frame in frames]
    if malformed_interior:
        lines.insert(2, b'{"entry":\n')
    original = b"".join(lines) + b'{"entry": {"page_id": 8, "slug": "\xc3'
    journal = tmp_path / "receipt.journal"
    journal.write_bytes(original)
    target = tmp_path / "report.json"
    target.write_text("old report")
    stdout, stderr = io.StringIO(), io.StringIO()

    def recover():
        call_command(
            "convert_weeknote_links", recover_receipt=str(journal), report=str(target), stdout=stdout, stderr=stderr
        )

    if malformed_interior:
        with pytest.raises(DjangoCommandError, match="Cannot recover receipt"):
            recover()
        assert target.read_text() == "old report"
    else:
        recover()
        assert json.loads(target.read_text()) == entries
        assert "status=partial" in stdout.getvalue()
        assert "--after-pk 7 --through-pk 9" in stdout.getvalue()
        assert "commit after its last complete frame" in stderr.getvalue()
    assert journal.read_bytes() == original


def test_recovery_rejects_fifo_without_replacing_report(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    journal = tmp_path / "receipt.journal"
    os.mkfifo(journal)
    target = tmp_path / "report.json"
    target.write_text("previous report")

    repo_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "manage.py"),
            "convert_weeknote_links",
            "--recover-receipt",
            str(journal),
            "--report",
            str(target),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "regular file" in result.stderr
    assert target.read_text() == "previous report"


@pytest.mark.parametrize("rewrite", [False, True], ids=["complete", "rewritten"])
def test_recovery_requires_stable_receipt_generation(monkeypatch, tmp_path, rewrite):
    import os

    journal = tmp_path / "receipt.journal"
    header = {"format": "homepage-weeknote-receipt-v1", "after_pk": 0, "through_pk": 0, "scope": {"slug": "old"}}
    outcome = {"outcome": {"after_pk": 0, "through_pk": 0, "status": "complete"}}
    original = json.dumps(header) + "\n" + json.dumps(outcome) + "\n"
    journal.write_text(original)
    target = tmp_path / "report.json"
    target.write_text("previous report")
    loads = json.loads

    def rewrite_after_header(line):
        frame = loads(line)
        if "format" in frame:
            # Same size and inode: only the forced mtime identifies the rewrite,
            # independent of the filesystem's timestamp granularity.
            before = journal.stat()
            journal.write_text(original.replace('"old"', '"new"'))
            os.utime(journal, ns=(before.st_atime_ns, before.st_mtime_ns + 5_000_000_000))
        return frame

    stdout = io.StringIO()
    options = dict(recover_receipt=str(journal), report=str(target), stdout=stdout)
    if rewrite:
        monkeypatch.setattr(json, "loads", rewrite_after_header)
        with pytest.raises(DjangoCommandError, match="changed while reading"):
            call_command("convert_weeknote_links", **options)
        assert target.read_text() == "previous report"
    else:
        call_command("convert_weeknote_links", **options)
        assert loads(target.read_text()) == []
        assert "status=complete" in stdout.getvalue()
        assert journal.read_text() == original


@pytest.mark.parametrize(
    "damage", ["format", "order", "outcome", "budget", "rows", "trailing", "trailing_torn", "torn_header", "empty"]
)
def test_receipt_recovery_refuses_invalid_frames(tmp_path, damage):
    header = {"format": "homepage-weeknote-receipt-v1", "after_pk": 0, "through_pk": 2, "scope": {}}
    entry = {
        "page_id": 1,
        "through_pk": 2,
        "slug": "weeknotes-test",
        "revision_id": 42,
        "published": True,
        "changed": True,
        "warnings": [],
        "skipped": "",
        "converted_sections": 1,
    }
    frames = [header, {"entry": entry}, {"outcome": {"after_pk": 1, "through_pk": 2, "status": "partial"}}]
    max_bytes, max_posts = 4096, 100
    if damage == "format":
        header["format"] = "foreign"
    elif damage == "order":
        entry["page_id"] = 0
    elif damage == "outcome":
        frames[-1]["outcome"]["after_pk"] = 2
    elif damage == "budget":
        max_bytes = 10
    elif damage == "rows":
        max_posts = 0
    elif damage == "trailing":
        frames.append({"entry": entry})
    elif damage in {"torn_header", "empty"}:
        frames = []
    path = tmp_path / "receipt.journal"
    tail = '{"format":' if damage in {"torn_header", "trailing_torn"} else ""
    path.write_text("".join(json.dumps(frame) + "\n" for frame in frames) + tail)
    with pytest.raises(ValueError):
        Command._read_receipt(path, max_posts, max_bytes)


@pytest.mark.django_db
def test_real_inventory_does_not_retain_previous_hydrated_posts(monkeypatch, tmp_path, django_assert_num_queries):
    import weakref

    from cast.models import Post

    posts = [_weeknote_post(slug=f"weeknotes-budget-{i}", overview_html=LEGACY_ARTICLES) for i in range(3)]
    loaded = []
    from_db = Post.from_db

    def observed_from_db(cls, *args, **kwargs):
        post = from_db(*args, **kwargs)
        loaded.append(weakref.ref(post))
        assert sum(ref() is not None for ref in loaded) == 1
        return post

    monkeypatch.setattr(Post, "from_db", classmethod(observed_from_db))
    # Max-ID lookup, three ID lookups and two admitted hydrations.
    with django_assert_num_queries(6), pytest.raises(DjangoCommandError, match="Partial run"):
        call_command(
            "convert_weeknote_links",
            max_posts=2,
            report=str(tmp_path / "bounded.json"),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )
    assert len(loaded) == 2
    assert [entry["page_id"] for entry in json.loads((tmp_path / "bounded.json").read_text())] == [
        post.pk for post in posts[:2]
    ]


def test_journal_preflight_failure_precedes_any_save(monkeypatch, tmp_path):
    post = FakePost(body=_overview(_paragraph(LEGACY_ARTICLES)))
    _patch_post_model(monkeypatch, [post])

    def fail_header(*args):
        raise OSError("journal unavailable")

    monkeypatch.setattr(Command, "_append_frame", staticmethod(fail_header))
    with pytest.raises(DjangoCommandError, match="journal unavailable"):
        call_command("convert_weeknote_links", write=True, report=str(tmp_path / "report.json"), stdout=io.StringIO())
    assert post.saved_revision is None


def test_complete_journal_recovery_keeps_json_shape_and_mode(monkeypatch, tmp_path):
    import os

    post = FakePost(body=_overview(_paragraph(LEGACY_ARTICLES)))
    _patch_post_model(monkeypatch, [post])
    target = tmp_path / "report.json"
    target.write_text("previous report")
    target.chmod(0o640)
    replace = os.replace
    monkeypatch.setattr(os, "replace", Mock(side_effect=OSError("replace failed")))
    with pytest.raises(DjangoCommandError, match="replace failed"):
        call_command("convert_weeknote_links", write=True, report=str(target), stdout=io.StringIO())
    (journal,) = tmp_path.glob("*.journal")
    (pending,) = tmp_path.glob("*.pending")
    expected = pending.read_bytes()
    monkeypatch.setattr(os, "replace", replace)
    stdout = io.StringIO()
    call_command("convert_weeknote_links", recover_receipt=str(journal), report=str(target), stdout=stdout)
    assert target.read_bytes() == expected
    assert target.stat().st_mode & 0o777 == 0o640
    assert "status=complete" in stdout.getvalue()


def test_warning_heavy_receipts_include_outer_json_indentation_in_budget(monkeypatch, tmp_path):
    ambiguous = '<h2>Podcasts / Videos</h2><ul><li><a href="https://example.test/a">A</a></li></ul>'
    post = FakePost(body=_overview(_paragraph(LEGACY_ARTICLES + ambiguous * 100)))
    _patch_post_model(monkeypatch, [post])
    entry = Command()._report_entry(post, convert_body(post.body.raw_data))
    entry.update(page_id=post.pk, through_pk=post.pk)
    # Flat-entry accounting fits, but nesting the many warnings in a JSON array does not.
    budget = len(json.dumps(entry, indent=2, ensure_ascii=False).encode("utf-8")) + 300
    assert len(json.dumps([entry], indent=2, ensure_ascii=False).encode("utf-8")) > budget
    target = tmp_path / "report.json"
    with pytest.raises(DjangoCommandError, match="report budget"):
        call_command(
            "convert_weeknote_links",
            write=True,
            max_report_bytes=budget,
            report=str(target),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )
    assert post.saved_revision is None
    assert json.loads(target.read_text()) == []


def test_budget_bound_journal_recovers_with_the_same_report_budget(monkeypatch, tmp_path):
    import os

    post = FakePost(body=_overview(_paragraph(LEGACY_ARTICLES)))
    _patch_post_model(monkeypatch, [post])
    entry = Command()._report_entry(post, convert_body(post.body.raw_data))
    entry.update(page_id=post.pk, through_pk=post.pk)
    reserved = {**entry, "revision_id": 9223372036854775807, "published": False, "skipped": "has_unpublished_changes"}
    # The smallest budget that admits this one receipt (list framing included).
    budget = str(len(json.dumps([reserved], indent=2, ensure_ascii=False).encode("utf-8")) + 1)
    target = tmp_path / "report.json"
    replace = os.replace
    monkeypatch.setattr(os, "replace", Mock(side_effect=OSError("replace failed")))
    with pytest.raises(DjangoCommandError, match="replace failed"):
        call_command(
            "convert_weeknote_links",
            "--write",
            "--slug",
            post.slug,
            "--max-report-bytes",
            budget,
            "--report",
            str(target),
            stdout=io.StringIO(),
        )
    assert post.saved_revision is not None
    (journal,) = tmp_path.glob("*.journal")
    # Header/outcome frames and the long --slug scope do not count against the receipt budget.
    assert journal.stat().st_size > int(budget)
    monkeypatch.setattr(os, "replace", replace)
    stdout = io.StringIO()
    call_command(
        "convert_weeknote_links",
        "--recover-receipt",
        str(journal),
        "--max-report-bytes",
        budget,
        "--report",
        str(target),
        stdout=stdout,
    )
    assert [item["revision_id"] for item in json.loads(target.read_text())] == [42]
    assert "status=complete" in stdout.getvalue()


def test_after_pk_beyond_last_eligible_page_keeps_a_valid_boundary(monkeypatch, tmp_path):
    posts = [FakePost(body=_overview(_paragraph(LEGACY_ARTICLES)), slug=f"weeknotes-{i}") for i in (1, 2)]
    for pk, post in enumerate(posts, 1):
        post.pk = pk
    _patch_post_model(monkeypatch, posts)
    target = tmp_path / "report.json"
    stdout = io.StringIO()
    call_command("convert_weeknote_links", write=True, after_pk=5, report=str(target), stdout=stdout)
    assert "Complete through page ID 5." in stdout.getvalue()
    assert json.loads(target.read_text()) == []
    assert all(post.saved_revision is None for post in posts)


@pytest.mark.parametrize("interrupt_at", ["second_save", "replace"])
def test_interrupted_conversion_reports_recoverable_receipt(monkeypatch, tmp_path, interrupt_at):
    from homepage.core.management.commands import convert_weeknote_links as command_module

    posts = [FakePost(body=_overview(_paragraph(LEGACY_ARTICLES)), slug=f"weeknotes-{i}") for i in (1, 2)]
    for i, post in enumerate(posts, 1):
        post.pk = i
    _patch_post_model(monkeypatch, posts)
    interruption = KeyboardInterrupt()
    original_save = Command._save_conversion
    original_replace = command_module.os.replace

    def save(self, post, *args, **kwargs):
        if post.pk == 2:
            raise interruption
        return original_save(self, post, *args, **kwargs)

    def replace(*args):
        raise interruption

    if interrupt_at == "second_save":
        monkeypatch.setattr(Command, "_save_conversion", save)
    else:
        monkeypatch.setattr(command_module.os, "replace", replace)
    target = tmp_path / "report.json"
    target.write_text("old report")
    stdout, stderr = io.StringIO(), io.StringIO()
    with pytest.raises(KeyboardInterrupt) as error:
        call_command("convert_weeknote_links", write=True, report=str(target), stdout=stdout, stderr=stderr)
    assert error.value is interruption
    assert "Complete through" not in stdout.getvalue()
    assert target.read_text() == "old report"
    (journal,) = tmp_path.glob("*.journal")
    assert journal.stat().st_mode & 0o777 == 0o600
    assert str(journal) in stderr.getvalue()
    assert "weeknotes-1 revision_id=42" in stderr.getvalue()
    if interrupt_at == "replace":
        (pending,) = tmp_path.glob("*.pending")
        assert str(pending) in stderr.getvalue()
        assert "weeknotes-2 revision_id=42" in stderr.getvalue()

    monkeypatch.setattr(command_module.os, "replace", original_replace)
    call_command("convert_weeknote_links", recover_receipt=str(journal), report=str(target), stdout=io.StringIO())
    entries = json.loads(target.read_text())
    assert [entry["page_id"] for entry in entries] == ([1] if interrupt_at == "second_save" else [1, 2])


@pytest.mark.django_db(databases=["default", "legacy"])
def test_weeknote_conversion_inventory_and_revision_use_writer(tmp_path, settings):
    from cast.models import Post
    from django.contrib.sessions.models import Session
    from django.db import connections
    from django.test.utils import CaptureQueriesContext, override_settings
    from wagtail.models import Page, Revision

    class ReadRoute:
        def __init__(self, alias, model=None):
            self.alias = alias
            self.model = model

        def db_for_read(self, model, **hints):
            if self.model is None or model is self.model:
                return self.alias

        def db_for_write(self, model, **hints):
            if self.model is None:
                return self.alias

    slug = "weeknotes-routed"
    writer = _weeknote_post(slug=slug, overview_html=LEGACY_ARTICLES, pk=10000)
    writer.save_revision(changed=False)
    with override_settings(DATABASE_ROUTERS=[ReadRoute("legacy")]):
        replica = _weeknote_post(slug=slug, overview_html="<p>Replica-only content</p>", pk=10000)
        replica.save_revision(changed=False)

    assert writer.pk == replica.pk
    settings.DATABASE_ROUTERS = [ReadRoute("legacy", Post)]
    stdout = io.StringIO()
    with CaptureQueriesContext(connections["legacy"]) as replica_queries:
        call_command("convert_weeknote_links", slug=slug, stdout=stdout)
    assert "would convert 1 post(s)" in stdout.getvalue()
    assert not replica_queries.captured_queries

    # Wagtail publication itself re-reads Posts and revisions through its router.
    # Its implicit routes must agree with the writer even when it has a replica.
    settings.DATABASE_ROUTERS = [ReadRoute("legacy", Post)]
    target = tmp_path / "report.json"
    with pytest.raises(DjangoCommandError, match="cast.Post.*legacy"):
        call_command("convert_weeknote_links", slug=slug, write=True, publish=True, report=str(target))
    assert not list(tmp_path.iterdir())

    class InstanceRoute:
        def db_for_write(self, model, instance=None, **hints):
            if model is Post and getattr(instance, "pk", None) == writer.pk:
                return "legacy"

    settings.DATABASE_ROUTERS = [InstanceRoute()]
    with pytest.raises(DjangoCommandError, match="routed to 'legacy', expected 'default'"):
        call_command("convert_weeknote_links", slug=slug, write=True, stdout=io.StringIO())
    assert Revision.objects.using("default").filter(object_id=str(writer.pk)).count() == 1

    settings.DATABASE_ROUTERS = [ReadRoute("legacy", Session)]
    with (
        CaptureQueriesContext(connections["default"]) as writer_queries,
        CaptureQueriesContext(connections["legacy"]) as replica_queries,
    ):
        call_command(
            "convert_weeknote_links",
            slug=slug,
            write=True,
            publish=True,
            suppress_webmentions=True,
            report=str(target),
            stdout=io.StringIO(),
        )
    assert not replica_queries.captured_queries
    if connections["default"].vendor == "postgresql":
        locks = [row["sql"] for row in writer_queries if "FOR NO KEY UPDATE" in row["sql"]]
        assert len(locks) == 2
        assert Revision._meta.db_table in locks[0] and Page._meta.db_table in locks[1]
    writer.refresh_from_db(using="default")
    replica.refresh_from_db(using="legacy")
    assert _overview_blocks(writer)[0][0] == "weeknote_links"
    assert _overview_blocks(replica) == [("paragraph", "<p>Replica-only content</p>")]
    assert writer.live_revision_id == json.loads(target.read_text())[0]["revision_id"]
    revisions = Revision.objects.filter(object_id=str(writer.pk))
    assert revisions.using("default").count() == 2
    assert revisions.using("legacy").count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("misrouted_model", ["post", "revision"])
def test_weeknote_conversion_rejects_unsupported_write_route_before_opening_receipt(
    tmp_path, settings, misrouted_model
):
    class SplitWriter:
        def db_for_write(self, model, **hints):
            if model._meta.model_name == misrouted_model:
                return "legacy"

    settings.DATABASE_ROUTERS = [SplitWriter()]
    with pytest.raises(DjangoCommandError, match="database.*legacy"):
        call_command("convert_weeknote_links", write=True, through_pk=0, report=str(tmp_path / "report.json"))
    assert not list(tmp_path.iterdir())
