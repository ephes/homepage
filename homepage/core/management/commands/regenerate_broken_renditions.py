from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from cast.models import Blog, Post
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


@dataclass
class RepairResult:
    """What happened to the renditions that were looked at."""

    regenerated: list = field(default_factory=list)
    # (rendition pk, stored file name, reason) for renditions whose database row was left as it was
    unknown: list = field(default_factory=list)
    failed: list = field(default_factory=list)
    cache_pending: list = field(default_factory=list)

    def extend(self, other: "RepairResult") -> None:
        self.regenerated.extend(other.regenerated)
        self.unknown.extend(other.unknown)
        self.failed.extend(other.failed)
        self.cache_pending.extend(other.cache_pending)

    @property
    def incomplete(self) -> bool:
        return bool(self.unknown or self.failed or self.cache_pending)


def regenerate_renditions_for_image(image) -> RepairResult:
    """
    Regenerate the renditions of an image whose file is definitely missing from storage.

    Only a clear "does not exist" answer from the storage backend counts as missing.
    If the storage cannot say (throttling, an outage, denied access, ...) the rendition
    is reported as unknown and left alone. A missing rendition keeps its database row:
    the new file is generated first and then attached inside a database savepoint.
    Failed saves retain the old row and compensate only owned, unreferenced output.
    """
    result = RepairResult()
    for rendition in image.renditions.all():
        stored_name = rendition.file.name
        observed = (
            stored_name,
            rendition.image_id,
            rendition.filter_spec,
            rendition.focal_point_key,
            rendition.width,
            rendition.height,
        )
        try:
            exists = rendition.file.storage.exists(stored_name)
        except Exception as error:  # noqa: BLE001 - any storage error means "we do not know"
            result.unknown.append((rendition.pk, stored_name, f"storage check failed: {error!r}"))
            continue
        if exists:
            continue
        allocated_name = None
        owned_output = False
        storage = rendition.file.storage
        failures = result.failed
        failure_context = "regeneration failed"
        try:
            # A distinct name keeps the missing row's old path and existing objects intact.
            with image.generate_rendition_file(rendition.filter) as new_file:
                rendition.file = new_file
                filename = f"repair-{uuid4().hex}{Path(new_file.name).suffix}"
                expected_name = rendition.file.field.generate_filename(rendition, filename)
                if storage.exists(expected_name):
                    raise FileExistsError(f"Repair destination already exists: {expected_name}")
                rendition.file.save(filename, new_file, save=False)
                allocated_name = rendition.file.name
                owned_output = allocated_name == expected_name and allocated_name != stored_name
            # Roll back even a save hook that writes the row and then raises. Cleanup queries
            # run after the savepoint exits, so a database failure cannot poison them.
            with transaction.atomic(using=rendition._state.db):
                current = type(rendition).objects.using(rendition._state.db).select_for_update().get(pk=rendition.pk)
                identity = (
                    current.file.name,
                    current.image_id,
                    current.filter_spec,
                    current.focal_point_key,
                    current.width,
                    current.height,
                )
                if identity != observed:
                    raise RuntimeError("Rendition changed during regeneration; current row was left unchanged")
                try:
                    original_exists = storage.exists(stored_name)
                except Exception:  # noqa: BLE001 - an inconclusive check must refuse attachment
                    failures = result.unknown
                    failure_context = "storage recheck failed"
                    raise
                if original_exists:
                    raise RuntimeError("Original rendition file reappeared during regeneration")
                current.file.name = rendition.file.name
                current.width, current.height = rendition.width, rendition.height
                current.save(update_fields=["file", "width", "height"])
                rendition = current
        except Exception as error:  # noqa: BLE001 - report and keep going with the other renditions
            reason = f"{failure_context}: {error!r}"
            if allocated_name:
                if not owned_output:
                    reason += f"; retained {allocated_name!r}: storage changed the name; ownership is uncertain"
                else:
                    try:
                        referenced = (
                            type(rendition).objects.using(rendition._state.db).filter(file=allocated_name).exists()
                        )
                        if not referenced:
                            storage.delete(allocated_name)
                    except Exception as cleanup_error:  # noqa: BLE001 - preserve the primary failure
                        reason += f"; cleanup failed for {allocated_name!r}: {cleanup_error!r}"
            failures.append((rendition.pk, stored_name, reason))
            continue
        result.regenerated.append(rendition)
        try:
            rendition.purge_from_cache()
        except Exception as error:  # the replacement is already committed
            result.cache_pending.append((rendition.pk, rendition.file.name, repr(error)[:300]))
    return result


