"""Bound channel discovery SQL while retaining Wagtail permission decisions."""

import pytest
from cast.models import Blog
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test.utils import CaptureQueriesContext
from wagtail.models import GroupPagePermission, Page

from .handler import CastPostMicropubHandler
from .test_micropub_permissions import get_or_create_root

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", ["publisher", "adder", "inactive", "superuser"])
def test_channel_discovery_has_bounded_sql_for_one_and_fifty_blogs(role):
    root = get_or_create_root()
    allowed = root.add_child(instance=Page(title="Allowed", slug="allowed"))
    denied = root.add_child(instance=Page(title="Denied", slug="denied"))
    group = Group.objects.create(name="Synthetic publishers")
    for codename in ["add_page", "publish_page"] if role != "adder" else ["add_page"]:
        GroupPagePermission.objects.create(
            group=group,
            page=allowed,
            permission=Permission.objects.get(content_type__app_label="wagtailcore", codename=codename),
        )
    user = get_user_model().objects.create_user(
        username="synthetic-publisher", is_active=role != "inactive", is_superuser=role == "superuser"
    )
    user.groups.add(group)
    # Another group on an unrelated branch must not grant publish there.
    unrelated = Group.objects.create(name="Synthetic unrelated")
    GroupPagePermission.objects.create(
        group=unrelated,
        page=denied,
        permission=Permission.objects.get(content_type__app_label="wagtailcore", codename="publish_page"),
    )

    allowed.add_child(instance=Blog(title="Blog 0", slug="blog-0"))

    def discover():
        # A fresh request user prevents the one-blog call warming user caches
        # for the fifty-blog call. Both calls exercise the actual config path.
        current = get_user_model().objects.get(pk=user.pk)
        with CaptureQueriesContext(connection) as queries:
            channels = CastPostMicropubHandler().get_config(current)["channels"]
        return channels, len(queries)

    first, small_count = discover()
    assert first == ([{"uid": "blog-0", "name": "Blog 0"}] if role in {"publisher", "superuser"} else [])
    for index in range(1, 50):
        allowed.add_child(instance=Blog(title=f"Blog {index}", slug=f"blog-{index}"))
    denied.add_child(instance=Blog(title="Denied blog", slug="denied-blog"))
    allowed.add_child(instance=Blog(title="Draft", slug="draft", live=False))
    allowed.add_child(instance=Blog(title="Duplicate allowed", slug="duplicate"))
    denied.add_child(instance=Blog(title="Duplicate denied", slug="duplicate"))

    channels, large_count = discover()
    expected = [{"uid": f"blog-{index}", "name": f"Blog {index}"} for index in range(50)]
    if role == "superuser":
        expected.append({"uid": "denied-blog", "name": "Denied blog"})
    if role not in {"publisher", "superuser"}:
        expected = []
    assert channels == expected
    assert large_count <= small_count + 2, (small_count, large_count)
    assert large_count <= 8, large_count
