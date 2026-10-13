"""
Publication and logging of the Micropub handler.

* a post goes live through Wagtail's revision API as ONE final revision that
  already carries its categories;
* neither submitted content nor secrets reach the logs.
"""

import json
import logging
import traceback
from unittest.mock import patch

import pytest
from cast.models import Post
from django.core.exceptions import ValidationError
from django.urls import reverse
from indieweb.models import Token
from wagtail.models import PageLogEntry, Revision
from wagtail.signals import page_published

from .handler import CastPostMicropubHandler, MicropubContentError, MicropubInternalError
from .test_micropub_permissions import HOST, blogs, create, micropub_post, users  # noqa: F401

pytestmark = pytest.mark.django_db


@pytest.fixture
def published_signals():
    """Collect ``page_published`` deliveries for Post pages."""
    received = []

    def receiver(sender, instance, revision, **kwargs):
        received.append((instance.pk, revision.pk))

    page_published.connect(receiver)
    try:
        yield received
    finally:
        page_published.disconnect(receiver)


def micropub_json(client, user, properties):
    token = Token.objects.create(owner=user, me=f"http://{HOST}/", client_id="https://client.example/", scope="create")
    return client.post(
        reverse("indieweb:micropub"),
        json.dumps({"type": ["h-entry"], "properties": properties}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token.key}",
    )


def body_html(post):
    return "".join(str(block.value) for section in post.body for block in section.value)


# One final revision, published through Wagtail


def test_tagged_post_is_published_as_one_final_revision(blogs, users, published_signals):  # noqa: F811
    create(users["publisher"], **{"mp-channel": ["alpha"], "category": ["python", "django"]})

    post = Post.objects.get(slug="hello")
    revisions = list(Revision.page_revisions.filter(object_id=str(post.pk)))
    assert len(revisions) == 1
    [revision] = revisions
    assert post.live and not post.has_unpublished_changes
    assert post.live_revision_id == post.latest_revision_id == revision.pk
    assert post.first_published_at is not None and post.last_published_at is not None
    assert sorted(post.tags.names()) == ["django", "python"]
    # The revision that is live IS the tagged post ...
    assert sorted(revision.as_object().tags.names()) == ["django", "python"]
    assert "Hello world" in body_html(revision.as_object())
    # ... and it went through the supported publication path exactly once.
    assert published_signals == [(post.pk, revision.pk)]
    actions = list(PageLogEntry.objects.filter(page=post).values_list("action", flat=True))
    assert sorted(actions) == ["wagtail.create", "wagtail.edit", "wagtail.publish"]
    assert set(PageLogEntry.objects.filter(page=post).values_list("user_id", flat=True)) == {users["publisher"].pk}


def test_republishing_the_live_revision_keeps_the_tags(blogs, users):  # noqa: F811
    create(users["publisher"], **{"mp-channel": ["alpha"], "category": ["python"]})
    post = Post.objects.get(slug="hello")

    # What "restore / publish this revision" does in the Wagtail admin.
    post.live_revision.publish(user=users["admin"])

    post = Post.objects.get(pk=post.pk)
    assert post.live
    assert list(post.tags.names()) == ["python"]


def test_untagged_post_is_still_published(blogs, users, published_signals):  # noqa: F811
    entry = create(users["publisher"], **{"mp-channel": ["alpha"]})

    post = Post.objects.get(slug="hello")
    assert post.live and post.live_revision_id == post.latest_revision_id
    assert entry.url == post.get_url()
    assert list(post.tags.names()) == []
    assert len(published_signals) == 1


@pytest.mark.parametrize("category", [{"name": "python"}, ["python"], 7, None])
def test_malformed_category_rejects_the_request(blogs, users, published_signals, category):  # noqa: F811
    with pytest.raises(MicropubContentError):
        create(users["publisher"], **{"mp-channel": ["alpha"], "category": ["fine", category]})

    assert not Post.objects.exists()
    assert published_signals == []


def test_failed_tag_application_publishes_nothing(blogs, users, published_signals):  # noqa: F811
    manager_class = type(Post().tags)
    with patch.object(manager_class, "add", side_effect=RuntimeError("tag store unavailable")):
        with pytest.raises(RuntimeError):
            create(users["publisher"], **{"mp-channel": ["alpha"], "category": ["python"]})

    assert not Post.objects.exists()
    assert published_signals == []


