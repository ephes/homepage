from __future__ import annotations

import io

import pytest
from cast.models import Blog, Gallery, Post
from django.core.management import call_command
from django.core.management.base import CommandError
from wagtail.images import get_image_model
from wagtail.images.models import Filter
from wagtail.images.tests.utils import get_test_image_file
from wagtail.models import Collection, Locale, Page

from homepage.core.management.commands import regenerate_broken_renditions as repair

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def root_collection():
    if Collection.get_first_root_node() is None:
        Collection.add_root(instance=Collection(name="Root"))


@pytest.fixture
def site_root():
    root = Page.get_first_root_node()
    if root is None:
        Locale.objects.get_or_create(language_code="en")
        root = Page.add_root(instance=Page(title="Root", slug="root"))
    return root.add_child(instance=Page(title="Home", slug="rendition-repair-home"))


def make_image(title):
    return get_image_model().objects.create(title=title, file=get_test_image_file(filename=f"{title}.png"))


def make_rendition(image, spec="width-100"):
    return image.create_rendition(Filter(spec=spec))


def make_post(blog, slug, *, images=(), gallery_images=()):
    post = blog.add_child(instance=Post(title=slug, slug=slug))
    post.images.add(*images)
    if gallery_images:
        gallery = Gallery.objects.create()
        gallery.images.add(*gallery_images)
        post.galleries.add(gallery)
    return post


def remove_file(rendition):
    rendition.file.storage.delete(rendition.file.name)
    assert not rendition.file.storage.exists(rendition.file.name)


def stored(rendition):
    """A fresh copy of the row; refresh_from_db would try to read a missing file."""
    return type(rendition).objects.get(pk=rendition.pk)


def file_exists(rendition):
    fresh = stored(rendition)
    return fresh.file.storage.exists(fresh.file.name)


class StorageError(Exception):
    def __init__(self, status):
        super().__init__(f"storage answered {status}")
        self.status = status


@pytest.fixture
def forbid_regeneration(monkeypatch):
    """Call the returned function once the fixtures exist: from then on nothing may be replaced."""

    def fail(*args, **kwargs):
        raise AssertionError("no rendition may be generated, saved or deleted")

    def activate():
        model = get_image_model()
        monkeypatch.setattr(model, "generate_rendition_file", fail)
        monkeypatch.setattr(model, "create_rendition", fail)
        monkeypatch.setattr(model.get_rendition_model(), "delete", fail)
        monkeypatch.setattr(model.get_rendition_model(), "save", fail)

    return activate


@pytest.mark.parametrize("status", [503, 429, 403, 301])
def test_unknown_storage_state_never_deletes_or_regenerates(monkeypatch, forbid_regeneration, status):
    image = make_image("unknown")
    rendition = make_rendition(image)
    before = (rendition.pk, rendition.file.name)

    def exists(name):
        raise StorageError(status)

    monkeypatch.setattr(rendition.file.storage, "exists", exists)
    forbid_regeneration()

    result = repair.regenerate_renditions_for_image(image)

    assert result.regenerated == [] and result.failed == []
    assert result.unknown == [
        (rendition.pk, before[1], f"storage check failed: StorageError('storage answered {status}')")
    ]
    monkeypatch.undo()
    assert (stored(rendition).pk, stored(rendition).file.name) == before
    assert file_exists(rendition)


def test_existing_rendition_is_left_alone(forbid_regeneration):
    image = make_image("healthy")
    make_rendition(image)
    forbid_regeneration()

    result = repair.regenerate_renditions_for_image(image)

    assert not result.regenerated and not result.incomplete


def test_missing_rendition_is_regenerated_on_the_same_row():
    image = make_image("missing")
    rendition = make_rendition(image)
    healthy = make_rendition(image, "width-50")
    remove_file(rendition)

    result = repair.regenerate_renditions_for_image(image)

    assert [r.pk for r in result.regenerated] == [rendition.pk]
    assert not result.incomplete
    assert file_exists(rendition) and file_exists(healthy)
    assert stored(rendition).filter_spec == "width-100"
    assert image.renditions.count() == 2


