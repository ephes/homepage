from dataclasses import dataclass, field

from cast.models import Blog, Post
from django.core.management.base import BaseCommand, CommandError


@dataclass
class RepairResult:
    """What happened to the renditions that were looked at."""

    regenerated: list = field(default_factory=list)
    # (rendition pk, stored file name, reason) for renditions whose database row was left as it was
    unknown: list = field(default_factory=list)
    failed: list = field(default_factory=list)

    def extend(self, other: "RepairResult") -> None:
        self.regenerated.extend(other.regenerated)
        self.unknown.extend(other.unknown)
        self.failed.extend(other.failed)

    @property
    def incomplete(self) -> bool:
        return bool(self.unknown or self.failed)


def regenerate_renditions_for_image(image) -> RepairResult:
    """
    Regenerate the renditions of an image whose file is definitely missing from storage.

    Only a clear "does not exist" answer from the storage backend counts as missing.
    If the storage cannot say (throttling, an outage, denied access, ...) the rendition
    is reported as unknown and left alone. A missing rendition keeps its database row:
    the new file is generated first and then attached to the existing row, so a failed
    regeneration changes nothing and can be retried.
    """
    result = RepairResult()
    for rendition in image.renditions.all():
        stored_name = rendition.file.name
        try:
            exists = rendition.file.storage.exists(stored_name)
        except Exception as error:  # noqa: BLE001 - any storage error means "we do not know"
            result.unknown.append((rendition.pk, stored_name, f"storage check failed: {error!r}"))
            continue
        if exists:
            continue
        try:
            # Generate first: the row is only touched once a replacement file exists.
            new_file = image.generate_rendition_file(rendition.filter)
            rendition.file = new_file
            rendition.save()
        except Exception as error:  # noqa: BLE001 - report and keep going with the other renditions
            result.failed.append((rendition.pk, stored_name, f"regeneration failed: {error!r}"))
            continue
        rendition.purge_from_cache()
        result.regenerated.append(rendition)
    return result


def regenerate_renditions_for_post(post) -> RepairResult:
    """Repair the renditions of all images of a post, including its gallery images."""
    result = RepairResult()
    for image in post.images.all():
        result.extend(regenerate_renditions_for_image(image))
    for gallery in post.galleries.all():
        for image in gallery.images.all():
            result.extend(regenerate_renditions_for_image(image))
    return result


class Command(BaseCommand):
    help = (
        "When the renditions were deleted from s3 - regenerate the ones that are missing. "
        "Provide slugs for blogs where renditions should be regenerated. All posts of each "
        "blog are checked unless --limit is given. Renditions whose state cannot be "
        "determined are never deleted or replaced."
    )

    def add_arguments(self, parser):
        parser.add_argument("blog_slugs", nargs="+", type=str)
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
        blogs = []
        for slug in options["blog_slugs"]:
            try:
                blogs.append(Blog.objects.get(slug=slug))
            except Blog.DoesNotExist as error:
                raise CommandError(f"Blog with slug {slug!r} does not exist; nothing was changed") from error

        total = RepairResult()
        for blog in blogs:
            self.stdout.write(f"Blog: {blog.slug} {blog.title}")
            post_queryset = Post.objects.descendant_of(blog).order_by("-visible_date", "-pk")
            if limit is not None:
                post_queryset = post_queryset[:limit]
            blog_result = RepairResult()
            post_count = 0
            for post in post_queryset.iterator(chunk_size=100):
                post_count += 1
                post_result = regenerate_renditions_for_post(post)
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
            total.extend(blog_result)
        self.stdout.write(f"generated renditions: {len(total.regenerated)}")
        if total.incomplete:
            raise CommandError(
                f"{len(total.unknown)} renditions could not be checked and {len(total.failed)} could not be "
                "regenerated. They were left unchanged; rerun the command to retry."
            )