def test_rejected_publication_leaves_no_partial_post(blogs, users):  # noqa: F811
    with patch.object(Revision, "publish", side_effect=ValidationError("policy says no")):
        with pytest.raises(MicropubContentError):
            create(users["publisher"], **{"mp-channel": ["alpha"], "category": ["python"]})

    assert not Post.objects.exists()
    assert not PageLogEntry.objects.filter(action="wagtail.publish").exists()


def test_endpoint_still_answers_201_with_location_for_tagged_post(client, blogs, users):  # noqa: F811
    response = micropub_post(
        client,
        users["publisher"],
        {"h": "entry", "name": "Hello", "content": "hi", "category[]": ["python", "django"], "mp-channel": "alpha"},
    )

    assert response.status_code == 201
    post = Post.objects.get()
    assert response["Location"] == f"http://{HOST}{post.get_url()}"
    assert sorted(post.tags.names()) == ["django", "python"]


# Nothing submitted reaches the logs

SECRETS = {
    "content": "CONTENT-MARKER-4f1c",
    "name": "TITLE-MARKER-9a7e",
    "category": "CATEGORY-MARKER-22bd",
    "photo": "PHOTO-MARKER-77c0",
    "link": "LINK-MARKER-5e31",
    "property": "PROPERTY-NAME-MARKER-c3d9",
    "channel": "CHANNEL-MARKER-08fa",
    "published": "PUBLISHED-MARKER-b6a2",
}


def secret_properties(**overrides):
    properties = {
        "name": [f"A {SECRETS['name']} title"],
        "content": [
            f'<p>Private {SECRETS["content"]} text '
            f'<a href="https://example.test/doc?token={SECRETS["link"]}">link</a></p>'
        ],
        "category": [SECRETS["category"]],
        "photo": [f"https://example.test/a.jpg?sig={SECRETS['photo']}", "https://example.test/b.jpg"],
        "published": [f"not-a-date-{SECRETS['published']}"],
        SECRETS["property"]: ["x"],
        "mp-channel": ["alpha"],
    }
    properties.update(overrides)
    return properties


@pytest.fixture
def webmention_results():
    """Publication sends webmentions; answer for the sender without any network."""

    def send_webmentions(source_url, html_content):
        target = f"https://user:pw@example.test:8443/doc?token={SECRETS['link']}#frag"
        return [
            {"target": target, "success": True, "response": "ok"},
            {"target": target, "success": False, "error": f"Max retries exceeded with url: {target}"},
            {"target": target, "success": False, "response": f"400 for {target}"},
        ]

    with patch("indieweb.senders.WebmentionSender.send_webmentions", side_effect=send_webmentions) as sender:
        with patch("homepage.core.webmention_integration.WebmentionSender", None):
            yield sender


def application_log_text(caplog):
    """Everything this project and django-indieweb log, plus all warnings and errors.

    Wagtail's own INFO line for a created page ("Page created: <title> ...") is
    left out: it is the same for CMS-created pages and below the production log
    level (root logger: WARNING).
    """
    return "\n".join(
        f"{record.name} {record.getMessage()} "
        + ("".join(traceback.format_exception(*record.exc_info)) if record.exc_info else "")
        for record in caplog.records
        if record.levelno >= logging.WARNING or record.name.split(".")[0] in {"homepage", "indieweb"}
    )


def handler_messages(caplog):
    return [record.getMessage() for record in caplog.records if record.name == "homepage.micropub.handler"]


def assert_no_secret(text):
    for name, marker in SECRETS.items():
        assert marker not in text, f"{name} leaked"
        assert marker.lower() not in text.lower(), f"{name} leaked (slug/lowercase form)"


