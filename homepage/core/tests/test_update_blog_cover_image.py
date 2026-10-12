from __future__ import annotations

import io

import pytest
from cast.image_metadata import has_gps
from cast.models import Blog
from django.core.files.base import ContentFile
from django.core.files.storage import InMemoryStorage, default_storage
from django.core.management import call_command
from django.core.management.base import CommandError
from PIL import Image as PILImage
from wagtail.actions.publish_page_revision import PublishPagePermissionError
from wagtail.images import get_image_model
from wagtail.images.tests.utils import get_test_image_file
from wagtail.models import Collection, Locale, Page, Revision

from homepage.core.management.commands import update_blog_cover_image as cover_command
from homepage.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

COMMAND = "update_blog_cover_image"


@pytest.fixture(autouse=True)
def root_collection():
    if Collection.get_first_root_node() is None:
        Collection.add_root(instance=Collection(name="Root"))


@pytest.fixture(autouse=True)
def storage(monkeypatch):
    """A private, empty image storage so file names never leak between tests."""
    private_storage = InMemoryStorage()
    monkeypatch.setattr(get_image_model()._meta.get_field("file"), "storage", private_storage)
    return private_storage


@pytest.fixture
def user():
    return UserFactory(username="cover-editor", is_superuser=True)


@pytest.fixture
def old_cover():
    return get_image_model().objects.create(title="old cover", file=get_test_image_file(filename="old-cover.png"))


@pytest.fixture
def blog(user, old_cover):
    root = Page.get_first_root_node()
    if root is None:
        Locale.objects.get_or_create(language_code="en")
        root = Page.add_root(instance=Page(title="Root", slug="root"))
    home = root.add_child(instance=Page(title="Home", slug="cover-import-home"))
    return home.add_child(
        instance=Blog(
            title="Cover blog",
            slug="cover_blog",
            owner=user,
            cover_image=old_cover,
            cover_alt_text="old alt text",
        )
    )


@pytest.fixture
def new_cover_path(tmp_path):
    path = tmp_path / "new-cover.png"
    path.write_bytes(get_test_image_file(filename="new-cover.png", colour="black").file.getvalue())
    return path


def stored_names(storage):
    """Every file name below the storage root."""
    names: set[str] = set()
    pending = [""]
    while pending:
        directory = pending.pop()
        directories, files = storage.listdir(directory)
        prefix = f"{directory}/" if directory else ""
        pending.extend(f"{prefix}{name}" for name in directories)
        names.update(f"{prefix}{name}" for name in files)
    return names


def run(path, *args):
    stdout, stderr = io.StringIO(), io.StringIO()
    call_command(
        COMMAND, str(path), "--blog-slug", "cover_blog", "--user", "cover-editor", *args, stdout=stdout, stderr=stderr
    )
    return stdout.getvalue(), stderr.getvalue()


def test_publishes_new_cover_and_keeps_the_old_image(blog, old_cover, new_cover_path, storage):
    before = stored_names(storage)

    stdout, stderr = run(new_cover_path, "--title", "new cover", "--alt-text", "new alt text")

    Image = get_image_model()
    live = Blog.objects.get(pk=blog.pk)
    new_image = Image.objects.get(title="new cover")
    assert live.cover_image_id == new_image.pk
    assert live.cover_alt_text == "new alt text"
    assert (new_image.width, new_image.height) == (640, 480)
    assert storage.exists(new_image.file.name)
    assert storage.open(new_image.file.name).read() == new_cover_path.read_bytes()
    # The previous cover image and its file are untouched.
    assert Image.objects.filter(pk=old_cover.pk).exists()
    assert before <= stored_names(storage)
    assert live.latest_revision.user.username == "cover-editor"
    assert "Updated cover_blog cover image" in stdout
    assert stderr == ""


def test_no_publish_saves_the_page_without_a_revision(blog, new_cover_path):
    run(new_cover_path, "--title", "new cover", "--no-publish")

    live = Blog.objects.get(pk=blog.pk)
    assert live.cover_image.title == "new cover"
    assert not Revision.objects.filter(object_id=str(blog.pk)).exists()


