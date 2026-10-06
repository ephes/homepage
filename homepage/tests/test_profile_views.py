import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_jochen_profile_is_404_without_the_user(client):
    response = client.get(reverse("jochen"))
    assert response.status_code == 404


def test_jochen_profile_renders_for_the_user(client):
    user = get_user_model().objects.create_user(username="jochen", name="Jochen Wersdörfer")
    response = client.get(reverse("jochen"))
    assert response.status_code == 200
    assert response.context["user"] == user
