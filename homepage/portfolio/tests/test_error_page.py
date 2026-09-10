from datetime import date
from unittest.mock import patch

import pytest
from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.test import RequestFactory, override_settings
from django.urls import reverse
from wagtail.contrib.settings.registry import registry as settings_registry
from wagtail.models import Locale, Page, Site

from homepage.portfolio.models import ErrorPageSettings, PortfolioIndexPage, ProjectPage
from homepage.portfolio.views import error_501

pytestmark = pytest.mark.django_db


def make_site(hostname, *, default=False, port=80, index_slug="portfolio"):
    Locale.objects.get_or_create(language_code="en")
    root = Page.add_root(instance=Page(title=hostname, slug=hostname.replace(".", "-")))
    site = Site.objects.create(
        hostname=hostname,
        root_page=root,
        is_default_site=default,
        site_name=hostname,
        port=port,
    )
    index = PortfolioIndexPage(
        title="Katharina Wersdörfer",
        slug=index_slug,
        hero_heading="Moin, ich bin Katharina",
        contact_email="katharina@example.com",
    )
    root.add_child(instance=index)
    index.save_revision().publish()
    return site


def request_for(hostname):
    return RequestFactory().get("/501/", HTTP_HOST=hostname)


def add_project(site, title, *, publish=True):
    index = PortfolioIndexPage.objects.descendant_of(site.root_page).get()
    project = ProjectPage(
        title=title,
        slug=title.lower().replace(" ", "-"),
        teaser_text=f"Teaser für {title}.",
        category=ProjectPage.Category.WEB,
        year=date.today().year,
        services="Design",
        live=False,
    )
    index.add_child(instance=project)
    revision = project.save_revision()
    if publish:
        revision.publish()
    return project


def featured_markup(content):
    if 'class="grid project-grid error-projects"' not in content:
        return ""
    return content.split('class="grid project-grid error-projects"', 1)[1].split("</section>", 1)[0]


def test_response_has_real_status_and_server_rendered_default_content():
    site = make_site("default.test", default=True)

    response = error_501(request_for("default.test"))
    content = response.content.decode()

    assert response.status_code == 501
    assert "Fehler 501" in content
    assert "Ablage P." in content
    assert (
        "Diese Idee hat es leider nicht weiter geschafft. Also zurück ans Zeichenbrett. "
        "Du könntest dir so lange diese Projekte anschauen."
    ) in content
    assert '<meta name="robots" content="noindex,follow">' in content
    assert "<script" not in content
    assert content.count('<link rel="stylesheet"') == 1
    assert "/static/portfolio/portfolio.css" in content
    assert "foundation.css" not in content
    assert "/static/portfolio/501.css" not in content
    assert not ErrorPageSettings.objects.filter(site=site).exists()


def test_settings_are_selected_for_the_request_site():
    alpha = make_site("alpha.test", default=True)
    beta = make_site("beta.test")
    ErrorPageSettings.objects.create(site=alpha, headline="Alpha fehlt", sentence="Satz für Alpha.")
    ErrorPageSettings.objects.create(site=beta, headline="Beta fehlt", sentence="Satz für Beta.")

    alpha_content = error_501(request_for("alpha.test")).content.decode()
    beta_content = error_501(request_for("beta.test")).content.decode()

    assert "Alpha fehlt" in alpha_content
    assert "Beta fehlt" not in alpha_content
    assert "Beta fehlt" in beta_content
    assert "Alpha fehlt" not in beta_content


def test_unknown_host_uses_the_default_site_settings():
    default_site = make_site("default.test", default=True)
    ErrorPageSettings.objects.create(
        site=default_site,
        headline="Idee verirrt",
        sentence="Der Entwurf sucht noch seinen Ausgang.",
    )

    content = error_501(request_for("unknown.test")).content.decode()

    assert "Idee verirrt" in content
    assert "Der Entwurf sucht noch seinen Ausgang." in content


def test_zero_projects_keeps_the_start_link_and_omits_the_teaser_grid():
    site = make_site("zero.test", default=True)
    index = PortfolioIndexPage.objects.descendant_of(site.root_page).get()

    content = error_501(request_for("zero.test")).content.decode()

    assert "error-projects" not in content
    assert "related-project-card" not in content
    assert f'href="{index.url}">Zur Startseite</a>' in content


def test_one_project_is_shown_once_and_drafts_are_ignored():
    site = make_site("one.test", default=True)
    published = add_project(site, "Erstes Projekt")
    draft = add_project(site, "Geheimer Entwurf", publish=False)

    content = error_501(request_for("one.test")).content.decode()
    featured = featured_markup(content)

    assert featured.count('class="related-project-card stack"') == 1
    assert '<div class="related-project-card__meta">' in featured
    assert '<h3 class="related-project-card__title">' in featured
    assert published.title in featured
    assert draft.title not in featured


def test_two_of_multiple_projects_are_selected_in_tree_order_without_duplicates():
    site = make_site("many.test", default=True)
    first = add_project(site, "Erstes Projekt")
    second = add_project(site, "Zweites Projekt")
    third = add_project(site, "Drittes Projekt")

    content = error_501(request_for("many.test")).content.decode()
    featured = featured_markup(content)

    assert featured.count('class="related-project-card stack"') == 2
    assert featured.count(f'href="{first.url}"') == 1
    assert featured.count(f'href="{second.url}"') == 1
    assert third.title not in featured
    assert featured.index(first.title) < featured.index(second.title)


