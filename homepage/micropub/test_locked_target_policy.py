"""Policy changes committed while Micropub waits for its parent-row lock."""

import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from unittest.mock import patch

import pytest
from cast.models import Blog, Post
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, transaction
from wagtail.models import GroupPagePermission, Page, Revision

from .handler import CastPostMicropubHandler, MicropubPermissionError, MicropubTargetError
from .test_micropub_permissions import blogs, users  # noqa: F401


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != "postgresql", reason="Requires real PostgreSQL row-lock waits")
@pytest.mark.parametrize("change", ["unpublish", "rename", "revoke", "deactivate"])
def test_waiting_create_rechecks_current_target_policy(users, change):  # noqa: F811
    user_pk = users["publisher"].pk
    blog_pk = Blog.objects.get(slug="alpha").pk
    resolved = Queue()
    original = CastPostMicropubHandler._get_target_blog
    revisions = Revision.objects.count()

    def resolve(self, properties, user):
        blog = original(self, properties, user)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            resolved.put(cursor.fetchone()[0])
        return blog

    def create():
        close_old_connections()
        try:
            return CastPostMicropubHandler().create_entry(
                {"mp-channel": ["alpha"], "name": ["Synthetic note"]},
                get_user_model().objects.get(pk=user_pk),
            )
        finally:
            close_old_connections()

    with patch.object(CastPostMicropubHandler, "_get_target_blog", resolve), ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            Blog.objects.select_for_update().get(pk=blog_pk)
            future = pool.submit(create)
            worker_pid = resolved.get(timeout=15)
            deadline = time.monotonic() + 10
            while True:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT cardinality(pg_blocking_pids(%s))", [worker_pid])
                    if cursor.fetchone()[0]:
                        break
                assert time.monotonic() < deadline, "Worker did not wait for the parent lock"
                time.sleep(0.01)
            if change == "unpublish":
                Page.objects.filter(pk=blog_pk).update(live=False)
            elif change == "rename":
                Page.objects.filter(pk=blog_pk).update(slug="renamed")
            elif change == "revoke":
                GroupPagePermission.objects.filter(page_id=blog_pk, permission__codename="publish_page").delete()
            else:
                get_user_model().objects.filter(pk=user_pk).update(is_active=False)
        error = MicropubTargetError if change in {"unpublish", "rename"} else MicropubPermissionError
        with pytest.raises(error):
            future.result(timeout=15)
    assert not Post.objects.exists()
    assert Revision.objects.count() == revisions
