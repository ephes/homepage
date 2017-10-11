import pytest
from django.urls import reverse


class TestBlogpostDetail:
    @pytest.mark.django_db
    def test_get_blogpost_detail(self, client, blogpost):
        slugs = {'blog_slug': blogpost.blog.slug, 'slug': blogpost.slug}
        feed_url = reverse('blogs:blogpost-detail', kwargs=slugs)

        r = client.get(feed_url)
        assert r.status_code == 200

        content = r.content.decode('utf-8')
        assert 'html' in content
        assert blogpost.title in content
