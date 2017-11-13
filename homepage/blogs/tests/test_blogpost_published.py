import pytest

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from ..models import BlogPost


class TestPublished:
    pytestmark = pytest.mark.django_db

    def test_get_only_published_entries(self, client, unpublished_blogpost):
        bp = unpublished_blogpost
        feed_url = reverse('blogs:blogpost_feed', kwargs={'slug': bp.blog.slug})

        r = client.get(feed_url)
        assert r.status_code == 200

        content = r.content.decode('utf-8')
        assert 'xml' in content
        assert bp.title not in content

    def test_get_blogpost_detail_not_published_not_auth(self, client, unpublished_blogpost):
        blogpost = unpublished_blogpost
        slugs = {'blog_slug': blogpost.blog.slug, 'slug': blogpost.slug}
        detail_url = reverse('blogs:blogpost_detail', kwargs=slugs)

        r = client.get(detail_url)
        assert r.status_code == 404

        content = r.content.decode('utf-8')
        assert blogpost.title not in content

    def test_get_blogpost_detail_not_published_authenticated(self, client, unpublished_blogpost):
        blogpost = unpublished_blogpost
        slugs = {'blog_slug': blogpost.blog.slug, 'slug': blogpost.slug}
        detail_url = reverse('blogs:blogpost_detail', kwargs=slugs)

        r = client.login(username=blogpost.author.username, password="password")

        r = client.get(detail_url)
        assert r.status_code == 200

        content = r.content.decode('utf-8')
        assert 'html' in content
        assert blogpost.title in content

    def test_get_blogpost_not_published_not_authenticated(self, client, unpublished_blogpost):
        blogpost = unpublished_blogpost
        blog_url = reverse('blogs:blogpost_list', kwargs={'slug': blogpost.blog.slug})

        r = client.get(blog_url)
        assert r.status_code == 200

        content = r.content.decode('utf-8')
        assert 'html' in content
        assert blogpost.title not in content

    def test_get_blogpost_not_published_authenticated(self, client, unpublished_blogpost):
        blogpost = unpublished_blogpost
        blog_url = reverse('blogs:blogpost_list', kwargs={'slug': blogpost.blog.slug})

        r = client.login(username=blogpost.author.username, password="password")

        r = client.get(blog_url)
        assert r.status_code == 200

        content = r.content.decode('utf-8')
        assert 'html' in content
        assert blogpost.title in content

    def test_published_manager_pub_date_null(self, blogpost):
        assert BlogPost.published.count() == 1
        blogpost.pub_date = None
        blogpost.save()
        assert BlogPost.objects.count() == 1
        assert BlogPost.published.count() == 0

    def test_published_manager_future_pubdate(self, blogpost):
        assert BlogPost.published.count() == 1
        blogpost.pub_date = timezone.now() + timedelta(seconds=10)
        blogpost.save()
        assert BlogPost.objects.count() == 1
        assert BlogPost.published.count() == 0
        blogpost.pub_date = timezone.now()
        blogpost.save()
        assert BlogPost.objects.count() == 1
        assert BlogPost.published.count() == 1
