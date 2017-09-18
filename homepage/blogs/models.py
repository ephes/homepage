import re

from io import BytesIO

from django.db import models
from django.core.urlresolvers import reverse
from django.core.files.images import ImageFile

from ckeditor_uploader.fields import RichTextUploadingField

from model_utils.models import TimeStampedModel

from slugify import slugify

from PIL import Image as PILImage

from ..users.models import User


class Blog(TimeStampedModel):
    user = models.ForeignKey(User)
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=500)
    slug = models.SlugField(max_length=50)

    def __str__(self):
        return self.title


class BlogPost(TimeStampedModel):
    author= models.ForeignKey(User)
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
    def processed_content(self):
        processed = self.content
        images = re.findall('img_\d+', processed)
        for image in images:
            pk = int(image.split('_')[-1])
            img = Image.objects.get(pk=pk)
            processed = processed.replace(image, img.get_img_tag())
        return processed


class Image(TimeStampedModel):
    user = models.ForeignKey(User)
    original = models.ImageField(
        upload_to='blogs_images/originals',
        height_field='original_height',
        width_field='original_width')
    original_height = models.PositiveIntegerField(blank=True, null=True)
    original_width= models.PositiveIntegerField(blank=True, null=True)

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
        (2200, 'img_xl'),
        (1100, 'img_lg'),
        (768, 'img_md'),
        (500, 'img_sm'),
        (300, 'img_xs'),
    ]

    def create_resized_images(self):
        for size, attr_name in self.sizes:
            img_size = size, size
            im = PILImage.open(self.original)
            im.thumbnail(img_size)
            im_io = BytesIO()
            im.save(im_io, format='JPEG')
            original_name = (self.original.name
                             .split('/')[-1]
                             .replace('.JPG', ''))
            resized_name = '{}_resized_{}.JPG'.format(original_name, img_size[0])
            img_attr = getattr(self, attr_name)
            img_attr.save(resized_name, im_io, save=False)

    def __str__(self):
        return self.original.name

    def save(self, *args, **kwargs):
        self.create_resized_images()
        return super().save(*args, **kwargs)

    def get_srcset(self):
        sources = []
        for size, attr_name in self.sizes:
            img = getattr(self, attr_name)
            sources.append(img.url)
        return ' '.join(sources)

    def get_img_tag(self):
        return (
            '<img width="100%" srcset="{srcset}" src="{src}"'
            '</img>'
        ).format(srcset=self.get_srcset(), src=self.img_xl.url)