def test_successful_publication_logs_no_submitted_values(
    blogs, users, caplog, capsys, webmention_results, django_capture_on_commit_callbacks  # noqa: F811
):
    caplog.set_level(logging.DEBUG)

    # Webmentions leave after the publishing transaction has committed.
    with django_capture_on_commit_callbacks(execute=True):
        CastPostMicropubHandler().create_entry(secret_properties(), users["publisher"])
        assert webmention_results.call_count == 0

    post = Post.objects.get()
    assert SECRETS["content"] in body_html(post)  # the content itself is stored untouched
    assert webmention_results.call_count == 1
    output = capsys.readouterr()
    assert_no_secret(application_log_text(caplog))
    # Webmention diagnostics name the target without query, fragment or credentials.
    assert "✓ Sent webmention to https://example.test:8443/doc\n" in output.out
    assert "✗ Failed to send to https://example.test:8443/doc (error)\n" in output.out
    assert "✗ Failed to send to https://example.test:8443/doc (rejected)\n" in output.out
    assert_no_secret(output.out + output.err)
    assert f"Webmentions sent for page {post.pk}: 1 successful, 2 failed\n" in output.out
    assert "pw@" not in output.out
    # Useful operational facts remain.
    messages = handler_messages(caplog)
    assert (
        "Micropub create: properties=category,content,mp-channel,name,photo,published (+1 other) "
        "categories=1 photos=2"
    ) in messages
    assert f"Micropub create: published post id={post.pk} in blog id={blogs['alpha'].pk}" in messages
    assert "Micropub create: unparseable published date, using the current time" in messages


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"mp-channel": [SECRETS["channel"]]}, "MicropubTargetError"),  # unknown target blog
        ({"category": [{"name": SECRETS["category"]}]}, "MicropubContentError"),  # malformed category
    ],
)
def test_rejected_request_logs_no_submitted_values(
    client, blogs, users, caplog, capsys, overrides, error  # noqa: F811
):
    caplog.set_level(logging.DEBUG)
    properties = secret_properties(**overrides)
    del properties[SECRETS["property"]]

    response = micropub_json(client, users["publisher"], properties)

    assert response.status_code == 400
    assert not Post.objects.exists()
    output = capsys.readouterr()
    assert_no_secret(application_log_text(caplog) + output.out + output.err)
    # The rejection came from the handler and is still diagnosable.
    assert f"Micropub create failed: {error}" in handler_messages(caplog)


def test_unexpected_failure_logs_only_the_error_type(blogs, users, caplog, capsys):  # noqa: F811
    caplog.set_level(logging.DEBUG)
    error = RuntimeError(f"cannot store {SECRETS['content']}")

    with patch.object(Post, "save_revision", side_effect=error):
        with pytest.raises(RuntimeError):
            CastPostMicropubHandler().create_entry(secret_properties(), users["publisher"])

    assert not Post.objects.exists()
    output = capsys.readouterr()
    assert_no_secret(application_log_text(caplog) + output.out + output.err)
    assert "Micropub create failed: RuntimeError" in caplog.text


@pytest.mark.parametrize(
    ("error_class", "status", "raised"),
    [(RuntimeError, 500, "MicropubInternalError"), (ValueError, 400, "MicropubContentError")],
)
def test_endpoint_failure_logs_no_submitted_values(
    client, blogs, users, caplog, capsys, error_class, status, raised  # noqa: F811
):
    """django-indieweb logs what the handler raises: message, or message plus traceback."""
    caplog.set_level(logging.DEBUG)
    properties = secret_properties()
    del properties[SECRETS["property"]]
    cause = KeyError(f"cause {SECRETS['category']}")
    error = error_class(f"cannot store {SECRETS['content']}")
    error.__cause__ = cause

    with patch.object(Post, "save_revision", side_effect=error):
        response = micropub_json(client, users["publisher"], properties)

    assert response.status_code == status
    assert not Post.objects.exists()
    output = capsys.readouterr()
    assert_no_secret(application_log_text(caplog) + output.out + output.err)
    assert f"Micropub create failed: {error_class.__name__}" in handler_messages(caplog)
    # django-indieweb did log the failure, with the stand-in error.
    indieweb_records = [record for record in caplog.records if record.name == "indieweb.views"]
    assert indieweb_records
    if status == 500:
        [record] = [record for record in indieweb_records if record.exc_info]
        logged = record.exc_info[1]
        assert type(logged).__name__ == raised and str(logged) == "Micropub create failed (RuntimeError)"
        assert logged.__cause__ is None and logged.__context__ is None


