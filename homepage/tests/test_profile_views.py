import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("usernames", [("jochen", "katharina"), ("jochen",), ("katharina",), ()])
def test_home_reads_profiles_together_and_renders_with_missing_profiles(client, django_user_model, usernames):
    profiles = {username: django_user_model.objects.create_user(username=username) for username in usernames}

    with CaptureQueriesContext(connection) as queries:
        response = client.get(reverse("home"))

    assert response.status_code == 200
    assert response.context["jochen"] == profiles.get("jochen")
    assert response.context["katharina"] == profiles.get("katharina")
    assert (b'class="h-card"' in response.content) == ("jochen" in profiles)
    assert (b'src="https://via.placeholder.com/150"' in response.content) == ("jochen" not in profiles)

    user_table = connection.ops.quote_name(django_user_model._meta.db_table)
    profile_queries = [query["sql"] for query in queries if f"FROM {user_table}" in query["sql"]]
    assert len(profile_queries) == 1, profile_queries


def test_jochen_profile_is_404_without_the_user(client):
    response = client.get(reverse("jochen"))
    assert response.status_code == 404


def test_jochen_profile_renders_for_the_user(client):
    user = get_user_model().objects.create_user(username="jochen", name="Jochen Wersdörfer")
    response = client.get(reverse("jochen"))
    assert response.status_code == 200
    assert response.context["user"] == user
