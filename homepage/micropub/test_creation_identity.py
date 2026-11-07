from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from unittest.mock import patch

import pytest
from cast.models import Post
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import override_settings
from django.urls import reverse
from indieweb.models import Token
from wagtail.models import Revision

from . import handler as handler_module
from .handler import CastPostMicropubHandler, MicropubContentError
from .test_micropub_permissions import blogs, users  # noqa: F401

pytestmark = pytest.mark.django_db


@pytest.fixture
def publish(client, users):  # noqa: F811
    issued = Token.objects.create(
        owner=users["publisher"], me="http://testserver/", client_id="https://client.example/", scope="create"
    )
    bearer = issued.key

    def send(title, **extra):
        return client.post(
            reverse("indieweb:micropub"),
            {
                "h": "entry",
                "mp-channel": "alpha",
                "name": title,
                "content": "Synthetic note",
                **extra,
            },
            HTTP_AUTHORIZATION=f"Bearer {bearer}",
        )

    return send


@pytest.mark.parametrize("title,expected", [("Daily note", "daily-note"), ("!!!", "post")])
def test_repeat_titles_get_distinct_published_pages_and_locations(publish, title, expected):  # noqa: F811
    first = publish(title)
    second = publish(title)
    assert first.status_code == second.status_code == 201
    posts = list(Post.objects.order_by("pk"))
    assert [post.slug for post in posts] == [expected, expected + "-2"]
    assert first["Location"] != second["Location"]
    assert [response["Location"] for response in (first, second)] == [post.get_full_url() for post in posts]
    assert all(post.live and post.live_revision_id == post.latest_revision_id for post in posts)


def test_slug_exhaustion_is_bounded_and_preserves_existing_post(publish, users, monkeypatch):  # noqa: F811
    assert publish("Daily note").status_code == 201
    original = Post.objects.get()
    revision_count = Revision.objects.count()
    monkeypatch.setattr(handler_module, "MAX_SLUG_ATTEMPTS", 1, raising=False)
    with pytest.raises(MicropubContentError, match="No available post slug"):
        CastPostMicropubHandler().create_entry(
            {"mp-channel": ["alpha"], "name": ["Daily note"], "content": ["Another note"]}, users["publisher"]
        )
    assert Post.objects.get().pk == original.pk
    assert Revision.objects.count() == revision_count


@pytest.mark.django_db(transaction=True)
def test_simultaneous_same_title_creates_serialize_parent_and_preserve_both(users):  # noqa: F811
    barrier = Barrier(2)
    original = CastPostMicropubHandler._get_target_blog
    user_pk = users["publisher"].pk

    def resolve_then_wait(self, properties, user):
        blog = original(self, properties, user)
        barrier.wait(timeout=15)
        return blog

    def create():
        close_old_connections()
        try:
            user = get_user_model().objects.get(pk=user_pk)
            return (
                CastPostMicropubHandler()
                .create_entry({"mp-channel": ["alpha"], "name": ["Same title"], "content": ["Synthetic body"]}, user)
                .url
            )
        finally:
            close_old_connections()

    with patch.object(CastPostMicropubHandler, "_get_target_blog", resolve_then_wait):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(create) for _ in range(2)]
            urls = [future.result(timeout=30) for future in futures]
    posts = list(Post.objects.order_by("slug"))
    assert [post.slug for post in posts] == ["same-title", "same-title-2"]
    assert set(urls) == {post.get_url() for post in posts}
    assert len(set(urls)) == 2
    assert all(post.live and post.live_revision_id == post.latest_revision_id for post in posts)


@pytest.mark.parametrize("published", ["0001-01-01T00:00:00+23:59", "9999-12-31T23:59:59-23:59"])
def test_utc_overflow_is_client_error_without_pages_or_revisions(publish, published):  # noqa: F811
    revision_count = Revision.objects.count()
    response = publish("Extreme date", published=published)
    assert response.status_code == 400
    assert not Post.objects.exists()
    assert Revision.objects.count() == revision_count


@pytest.mark.parametrize(
    "published,expected",
    [
        ("2026-11-07T12:34:56+05:30", datetime(2026, 11, 7, 7, 4, 56, tzinfo=UTC)),
        ("2026-11-07T12:34:56", datetime(2026, 11, 7, 12, 34, 56, tzinfo=UTC)),
        ("not a date", datetime(2026, 11, 7, 1, 2, 3, tzinfo=UTC)),
    ],
)
@override_settings(TIME_ZONE="UTC")
def test_ordinary_offset_naive_and_invalid_date_policy(publish, published, expected):  # noqa: F811
    with patch("homepage.micropub.handler.timezone.now", return_value=datetime(2026, 11, 7, 1, 2, 3, tzinfo=UTC)):
        response = publish("Date policy", published=published)
    assert response.status_code == 201
    assert Post.objects.get().visible_date == expected


@override_settings(TIME_ZONE="Europe/Berlin")
def test_naive_date_uses_configured_timezone(publish):
    response = publish("Local date", published="2026-11-07T12:34:56")
    assert response.status_code == 201
    assert Post.objects.get().visible_date == datetime(2026, 11, 7, 11, 34, 56, tzinfo=UTC)


@override_settings(TIME_ZONE="Etc/GMT-1")
def test_naive_utc_underflow_is_rejected_before_creation(publish):
    revision_count = Revision.objects.count()
    response = publish("Local extreme", published="0001-01-01T00:00:00")
    assert response.status_code == 400
    assert not Post.objects.exists()
    assert Revision.objects.count() == revision_count
