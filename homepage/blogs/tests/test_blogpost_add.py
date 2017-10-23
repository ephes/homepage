import pytest
from django.urls import reverse

from ...users.tests.factories import UserFactory

from ..models import BlogPost
from .factories import BlogFactory


class TestBlogpostAdd:
    @pytest.mark.django_db
    def test_get_blogpost_add_not_authenticated(self, client, blog):
        create_url = reverse('blogs:blogpost-create', kwargs={'slug': blog.slug})

        r = client.get(create_url)
        # redirect to login
        assert r.status_code == 302

    @pytest.mark.django_db
    def test_get_blogpost_add_authenticated(self, client, blog):
        create_url = reverse('blogs:blogpost-create', kwargs={'slug': blog.slug})
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
        create_url = reverse('blogs:blogpost-create', kwargs={'slug': blog.slug})
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
        create_url = reverse('blogs:blogpost-create', kwargs={'slug': blog.slug})
        data = {
            'title': 'test title',
            'content': 'foo bar baz',
            'published': True,
            'slug': 'blog-slug',
        }
        r = client.post(create_url, data)
        assert r.status_code == 302
        assert BlogPost.objects.get(slug=data['slug']).title == data['title']
