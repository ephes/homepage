"""Exercise the configured adapters through real allauth routes, with no OAuth calls."""

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.socialaccount.providers import registry
from allauth.socialaccount.providers.base import Provider, ProviderAccount
from cast.models import TemplateBaseDirectory
from django.urls import include, path, reverse
from wagtail.models import Locale, Page, Site

from homepage.users.models import User

pytestmark = pytest.mark.django_db


class SyntheticProvider(Provider):
    id = "synthetic-signup"
    name = "Synthetic"
    uses_apps = False
    account_class = ProviderAccount

    def get_login_url(self, request, **kwargs):
        return reverse("account_login")


def social_login(request=None):
    return SocialLogin(
        provider=SyntheticProvider(request),
        user=User(username="socialuser", email="social@example.test"),
        account=SocialAccount(provider=SyntheticProvider.id, uid="synthetic-uid"),
        email_addresses=[EmailAddress(email="social@example.test", verified=True, primary=True)],
    )


def synthetic_callback(request):
    return complete_social_login(request, social_login(request))


urlpatterns = [
    path("synthetic-callback/", synthetic_callback),
    path("", include("config.urls")),
]


@pytest.fixture(autouse=True)
def signup_settings(settings, monkeypatch):
    settings.ROOT_URLCONF = __name__
    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node() or Page.add_root(instance=Page(title="Root", slug="root"))
    Site.objects.all().delete()
    site = Site.objects.create(hostname="testserver", root_page=root, is_default_site=True)
    TemplateBaseDirectory.objects.create(site=site, name="bootstrap4")
    registry.load()
    monkeypatch.setitem(registry.provider_map, SyntheticProvider.id, SyntheticProvider)


def assert_no_accounts():
    assert User.objects.count() == 0
    assert EmailAddress.objects.count() == 0
    assert SocialAccount.objects.count() == 0


@pytest.mark.parametrize("enabled", [False, True])
def test_local_signup_admission(client, settings, enabled):
    settings.ACCOUNT_ALLOW_REGISTRATION = enabled
    url = reverse("account_signup")
    response = client.get(url)
    assert response.status_code == 200
    assert (response.context.get("form") is not None) is enabled
    assert (b'id="signup_form"' in response.content) is enabled
    assert_no_accounts()

    response = client.post(
        url,
        {
            "username": "newuser",
            "email": "new@example.test",
            "password1": "Synthetic-password-472!",
            "password2": "Synthetic-password-472!",
        },
    )
    if enabled:
        assert response.status_code == 302
        user = User.objects.get(username="newuser")
        assert EmailAddress.objects.filter(user=user, email="new@example.test").count() == 1
        assert not SocialAccount.objects.exists()
    else:
        assert response.status_code == 200
        assert response.context.get("form") is None
        assert_no_accounts()


@pytest.mark.parametrize("enabled", [False, True])
def test_social_signup_form_admission(client, settings, enabled):
    settings.ACCOUNT_ALLOW_REGISTRATION = enabled
    session = client.session
    session["socialaccount_sociallogin"] = social_login().serialize()
    session.save()
    url = reverse("socialaccount_signup")
    response = client.get(url)
    assert response.status_code == 200
    assert (response.context.get("form") is not None) is enabled
    assert_no_accounts()

    response = client.post(url, {"username": "socialuser", "email": "social@example.test"})
    if enabled:
        assert response.status_code == 302
        user = User.objects.get(username="socialuser")
        assert EmailAddress.objects.filter(user=user, email="social@example.test").count() == 1
        assert SocialAccount.objects.filter(user=user, provider=SyntheticProvider.id, uid="synthetic-uid").count() == 1
    else:
        assert response.status_code == 200
        assert response.context.get("form") is None
        assert_no_accounts()


@pytest.mark.parametrize("enabled", [False, True])
def test_social_callback_auto_signup_admission(client, settings, enabled):
    settings.ACCOUNT_ALLOW_REGISTRATION = enabled
    settings.SOCIALACCOUNT_AUTO_SIGNUP = True
    response = client.get("/synthetic-callback/")
    if enabled:
        assert response.status_code == 302
        user = User.objects.get(username="socialuser")
        assert EmailAddress.objects.filter(user=user, verified=True).count() == 1
        assert SocialAccount.objects.filter(user=user, uid="synthetic-uid").count() == 1
        assert client.session["_auth_user_id"] == str(user.pk)
    else:
        assert response.status_code == 200
        assert response.context.get("form") is None
        assert_no_accounts()


@pytest.mark.parametrize("method", ["local", "social"])
def test_existing_user_login_with_registration_closed(client, settings, method):
    settings.ACCOUNT_ALLOW_REGISTRATION = False
    user = User.objects.create_user(
        username="socialuser", email="social@example.test", password="Synthetic-password-472!"
    )
    EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    SocialAccount.objects.create(user=user, provider=SyntheticProvider.id, uid="synthetic-uid")
    if method == "local":
        response = client.post(
            reverse("account_login"), {"login": user.username, "password": "Synthetic-password-472!"}
        )
    else:
        response = client.get("/synthetic-callback/")
    assert response.status_code == 302
    assert client.session["_auth_user_id"] == str(user.pk)
    assert (User.objects.count(), EmailAddress.objects.count(), SocialAccount.objects.count()) == (1, 1, 1)
