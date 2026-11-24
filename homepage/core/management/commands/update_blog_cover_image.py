import os
import stat
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryFile
from uuid import uuid4

from cast.models import Blog
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError, router, transaction
from django.db.models.signals import pre_save
from wagtail.images import get_image_model
from wagtail.models import Page

SOCIAL_COVER_RENDITION_SPEC = "fill-1200x630|format-jpeg|jpegquality-75"
DEFAULT_MAX_SOURCE_SIZE = 60 * 1024 * 1024


def _open_nonblocking(path, flags):
    return os.open(path, flags | os.O_NONBLOCK)


def _stage_source(path, staged):
    limit = settings.WAGTAILIMAGES_MAX_UPLOAD_SIZE
    if limit is None:
        limit = DEFAULT_MAX_SOURCE_SIZE

    try:
        with open(path, "rb", opener=_open_nonblocking) as source:
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise CommandError(f"Image path is not a regular file: {path}")
            if before.st_size == 0:
                raise CommandError(f"Image file is empty: {path}")
            if before.st_size > limit:
                raise CommandError(f"Image file exceeds the {limit}-byte limit: {path}")

            remaining = before.st_size
            while remaining:
                chunk = source.read(min(remaining, 1024 * 1024))
                if not chunk:
                    raise CommandError(f"Image file changed while being read: {path}")
                staged.write(chunk)
                remaining -= len(chunk)
            after = os.fstat(source.fileno())
            if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            ):
                raise CommandError(f"Image file changed while being read: {path}")
    except FileNotFoundError as exc:
        raise CommandError(f"Image file does not exist: {path}") from exc
    except OSError as exc:
        raise CommandError(f"Could not stage image file {path}: {exc}") from exc
    staged.seek(0)


class _CoverUploadStorage:
    """Record backend receipts for one operation-owned file field."""

    def __init__(self, backend):
        self.backend = backend
        self.saved_names: list[tuple[str, bool]] = []
        # Only this backend guarantees exclusive creation even during a naming race.
        self.exclusive = False
        if type(backend) is FileSystemStorage:
            _, args, kwargs = backend.deconstruct()
            self.exclusive = not kwargs.get("allow_overwrite", args[4] if len(args) > 4 else False)

    def save(self, name, content, max_length=None):
        path = Path(name)
        allocated = str(path.with_name(f"cover-{uuid4().hex}{path.suffix}"))
        saved_name = self.backend.save(allocated, content, max_length=max_length)
        self.saved_names.append((saved_name, self.exclusive))
        return saved_name

    def __getattr__(self, name):
        return getattr(self.backend, name)


@contextmanager
def _record_cover_uploads(image, uploads):
    Image = type(image)
    Rendition = Image.get_rendition_model()
    attached = []

    def attach_recorder(sender, instance, **kwargs):
        if instance is not image:
            if sender is not Rendition or instance.image_id != image.pk or instance.image is not image:
                return
        # Capture the final FieldFile after django-cast's GPS sanitization receiver
        # has had a chance to replace the original upload.
        file = instance.file
        recorder = _CoverUploadStorage(file.storage)
        uploads.append(recorder)
        attached.append((file, recorder.backend))
        file.storage = recorder

    pre_save.connect(attach_recorder, sender=Image)
    pre_save.connect(attach_recorder, sender=Rendition)
    try:
        yield
    finally:
        pre_save.disconnect(attach_recorder, sender=Image)
        pre_save.disconnect(attach_recorder, sender=Rendition)
        for file, backend in reversed(attached):
            file.storage = backend


