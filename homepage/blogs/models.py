import os
import re

from io import BytesIO

from django.db import models
from django.core.urlresolvers import reverse
from django.core.files.images import ImageFile

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

    def replace_images(self, content):
        images = re.findall('blog_img_\d+', content)
        for image in images:
            pk = int(image.split('_')[-1])
            try:
                img = BlogImage.objects.get(pk=pk)
                content = content.replace(image, img.get_img_tag())
            except BlogImage.DoesNotExist:
                pass
        return content

    def replace_videos(self, content):
        videos= re.findall('blog_video_\d+', content)
        for video in videos:
            pk = int(video.split('_')[-1])
            try:
                video_obj = BlogVideo.objects.get(pk=pk)
                content = content.replace(video, video_obj.get_video_tag())
            except BlogVideo.DoesNotExist as e:
                pass
        return content

    def replace_galleries(self, content):
        galleries = re.findall('blog_gallery_\d+', content)
        for gallery in galleries:
            pk = int(gallery.split('_')[-1])
            try:
                gallery_obj = BlogGallery.objects.get(pk=pk)
                content = content.replace(gallery, gallery_obj.get_gallery_tag())
            except BlogGallery.DoesNotExist as e:
                pass
        return content

    @property
    def processed_content(self):
        processed = self.replace_images(self.content)
        processed = self.replace_videos(processed)
        processed = self.replace_galleries(processed)
        return processed

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
    original_width= models.PositiveIntegerField(blank=True, null=True)

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

        exif = self.get_exif_tags(original)

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

    def get_img_tag(self):
        return (
            '<a href="{full}">'
            '  <img class="blog-image" src="{src}" srcset="{srcset}" sizes="100vw"></img>'
            '</a>'
        ).format(srcset=self.get_srcset(), src=self.img_xs.url, full=self.img_full.url)


class BlogVideo(TimeStampedModel):
    user = models.ForeignKey(User)
    original = models.FileField(upload_to='blogs_videos/')

    def get_video_tag(self):
        return (
            '<video class="blog-video" preload="auto" controls>'
            '  <source src="{src}" type="video/mp4">'
            '</video>'
        ).format(src=self.original.url)


class BlogGallery(TimeStampedModel):
    user = models.ForeignKey(User)
    images = models.ManyToManyField(BlogImage)

    def get_modal_tmpl(self):
        return '''
	    <!-- Button trigger modal -->
	    <a data-toggle="modal" data-target="#galleryModal{pk}">
	      {thumbnail_tag}
	    </a>

	    <!-- Modal -->
	    <div class="modal" id="galleryModal{pk}" tabindex="-1" role="dialog" aria-labelledby="galleryModalLabel" aria-hidden="true">
	      <div class="modal-dialog modal-lg" role="document">
		<div class="modal-content">
		  <div class="modal-header">
		    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
		      <span aria-hidden="true">&times;</span>
		    </button>
		  </div>
		  <div class="modal-body">
		    {img_tag}
		  </div>
		  <div class="modal-footer">
                    {prev_button}
                    {next_button}
		  </div>
		</div>
	      </div>
	    </div>
        '''

    def get_prev_button(self, prev_pk):
        return (
            '<button id="prev" type="button" class="btn btn-primary" '
            'data-toggle="modal" data-target="#galleryModal{prev_pk}" data-dismiss="modal">'
            'Previous</button>'
        ).format(prev_pk=prev_pk)

    def get_next_button(self, next_pk):
        return (
            '<button id="next" type="button" class="btn btn-primary" '
            'data-toggle="modal" data-target="#galleryModal{next_pk}" data-dismiss="modal">'
            'Next</button>'
        ).format(next_pk=next_pk)

    def get_gallery_tag(self):
        image_tags = []
        prev_img, next_img = None, None
        images = list(self.images.all())
        for num, image in enumerate(images, 1):
            if num < len(images):
                next_img = images[num]
            else:
                next_img = None
            srcset = image.get_srcset()
            thumbnail_tmpl = '<img class="gallery-thumbnail" src={src} srcset="{srcset}"></img>'
            thumbnail_tag = thumbnail_tmpl.format(srcset=srcset, src=image.img_xs.url)
            img_tag = image.get_img_tag()
            modal_tmpl= self.get_modal_tmpl()

            if prev_img is not None:
                prev_button = self.get_prev_button(prev_img.pk)
            else:
                prev_button = ""
            if next_img is not None:
                next_button = self.get_next_button(next_img.pk)
            else:
                next_button = ""
            modal_tag = modal_tmpl.format(
                pk=image.pk, thumbnail_tag=thumbnail_tag, img_tag=img_tag,
                prev_button=prev_button, next_button=next_button)
            image_tags.append(modal_tag)
            prev_img = image
        return '\n'.join(image_tags)
