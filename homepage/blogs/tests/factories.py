import factory

from ..models import Blog


class BlogFactory(factory.django.DjangoModelFactory):
    user = None
    title = factory.Sequence(lambda n: 'blog-{0}'.format(n))
    slug = factory.Sequence(lambda n: 'blog-{0}'.format(n))

    class Meta:
        model = Blog
        django_get_or_create = ('slug',)
