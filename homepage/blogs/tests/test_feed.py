import pytest
from django.urls import reverse

from ...users.tests.factories import UserFactory

from .factories import BlogFactory
from .factories import BlogPostFactory


class TestFeed:
    @pytest.mark.django_db
    def test_get_feed(self, client, blogpost):
        feed_url = reverse('blogs:blogpost_feed', kwargs={'slug': blogpost.blog.slug})

        r = client.get(feed_url)
        assert r.status_code == 200

        content = r.content.decode('utf-8')
        assert 'xml' in content
        assert blogpost.title in content

    @pytest.mark.django_db
    def test_get_only_published_entries(self, client):
        user = UserFactory()
        blog = BlogFactory(user=user, title='fooblog', slug='fooblog')
        bp = BlogPostFactory(author=user, blog=blog, published=False,
                             title='testpost', slug='testpost')

        feed_url = reverse('blogs:blogpost_feed', kwargs={'slug': bp.blog.slug})

        r = client.get(feed_url)
        assert r.status_code == 200

        content = r.content.decode('utf-8')
        assert 'xml' in content
        assert bp.title not in content
