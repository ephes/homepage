import os

from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.core.files.storage import get_storage_class

from django.conf import settings

from blogs.utils import storage_walk_paths


class Command(BaseCommand):
    help = (
        'replace paths on s3 with local versions - useful for'
        ' compressed videos for example')

    def add_arguments(self, parser):
        parser.add_argument('paths', nargs='+', type=str)

    def handle(self, *args, **options):
        s3 = get_storage_class('storages.backends.s3boto3.S3Boto3Storage')()
        for path in options['paths']:
            if default_storage.exists(path):
                if s3.exists(path):
                    s3.delete(path)
                with default_storage.open(path, 'rb') as in_f:
                    s3.save(path, in_f)
