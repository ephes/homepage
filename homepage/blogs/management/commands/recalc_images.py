from django.core.management.base import BaseCommand

from ...models import BlogImage


class Command(BaseCommand):
    help = (
        'recalc resized images')

    def handle(self, *args, **options):
        for image in BlogImage.objects.all():
            orig = image.original
            print(image.portrait, orig.name, orig.size, orig.width, orig.height)
            image.create_resized_images()
            image.save(resize=False)
            # break
