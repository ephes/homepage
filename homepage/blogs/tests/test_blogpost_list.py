import pytest
from django.urls import reverse


class TestBlogpostList:
    pytestmark = pytest.mark.django_db

    def test_get_blogpost_list(self, client, blogpost):
        blog_url = reverse('blogs:blogpost_list', kwargs={'slug': blogpost.blog.slug})

        r = client.get(blog_url)
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
