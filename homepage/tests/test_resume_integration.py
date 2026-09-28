"""Contracts between homepage's editorial overrides and django-resume's page registry."""

from datetime import timedelta
from urllib.parse import urlsplit

import pytest
from bs4 import BeautifulSoup
from cast.models import Blog
from django.contrib.staticfiles import finders
from django.urls import resolve, reverse
from django.utils import timezone
from django_resume.models import Resume
from django_resume.pages import page_registry
from django_resume.pages.builtins import CoverLetterPage, CvPage
from django_resume.plugins import plugin_registry
from wagtail.models import Locale, Page, Site

from homepage.portfolio.models import PortfolioIndexPage
from homepage.resume_cover.plugin import EditorialCoverPlugin

pytestmark = pytest.mark.django_db


@pytest.fixture
def editorial_resume(django_user_model, settings, tmp_path):
    # Rendering must never contact production media storage.
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(tmp_path)},
        },
    }
    settings.DJANGO_RESUME_TOKEN_TTL = timedelta(days=30)
    owner = django_user_model.objects.create_user(username="resume-owner")
    return Resume.objects.create(
        name="Editorial integration",
        slug="editorial-integration",
        owner=owner,
        plugin_data={
            "theme": {"name": "editorial"},
            "identity": {"name": "Ada Example", "tagline": "Editorial designer"},
            "about": {"text": "Designing useful things."},
            "cover": {
                "flat": {
                    "recipient": "Example Studio",
                    "place_date": "Berlin, 28. September 2026",
                    "subject": "Bewerbung Design",
                    "salutation": "Liebes Team,",
                    "closing": "Mit besten Grüßen",
                    "signature_name": "Ada Example",
                },
                "items": [{"id": "paragraph", "title": "Introduction", "text": "My editorial work."}],
            },
            "education": {
                "flat": {"title": "Education"},
                "items": [
                    {"id": "later", "position": 1, "school_name": "Design Academy", "degree": "MA", "end": "2024"},
                    {"id": "earlier", "position": 0, "school_name": "Art College", "degree": "BA", "end": "2022"},
                ],
            },
            "languages": {
                "flat": {"title": "Languages"},
                "items": [{"id": "german", "name": "Deutsch", "level": 100, "position": 0}],
            },
            "awards": {
                "flat": {"title": "Awards"},
                "items": [{"id": "award", "title": "Design Prize", "year": "2025", "position": 0}],
            },
            "token": {
                "flat": {"token_required": True},
                "items": [
                    {"token": "integration-valid", "created": timezone.now().isoformat()},
                    {"token": "integration-expired", "created": (timezone.now() - timedelta(days=31)).isoformat()},
                ],
            },
        },
    )


def test_registered_pages_keep_homepage_routes_and_cover_override(client, editorial_resume):
    assert isinstance(page_registry.get_page("detail"), CoverLetterPage)
    assert isinstance(page_registry.get_page("cv"), CvPage)
    assert isinstance(plugin_registry.get_plugin("cover"), EditorialCoverPlugin)
    assert "cover" in plugin_registry.get_plugin("cover").capabilities
    for name, suffix in (("detail", ""), ("cv", "cv/")):
        url = reverse(f"resume:{name}", kwargs={"slug": editorial_resume.slug})
        assert url == f"/resume/{editorial_resume.slug}/{suffix}"
        assert resolve(url).url_name == name
        assert client.post(url).status_code == 405


def test_public_cover_renders_editorial_fields_without_owner_controls(client, editorial_resume):
    response = client.get(reverse("resume:detail", args=[editorial_resume.slug]), {"edit": "true"})
    assert response.status_code == 200
    assert response.context["show_edit_button"] is False
    document = BeautifulSoup(response.content, "html.parser")
    assert document.select_one(".editorial-sheet.cover-sheet") is not None
    for text in ("Example Studio", "Bewerbung Design", "Liebes Team,", "My editorial work.", "Mit besten Grüßen"):
        assert text in document.get_text()
    assert document.select_one("[hx-post], [hx-delete], .cover-head-edit") is None
    assert document.select_one('a[download][href*="katharina-anschreiben"]') is None