@pytest.mark.parametrize(
    ("flags", "failing_method"),
    [
        ((), "save_revision"),
        (("--no-publish",), "save"),
    ],
)
def test_blog_save_failure_rolls_back_and_removes_only_the_new_upload(
    blog, old_cover, new_cover_path, storage, monkeypatch, flags, failing_method
):
    Image = get_image_model()
    before = stored_names(storage)
    old_cover_bytes = storage.open(old_cover.file.name).read()
    image_pks = set(Image.objects.values_list("pk", flat=True))

    def fail(self, *args, **kwargs):
        raise RuntimeError("revision storage is down")

    monkeypatch.setattr(Blog, failing_method, fail)

    with pytest.raises(RuntimeError, match="revision storage is down"):
        run(new_cover_path, "--title", "new cover", "--alt-text", "new alt text", *flags)

    live = Blog.objects.get(pk=blog.pk)
    assert live.cover_image_id == old_cover.pk
    assert live.cover_alt_text == "old alt text"
    assert set(Image.objects.values_list("pk", flat=True)) == image_pks
    assert not Revision.objects.filter(object_id=str(blog.pk)).exists()
    # Exactly the pre-existing files remain, with their content.
    assert stored_names(storage) == before
    assert storage.open(old_cover.file.name).read() == old_cover_bytes


def test_publish_failure_after_the_revision_was_saved_rolls_everything_back(
    blog, old_cover, new_cover_path, storage, monkeypatch
):
    before = stored_names(storage)

    def fail(self, *args, **kwargs):
        raise RuntimeError("publish failed")

    monkeypatch.setattr(Revision, "publish", fail)

    with pytest.raises(RuntimeError, match="publish failed"):
        run(new_cover_path, "--title", "new cover")

    live = Blog.objects.get(pk=blog.pk)
    assert live.cover_image_id == old_cover.pk
    assert not get_image_model().objects.filter(title="new cover").exists()
    assert not Revision.objects.filter(object_id=str(blog.pk)).exists()
    assert stored_names(storage) == before


def test_user_without_publish_permission_leaves_no_image_or_file_behind(blog, old_cover, new_cover_path, storage):
    # A real failure after the upload and the revision: Wagtail refuses to
    # publish for a user without publish permission.
    UserFactory(username="no-publisher")
    before = stored_names(storage)

    with pytest.raises(PublishPagePermissionError):
        call_command(
            COMMAND, str(new_cover_path), "--blog-slug", "cover_blog", "--user", "no-publisher", "--title", "x"
        )

    assert Blog.objects.get(pk=blog.pk).cover_image_id == old_cover.pk
    assert not get_image_model().objects.filter(title="x").exists()
    assert not Revision.objects.filter(object_id=str(blog.pk)).exists()
    assert stored_names(storage) == before


