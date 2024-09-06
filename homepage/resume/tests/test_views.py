import pytest
from django.urls import reverse

from ..models import CVToken


@pytest.mark.django_db
def test_cv_view_without_token(client):
    url = reverse("resume:cv")
    r = client.get(url)
    assert r.status_code == 403

    content = r.content.decode("utf-8")
    assert "Please write a mail" in content


@pytest.mark.django_db
def test_cv_view_with_wrong_token(client):
    url = reverse("resume:cv")
    r = client.get(f"{url}?token=wrong")
    assert r.status_code == 403

    content = r.content.decode("utf-8")
    assert "Please write a mail" in content


@pytest.fixture
def cv_token():
    token = CVToken.objects.create(receiver="test")
    return token


@pytest.mark.django_db
def test_cv_view_with_correct_token(client, cv_token):
    url = reverse("resume:cv")
    r = client.get(f"{url}?token={cv_token.token}")
    assert r.status_code == 200

    content = r.content.decode("utf-8")
    assert "avatar-container" in content