def test_cv_token_policy_survives_page_registry_dispatch(client, editorial_resume):
    url = reverse("resume:cv", args=[editorial_resume.slug])
    for query in ({}, {"token": "wrong"}, {"token": "integration-expired"}):
        denied = client.get(url, query)
        assert denied.status_code == 403
        assert denied["Referrer-Policy"] == "no-referrer"
        assert "Design Academy" not in denied.content.decode()
    allowed = client.get(url, {"token": "integration-valid"})
    assert allowed.status_code == 200
    assert allowed["Referrer-Policy"] == "no-referrer"


def test_editorial_cv_renders_list_sections_and_resolves_theme_resources(client, editorial_resume, settings):
    response = client.get(reverse("resume:cv", args=[editorial_resume.slug]), {"token": "integration-valid"})
    assert response.status_code == 200
    document = BeautifulSoup(response.content, "html.parser")
    assert document.select_one(".editorial-sheet .cv-body") is not None
    education = document.select_one("#education")
    assert education is not None
    assert [item.get_text(strip=True) for item in education.select(".education-school")] == [
        "Art College",
        "Design Academy",
    ]
    assert "Deutsch" in document.get_text()
    assert "Design Prize" in document.get_text()
    assert document.select_one('a[download][href*="katharina-lebenslauf"]') is None
    assert document.select_one('a[href="#"]') is None
    # Resolve the resources actually emitted by the combined templates, including
    # dependency-provided illustration files and homepage's CSS/JS overrides.
    resources = []
    for element in document.select("[src], link[href], a[download][href], source[srcset]"):
        value = element.get("src") or element.get("href") or element.get("srcset")
        path = urlsplit(value).path
        if path.startswith(settings.STATIC_URL):
            resources.append(path.removeprefix(settings.STATIC_URL))
    assert "django_resume/css/editorial/screen.css" in resources
    assert "handwriting/handwriting.js" in resources
    for path in resources:
        assert finders.find(path), f"Rendered editorial resource is missing: {path}"


def test_owner_can_edit_and_persist_editorial_cover_fields(client, editorial_resume):
    client.force_login(editorial_resume.owner)
    cover_url = reverse("resume:detail", args=[editorial_resume.slug])
    response = client.get(cover_url, {"edit": "true"})
    assert response.status_code == 200
    assert response.context["show_edit_button"] is True
    document = BeautifulSoup(response.content, "html.parser")
    edit_url = plugin_registry.get_plugin("cover").inline.get_edit_flat_url(editorial_resume.pk)
    assert document.select_one(f'[hx-get="{edit_url}"]') is not None
    form_response = client.get(edit_url)
    assert form_response.status_code == 200
    form = BeautifulSoup(form_response.content, "html.parser").select_one("form")
    assert form.select_one('[name="closing"]') is not None
    assert form.select_one('[name="signature_img"]') is not None
    updates = {
        "recipient": "Another Studio",
        "place_date": "Berlin, heute",
        "subject": "Updated application",
        "salutation": "Guten Tag,",
        "closing": "Herzliche Grüße",
        "signature_name": "Ada Designer",
    }
    saved = client.post(form["hx-post"], updates)
    assert saved.status_code == 200
    editorial_resume.refresh_from_db()
    for field, value in updates.items():
        assert editorial_resume.plugin_data["cover"]["flat"][field] == value
    assert editorial_resume.plugin_data["cover"]["items"][0]["id"] == "paragraph"
    assert client.get(reverse("resume:cv", args=[editorial_resume.slug])).status_code == 200
    client.logout()
    public = client.get(cover_url)
    assert "Herzliche Grüße" in public.content.decode()
    assert "Another Studio" in public.content.decode()


