"""
Received Webmentions are queued on the ``cast_transcripts`` worker and the
endpoint is rate limited.
"""

from functools import partial

import httpx
import pytest
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.urls import reverse
from django_tasks_db.models import DBTaskResult
from indieweb.models import Webmention
from indieweb.processors import process_queued_webmention

from homepage.core import webmention_tasks

SOURCE = "https://remote.example/post-mentioning-us"
TARGET = "https://homepage.example/jochen/"
IMMEDIATE_TASKS = {
    "default": {"BACKEND": "django_tasks.backends.immediate.ImmediateBackend"},
    "cast_transcripts": {"BACKEND": "django_tasks.backends.immediate.ImmediateBackend"},
}


@pytest.fixture(autouse=True)
def fresh_rate_limit_counters():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def site_domain(db):
    Site.objects.update_or_create(pk=settings.SITE_ID, defaults={"domain": "homepage.example"})
    Site.objects.clear_cache()
    yield
    Site.objects.clear_cache()


@pytest.fixture
def no_remote_fetch(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the Webmention request must not fetch a remote page")

    monkeypatch.setattr(httpx.Client, "send", refuse)


def post_webmention(client):
    return client.post(reverse("indieweb:webmention"), data={"source": SOURCE, "target": TARGET})


def test_settings_queue_webmentions_and_limit_the_endpoint():
    assert settings.INDIEWEB_WEBMENTION_ENQUEUE == "homepage.core.webmention_tasks.enqueue_webmention"
    assert settings.INDIEWEB_RATE_LIMITS == {"webmention": {"limit": 60, "window": 300}}
    assert webmention_tasks.process_webmention.backend == "cast_transcripts"


@pytest.mark.django_db
def test_post_queues_the_webmention_without_fetching_the_source(client, no_remote_fetch):
    response = post_webmention(client)

    assert response.status_code == 202
    webmention = Webmention.objects.get(source_url=SOURCE)
    assert webmention.status == "pending"
    assert response["Location"].endswith(f"/indieweb/webmention/{webmention.status_token}/")
    queued = DBTaskResult.objects.get()
    assert queued.task_path == "homepage.core.webmention_tasks.process_webmention"
    assert queued.backend_name == "cast_transcripts"
    assert queued.queue_name == "default"
    assert queued.args_kwargs["args"] == [webmention.pk]


@pytest.mark.django_db
def test_running_the_queued_task_processes_the_webmention(client, monkeypatch):
    def remote_site(request):
        assert str(request.url) == SOURCE
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text=f'<html><body><a href="{TARGET}">a mention</a></body></html>',
        )

    monkeypatch.setattr(
        webmention_tasks,
        "process_queued_webmention",
        partial(process_queued_webmention, client=httpx.Client(transport=httpx.MockTransport(remote_site))),
    )
    assert post_webmention(client).status_code == 202
    assert Webmention.objects.get(source_url=SOURCE).status == "pending"

    # What the worker does with the stored row: import the task by its path
    # and call it with the stored arguments.
    queued = DBTaskResult.objects.get().task_result
    queued.task.call(*queued.args, **queued.kwargs)

    assert Webmention.objects.get(source_url=SOURCE).status == "verified"


@pytest.mark.django_db
def test_requests_over_the_limit_are_rejected(client, no_remote_fetch, settings):
    settings.INDIEWEB_RATE_LIMITS = {"webmention": {"limit": 2, "window": 300}}

    assert [post_webmention(client).status_code for _ in range(3)] == [202, 202, 429]
    rejected = post_webmention(client)
    assert rejected.status_code == 429
    assert 0 < int(rejected["Retry-After"]) <= 300
    assert DBTaskResult.objects.count() == 2


@pytest.mark.django_db
def test_immediate_backend_processes_the_webmention_in_the_request(client, monkeypatch, settings):
    settings.TASKS = IMMEDIATE_TASKS
    processed = []
    monkeypatch.setattr(webmention_tasks, "process_queued_webmention", processed.append)

    response = post_webmention(client)

    assert response.status_code == 202
    assert processed == [Webmention.objects.get(source_url=SOURCE).pk]
    assert not DBTaskResult.objects.exists()
