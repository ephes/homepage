import pytest
from django.urls import reverse


class TestBlogpostDetail:
    pytestmark = pytest.mark.django_db

    def test_get_blogpost_detail(self, client, blogpost):
        slugs = {'blog_slug': blogpost.blog.slug, 'slug': blogpost.slug}
        detail_url = reverse('blogs:blogpost_detail', kwargs=slugs)

        r = client.get(detail_url)
        assert r.status_code == 200

        content = r.content.decode('utf-8')
        assert 'html' in content
        assert blogpost.title in content

    def test_get_blogpost_detail_not_published_not_auth(self, client, unpublished_blogpost):
        blogpost = unpublished_blogpost
        slugs = {'blog_slug': blogpost.blog.slug, 'slug': blogpost.slug}
        detail_url = reverse('blogs:blogpost_detail', kwargs=slugs)

        print(blogpost.published)

        r = client.get(detail_url)
        assert r.status_code == 404

        content = r.content.decode('utf-8')
        assert blogpost.title not in content
