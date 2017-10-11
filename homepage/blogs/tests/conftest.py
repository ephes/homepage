from django.core.files.uploadedfile import SimpleUploadedFile

import pytest

from ..models import (
    Blog,
    BlogPost,
    BlogImage
)
from ...users.models import User


@pytest.fixture(scope='module')
def image_1px():
    # This is a 1x1 black png
    png = (
         b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00'
         b'\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00'
         b'\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc````'
         b'\x00\x00\x00\x05\x00\x01\xa5\xf6E@\x00\x00'
         b'\x00\x00IEND\xaeB`\x82')
    simple_png = SimpleUploadedFile(name='test.png', content=png, content_type='image/png')
    return simple_png


@pytest.fixture(scope='module')
def user(scope='module'):
    test_user = User.objects.create(name='testuser', password='password')
    return test_user


@pytest.fixture(scope='module')
def blog_image(user, image_1px):
    image = BlogImage(user=user, original=image_1px)
    for size, attr_name in image.sizes:
        setattr(image, attr_name, image_1px)
    image.save(resize=False)
    return image


@pytest.fixture(scope='module')
def blog(user):
    return Blog.objects.create(user=user, title='testblog', slug='testblog')


@pytest.fixture(scope='module')
def blogpost(blog):
    return BlogPost.objects.create(
        author=blog.user, blog=blog, title='test entry',
        slug='test-entry', published=True, content='foobar')


@pytest.fixture(scope='module')
def test_templ():
    return '''
        {% lorem %}
    '''


@pytest.fixture(scope='module')
def img_templ():
    return '''
        {% load blogs_extras %}
        {% blog_image 1 %}
    '''