class Command(BaseCommand):
    help = (
        "Import an image file and set it as the cover image for a blog page. "
        "If saving the image or the blog page fails, the database changes are rolled back "
        "and exclusively owned uploads are removed again. Uncertain storage names are reported "
        "for recovery; existing files are never deleted. A post-commit callback failure retains "
        "the committed cover and reports its image/revision IDs; do not repeat publication."
    )

    def add_arguments(self, parser):
        parser.add_argument("image_path", type=Path)
        parser.add_argument("--blog-slug", default="ephes_blog")
        parser.add_argument("--title", default="wersdoerfer-de-blogs-ephes_blog")
        parser.add_argument("--alt-text", default="Just a screenshot of the blog overview page.")
        parser.add_argument(
            "--user",
            default="jochen",
            help="Username to attribute the Wagtail revision and publish action to.",
        )
        parser.add_argument(
            "--no-publish",
            action="store_true",
            help="Save the blog page without publishing a new revision.",
        )

    def handle(self, *args, **options):
        image_path = options["image_path"]
        with TemporaryFile() as staged:
            _stage_source(image_path, staged)
            self._publish(File(staged, name=image_path.name), options)

    def _publish(self, source, options):
        alias = router.db_for_write(Blog)
        blog_slug = options["blog_slug"]
        try:
            blog = Blog.objects.using(alias).get(slug=blog_slug)
        except Blog.DoesNotExist as exc:
            raise CommandError(f"No blog found with slug={blog_slug!r}") from exc
        except Blog.MultipleObjectsReturned as exc:
            raise CommandError(f"Multiple blogs found with slug={blog_slug!r}") from exc

        expected_revisions = (blog.latest_revision_id, blog.live_revision_id)
        username = options["user"]
        User = get_user_model()
        try:
            user = User.objects.using(alias).get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"No user found with username={username!r}") from exc
        except User.MultipleObjectsReturned as exc:
            raise CommandError(f"Multiple users found with username={username!r}") from exc

        Image = get_image_model()
        uploads = []

        committed = False
        revision_id = None

        def record_commit():
            nonlocal committed
            committed = True

        try:
            # Own the commit boundary. Register before any model/signal callbacks:
            # they can raise after the database has committed successfully.
            with transaction.atomic(using=alias, durable=True):
                transaction.on_commit(record_commit, using=alias)
                image = Image(title=options["title"], file=source)
                with _record_cover_uploads(image, uploads):
                    image.save(using=alias)
                    # A required rendition is part of the publication precondition.
                    rendition = image.get_rendition(SOCIAL_COVER_RENDITION_SPEC)
                rendition_url = rendition.url
                with self._current_blog(blog.pk, alias) as current:
                    if not options["no_publish"] and (
                        (current.latest_revision_id, current.live_revision_id) != expected_revisions
                        or current.has_unpublished_changes
                    ):
                        raise CommandError("Blog changed or has an editor draft; rerun after reviewing it.")
                    current.cover_image = image
                    current.cover_alt_text = options["alt_text"]
                    if options["no_publish"]:
                        current.save(using=alias, update_fields=["cover_image", "cover_alt_text"])
                    else:
                        revision = current.save_revision(user=user)
                        revision_id = revision.pk
                        revision.publish(user=user)
        except BaseException:
            if committed:
                self.stderr.write(
                    f"Committed blog {blog.pk}: image {image.pk}, revision {revision_id}; "
                    "post-commit callbacks failed or remain pending. Cover files retained. "
                    "Inspect the committed page and callback/cache state. Do not rerun the import or republish."
                )
            else:
                for upload in uploads:
                    self._remove_saved_files(upload.backend, upload.saved_names)
            raise

        message = "Updated {} cover image to image {}; social rendition: {}".format(
            blog.slug,
            image.pk,
            rendition_url,
        )
        self.stdout.write(self.style.SUCCESS(message))

    @contextmanager
    def _current_blog(self, pk, alias):
        # Match the converter's NOWAIT policy: editors can lock page/revision rows
        # in either order, so waiting here while holding another row could deadlock.
        try:
            with transaction.atomic(using=alias):
                list(
                    Page.objects.using(alias)
                    .get(pk=pk)
                    .revisions.using(alias)
                    .select_for_update(nowait=True, no_key=True)
                    .order_by("pk")
                    .values_list("pk", flat=True)
                )
                Page.objects.using(alias).select_for_update(nowait=True, no_key=True).get(pk=pk)
                yield Blog.objects.using(alias).select_for_update(nowait=True, no_key=True).get(pk=pk)
        except OperationalError as error:
            if getattr(error.__cause__, "sqlstate", None) != "55P03":
                raise
            raise CommandError("Blog changed or is being edited; rerun after reviewing it.") from error
        except (Page.DoesNotExist, Blog.DoesNotExist) as error:
            raise CommandError("Blog was removed during upload; nothing was published.") from error

    def _remove_saved_files(self, storage, saved_names):
        """Delete the files this run stored; report any that could not be removed."""
        for name, owned in saved_names:
            if not owned:
                self.stderr.write(
                    f"Retained unreferenced upload {name!r}: storage does not guarantee exclusive creation."
                )
                continue
            try:
                storage.delete(name)
            except Exception as exc:  # the original failure must stay the reported error
                self.stderr.write(
                    self.style.ERROR(f"Could not remove the unreferenced upload {name!r} from storage: {exc}")
                )
            else:
                self.stderr.write(f"Removed the unreferenced upload {name!r} from storage.")
