import pytest
from django.urls import reverse


class TestBlogpostList:
    @pytest.mark.django_db
    def test_get_blogpost_list(self, client, blogpost):
        blog_url = reverse('blogs:blogpost_list', kwargs={'slug': blogpost.blog.slug})

        r = client.get(blog_url)
        assert r.status_code == 200

        print(r.content)

        content = r.content.decode('utf-8')
        assert 'html' in content
        assert blogpost.title in content
