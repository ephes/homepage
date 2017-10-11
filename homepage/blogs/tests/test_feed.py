import pytest
from django.urls import reverse


class TestFeed:
    @pytest.mark.django_db
    def test_get_feed(self, client, blogpost):
        feed_url = reverse('blogs:blogpost-feed', kwargs={'slug': blogpost.blog.slug})

        r = client.get(feed_url)
        assert r.status_code == 200

        content = r.content.decode('utf-8')
        assert 'xml' in content
        assert blogpost.title in content