def regenerate_renditions_for_post(post, *, seen_images: set | None = None) -> RepairResult:
    """Repair each image once, optionally sharing invocation-wide identities."""
    if seen_images is None:
        seen_images = set()
    result = RepairResult()

    def repair_once(image):
        identity = (image._state.db, image.pk)
        if identity in seen_images:
            return
        # Unknown/failed/cache-pending outcomes also belong to this one attempt.
        seen_images.add(identity)
        result.extend(regenerate_renditions_for_image(image))

    for image in post.images.all():
        repair_once(image)
    for gallery in post.galleries.all():
        for image in gallery.images.all():
            repair_once(image)
    return result


class Command(BaseCommand):
    help = (
        "When the renditions were deleted from s3 - regenerate the ones that are missing. "
        "Provide slugs for blogs where renditions should be regenerated. All posts of each "
        "blog are checked unless --limit is given. Renditions whose state cannot be "
        "determined are never deleted or replaced. Shared images are checked once per invocation."
    )

    def add_arguments(self, parser):
        parser.add_argument("blog_slugs", nargs="*", type=str)
        parser.add_argument(
            "--retry-cache-purge",
            nargs="+",
            type=int,
            metavar="RENDITION_ID",
            help="Retry cache invalidation of current rows only; never generate files.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Only check the newest LIMIT posts of each blog (default: all posts).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit is not None and limit < 1:
            raise CommandError("--limit must be a positive number")
        if options["retry_cache_purge"]:
            if options["blog_slugs"] or limit is not None:
                raise CommandError("--retry-cache-purge is used without blog slugs or --limit")
            from wagtail.images import get_image_model

            Rendition = get_image_model().get_rendition_model()
            pending = []
            for pk in dict.fromkeys(options["retry_cache_purge"]):
                try:
                    Rendition.objects.get(pk=pk).purge_from_cache()
                except Exception as error:
                    pending.append(pk)
                    self.stderr.write(f"rendition {pk}: cache purge failed: {repr(error)[:300]}")
            if pending:
                raise CommandError(f"Retry cache purge for rendition IDs: {pending}")
            self.stdout.write("Cache purge completed; no rendition files were generated.")
            return
        if not options["blog_slugs"]:
            raise CommandError("Provide blog slugs or --retry-cache-purge")
        blogs = []
        for slug in options["blog_slugs"]:
            try:
                blogs.append(Blog.objects.get(slug=slug))
            except Blog.DoesNotExist as error:
                raise CommandError(f"Blog with slug {slug!r} does not exist; nothing was changed") from error

        total = RepairResult()
        seen_images = set()
        for blog in blogs:
            self.stdout.write(f"Blog: {blog.slug} {blog.title}")
            post_queryset = (
                Post.objects.descendant_of(blog)
                .order_by("-visible_date", "-pk")
                .prefetch_related("images", "galleries__images")
            )
            if limit is not None:
                post_queryset = post_queryset[:limit]
            blog_result = RepairResult()
            post_count = 0
            for post in post_queryset.iterator(chunk_size=100):
                post_count += 1
                post_result = regenerate_renditions_for_post(post, seen_images=seen_images)
                blog_result.extend(post_result)
                self.stdout.write(
                    f"  post {post.pk} {post}: regenerated {len(post_result.regenerated)}, "
                    f"unknown {len(post_result.unknown)}, failed {len(post_result.failed)}"
                )
                for pk, stored_name, reason in [*post_result.unknown, *post_result.failed]:
                    self.stderr.write(f"    rendition {pk} ({stored_name}) left unchanged: {reason}")
            self.stdout.write(
                f"Blog {blog.slug}: checked {post_count} posts, regenerated {len(blog_result.regenerated)}, "
                f"unknown {len(blog_result.unknown)}, failed {len(blog_result.failed)}"
            )
            for pk, stored_name, reason in blog_result.cache_pending:
                self.stderr.write(
                    f"rendition {pk} ({stored_name}) repaired; cache purge pending: {reason}. "
                    f"Retry with --retry-cache-purge {pk}"
                )
            total.extend(blog_result)
        self.stdout.write(f"checked images: {len(seen_images)}")
        self.stdout.write(f"generated renditions: {len(total.regenerated)}")
        if total.incomplete:
            raise CommandError(
                f"{len(total.unknown)} renditions could not be checked and {len(total.failed)} could not be "
                f"regenerated. They were left unchanged; rerun the command to retry. "
                f"{len(total.cache_pending)} committed repairs have cache purge pending; "
                "use --retry-cache-purge with the reported IDs."
            )
