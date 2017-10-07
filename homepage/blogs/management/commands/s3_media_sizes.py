import os

from django.core.management.base import BaseCommand
from django.core.files.storage import get_storage_class

class Command(BaseCommand):
    help = 'shows size of media on s3'

    def walk(self, storage, cur_dir=''):
        dirs, files = storage.listdir(cur_dir)
        for directory in dirs:
            new_dir = os.path.join(cur_dir, directory)
            for path in self.walk(storage, cur_dir=new_dir):
                yield path
        for fname in files:
            path = os.path.join(cur_dir, fname)
            yield path

    def show_usage(self, paths):
        video_endings = {'mov', 'mp4'}
        image_endings = {'jpg', 'jpeg'}
        image, video, misc = 0, 0, 0
        for path, size in paths.items():
            ending = path.split('.')[-1].lower()
            if ending in video_endings:
                video += size
            elif ending in image_endings:
                image += size
            else:
                misc += size
        unit = 2 ** 20  # MB
        print('video usage: {}'.format(video / unit))
        print('image usage: {}'.format(image / unit))
        print('misc  usage: {}'.format(misc / unit))
        print('total usage: {}'.format(sum(paths.values()) / unit))

    def handle(self, *args, **options):
        s3 = get_storage_class('storages.backends.s3boto3.S3Boto3Storage')()
        paths = {}
        for path in self.walk(s3):
            size = s3.size(path)
            paths[path] = size
            print(path, size / 2 ** 20)
        self.show_usage(paths)
