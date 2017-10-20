import logging

from django.core.management.base import BaseCommand

from ...models import BlogPost

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'add links between blogpost and media objects'

    def handle(self, *args, **options):
        blogposts = list(BlogPost.objects.all().order_by('-created'))
        for bp in blogposts:
            logger.info('-----------------')
            bp.add_missing_media_objects()