def test_headline_validator_rejects_more_than_three_words_in_german():
    site = make_site("validation.test", default=True)
    settings = ErrorPageSettings(site=site, headline="Hier fehlt die Idee")

    with pytest.raises(ValidationError) as error:
        settings.full_clean()

    assert error.value.message_dict["headline"] == ["Die Überschrift darf höchstens drei Wörter enthalten."]


def test_preview_route_is_explicit_and_does_not_mount_a_catch_all(client):
    make_site("testserver", default=True)

    with override_settings(ROOT_URLCONF="homepage.portfolio.urls"):
        response = client.get("/501/")
        missing = client.get("/anything-else/")

    assert response.status_code == 501
    assert missing.status_code == 404


def test_project_route_is_mounted_under_an_explicit_prefix(client):
    make_site("testserver", default=True)

    assert reverse("portfolio:error_501") == "/portfolio/501/"
    assert client.get("/portfolio/501/").status_code == 501


def test_missing_site_uses_defaults_without_broken_navigation():
    with patch("homepage.portfolio.views.Site.find_for_request", return_value=None):
        response = error_501(request_for("missing.test"))

    content = response.content.decode()

    assert response.status_code == 501
    assert "Ablage P." in content
    assert ">Katharina Wersdörfer</span>" in content
    assert 'href="">' not in content
    assert "#projekte" not in content
    assert "#ueber-mich" not in content
    assert "#kontakt" not in content
    assert 'href="None' not in content
    assert 'href="mailto:' not in content


def test_site_without_portfolio_index_omits_index_dependent_links():
    Locale.objects.get_or_create(language_code="en")
    root = Page.add_root(instance=Page(title="Bare site", slug="bare-site"))
    Site.objects.create(
        hostname="bare.test",
        root_page=root,
        is_default_site=True,
        site_name="bare.test",
    )

    response = error_501(request_for("bare.test"))
    content = response.content.decode()

    assert response.status_code == 501
    assert 'href="">' not in content
    assert "#projekte" not in content
    assert "#ueber-mich" not in content
    assert "#kontakt" not in content
    assert 'href="mailto:' not in content
    assert 'href="/">Zur Startseite</a>' in content


def test_error_page_settings_dependency_and_registration_are_active():
    assert "wagtail.contrib.settings" in django_settings.INSTALLED_APPS
    assert ErrorPageSettings in settings_registry
    assert [panel.field_name for panel in ErrorPageSettings.panels] == ["headline", "sentence"]


def test_https_multisite_links_are_relative_to_the_request_site():
    make_site("default.test", default=True, index_slug="default-portfolio")
    secure_site = make_site("secure.test", port=8443, index_slug="arbeiten")
    add_project(secure_site, "Sicheres Projekt")
    request = RequestFactory().get(
        "/portfolio/501/",
        secure=True,
        HTTP_HOST="secure.test:8443",
    )

    content = error_501(request).content.decode()

    assert 'href="/blogs/arbeiten/">Katharina Wersdörfer</a>' in content
    assert 'href="/blogs/arbeiten/#projekte">Projekte</a>' in content
    assert 'href="/blogs/arbeiten/#ueber-mich">Über mich</a>' in content
    assert 'href="/blogs/arbeiten/#kontakt">Kontakt</a>' in content
    assert (
        '<a class="related-project-card stack" href="/blogs/arbeiten/sicheres-projekt/">'
        in content
    )
    assert 'href="/blogs/arbeiten/">Zur Startseite</a>' in content
    assert "default-portfolio" not in content


def test_https_multisite_index_uses_its_own_request_relative_navigation(client, settings):
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "secure.test"]
    make_site("default.test", default=True, index_slug="default-portfolio")
    secure_site = make_site("secure.test", port=8443, index_slug="arbeiten")
    add_project(secure_site, "Sicheres Projekt")

    response = client.get(
        "/blogs/arbeiten/",
        secure=True,
        HTTP_HOST="secure.test:8443",
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert 'href="/blogs/arbeiten/">Katharina Wersdörfer</a>' in content
    assert 'href="/blogs/arbeiten/#projekte">Projekte</a>' in content
    assert 'href="/blogs/arbeiten/#ueber-mich">Über mich</a>' in content
    assert 'href="/blogs/arbeiten/#kontakt">Kontakt</a>' in content
    assert '<h3><a href="/blogs/arbeiten/sicheres-projekt/">Sicheres Projekt</a></h3>' in content
    assert "default-portfolio" not in content

    project_response = client.get(
        "/blogs/arbeiten/sicheres-projekt/",
        secure=True,
        HTTP_HOST="secure.test:8443",
    )
    project_content = project_response.content.decode()

    assert project_response.status_code == 200
    assert 'href="/blogs/arbeiten/#projekte">Zurück zu den Projekten</a>' in project_content
    assert "default-portfolio" not in project_content
