import os
import re
import logging

from collections import defaultdict

from io import BytesIO

from django.db import models
from django.core.urlresolvers import reverse

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from ckeditor_uploader.fields import RichTextUploadingField

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

    img_full = models.ImageField(
        upload_to='blogs_images/resized',
        height_field='full_height',
        width_field='full_width',
        null=True,
        blank=True,)
    full_height = models.PositiveIntegerField(blank=True, null=True)
    full_width = models.PositiveIntegerField(blank=True, null=True)

    img_xl = models.ImageField(
        upload_to='blogs_images/resized',
        height_field='xl_height',
        width_field='xl_width',
        null=True,
        blank=True,)
    xl_height = models.PositiveIntegerField(blank=True, null=True)
    xl_width = models.PositiveIntegerField(blank=True, null=True)

    img_lg = models.ImageField(
        upload_to='blogs_images/resized',
        height_field='lg_height',
        width_field='lg_width',
        null=True,
        blank=True,)
    lg_height = models.PositiveIntegerField(blank=True, null=True)
    lg_width = models.PositiveIntegerField(blank=True, null=True)

    img_md = models.ImageField(
        upload_to='blogs_images/resized',
        height_field='md_height',
        width_field='md_width',
        null=True,
        blank=True,)
    md_height = models.PositiveIntegerField(blank=True, null=True)
    md_width = models.PositiveIntegerField(blank=True, null=True)

    img_sm = models.ImageField(
        upload_to='blogs_images/resized',
        height_field='sm_height',
        width_field='sm_width',
        null=True,
        blank=True,)
    sm_height = models.PositiveIntegerField(blank=True, null=True)
    sm_width = models.PositiveIntegerField(blank=True, null=True)

    img_xs = models.ImageField(
        upload_to='blogs_images/resized',
        height_field='xs_height',
        width_field='xs_width',
        null=True,
        blank=True,)
    xs_height = models.PositiveIntegerField(blank=True, null=True)
    xs_width = models.PositiveIntegerField(blank=True, null=True)

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
            width = getattr(self, '{}_width'.format(prefix))
            img = getattr(self, attr_name)
            sources.append(img.url)
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
    blogpost_context_key = 'video'


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
        return reverse("blogs:blogpost-detail", kwargs=params)

    def get_slug(self):
        return slugify(self.title)

    @property
    def media_lookup(self):
        lookup = defaultdict(dict)
        media = list(self.media.all().prefetch_related('content_object'))
        for item in media:
            obj = item.content_object
            lookup[obj.blogpost_context_key][obj.pk] = obj
        return lookup

    @property
    def media_from_content(self):
        regex = re.compile('{% blog_(\w+) (\d+) %}')
        groups = regex.findall(self.content)
        media = []
        for name, pk in groups:
            media.append((name, int(pk)))
        return media

    def add_missing_media_objects(self):
        media_lookup = self.media_lookup
        model_lookup = self.media_model_lookup
        for model_name, model_pk in self.media_from_content:
            try:
                model = media_lookup[model_name][model_pk]
                logger.info("found: {} {} {}".format(model_name, model_pk, model))
            except KeyError:
                media_object = model_lookup[model_name].objects.get(pk=model_pk)
                bm = BlogMedia.objects.create(blogpost=self, content_object=media_object)
                logger.info('added: {} {} {}'.format(model_name, model_pk, media_object))

    def save(self, *args, **kwargs):
        save_return = super().save(*args, **kwargs)
        self.add_missing_media_objects()
        return save_return


class BlogMedia(models.Model):
    blogpost = models.ForeignKey(BlogPost, related_name='media')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