def test_handler_replaces_unexpected_errors(blogs, users):  # noqa: F811
    with patch.object(Post, "save_revision", side_effect=TypeError(f"bad {SECRETS['content']}")):
        with pytest.raises(MicropubInternalError) as raised:
            create(users["publisher"], **{"mp-channel": ["alpha"]})

    assert str(raised.value) == "Micropub create failed (TypeError)"
    assert raised.value.__cause__ is None and raised.value.__context__ is None
    with patch.object(Post, "save_revision", side_effect=ValueError(f"bad {SECRETS['content']}")):
        with pytest.raises(MicropubContentError) as rejected:
            create(users["publisher"], **{"mp-channel": ["alpha"]})

    assert str(rejected.value) == "The request could not be processed"
    assert rejected.value.__cause__ is None and rejected.value.__context__ is None
    assert not Post.objects.exists()


def test_form_logs_no_submitted_values(client, blogs, users, caplog, capsys):  # noqa: F811
    caplog.set_level(logging.DEBUG)
    client.force_login(users["publisher"])
    data = {
        "post_type": "note",
        "content": f"Form {SECRETS['content']}",
        "category": SECRETS["category"],
        "photo": f"https://example.test/a.jpg?sig={SECRETS['photo']}",
        "blog": "alpha",
    }

    assert client.post(reverse("micropub-form"), data).status_code in (200, 302)
    assert Post.objects.count() == 1
    data["content"] = f"Second {SECRETS['content']}"
    with patch.object(Post, "save_revision", side_effect=RuntimeError(f"boom {SECRETS['content']}")):
        assert client.post(reverse("micropub-form"), data).status_code in (200, 302)
    assert Post.objects.count() == 1

    output = capsys.readouterr()
    assert_no_secret(application_log_text(caplog) + output.out + output.err)
    assert "Micropub create failed: RuntimeError" in caplog.text
    assert "Micropub form: error creating post (MicropubInternalError)" in caplog.text
    assert f"Micropub form: post created by user {users['publisher'].pk}" in caplog.text


@pytest.mark.parametrize("property_name", ["name", "category"])
@pytest.mark.parametrize("invalid", ["overlong", "nul", "surrogate"])
def test_invalid_storage_text_returns_400_without_writes(client, blogs, users, property_name, invalid):  # noqa: F811
    from .validation import TAG_NAME_FIELD, TITLE_FIELD

    field = TITLE_FIELD if property_name == "name" else TAG_NAME_FIELD
    value = {"overlong": "x" * (field.max_length + 1), "nul": "hello\x00world", "surrogate": "hello\ud800"}[invalid]
    tag_model = Post._meta.get_field("tags").remote_field.model
    counts = (Revision.objects.count(), PageLogEntry.objects.count(), tag_model.objects.count())
    response = micropub_json(
        client,
        users["publisher"],
        {"mp-channel": ["alpha"], "name": ["Title"], "content": ["Body"], property_name: [value]},
    )
    assert response.status_code == 400
    assert not Post.objects.exists()
    assert (Revision.objects.count(), PageLogEntry.objects.count(), tag_model.objects.count()) == counts


def test_boundary_title_and_tag_publish(client, blogs, users):  # noqa: F811
    from .validation import TAG_NAME_FIELD, TITLE_FIELD

    title = "ä" * TITLE_FIELD.max_length
    category = "猫" * TAG_NAME_FIELD.max_length
    response = micropub_json(
        client,
        users["publisher"],
        {"mp-channel": ["alpha"], "name": [title], "content": ["Body"], "category": [category]},
    )
    assert response.status_code == 201
    post = Post.objects.get()
    assert post.live and post.title == title
    assert list(post.tags.names()) == [category]


@pytest.mark.parametrize("kind", ["text", "html"])
def test_explicit_content_format_survives_publication(client, blogs, users, kind):  # noqa: F811
    response = micropub_json(
        client,
        users["publisher"],
        {"mp-channel": ["alpha"], "name": ["Title"], "content": [{kind: "<p>literal &amp; text</p>"}]},
    )
    assert response.status_code == 201
    html = body_html(Post.objects.get())
    if kind == "text":
        assert "&lt;p&gt;literal &amp;amp; text&lt;/p&gt;" in html
    else:
        assert "<p>literal &amp; text</p>" in html
