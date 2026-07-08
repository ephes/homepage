from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
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


class FakeRevision:
    id = 42

    def __init__(self):
        self.published = False

    def publish(self):
        self.published = True


class FakePost:
    def __init__(self, *, body, slug="weeknotes-2026-04-27", live=True, has_unpublished_changes=False):
        self.slug = slug
        self.body = SimpleNamespace(raw_data=body)
        self.live = live
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


def test_save_conversion_skips_pages_with_existing_unpublished_changes():
    post = FakePost(body=[], live=True, has_unpublished_changes=True)
    conversion = BodyConversion(body=[{"type": "overview", "value": []}], changed=True)

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