def test_failure_cleanup_reports_the_removed_upload(blog, new_cover_path, storage, monkeypatch):
    monkeypatch.setattr(Blog, "save_revision", lambda self, *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    stderr = io.StringIO()

    with pytest.raises(RuntimeError):
        call_command(
            COMMAND, str(new_cover_path), "--blog-slug", "cover_blog", "--user", "cover-editor", stderr=stderr
        )

    assert "Removed the unreferenced upload 'original_images/new-cover.png'" in stderr.getvalue()


def test_same_named_existing_file_survives_a_failed_import(blog, new_cover_path, storage, monkeypatch):
    # An earlier upload already owns the name this import asks for; the storage
    # hands out a different name, and only that one is removed on failure.
    existing_name = storage.save("original_images/new-cover.png", ContentFile(b"earlier upload"))
    assert existing_name == "original_images/new-cover.png"
    before = stored_names(storage)
    deleted: list[str] = []
    original_delete = storage.delete

    def recording_delete(name):
        deleted.append(name)
        return original_delete(name)

    monkeypatch.setattr(storage, "delete", recording_delete)
    monkeypatch.setattr(Blog, "save_revision", lambda self, *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(RuntimeError):
        run(new_cover_path)

    assert len(deleted) == 1
    assert deleted[0] != existing_name
    assert deleted[0].startswith("original_images/new-cover")
    assert stored_names(storage) == before
    assert storage.open(existing_name).read() == b"earlier upload"


def test_overwriting_storage_never_deletes_a_name_that_existed_before(blog, new_cover_path, storage, monkeypatch):
    # A storage configured to overwrite returns the requested name even though
    # an object with that name was there before. That name is not ours to delete.
    existing_name = storage.save("original_images/new-cover.png", ContentFile(b"earlier upload"))
    monkeypatch.setattr(storage, "get_available_name", lambda name, max_length=None: name)
    deleted: list[str] = []
    monkeypatch.setattr(storage, "delete", deleted.append)
    monkeypatch.setattr(Blog, "save_revision", lambda self, *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(RuntimeError):
        run(new_cover_path)

    assert deleted == []
    assert storage.exists(existing_name)


def test_failed_storage_save_deletes_nothing(blog, old_cover, new_cover_path, storage, monkeypatch):
    before = stored_names(storage)
    deleted: list[str] = []

    def fail_save(name, content, max_length=None):
        raise OSError("bucket unreachable")

    monkeypatch.setattr(storage, "save", fail_save)
    monkeypatch.setattr(storage, "delete", deleted.append)

    with pytest.raises(OSError, match="bucket unreachable"):
        run(new_cover_path)

    assert deleted == []
    assert stored_names(storage) == before
    assert Blog.objects.get(pk=blog.pk).cover_image_id == old_cover.pk


def test_cleanup_failure_keeps_the_original_error_and_names_the_leftover(blog, new_cover_path, storage, monkeypatch):
    def fail_delete(name):
        raise OSError("delete denied")

    monkeypatch.setattr(storage, "delete", fail_delete)
    monkeypatch.setattr(Blog, "save_revision", lambda self, *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    stderr = io.StringIO()

    with pytest.raises(RuntimeError, match="boom"):
        call_command(
            COMMAND, str(new_cover_path), "--blog-slug", "cover_blog", "--user", "cover-editor", stderr=stderr
        )

    assert "Could not remove the unreferenced upload 'original_images/new-cover.png'" in stderr.getvalue()
    assert "delete denied" in stderr.getvalue()


def test_missing_image_file_is_rejected_before_anything_is_stored(blog, tmp_path, storage):
    before = stored_names(storage)

    with pytest.raises(CommandError, match="does not exist"):
        run(tmp_path / "missing.png")

    assert stored_names(storage) == before


def _jpeg_with_gps(path):
    image = PILImage.new("RGB", (64, 48), "navy")
    exif = PILImage.Exif()
    exif[0x8825] = {1: "N", 2: (52.0, 31.0, 12.0), 3: "E", 4: (13.0, 24.0, 18.0)}
    image.save(path, format="JPEG", exif=exif)
    with PILImage.open(path) as written:
        assert has_gps(written)


def test_gps_metadata_is_stripped_from_the_imported_cover(blog, tmp_path, storage):
    # The upload must keep going through the model so django-cast sanitizes it.
    path = tmp_path / "geotagged.jpg"
    _jpeg_with_gps(path)

    run(path, "--title", "geotagged cover")

    new_image = get_image_model().objects.get(title="geotagged cover")
    with storage.open(new_image.file.name) as stored, PILImage.open(stored) as stored_image:
        assert not has_gps(stored_image)
        assert stored_image.size == (64, 48)
    assert Blog.objects.get(pk=blog.pk).cover_image_id == new_image.pk


def test_failed_geotagged_import_removes_the_sanitized_upload(blog, tmp_path, storage, monkeypatch):
    path = tmp_path / "geotagged.jpg"
    _jpeg_with_gps(path)
    before = stored_names(storage)
    monkeypatch.setattr(Blog, "save_revision", lambda self, *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(RuntimeError):
        run(path)

    assert stored_names(storage) == before


def test_storage_save_is_restored_after_the_command(blog, new_cover_path, storage):
    save_before = storage.save

    run(new_cover_path)

    assert storage.save == save_before
    assert "save" not in vars(storage)


def test_recorder_wraps_and_restores_the_lazy_default_storage():
    # Production uses Django's lazily configured default storage object.
    names: list[str] = []

    with cover_command._record_saved_names(default_storage, names):
        saved = default_storage.save("cover-recorder/probe.txt", ContentFile(b"probe"))
    try:
        assert names == [saved]
        assert "save" not in vars(default_storage._wrapped)
        default_storage.save("cover-recorder/other.txt", ContentFile(b"later"))
        assert names == [saved]
    finally:
        default_storage.delete(saved)
        default_storage.delete("cover-recorder/other.txt")
