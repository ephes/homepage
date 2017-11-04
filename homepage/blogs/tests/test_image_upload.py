import pytest

from django.urls import reverse

from ...users.tests.factories import UserFactory


class TestImageUpload:
    @pytest.mark.django_db
    def test_upload_image_not_authenticated(self, client, small_jpeg_io):
        upload_url = reverse('api:upload_image')

        small_jpeg_io.seek(0)
        r = client.post(upload_url, {'original': small_jpeg_io})
        # redirect to login
        assert r.status_code == 302

    @pytest.mark.django_db
    def test_upload_image_authenticated(self, client, small_jpeg_io):
        # login
        user = UserFactory()
        r = client.login(username=user.username, password="password")

        # upload
        upload_url = reverse('api:upload_image')
        small_jpeg_io.seek(0)
        r = client.post(upload_url, {'original': small_jpeg_io})

        assert r.status_code == 201
        assert int(r.content.decode('utf-8')) > 0