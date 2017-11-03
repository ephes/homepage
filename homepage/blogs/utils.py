import os

from imagekit.models import ImageSpecField
from imagekit.processors import Thumbnail

class ImageSpecField2(ImageSpecField):
    pass


class Thumbnail2(Thumbnail):
    def process(self, img):
        print('foo bar baz asldfkjasldfkjasldfkja ____________________________')
        result = super().process(img)
        return result


def storage_walk_paths(storage, cur_dir=''):
    dirs, files = storage.listdir(cur_dir)
    for directory in dirs:
        new_dir = os.path.join(cur_dir, directory)
        for path in storage_walk_paths(storage, cur_dir=new_dir):
            yield path
    for fname in files:
        path = os.path.join(cur_dir, fname)
        yield path
