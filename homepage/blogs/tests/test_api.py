import pytest

from django.urls import reverse

from ...users.tests.factories import UserFactory


class TestBlogImage:
    @classmethod
    def setup_class(cls):
        cls.list_url = reverse('api:image-list')
        cls.detail_url = reverse('api:image-detail', kwargs={'pk': 1})

    @pytest.mark.django_db
    def test_image_list_endpoint_without_authentication(self, api_client):
        """Check for not authenticated status code if trying to access the list
        endpoint without being authenticated.
        """
        r = api_client.get(self.list_url, format='json')
        assert r.status_code == 403

    @pytest.mark.django_db
    def test_image_detail_endpoint_without_authentication(self, api_client):
        """Check for not authenticated status code if trying to access the
        detail endpoint without being authenticated.
        """
        r = api_client.get(self.detail_url, format='json')
        assert r.status_code == 403

    @pytest.mark.django_db
    def test_image_list_endpoint_with_authentication(self, api_client):
        """Check for list result when accessing the list endpoint
        being logged in.
        """
        user = UserFactory()
        api_client.login(username=user.username, password="password")
        r = api_client.get(self.list_url, format='json')
        # dont redirect to login page
        assert r.status_code == 200
        assert 'results' in r.json()


class TestBlogGallery:
    @classmethod
    def setup_class(cls):
        cls.list_url = reverse('api:gallery-list')
        cls.detail_url = reverse('api:gallery-detail', kwargs={'pk': 1})

    @pytest.mark.django_db
    def test_gallery_list_endpoint_without_authentication(self, api_client):
        """Check for not authenticated status code if trying to access the list
        endpoint without being authenticated.
        """
        r = api_client.get(self.list_url, format='json')
        assert r.status_code == 403

    @pytest.mark.django_db
    def test_gallery_detail_endpoint_without_authentication(self, api_client):
        """Check for not authenticated status code if trying to access the
        detail endpoint without being authenticated.
        """
        r = api_client.get(self.detail_url, format='json')
        assert r.status_code == 403

    @pytest.mark.django_db
    def test_gallery_list_endpoint_with_authentication(self, api_client):
        """Check for list result when accessing the list endpoint
        being logged in.
        """
        user = UserFactory()
        api_client.login(username=user.username, password="password")
        r = api_client.get(self.list_url, format='json')
        # dont redirect to login page
        assert r.status_code == 200
        assert 'results' in r.json()


class TestBlogVideo:
    @classmethod
    def setup_class(cls):
        cls.list_url = reverse('api:video-list')
        cls.detail_url = reverse('api:video-detail', kwargs={'pk': 1})

    @pytest.mark.django_db
    def test_video_list_endpoint_without_authentication(self, api_client):
        """Check for not authenticated status code if trying to access the list
        endpoint without being authenticated.
        """
        r = api_client.get(self.list_url, format='json')
        assert r.status_code == 403

    @pytest.mark.django_db
    def test_video_detail_endpoint_without_authentication(self, api_client):
        """Check for not authenticated status code if trying to access the
        detail endpoint without being authenticated.
        """
        r = api_client.get(self.detail_url, format='json')
        assert r.status_code == 403

    @pytest.mark.django_db
    def test_video_list_endpoint_with_authentication(self, api_client):
        """Check for list result when accessing the list endpoint
        being logged in.
        """
        user = UserFactory()
        api_client.login(username=user.username, password="password")
        r = api_client.get(self.list_url, format='json')
        # dont redirect to login page
        assert r.status_code == 200
        assert 'results' in r.json()
