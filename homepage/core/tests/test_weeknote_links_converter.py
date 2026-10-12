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
from homepage.core.weeknotes.converter import BodyConversion, convert_body, convert_paragraph_html


def _paragraph(value):
    return {"type": "paragraph", "value": value, "id": "paragraph-id"}


def _overview(*blocks):
    return [{"type": "overview", "value": list(blocks), "id": "overview-id"}]


def _weeknote_values(block):
    return [item["value"] for item in block["value"]]


def test_convert_paragraph_html_merges_consecutive_link_sections_and_preserves_surrounding_prose():
    conversion = convert_paragraph_html(
        "<p>Intro.</p><h2>Articles</h2><ul>"
        '<li><a href="https://example.com/a">Article A</a> | Useful</li>'
        "</ul><h2>Software</h2><ul>"
        '<li><a href="https://example.com/tool">Tool</a> (Example) | Handy</li>'
        "</ul><p>Outro.</p>"
    )

    assert conversion.changed is True
    assert conversion.converted_sections == 2
    assert [block["type"] for block in conversion.blocks] == ["paragraph", "weeknote_links", "paragraph"]
    assert conversion.blocks[0]["value"] == "<p>Intro.</p>"
    assert conversion.blocks[2]["value"] == "<p>Outro.</p>"
    values = _weeknote_values(conversion.blocks[1])
    assert [item["category"] for item in values] == ["articles", "software"]
    assert [item["kind"] for item in values] == ["article", "link"]
    assert values[0]["title"] == "Article A"
    assert values[0]["description"] == "<p>Useful</p>"
    assert values[1]["source"] == "Example"


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
        '<li><a href="https://example.test/a">A</a></li>\n\t&nbsp;'
        '<li><a href="https://example.test/b">B</a></li>\n</ul>'
    )

    assert conversion.changed is True
    assert conversion.warnings == []
    assert [item["title"] for item in _weeknote_values(conversion.blocks[0])] == ["A", "B"]


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
        ("Podcasts", "List item source has several links or rich markup that the source fields cannot keep.")
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
        ("Podcasts", "List item source has several links or rich markup that the source fields cannot keep."),
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
    def __init__(self, posts):
        self.posts = posts

    def filter(self, **kwargs):
        slug = kwargs.get("slug")
        if slug is None:
            return self
        return FakeQuerySet([post for post in self.posts if post.slug == slug])

    def order_by(self, *_fields):
        return self

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

    monkeypatch.setattr(cast.models, "Post", SimpleNamespace(objects=FakeQuerySet(posts)))
    _patch_locked_current_post(monkeypatch)


def _patch_locked_current_post(monkeypatch):
    """Fake posts have no database row to lock: the current post is the fake itself."""

    @contextmanager
    def locked_current_post(self, post):
        yield post

    monkeypatch.setattr(Command, "_locked_current_post", locked_current_post)


def _weeknote_post(*, slug, overview_html):
    from cast.models import Blog, Post
    from wagtail.models import Locale, Page

    root = Page.get_first_root_node()
    if root is None:
        Locale.objects.get_or_create(language_code="en")
        root = Page.add_root(instance=Page(title="Root", slug="root"))
    blog = root.add_child(instance=Blog(title="Weeknote blog", slug=f"blog-{slug}"))
    body = json.dumps([{"type": "overview", "value": [{"type": "paragraph", "value": overview_html}]}])
    return blog.add_child(instance=Post(title=slug, slug=slug, body=body))


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
