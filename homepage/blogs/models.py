import os
import re
import logging
import tempfile
import subprocess

from subprocess import check_output

from collections import defaultdict

from django.db import models
from django.utils import timezone
from django.core.files import File
from django.core.urlresolvers import reverse

from ckeditor_uploader.fields import RichTextUploadingField

from imagekit.models import ImageSpecField
from imagekit.processors import Thumbnail
from imagekit.processors import Transpose

from model_utils.models import TimeStampedModel

from slugify import slugify

from ..users.models import User

logger = logging.getLogger(__name__)


class Blog(TimeStampedModel):
    user = models.ForeignKey(User)
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=500)
    slug = models.SlugField(max_length=50)

    def __str__(self):
        return self.title


def image_spec_thumbnail(size):
    processors = [Transpose(), Thumbnail(size, size, crop=False)]
    return ImageSpecField(source='original', processors=processors,
                          format='JPEG', options={'quality': 60})


IMAGE_SIZES = {
    'img_full': None,
    'img_xl': 2200,
    'img_lg': 1100,
    'img_md': 768,
    'img_sm': 500,
    'img_xs': 300,
}

class BlogImage(TimeStampedModel):
    user = models.ForeignKey(User)

    original = models.ImageField(
        upload_to='blogs_images/originals',
        height_field='original_height',
        width_field='original_width')
    original_height = models.PositiveIntegerField(blank=True, null=True)
    original_width = models.PositiveIntegerField(blank=True, null=True)

    img_full = ImageSpecField(source='original', processors=[Transpose()],
                              format='JPEG', options={'quality': 60})

    img_xl = image_spec_thumbnail(IMAGE_SIZES['img_xl'])
    img_lg = image_spec_thumbnail(IMAGE_SIZES['img_lg'])
    img_md = image_spec_thumbnail(IMAGE_SIZES['img_md'])
    img_sm = image_spec_thumbnail(IMAGE_SIZES['img_sm'])
    img_xs = image_spec_thumbnail(IMAGE_SIZES['img_xs'])

    sizes = [(v, k) for k, v in IMAGE_SIZES.items()]

    blogpost_context_key = 'image'

    def get_all_paths(self):
        paths = set()
        paths.add(self.original.name)
        for size, attr_name in self.sizes:
            paths.add(getattr(self, attr_name).name)
        return paths

    def __str__(self):
        return self.original.name

    def get_srcset(self):
        sources = []
        for size, attr_name in self.sizes:
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

    def _get_video_dimensions(self, video_url):
        ffprobe_cmd = 'ffprobe -i "{}"'.format(video_url)
        result = subprocess.check_output(ffprobe_cmd, shell=True, stderr=subprocess.STDOUT)
        lines = result.decode('utf8').split("\n")
        width, height = None, None
        for line in lines:
            if 'SAR' in line:
                data = line.split(', ')[3]
                r1, r2 = map(int, data.split(' ')[0].split('x'))
                o1, o2 = map(int, data.rstrip(']').split(' ')[-1].split(':'))
                portrait = o1 < o2
                width, height = (r2, r1) if portrait else (r1, r2)
                break
        return width, height

    def _create_poster(self):
        """Moved into own method to make it mockable in tests."""
        fp, tmp_path = tempfile.mkstemp(prefix='poster_', suffix='.jpg')
        logger.info('original url: {}'.format(self.original.url))
        video_url = self.original.url
        if not video_url.startswith('http'):
            video_url = self.original.path
        width, height = self._get_video_dimensions(video_url)
        poster_cmd = (
            'ffmpeg -ss {seconds} -i "{video_path}" -vframes 1'
            ' -y -f image2 -s {width}x{height} {poster_path}'
        ).format(video_path=video_url, seconds=self.poster_seconds,
                 poster_path=tmp_path, width=width, height=height)
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
                logger.info(e)
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


class BlogFile(TimeStampedModel):
    user = models.ForeignKey(User)
    original = models.FileField(upload_to='blogs_files/')

    def get_all_paths(self):
        paths = set()
        paths.add(self.original.name)
        return paths


class PublishedManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return (super().get_queryset()
                       .filter(pub_date__lte=timezone.now()))


class BlogPost(TimeStampedModel):
    author = models.ForeignKey(User)
    blog = models.ForeignKey(Blog)
    title = models.CharField(max_length=255)
    pub_date = models.DateTimeField(null=True, blank=True)

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

    objects = models.Manager()
    published = PublishedManager()

    @property
    def is_published(self):
        return self.pub_date is not None and self.pub_date < timezone.now()

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

    @property
    def media_attr_lookup(self):
        return {
            'image': self.images,
            'video': self.videos,
            'gallery': self.galleries,
        }

    def add_missing_media_objects(self):
        media_attr_lookup = self.media_attr_lookup

        media_lookup = self.media_lookup
        model_lookup = self.media_model_lookup
        for model_name, model_pk in self.media_from_content:
            try:
                model = media_lookup[model_name][model_pk]
                logger.info("found: {} {} {}".format(model_name, model_pk, model))
            except KeyError:
                media_object = model_lookup[model_name].objects.get(pk=model_pk)
                # print(model_name, media_object, media_attr_lookup[model_name])
                # bm = BlogMedia.objects.create(blogpost=self, content_object=media_object)  # noqa
                media_attr_lookup[model_name].add(media_object)
                logger.info('added: {} {} {}'.format(model_name, model_pk, media_object))

    def remove_obsolete_media_objects(self):
        media_from_db = {k: set(v.keys()) for k, v in self.media_lookup.items()}

        # media from content
        media_content_lookup = defaultdict(set)
        for model_name, model_pk in self.media_from_content:
            media_content_lookup[model_name].add(model_pk)

        # remove all PKs which are in db but not in content
        media_attr_lookup = self.media_attr_lookup
        for media_type, media_pks in media_from_db.items():
            for media_pk in media_pks:
                if media_pk not in media_content_lookup.get(media_type, set()):
                    media_attr_lookup[media_type].remove(media_pk)

    def save(self, *args, **kwargs):
        save_return = super().save(*args, **kwargs)
        self.add_missing_media_objects()
        self.remove_obsolete_media_objects()
        return save_return