def test_failed_regeneration_keeps_the_row_for_a_retry(monkeypatch):
    image = make_image("broken")
    rendition = make_rendition(image)
    remove_file(rendition)
    before = (rendition.pk, rendition.file.name, rendition.filter_spec, rendition.width, rendition.height)

    def fail(self, filter, **kwargs):
        raise RuntimeError("source image unavailable")

    monkeypatch.setattr(get_image_model(), "generate_rendition_file", fail)
    result = repair.regenerate_renditions_for_image(image)

    assert result.regenerated == [] and result.unknown == []
    assert result.failed == [
        (rendition.pk, before[1], "regeneration failed: RuntimeError('source image unavailable')")
    ]
    fresh = stored(rendition)
    assert (fresh.pk, fresh.file.name, fresh.filter_spec, fresh.width, fresh.height) == before

    monkeypatch.undo()
    retry = repair.regenerate_renditions_for_image(image)

    assert [r.pk for r in retry.regenerated] == [rendition.pk]
    assert file_exists(rendition)


def run_command(*args):
    stdout, stderr = io.StringIO(), io.StringIO()
    call_command("regenerate_broken_renditions", *args, stdout=stdout, stderr=stderr)
    return stdout.getvalue(), stderr.getvalue()


def test_command_repairs_every_post_of_every_requested_blog(site_root):
    first = site_root.add_child(instance=Blog(title="First", slug="first"))
    second = site_root.add_child(instance=Blog(title="Second", slug="second"))
    ignored = site_root.add_child(instance=Blog(title="Ignored", slug="ignored"))
    renditions = []
    for index in range(3):
        rendition = make_rendition(make_image(f"first-{index}"))
        renditions.append(rendition)
        make_post(first, f"first-post-{index}", images=[rendition.image])
    gallery_rendition = make_rendition(make_image("gallery"))
    make_post(first, "first-gallery-post", gallery_images=[gallery_rendition.image])
    second_rendition = make_rendition(make_image("second"))
    make_post(second, "second-post", images=[second_rendition.image])
    ignored_rendition = make_rendition(make_image("ignored"))
    make_post(ignored, "ignored-post", images=[ignored_rendition.image])
    for rendition in [*renditions, gallery_rendition, second_rendition, ignored_rendition]:
        remove_file(rendition)

    stdout, stderr = run_command("first", "second")

    assert all(file_exists(r) for r in [*renditions, gallery_rendition, second_rendition])
    assert not file_exists(ignored_rendition)
    assert "Blog first: checked 4 posts, regenerated 4, unknown 0, failed 0" in stdout
    assert "Blog second: checked 1 posts, regenerated 1, unknown 0, failed 0" in stdout
    assert "generated renditions: 5" in stdout
    assert stderr == ""


def test_command_limit_restricts_posts_per_blog_explicitly(site_root):
    blog = site_root.add_child(instance=Blog(title="Limited", slug="limited"))
    renditions = []
    for index in range(3):
        rendition = make_rendition(make_image(f"limited-{index}"))
        renditions.append(rendition)
        make_post(blog, f"limited-post-{index}", images=[rendition.image])
        remove_file(rendition)

    stdout, _ = run_command("limited", "--limit", "2")

    assert "Blog limited: checked 2 posts, regenerated 2" in stdout
    assert sum(file_exists(r) for r in renditions) == 2


def test_command_succeeds_for_an_empty_blog(site_root):
    site_root.add_child(instance=Blog(title="Empty", slug="empty"))

    stdout, stderr = run_command("empty")

    assert "Blog empty: checked 0 posts, regenerated 0, unknown 0, failed 0" in stdout
    assert "generated renditions: 0" in stdout