def test_configured_resume_resources_render_real_downloads(client, editorial_resume, settings):
    from homepage.resume_cover.resources import DEFAULT_PUBLIC_RESOURCES

    resources = {**DEFAULT_PUBLIC_RESOURCES["katharina"], "portfolio_url": "/blogs/portfolio/katharina/"}
    settings.RESUME_PUBLIC_RESOURCES = {editorial_resume.slug: resources}
    for route, key in (("cv", "cv_pdf"), ("detail", "cover_pdf")):
        response = client.get(reverse(f"resume:{route}", args=[editorial_resume.slug]), {"token": "integration-valid"})
        assert response.status_code == 200
        document = BeautifulSoup(response.content, "html.parser")
        link = document.select_one("a[download]")
        assert link is not None
        assert urlsplit(link["href"]).path == settings.STATIC_URL + resources[key]
        assert finders.find(resources[key])
        if route == "cv":
            rail = document.select_one(".cv-rail--resources")
            assert rail is not None
            assert rail.select_one(f'a[href="{resources["portfolio_url"]}"]') is not None


def test_nonowner_cannot_edit_cover_or_permission_denied_page(client, editorial_resume, django_user_model):
    other = django_user_model.objects.create_user(username="another-resume-owner")
    client.force_login(other)
    response = client.get(reverse("resume:detail", args=[editorial_resume.slug]), {"edit": "true"})
    assert response.context["show_edit_button"] is False
    plugin = plugin_registry.get_plugin("cover")
    original = editorial_resume.plugin_data
    assert client.get(plugin.inline.get_edit_flat_url(editorial_resume.pk)).status_code == 403
    assert (
        client.post(plugin.inline.get_edit_flat_post_url(editorial_resume.pk), {"closing": "Changed"}).status_code
        == 403
    )
    assert client.get(reverse("resume:403", args=[editorial_resume.slug])).status_code == 403
    editorial_resume.refresh_from_db()
    assert editorial_resume.plugin_data == original


def test_trusted_authenticated_accounts_can_read_but_not_edit_other_cvs(client, editorial_resume, django_user_model):
    """Preserve django-resume's existing account policy, not just anonymous tokens."""
    other = django_user_model.objects.create_user(username="trusted-reader")
    client.force_login(other)
    response = client.get(reverse("resume:cv", args=[editorial_resume.slug]), {"edit": "true"})
    assert response.status_code == 200
    assert response.context["show_edit_button"] is False
    assert response["Referrer-Policy"] == "no-referrer"
    assert BeautifulSoup(response.content, "html.parser").select_one("[hx-post], [hx-delete]") is None


def test_public_signup_stays_closed_for_trusted_account_cv_access(settings, rf):
    from homepage.users.adapters import AccountAdapter, SocialAccountAdapter

    assert settings.ACCOUNT_ALLOW_REGISTRATION is False
    request = rf.get("/accounts/signup/")
    assert AccountAdapter().is_open_for_signup(request) is False
    assert SocialAccountAdapter().is_open_for_signup(request, None) is False


def test_resume_routes_coexist_with_cast_and_portfolio_tree(client, editorial_resume):
    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node()
    if root is None:
        root = Page.add_root(instance=Page(title="Root", slug="root"))
    Site.objects.update_or_create(
        hostname="testserver",
        defaults={"root_page": root, "is_default_site": True},
    )
    blog = root.add_child(instance=Blog(title="Integration blog", slug="integration-blog"))
    portfolio = root.add_child(
        instance=PortfolioIndexPage(title="Integration portfolio", slug="integration-portfolio")
    )
    blog.save_revision().publish()
    portfolio.save_revision().publish()
    assert Blog.objects.get(pk=blog.pk).specific == blog
    assert PortfolioIndexPage.objects.get(pk=portfolio.pk).specific == portfolio
    assert blog.url.startswith("/blogs/")
    assert portfolio.url.startswith("/blogs/")
    assert resolve(portfolio.url).url_name == "wagtail_serve"
    assert client.get(portfolio.url).status_code == 200
    assert client.get(reverse("portfolio:error_501")).status_code == 501
    assert client.get(reverse("resume:detail", args=[editorial_resume.slug])).status_code == 200
