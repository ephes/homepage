from django.core.management.base import BaseCommand

from ...models import BlogImage


class Command(BaseCommand):
    help = (
        'show media files which are in the filesystem (s3, locale), '
        'but not in database and optionally delete them')

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            dest='delete',
            default=False,
            help='Delete stale files instead of only showing them',
        )

    def handle(self, *args, **options):
        for image in BlogImage.objects.all():
            orig = image.original
            print(image.portrait, orig.name, orig.size, orig.width, orig.height)
            image.create_resized_images()
            image.save(resize=False)
            # break