def test_command_rejects_unknown_blog_before_changing_anything(site_root):
    blog = site_root.add_child(instance=Blog(title="Known", slug="known"))
    rendition = make_rendition(make_image("known"))
    make_post(blog, "known-post", images=[rendition.image])
    remove_file(rendition)

    with pytest.raises(CommandError, match="'nope' does not exist"):
        run_command("known", "nope")

    assert not file_exists(rendition)


@pytest.mark.parametrize("limit", ["0", "-1"])
def test_command_rejects_non_positive_limit(site_root, limit):
    site_root.add_child(instance=Blog(title="Any", slug="any"))

    with pytest.raises(CommandError, match="--limit"):
        run_command("any", "--limit", limit)


def test_command_reports_unchecked_renditions_and_fails(site_root, monkeypatch, forbid_regeneration):
    blog = site_root.add_child(instance=Blog(title="Flaky", slug="flaky"))
    rendition = make_rendition(make_image("flaky"))
    make_post(blog, "flaky-post", images=[rendition.image])

    def exists(name):
        raise StorageError(503)

    monkeypatch.setattr(rendition.file.storage, "exists", exists)
    forbid_regeneration()
    stdout, stderr = io.StringIO(), io.StringIO()

    with pytest.raises(CommandError, match="1 renditions could not be checked and 0 could not be regenerated"):
        call_command("regenerate_broken_renditions", "flaky", stdout=stdout, stderr=stderr)

    assert "Blog flaky: checked 1 posts, regenerated 0, unknown 1, failed 0" in stdout.getvalue()
    assert f"rendition {rendition.pk}" in stderr.getvalue() and "left unchanged" in stderr.getvalue()


@pytest.fixture
def repair_storage(monkeypatch, tmp_path):
    from django.core.files.storage import FileSystemStorage

    storage = FileSystemStorage(location=tmp_path)
    field = get_image_model().get_rendition_model()._meta.get_field("file")
    monkeypatch.setattr(field, "storage", storage)
    return storage


def failed_row_save(monkeypatch, rendition, storage):
    """Let the real FileField write, then fail the database write boundary."""
    from django.db import DatabaseError

    allocated = []
    save = storage.save

    def record_save(*args, **kwargs):
        name = save(*args, **kwargs)
        allocated.append(name)
        return name

    def fail(*args, **kwargs):
        assert allocated and storage.exists(allocated[-1])
        raise DatabaseError("row write failed")

    monkeypatch.setattr(storage, "save", record_save)
    monkeypatch.setattr(type(rendition), "_save_table", fail)
    return allocated


def missing_legacy_rendition():
    image = make_image("save-failure")
    rendition = make_rendition(image)
    remove_file(rendition)
    type(rendition).objects.filter(pk=rendition.pk).update(file="images/legacy-missing.png")
    return image, stored(rendition)


def test_failed_row_save_removes_only_owned_output_and_retry_attaches_one(monkeypatch, repair_storage):
    from django.core.files.base import ContentFile

    image, rendition = missing_legacy_rendition()
    before = (rendition.file.name, rendition.width, rendition.height)
    survivor = repair_storage.save("images/existing.png", ContentFile(b"existing"))
    allocated = failed_row_save(monkeypatch, rendition, repair_storage)

    result = repair.regenerate_renditions_for_image(image)

    assert len(allocated) == 1
    assert not repair_storage.exists(allocated[0])
    assert repair_storage.open(survivor).read() == b"existing"
    fresh = stored(rendition)
    assert (fresh.file.name, fresh.width, fresh.height) == before
    assert not result.regenerated and "row write failed" in result.failed[0][2]
    monkeypatch.undo()
    # Reinstall the temporary backend after undoing the fault injection.
    monkeypatch.setattr(type(rendition)._meta.get_field("file"), "storage", repair_storage)
    retry = repair.regenerate_renditions_for_image(image)
    assert [r.pk for r in retry.regenerated] == [rendition.pk]
    assert image.renditions.count() == 1
    assert file_exists(rendition)


