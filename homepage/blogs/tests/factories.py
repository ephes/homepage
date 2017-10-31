import factory

from ..models import Blog
from ..models import BlogPost
from ..models import BlogImage
from ..models import BlogVideo
from ..models import BlogGallery


class BlogFactory(factory.django.DjangoModelFactory):
    user = None
    title = factory.Sequence(lambda n: 'blog-{0}'.format(n))
    slug = factory.Sequence(lambda n: 'blog-{0}'.format(n))

    class Meta:
        model = Blog
        django_get_or_create = ('slug',)


class BlogImageFactory(factory.django.DjangoModelFactory):
    user = None
    original = factory.django.ImageField(color='blue')

    class Meta:
        model = BlogImage


class BlogVideoFactory(factory.django.DjangoModelFactory):
    user = None
    original = factory.django.ImageField(color='blue')

    class Meta:
        model = BlogVideo


class BlogGalleryFactory(factory.django.DjangoModelFactory):
    user = None

    class Meta:
        model = BlogGallery


class BlogPostFactory(factory.django.DjangoModelFactory):
    author = None
    blog = None
    published = None

    class Meta:
        model = BlogPost
