from pathlib import Path

from cast.models import Blog
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from wagtail.images import get_image_model

SOCIAL_COVER_RENDITION_SPEC = "fill-1200x630|format-jpeg|jpegquality-75"


class Command(BaseCommand):
    help = "Import an image file and set it as the cover image for a blog page."

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
        if not image_path.exists():
            raise CommandError(f"Image file does not exist: {image_path}")
        if not image_path.is_file():
            raise CommandError(f"Image path is not a file: {image_path}")

        blog_slug = options["blog_slug"]
        try:
            blog = Blog.objects.get(slug=blog_slug)
        except Blog.DoesNotExist as exc:
            raise CommandError(f"No blog found with slug={blog_slug!r}") from exc
        except Blog.MultipleObjectsReturned as exc:
            raise CommandError(f"Multiple blogs found with slug={blog_slug!r}") from exc

        username = options["user"]
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"No user found with username={username!r}") from exc
        except User.MultipleObjectsReturned as exc:
            raise CommandError(f"Multiple users found with username={username!r}") from exc

        Image = get_image_model()

        with image_path.open("rb") as image_file:
            image = Image(
                title=options["title"],
                file=File(image_file, name=image_path.name),
            )
            image.save()

        blog.cover_image = image
        blog.cover_alt_text = options["alt_text"]
        if options["no_publish"]:
            blog.save()
        else:
            blog.save_revision(user=user).publish(user=user)

        rendition = image.get_rendition(SOCIAL_COVER_RENDITION_SPEC)
        message = "Updated {} cover image to image {}; social rendition: {}".format(
            blog.slug,
            image.pk,
            rendition.url,
        )
        self.stdout.write(self.style.SUCCESS(message))