def test_failed_row_save_preserves_output_referenced_by_another_row(monkeypatch, repair_storage):
    image, rendition = missing_legacy_rendition()
    other = make_rendition(make_image("shared-output"))
    allocated = failed_row_save(monkeypatch, rendition, repair_storage)
    save = repair_storage.save

    def share(*args, **kwargs):
        name = save(*args, **kwargs)
        type(other).objects.filter(pk=other.pk).update(file=name)
        return name

    monkeypatch.setattr(repair_storage, "save", share)
    result = repair.regenerate_renditions_for_image(image)

    assert allocated and stored(other).file.name == allocated[0]
    assert repair_storage.exists(allocated[0])
    assert stored(rendition).file.name == "images/legacy-missing.png"
    assert "row write failed" in result.failed[0][2]


def test_failed_row_save_never_deletes_a_preexisting_returned_name(monkeypatch, repair_storage):
    from django.core.files.base import ContentFile

    image, rendition = missing_legacy_rendition()
    existing = repair_storage.save("images/preexisting.png", ContentFile(b"existing"))
    allocated = failed_row_save(monkeypatch, rendition, repair_storage)

    def reuse(*args, **kwargs):
        allocated.append(existing)
        return existing

    monkeypatch.setattr(repair_storage, "save", reuse)
    result = repair.regenerate_renditions_for_image(image)

    assert allocated == [existing]
    assert repair_storage.open(existing).read() == b"existing"
    assert "row write failed" in result.failed[0][2]
    assert existing in result.failed[0][2]  # Recovery location when ownership cannot be proven.


def test_cleanup_failure_preserves_primary_error_and_reports_recovery(monkeypatch, repair_storage):
    image, rendition = missing_legacy_rendition()
    allocated = failed_row_save(monkeypatch, rendition, repair_storage)

    def fail_delete(name):
        raise OSError("cleanup unavailable")

    monkeypatch.setattr(repair_storage, "delete", fail_delete)
    result = repair.regenerate_renditions_for_image(image)

    assert allocated and repair_storage.exists(allocated[0])
    assert "row write failed" in result.failed[0][2]
    assert "cleanup unavailable" in result.failed[0][2]
    assert allocated[0] in result.failed[0][2]
    assert stored(rendition).file.name == "images/legacy-missing.png"


def test_failed_save_after_database_write_rolls_back_the_old_row(monkeypatch, repair_storage):
    image, rendition = missing_legacy_rendition()
    save = type(rendition).save
    calls = []

    def save_then_fail(self, *args, **kwargs):
        save(self, *args, **kwargs)
        calls.append(self.file.name)
        raise RuntimeError("post-save failure")

    monkeypatch.setattr(type(rendition), "save", save_then_fail)
    result = repair.regenerate_renditions_for_image(image)

    assert len(calls) == 1
    assert stored(rendition).file.name == "images/legacy-missing.png"
    assert not repair_storage.exists(calls[0])
    assert "post-save failure" in result.failed[0][2]


def test_reference_check_failure_retains_output_for_recovery(monkeypatch, repair_storage):
    from django.db.models import QuerySet

    image, rendition = missing_legacy_rendition()
    allocated = failed_row_save(monkeypatch, rendition, repair_storage)
    exists = QuerySet.exists
    checked = []

    def fail_check(self):
        if self.model is type(rendition) and allocated:
            checked.append(True)
            raise RuntimeError("reference check unavailable")
        return exists(self)

    monkeypatch.setattr(QuerySet, "exists", fail_check)
    result = repair.regenerate_renditions_for_image(image)

    assert checked == [True]
    assert repair_storage.exists(allocated[0])
    assert "row write failed" in result.failed[0][2]
    assert "reference check unavailable" in result.failed[0][2]
    assert allocated[0] in result.failed[0][2]
