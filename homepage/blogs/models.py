import os
import re
import logging
import tempfile

from subprocess import check_output

from collections import defaultdict

from io import BytesIO

from django.db import models
from django.core.files import File
from django.core.urlresolvers import reverse

from ckeditor_uploader.fields import RichTextUploadingField

from imagekit.models import ImageSpecField
from imagekit.processors import Thumbnail

from model_utils.models import TimeStampedModel

from slugify import slugify

from PIL import Image as PILImage
from PIL import ExifTags

from ..users.models import User

logger = logging.getLogger(__name__)


class Blog(TimeStampedModel):
    user = models.ForeignKey(User)
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=500)
    slug = models.SlugField(max_length=50)

    def __str__(self):
        return self.title


class BlogImage(TimeStampedModel):
    user = models.ForeignKey(User)
    portrait = models.BooleanField(default=False)

    original = models.ImageField(
        upload_to='blogs_images/originals',
        height_field='original_height',
        width_field='original_width')
    original_height = models.PositiveIntegerField(blank=True, null=True)
    original_width = models.PositiveIntegerField(blank=True, null=True)

    img_full = ImageSpecField(source='original', processors=[],
                              format='JPEG', options={'quality': 60})

    img_xl = ImageSpecField(source='original',
                            processors=[Thumbnail(2200, 2200, crop=False)],
                            format='JPEG',
                            options={'quality': 60})

    img_lg = ImageSpecField(source='original',
                            processors=[Thumbnail(1100, 1100, crop=False)],
                            format='JPEG',
                            options={'quality': 60})

    img_md = ImageSpecField(source='original',
                            processors=[Thumbnail(768, 768, crop=False)],
                            format='JPEG',
                            options={'quality': 60})

    img_sm = ImageSpecField(source='original',
                            processors=[Thumbnail(500, 500, crop=False)],
                            format='JPEG',
                            options={'quality': 60})

    img_xs = ImageSpecField(source='original',
                            processors=[Thumbnail(300, 300, crop=False)],
                            format='JPEG',
                            options={'quality': 60})

    sizes = [
        (None, 'img_full'),
        (2200, 'img_xl'),
        (1100, 'img_lg'),
        (768, 'img_md'),
        (500, 'img_sm'),
        (300, 'img_xs'),
    ]

    blogpost_context_key = 'image'

    def get_all_paths(self):
        paths = set()
        paths.add(self.original.name)
        for size, attr_name in self.sizes:
            paths.add(getattr(self, attr_name).name)
        return paths

    def get_exif_tags(self, image):
        exif = {}
        for k, v in image._getexif().items():
            if k in ExifTags.TAGS:
                exif[ExifTags.TAGS[k]] = v
        return exif

    def adjust_orientation(self, exif, image):
        rotate_lookup = {3: 180, 6: 270, 8: 90}
        orientation = exif.get('Orientation')
        rotate = rotate_lookup.get(orientation)

        if rotate is not None:
            return image.rotate(rotate, expand=True)
        else:
            return image

    def create_resized_images(self):
        self.original.open()
        original = PILImage.open(self.original)
        original_name = os.path.basename(self.original.name)

        try:
            exif = self.get_exif_tags(original)
        except AttributeError as e:
            exif = {}

        for size, attr_name in self.sizes:
            im = self.adjust_orientation(exif, original.copy())

            if size is None:
                width, height = im.width, im.height
            else:
                width, height = size, size

            im.thumbnail((width, height))
            im_io = BytesIO()
            im.save(im_io, format='JPEG', quality=60, optimize=True, progressive=True)
            suffix = size if size is not None else 'full'
            resized_name = '{}_resized_{}.JPG'.format(original_name, suffix)
            img_attr = getattr(self, attr_name)
            img_attr.save(resized_name, im_io, save=False)

    def __str__(self):
        return self.original.name

    def save(self, *args, **kwargs):
        if kwargs.pop('resize', True):
            # resize by default, but make it optional for recalc
            # management command
            self.create_resized_images()
        return super().save(*args, **kwargs)

    def get_srcset(self):
        sources = []
        for size, attr_name in self.sizes:
            prefix = attr_name.split('_')[-1]
            img = getattr(self, attr_name)
            width = self.original_width if size is None else size
            url = img.url
            sources.append(url)
            sources.append('{}w,'.format(width))
        return ' '.join(sources)

    @property
    def srcset(self):
        return self.get_srcset()

    @property
    def thumbnail_src(self):
        return self.img_xs.url

    @property
    def full_src(self):
        return self.full.url


