import pytest
from django.urls import reverse

from ...users.tests.factories import UserFactory

from ..models import BlogPost
from .factories import BlogFactory
from .factories import BlogImageFactory
from .factories import BlogVideoFactory
from .factories import BlogGalleryFactory


class TestBlogpostAdd:
    @pytest.mark.django_db
    def test_get_blogpost_add_not_authenticated(self, client, blog):
        create_url = reverse('blogs:blogpost_create', kwargs={'slug': blog.slug})

        r = client.get(create_url)
        # redirect to login
        assert r.status_code == 302

    @pytest.mark.django_db
    def test_get_blogpost_add_authenticated(self, client, blog):
        create_url = reverse('blogs:blogpost_create', kwargs={'slug': blog.slug})
        user = UserFactory()
        r = client.login(username=user.username, password="password")
        r = client.get(create_url)
        assert r.status_code == 200

        content = r.content.decode('utf-8')
        assert 'html' in content
        assert 'ckeditor' in content

    @pytest.mark.django_db
    def test_blogpost_create_not_authenticated(self, client):
        blog = BlogFactory(user=UserFactory())
        create_url = reverse('blogs:blogpost_create', kwargs={'slug': blog.slug})
        data = {
            'title': 'test title',
            'content': 'foo bar baz',
            'published': True,
            'slug': 'blog-slug',
        }
        r = client.post(create_url, data, follow=True)
        assert r.status_code == 200

        content = r.content.decode('utf-8')
        assert 'Sign In' in content

    @pytest.mark.django_db
    def test_blogpost_create_authenticated(self, client):
        user = UserFactory()
        r = client.login(username=user.username, password="password")

        blog = BlogFactory(user=user)
        create_url = reverse('blogs:blogpost_create', kwargs={'slug': blog.slug})
        data = {
            'title': 'test title',
            'content': 'foo bar baz',
            'published': True,
            'slug': 'blog-slug',
        }
        r = client.post(create_url, data)
        assert r.status_code == 302
        assert BlogPost.objects.get(slug=data['slug']).title == data['title']

    @pytest.mark.django_db
    def test_blogpost_create_authenticated_with_image(self, client):
        user = UserFactory()
        r = client.login(username=user.username, password="password")

        blog = BlogFactory(user=user)
        image = BlogImageFactory(user=user)
        content = 'with image: {{% blog_image {} %}}'.format(image.pk)
        create_url = reverse('blogs:blogpost_create', kwargs={'slug': blog.slug})
        data = {
            'title': 'test title',
            'content': content,
            'published': True,
            'slug': 'blog-slug',
        }
        r = client.post(create_url, data)
        assert r.status_code == 302
        bp = BlogPost.objects.get(slug=data['slug'])
        bis = list(bp.images.all())
        assert bp.title == data['title']
        assert len(bis) == 1
        assert bis[0].pk == image.pk

    @pytest.mark.django_db
    def test_blogpost_create_authenticated_with_video(self, client):
        user = UserFactory()
        r = client.login(username=user.username, password="password")

        blog = BlogFactory(user=user)
        video = BlogVideoFactory(user=user)
        content = 'with video: {{% blog_video {} %}}'.format(video.pk)
        create_url = reverse('blogs:blogpost_create', kwargs={'slug': blog.slug})
        data = {
            'title': 'test title',
            'content': content,
            'published': True,
            'slug': 'blog-slug',
        }
        r = client.post(create_url, data)
        assert r.status_code == 302
        bp = BlogPost.objects.get(slug=data['slug'])
        bvs = list(bp.videos.all())
        assert bp.title == data['title']
        assert len(bvs) == 1
        assert bvs[0].pk == video.pk

    @pytest.mark.django_db
    def test_blogpost_create_authenticated_with_gallery(self, client):
        user = UserFactory()
        r = client.login(username=user.username, password="password")

        blog = BlogFactory(user=user)
        gallery = BlogGalleryFactory(user=user)
        image1 = BlogImageFactory(user=user)
        image2 = BlogImageFactory(user=user)
        gallery.images.add(image1)
        gallery.images.add(image2)
        content = 'with gallery: {{% blog_gallery {} %}}'.format(gallery.pk)
        create_url = reverse('blogs:blogpost_create', kwargs={'slug': blog.slug})
        data = {
            'title': 'test title',
            'content': content,
            'published': True,
            'slug': 'blog-slug',
        }
        r = client.post(create_url, data)
        assert r.status_code == 302
        bp = BlogPost.objects.get(slug=data['slug'])
        bgs = list(bp.galleries.all())
        assert bp.title == data['title']
        assert len(bgs) == 1
        assert bgs[0].pk == gallery.pk
        assert len(gallery.images.all()) == 2
