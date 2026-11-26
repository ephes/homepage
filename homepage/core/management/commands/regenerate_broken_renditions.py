from dataclasses import dataclass, field
from functools import partial
from itertools import chain
from pathlib import Path
from shlex import quote
from uuid import uuid4

from cast.models import Blog, Gallery, Post
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, router, transaction
from django.db.models import Prefetch
from wagtail.images import get_image_model


@dataclass
class RepairResult:
    """What happened to the renditions that were looked at."""

    regenerated: list = field(default_factory=list)
    # (rendition pk, stored file name, reason) for renditions whose database row was left as it was
    unknown: list = field(default_factory=list)
    failed: list = field(default_factory=list)
    # (database alias, rendition pk, replacement file name, reason)
    cache_pending: list = field(default_factory=list)

    def extend(self, other: "RepairResult") -> None:
        self.regenerated.extend(other.regenerated)
        self.unknown.extend(other.unknown)
        self.failed.extend(other.failed)
        self.cache_pending.extend(other.cache_pending)

    @property
    def incomplete(self) -> bool:
        return bool(self.unknown or self.failed or self.cache_pending)


@dataclass
class RepairCounts:
    regenerated: int = 0
    unknown: int = 0
    failed: int = 0
    cache_pending: int = 0

    def add(self, other: "RepairCounts") -> None:
        self.regenerated += other.regenerated
        self.unknown += other.unknown
        self.failed += other.failed
        self.cache_pending += other.cache_pending


def _purge_repaired_rendition(rendition, alias, result: RepairResult) -> None:
    try:
        rendition.purge_from_cache()
    except Exception as error:  # noqa: BLE001 - cache failure cannot undo a committed repair
        result.cache_pending.append((alias, rendition.pk, rendition.file.name, repr(error)[:300]))


def _repair_alias(rendition_model, *, instance=None):
    alias = (
        router.db_for_write(rendition_model)
        if instance is None
        else router.db_for_write(rendition_model, instance=instance)
    )
    if alias not in connections:
        raise CommandError(f"Unknown rendition writer database alias: {alias!r}")
    if instance is not None and instance._state.db != alias:
        raise CommandError(f"Rendition repair requires the source to be loaded from writer database {alias!r}")
    if not transaction.get_autocommit(using=alias):
        raise CommandError(f"Rendition repair requires autocommit on database {alias!r}; run it outside a transaction")
    return alias


def regenerate_renditions_for_image(image) -> RepairResult:
    """
    Regenerate the renditions of an image whose file is definitely missing from storage.

    Only a clear "does not exist" answer from the storage backend counts as missing.
    If the storage cannot say (throttling, an outage, denied access, ...) the rendition
    is reported as unknown and left alone. A missing rendition keeps its database row:
    the new file is generated and verified in storage before attachment in a transaction.
    Failed saves retain the old row and compensate only owned, unreferenced output.
    Repair requires autocommit on the rendition database so attachment commits
    independently. Cache invalidation follows that commit.
    """
    alias = _repair_alias(image.renditions.model, instance=image)
    result = RepairResult()
    for rendition in image.renditions.using(alias):
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
                expected_size = new_file.size
                rendition.file.save(filename, new_file, save=False)
                allocated_name = rendition.file.name
                owned_output = allocated_name == expected_name and allocated_name != stored_name
            if not storage.exists(allocated_name):
                raise FileNotFoundError(f"Published repair is missing: {allocated_name}")
            try:
                published_size = storage.size(allocated_name)
            except NotImplementedError:
                pass  # This backend can confirm existence but does not expose sizes.
            else:
                if published_size != expected_size:
                    raise OSError(f"Published repair size is {published_size} bytes, expected {expected_size}")
            # Roll back even a save hook that writes the row and then raises. Cleanup queries
            # run after the transaction exits, so a database failure cannot poison them.
            with transaction.atomic(using=alias, durable=True):
                current = (
                    type(rendition)
                    .objects.using(alias)
                    .select_related("image")
                    .select_for_update(of=("self",))
                    .get(pk=rendition.pk)
                )
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
                current.save(using=alias, update_fields=["file", "width", "height"])
                transaction.on_commit(partial(_purge_repaired_rendition, current, alias, result), using=alias)
                rendition = current
        except Exception as error:  # noqa: BLE001 - report and keep going with the other renditions
            reason = f"{failure_context}: {error!r}"
            if allocated_name:
                if not owned_output:
                    reason += f"; retained {allocated_name!r}: storage changed the name; ownership is uncertain"
                else:
                    try:
                        referenced = type(rendition).objects.using(alias).filter(file=allocated_name).exists()
                        if not referenced:
                            storage.delete(allocated_name)
                    except Exception as cleanup_error:  # noqa: BLE001 - preserve the primary failure
                        reason += f"; cleanup failed for {allocated_name!r}: {cleanup_error!r}"
            failures.append((rendition.pk, stored_name, reason))
            continue
        result.regenerated.append(rendition)
    return result


