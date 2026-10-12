from pathlib import Path

from cast.models import Blog
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.images import get_image_model

SOCIAL_COVER_RENDITION_SPEC = "fill-1200x630|format-jpeg|jpegquality-75"


class Command(BaseCommand):
    help = (
        "Import an image file and set it as the cover image for a blog page. "
        "If saving the image or the blog page fails, the database changes are rolled back "
        "and the newly uploaded file is removed again; existing files are never deleted."
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
        file_field = Image._meta.get_field("file")
        storage = file_field.storage
        # Storage names returned by this run's own storage.save() calls. Only
        # these may be removed again, and only when the name was free before:
        # a requested or reused name could belong to an object that existed
        # before this run.
        saved_names: list[str] = []

        try:
            # The image row and the blog change belong together: either the blog
            # points at the new image, or neither row changed.
            with transaction.atomic():
                image = Image(title=options["title"])
                with image_path.open("rb") as image_file:
                    requested_name = file_field.generate_filename(image, image_path.name)
                    # A storage that overwrites returns the requested name even
                    # when an object with that name was already there.
                    name_was_taken = storage.exists(requested_name)
                    saved_name = storage.save(
                        requested_name,
                        File(image_file, name=image_path.name),
                        max_length=file_field.max_length,
                    )
                if not (name_was_taken and saved_name == requested_name):
                    saved_names.append(saved_name)
                image.file = saved_name
                file_field.update_dimension_fields(image, force=True)
                image.save()

                blog.cover_image = image
                blog.cover_alt_text = options["alt_text"]
                if options["no_publish"]:
                    blog.save()
                else:
                    blog.save_revision(user=user).publish(user=user)
        except BaseException:
            # The database changes were rolled back, so the uploaded file is not
            # referenced by anything. Storage is not transactional: remove it.
            self._remove_saved_files(storage, saved_names)
            raise

        rendition = image.get_rendition(SOCIAL_COVER_RENDITION_SPEC)
        message = "Updated {} cover image to image {}; social rendition: {}".format(
            blog.slug,
            image.pk,
            rendition.url,
        )
        self.stdout.write(self.style.SUCCESS(message))

    def _remove_saved_files(self, storage, saved_names):
        """Delete the files this run stored; report any that could not be removed."""
        for name in saved_names:
            try:
                storage.delete(name)
            except Exception as exc:  # the original failure must stay the reported error
                self.stderr.write(
                    self.style.ERROR(f"Could not remove the unreferenced upload {name!r} from storage: {exc}")
                )
            else:
                self.stderr.write(f"Removed the unreferenced upload {name!r} from storage.")
