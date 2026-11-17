"""allauth rate limits behind Traefik key on the client address, not on the proxy.

Traefik connects from one local address, so with allauth's default (no trusted
proxy) every visitor shared a single per-IP bucket: one client could exhaust
``/accounts/login/`` (and the IndieAuth sign-in that redirects there) for all
others. See docs/admin_login_throttle.rst.
"""

import pytest
from allauth.core.internal.httpkit import get_client_ip
from cast.models import TemplateBaseDirectory
from django.core.cache import cache
from django.test import RequestFactory
from django.urls import reverse
from wagtail.models import Locale, Page, Site

from homepage.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PROXY = "127.0.0.1"
ATTACKER = "203.0.113.9"
VISITOR = "198.51.100.7"


@pytest.fixture(autouse=True)
def fresh_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def login_site():
    """The login page extends the site's cast theme."""
    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node() or Page.add_root(instance=Page(title="Root", slug="root"))
    Site.objects.all().delete()
    site = Site.objects.create(hostname="testserver", root_page=root, is_default_site=True)
    TemplateBaseDirectory.objects.create(site=site, name="bootstrap4")


def test_client_ip_is_the_address_traefik_appended():
    request = RequestFactory().get("/", REMOTE_ADDR=PROXY, HTTP_X_FORWARDED_FOR=f"192.0.2.1, {ATTACKER}")

    assert get_client_ip(request) == ATTACKER


def test_client_ip_falls_back_to_the_peer_without_forwarding():
    request = RequestFactory().get("/", REMOTE_ADDR=PROXY)

    assert get_client_ip(request) == PROXY


def test_one_client_cannot_exhaust_the_login_rate_limit_for_others(client, login_site):
    UserFactory(username="visitor")
    url = reverse("account_login")

    def attempt(address, username):
        return client.post(
            url,
            {"login": username, "password": "wrong-password"},
            REMOTE_ADDR=PROXY,
            HTTP_X_FORWARDED_FOR=address,
        )

    # Distinct usernames, so only the per-address limits apply.
    statuses = [attempt(ATTACKER, f"guess{number}").status_code for number in range(31)]
    assert 429 in statuses

    assert attempt(VISITOR, "visitor").status_code == 200