def regenerate_renditions_for_post(post, *, seen_images: set | None = None) -> RepairResult:
    """Repair each image once, optionally sharing invocation-wide identities."""
    alias = _repair_alias(get_image_model().get_rendition_model(), instance=post)
    if seen_images is None:
        seen_images = set()
    result = RepairResult()

    def repair_once(image):
        identity = (image._state.db, image.pk)
        if identity in seen_images:
            return
        # Unknown/failed/cache-pending outcomes also belong to this one attempt.
        result.extend(regenerate_renditions_for_image(image))
        seen_images.add(identity)

    for image in post.images.db_manager(alias).all():
        repair_once(image)
    for gallery in post.galleries.db_manager(alias).all():
        for image in gallery.images.db_manager(alias).all():
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
            help="Retry cache invalidation of current rows on --database; never generate files.",
        )
        parser.add_argument(
            "--database",
            metavar="ALIAS",
            help="Database alias reported by repair (required for --retry-cache-purge).",
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
        alias = options["database"]
        if options["retry_cache_purge"]:
            if options["blog_slugs"] or limit is not None:
                raise CommandError("--retry-cache-purge is used without blog slugs or --limit")
            if alias is None:
                raise CommandError("--retry-cache-purge requires the reported --database alias")
            if alias not in connections:
                raise CommandError(f"Unknown database alias: {alias!r}")
            Rendition = get_image_model().get_rendition_model()
            renditions = Rendition.objects.using(alias).select_related("image")
            pending = []
            for pk in dict.fromkeys(options["retry_cache_purge"]):
                try:
                    rendition = renditions.get(pk=pk)
                except Rendition.DoesNotExist:
                    self.stderr.write(f"rendition {pk} on database {alias!r}: row no longer exists; skipped")
                    continue
                try:
                    rendition.purge_from_cache()
                except Exception as error:
                    pending.append(pk)
                    self.stderr.write(f"rendition {pk} on database {alias!r}: cache purge failed: {repr(error)[:300]}")
            if pending:
                ids = " ".join(map(str, pending))
                raise CommandError(f"Retry with --retry-cache-purge {ids} --database={quote(alias)}")
            self.stdout.write("Cache purge completed; no rendition files were generated.")
            return
        if alias is not None:
            raise CommandError("--database requires --retry-cache-purge")
        if not options["blog_slugs"]:
            raise CommandError("Provide blog slugs or --retry-cache-purge")
        image_model = get_image_model()
        alias = _repair_alias(image_model.get_rendition_model())
        blog_queryset = Blog.objects.using(alias)
        blogs = {}
        for slug in options["blog_slugs"]:
            try:
                blog = blog_queryset.get(slug=slug)
            except Blog.DoesNotExist as error:
                raise CommandError(f"Blog with slug {slug!r} does not exist; nothing was changed") from error

            except Blog.MultipleObjectsReturned as error:
                matches = blog_queryset.filter(slug=slug).values_list("pk", "url_path")
                candidates = ", ".join(f"page {pk} ({path})" for pk, path in matches)
                raise CommandError(
                    f"Blog slug {slug!r} is ambiguous: {candidates}. "
                    "Identify the intended blog in the Wagtail page tree and use a unique slug; nothing was changed."
                ) from error

            blogs.setdefault(blog.pk, blog)

        total = RepairCounts()
        seen_images = set()
        for blog in blogs.values():
            self.stdout.write(f"Blog: {blog.slug} {blog.title}")
            post_queryset = (
                Post.objects.using(alias)
                .descendant_of(blog)
                .order_by("-visible_date", "-pk")
                .prefetch_related(
                    Prefetch("images", queryset=image_model.objects.using(alias)),
                    Prefetch("galleries", queryset=Gallery.objects.using(alias)),
                    Prefetch("galleries__images", queryset=image_model.objects.using(alias)),
                )
            )
            if limit is not None:
                post_queryset = post_queryset[:limit]
            blog_counts = RepairCounts()
            post_count = 0
            for post in post_queryset.iterator(chunk_size=100):
                post_count += 1
                blog_counts.add(self._repair_and_report_post(post, seen_images))
            self.stdout.write(
                f"Blog {blog.slug}: checked {post_count} posts, regenerated {blog_counts.regenerated}, "
                f"unknown {blog_counts.unknown}, failed {blog_counts.failed}"
            )
            total.add(blog_counts)
        self.stdout.write(f"checked images: {len(seen_images)}")
        self.stdout.write(f"generated renditions: {total.regenerated}")
        if total.unknown or total.failed or total.cache_pending:
            raise CommandError(
                f"{total.unknown} renditions could not be checked and {total.failed} could not be "
                f"regenerated. They were left unchanged; rerun the command to retry. "
                f"{total.cache_pending} committed repairs have cache purge pending; "
                "use --retry-cache-purge with the reported IDs and --database alias."
            )

    def _repair_and_report_post(self, post, seen_images) -> RepairCounts:
        result = regenerate_renditions_for_post(post, seen_images=seen_images)
        counts = RepairCounts(
            len(result.regenerated), len(result.unknown), len(result.failed), len(result.cache_pending)
        )
        self.stdout.write(
            f"  post {post.pk} {post}: regenerated {counts.regenerated}, "
            f"unknown {counts.unknown}, failed {counts.failed}"
        )
        for pk, stored_name, reason in chain(result.unknown, result.failed):
            self.stderr.write(f"    rendition {pk} ({stored_name}) left unchanged: {reason}")
        for alias, pk, stored_name, reason in result.cache_pending:
            self.stderr.write(
                f"rendition {pk} ({stored_name}) repaired; cache purge pending: {reason}. "
                f"Retry with --retry-cache-purge {pk} --database={quote(alias)}"
            )
        return counts
