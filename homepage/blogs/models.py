from django.db import models
from django.core.urlresolvers import reverse

from ckeditor_uploader.fields import RichTextUploadingField

from model_utils.models import TimeStampedModel

from slugify import slugify

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


class Image(TimeStampedModel):
    user = models.ForeignKey(User)
    original = models.ImageField(upload_to='blogs_images')

    def __str__(self):
        return 'foo'