class BlogVideo(TimeStampedModel):
    user = models.ForeignKey(User)
    original = models.FileField(upload_to='blogs_videos/')
    poster = models.ImageField(upload_to='blogs_videos/poster/', null=True, blank=True)
    poster_seconds = models.FloatField(default=1)

    poster_thumbnail = ImageSpecField(source='poster',
                                      processors=[Thumbnail(300, 300, crop=False)],
                                      format='JPEG',
                                      options={'quality': 60})

    blogpost_context_key = 'video'
    calc_poster = True

    def _create_poster(self):
        """Moved into own method to make it mockable in tests."""
        fp, tmp_path = tempfile.mkstemp(prefix='poster_', suffix='.jpg')
        original = self.original.open()
        logger.info(original)
        logger.info('original url: {}'.format(self.original.url))
        logger.info('original path: {}'.format(self.original.path))
        video_url = self.original.url
        if not video_url.startswith('http'):
            video_url = self.original.path
        poster_cmd = (
            'ffmpeg -i "{video_path}" -ss {seconds} -vframes 1'
            ' -y -f image2 {poster_path}'
        ).format(video_path=video_url, seconds=self.poster_seconds,
                 poster_path=tmp_path)
        logger.info(poster_cmd)
        check_output(poster_cmd, shell=True)
        self.poster.save(
            os.path.basename(tmp_path), File(open(tmp_path, 'rb')),
            save=False)
        os.unlink(tmp_path)
        logger.info(self.pk)
        logger.info(self.poster)

    def create_poster(self):
        if self.poster or not self.calc_poster:
            # poster is not null
            logger.info('skip creating poster')
        else:
            try:
                self._create_poster()
            except Exception as e:
                logger.info('create poster failed')

    def get_all_paths(self):
        paths = set()
        paths.add(self.original.name)
        if self.poster:
            paths.add(self.poster.name)
            try:
                if self.poster_thumbnail:
                    paths.add(self.poster_thumbnail.name)
            except FileNotFoundError as e:
                pass
        return paths

    def save(self, *args, **kwargs):
        generate_poster = kwargs.pop('poster', True)
        # need to save original first - django file handling is driving me nuts
        result = super().save(*args, **kwargs)
        if generate_poster:
            logger.info('generate video poster')
            # generate poster thumbnail by default, but make it optional
            # for recalc management command
            self.create_poster()
            # save again after adding poster
            result = super().save(*args, **kwargs)
        return result


class BlogGallery(TimeStampedModel):
    user = models.ForeignKey(User)
    images = models.ManyToManyField(BlogImage)
    blogpost_context_key = 'gallery'

    @property
    def image_ids(self):
        return set([i.pk for i in self.images.all()])


class BlogPost(TimeStampedModel):
    author = models.ForeignKey(User)
    blog = models.ForeignKey(Blog)
    title = models.CharField(max_length=255)
    published = models.BooleanField(default=False)

    content = RichTextUploadingField()
    slug = models.SlugField(max_length=50)

    images = models.ManyToManyField(BlogImage)
    videos = models.ManyToManyField(BlogVideo)
    galleries = models.ManyToManyField(BlogGallery)

    media_model_lookup = {
        'image': BlogImage,
        'video': BlogVideo,
        'gallery': BlogGallery,
    }

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        params = {
            "slug": self.slug,
            "blog_slug": self.blog.slug,
        }
        return reverse("blogs:blogpost_detail", kwargs=params)

    def get_slug(self):
        return slugify(self.title)

    @property
    def media_lookup_old(self):
        lookup = defaultdict(dict)
        media = list(self.media.all().prefetch_related('content_object'))
        for item in media:
            obj = item.content_object
            lookup[obj.blogpost_context_key][obj.pk] = obj
        return lookup

    @property
    def media_lookup(self):
        return {
            "image": {i.pk: i for i in self.images.all()},
            "video": {v.pk: v for v in self.videos.all()},
            "gallery": {g.pk: g for g in self.galleries.all()}
        }

    @property
    def media_from_content(self):
        regex = re.compile('{% blog_(\w+) (\d+) %}')
        groups = regex.findall(self.content)
        media = []
        for name, pk in groups:
            media.append((name, int(pk)))
        return media

    def add_missing_media_objects(self):
        media_attr_lookup = {
            'image': self.images,
            'video': self.videos,
            'gallery': self.galleries,
        }

        media_lookup = self.media_lookup
        model_lookup = self.media_model_lookup
        for model_name, model_pk in self.media_from_content:
            try:
                model = media_lookup[model_name][model_pk]
                logger.info("found: {} {} {}".format(model_name, model_pk, model))
            except KeyError:
                media_object = model_lookup[model_name].objects.get(pk=model_pk)
                print(model_name, media_object, media_attr_lookup[model_name])
                # bm = BlogMedia.objects.create(blogpost=self, content_object=media_object)  # noqa
                media_attr_lookup[model_name].add(media_object)
                logger.info('added: {} {} {}'.format(model_name, model_pk, media_object))

    def save(self, *args, **kwargs):
        save_return = super().save(*args, **kwargs)
        self.add_missing_media_objects()
        return save_return
