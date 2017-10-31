import pytest

from django.urls import reverse

from ...users.tests.factories import UserFactory

from ..models import BlogVideo


class TestVideoUpload:
    @pytest.mark.django_db
    def test_upload_video_not_authenticated(self, client, image_1px_io):
        upload_url = reverse('api:upload_video')

        image_1px_io.seek(0)
        r = client.post(upload_url, {'original': image_1px_io})
        # redirect to login
        assert r.status_code == 302

    @pytest.mark.django_db
    def test_upload_video_authenticated(self, client, image_1px_io):
        # login
        user = UserFactory()
        r = client.login(username=user.username, password="password")

        self.called_create_poster = False

        def set_called_create_poster():
            self.called_create_poster = True

        BlogVideo._saved_create_poster = BlogVideo._create_poster
        BlogVideo._create_poster = lambda x: set_called_create_poster()

        # upload
        upload_url = reverse('api:upload_video')
        image_1px_io.seek(0)
        r = client.post(upload_url, {'original': image_1px_io})

        BlogVideo._create_poster = BlogVideo._saved_create_poster

        assert r.status_code == 201
        assert self.called_create_poster
        assert int(r.content.decode('utf-8')) > 0
