import pytest
from django.urls import reverse


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
    def test_get_only_published_entries(self, client, unpublished_blogpost):
        bp = unpublished_blogpost
        feed_url = reverse('blogs:blogpost_feed', kwargs={'slug': bp.blog.slug})

        r = client.get(feed_url)
        assert r.status_code == 200

        content = r.content.decode('utf-8')
        assert 'xml' in content
        assert bp.title not in content
