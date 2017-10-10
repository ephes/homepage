import os

from io import BytesIO

from django.db import models
from django.core.urlresolvers import reverse

from ckeditor_uploader.fields import RichTextUploadingField

from model_utils.models import TimeStampedModel

from slugify import slugify

from PIL import Image as PILImage
from PIL import ExifTags

from ..users.models import User


class Blog(TimeStampedModel):
    user = models.ForeignKey(User)
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=500)
    slug = models.SlugField(max_length=50)

    def __str__(self):
        return self.title


class BlogPost(TimeStampedModel):
    author = models.ForeignKey(User)
    blog = models.ForeignKey(Blog)
    title = models.CharField(max_length=255)
    published = models.BooleanField(default=False)

    content = RichTextUploadingField()
    slug = models.SlugField(max_length=50)

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
    def description(self):
        return self.processed_content


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


class BlogVideo(TimeStampedModel):
    user = models.ForeignKey(User)
    original = models.FileField(upload_to='blogs_videos/')


class BlogGallery(TimeStampedModel):
    user = models.ForeignKey(User)
    images = models.ManyToManyField(BlogImage)
