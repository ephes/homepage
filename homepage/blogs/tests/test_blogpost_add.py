import pytest
from django.urls import reverse

from ...users.tests.factories import UserFactory


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
