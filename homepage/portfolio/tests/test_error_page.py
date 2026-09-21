from datetime import date
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.test import RequestFactory, override_settings
from django.urls import reverse
from wagtail.contrib.settings.registry import registry as settings_registry
from wagtail.models import Locale, Page, Site

from homepage.portfolio.models import (
    ErrorPageSettings,
    LegalPageSettings,
    PortfolioIndexPage,
    PortfolioSiteSettings,
    ProjectCategory,
    ProjectPage,
)
from homepage.portfolio.views import _portfolio_shell_context, error_501

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
        category=ProjectCategory.objects.get_or_create(name="Web")[0],
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
    if 'class="error-projects"' not in content:
        return ""
    return content.split('class="error-projects"', 1)[1].split("</nav>", 1)[0]


def test_response_has_real_status_and_server_rendered_default_content():
    site = make_site("default.test", default=True)

    response = error_501(request_for("default.test"))
    content = response.content.decode()
    document = BeautifulSoup(content, "html.parser")
    stylesheet_hrefs = {
        link["href"] for link in document.select('link[rel="stylesheet"][href]')
    }

    assert response.status_code == 501
    assert document.body.has_attr("data-portfolio-shell")
    assert document.select_one('.pagegrid[aria-hidden="true"]') is not None
    assert document.select_one('.linen[aria-hidden="true"]') is not None
    assert "Fehler 501" in content
    assert "Ablage P." in content
    assert (
        "Diese Idee hat es leider nicht weiter geschafft. Also zurück ans Zeichenbrett. "
        "Du könntest dir so lange diese Projekte anschauen."
    ) in content
    assert '<meta name="robots" content="noindex,follow">' in content
    assert "/static/portfolio/prototype/project-teasers.js" in content
    assert "/static/portfolio/prototype/site-shell.js" in content
    assert stylesheet_hrefs == {
        "/static/portfolio/fonts.css",
        "/static/portfolio/portfolio.css",
        "/static/portfolio/prototype/projekte/projekt.css",
        "/static/portfolio/prototype/motion.css",
        "/static/portfolio/prototype/501.css",
        "/static/portfolio/project-wagtail.css",
    }
    assert content.index("/static/portfolio/fonts.css") < content.index(
        "/static/portfolio/portfolio.css"
    )
    assert (
        '<link rel="preload" href="/static/portfolio/fonts/saira-variable.woff2" '
        'as="font" type="font/woff2" crossorigin>'
    ) in content
    assert 'rel="preload" href="/static/portfolio/fonts/astagina.woff2"' not in content
    assert "/static/portfolio/portfolio.css" in content
    assert "foundation.css" not in content
    assert "/static/portfolio/prototype/projekte/projekt.css" in content
    assert "/static/portfolio/prototype/501.css" in content
    assert "/static/portfolio/project-wagtail.css" in content
    assert not ErrorPageSettings.objects.filter(site=site).exists()
    assert not PortfolioSiteSettings.objects.filter(site=site).exists()
    assert not LegalPageSettings.objects.filter(site=site).exists()


def test_501_shell_uses_empty_unsaved_legal_sections_without_site_leakage():
    site = make_site("shell.test", default=True)
    request = request_for("shell.test")

    with (
        patch(
            "homepage.portfolio.views.Site.find_for_request", return_value=site
        ) as find_site,
        patch("homepage.portfolio.views.render", return_value=object()) as render,
    ):
        error_501(request)

    find_site.assert_called_once_with(request)
    context = render.call_args.args[2]
    legal_settings = context["portfolio_legal_settings"]
    assert "site" not in context
    assert list(legal_settings.imprint_sections) == []
    assert list(legal_settings.privacy_sections) == []
    assert not LegalPageSettings.objects.filter(site=site).exists()


def test_shell_context_never_performs_its_own_site_lookup():
    site = make_site("resolved.test", default=True)

    with patch(
        "homepage.portfolio.views.Site.find_for_request",
        side_effect=AssertionError("site lookup must stay with the request entry point"),
    ):
        context = _portfolio_shell_context(site=site)

    assert "site" not in context
    assert context["portfolio_index"].get_site() == site


def test_settings_are_selected_for_the_request_site():
    alpha = make_site("alpha.test", default=True)
    beta = make_site("beta.test")
    ErrorPageSettings.objects.create(
        site=alpha, headline="Alpha fehlt", sentence="Satz für Alpha."
    )
    ErrorPageSettings.objects.create(
        site=beta, headline="Beta fehlt", sentence="Satz für Beta."
    )

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
    assert f'href="{index.url}"' in content
    assert "Zur Startseite" in content


def test_one_project_is_shown_once_and_drafts_are_ignored():
    site = make_site("one.test", default=True)
    published = add_project(site, "Erstes Projekt")
    draft = add_project(site, "Geheimer Entwurf", publish=False)

    content = error_501(request_for("one.test")).content.decode()
    featured = featured_markup(content)

    assert featured.count('class="more-card related-project-card"') == 1
    assert 'class="meta related-project-card__meta"' in featured
    assert 'class="row1 related-project-card__title"' in featured
    assert published.title in featured
    assert draft.title not in featured


def test_two_of_multiple_projects_are_selected_in_tree_order_without_duplicates():
    site = make_site("many.test", default=True)
    first = add_project(site, "Erstes Projekt")
    second = add_project(site, "Zweites Projekt")
    third = add_project(site, "Drittes Projekt")

    content = error_501(request_for("many.test")).content.decode()
    featured = featured_markup(content)

    assert featured.count('class="more-card related-project-card"') == 2
    assert featured.count(f'href="{first.url}"') == 1
    assert featured.count(f'href="{second.url}"') == 1
    assert third.title not in featured
    assert featured.index(first.title) < featured.index(second.title)


def test_headline_validator_rejects_more_than_three_words_in_german():
    site = make_site("validation.test", default=True)
    settings = ErrorPageSettings(site=site, headline="Hier fehlt die Idee")

    with pytest.raises(ValidationError) as error:
        settings.full_clean()

    assert error.value.message_dict["headline"] == [
        "Die Überschrift darf höchstens drei Wörter enthalten."
    ]


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
    assert "Katharina Wersdörfer" not in content
    assert 'class="site site-header"' not in content
    assert '<footer class="site on-dark"' not in content
    assert "data-portfolio-shell" not in content
    assert 'class="pagegrid"' not in content
    assert 'class="linen"' not in content
    assert 'href="">' not in content
    assert "#projekte" not in content
    assert "#ueber-mich" not in content
    assert "#kontakt" not in content
    assert 'href="None' not in content
    assert 'href="mailto:' not in content


def test_site_without_portfolio_index_omits_index_dependent_links():
    Locale.objects.get_or_create(language_code="en")
    root = Page.add_root(instance=Page(title="Bare site", slug="bare-site"))
    site = Site.objects.create(
        hostname="bare.test",
        root_page=root,
        is_default_site=True,
        site_name="bare.test",
    )
    PortfolioSiteSettings.objects.create(
        site=site,
        brand_name="Fremde Marke",
        availability_text="Fremde Verfügbarkeit",
        profile_text="Fremdes Profil",
        contact_email="fremd@example.com",
        linkedin_url="https://example.com/linkedin",
        github_url="https://example.com/github",
        mastodon_url="https://example.com/mastodon",
        copyright_text="Fremdes Copyright",
        location_text="Fremder Ort",
    )

    response = error_501(request_for("bare.test"))
    content = response.content.decode()

    assert response.status_code == 501
    assert 'class="site site-header"' not in content
    assert '<footer class="site on-dark"' not in content
    assert "data-portfolio-shell" not in content
    assert 'class="pagegrid"' not in content
    assert 'class="linen"' not in content
    assert "Fremde Marke" not in content
    assert "Fremde Verfügbarkeit" not in content
    assert "Fremdes Profil" not in content
    assert "fremd@example.com" not in content
    assert "example.com/linkedin" not in content
    assert "example.com/github" not in content
    assert "example.com/mastodon" not in content
    assert "Fremdes Copyright" not in content
    assert "Fremder Ort" not in content
    assert "Katharina Wersdörfer" not in content
    assert 'href="">' not in content
    assert "#projekte" not in content
    assert "#ueber-mich" not in content
    assert "#kontakt" not in content
    assert 'href="mailto:' not in content
    assert 'href="/"' in content
    assert "Zur Startseite" in content


def test_error_page_settings_dependency_and_registration_are_active():
    assert "wagtail.contrib.settings" in django_settings.INSTALLED_APPS
    assert ErrorPageSettings in settings_registry
    assert [panel.field_name for panel in ErrorPageSettings.panels] == [
        "code_label",
        "headline",
        "sentence",
        "featured_projects_heading",
        "home_link_label",
    ]


def test_error_page_renders_all_editorial_labels_from_site_settings():
    site = make_site("labels.test", default=True)
    add_project(site, "Empfohlenes Projekt")
    ErrorPageSettings.objects.create(
        site=site,
        code_label="Sentinel Fehlercode",
        headline="Sentinel fehlt",
        sentence="Sentinel Erklärungssatz.",
        featured_projects_heading="Sentinel Empfehlungen",
        home_link_label="Sentinel Startlink",
    )

    content = error_501(request_for("labels.test")).content.decode()

    assert "Sentinel Fehlercode" in content
    assert "Sentinel fehlt" in content
    assert "Sentinel Erklärungssatz." in content
    assert "Sentinel Empfehlungen" in content
    assert "Sentinel Startlink" in content


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
    assert 'href="/blogs/arbeiten/#about">Über mich</a>' in content
    assert 'href="/blogs/arbeiten/#kontakt">Kontakt</a>' in content
    assert (
        '<a class="more-card related-project-card" href="/blogs/arbeiten/sicheres-projekt/">'
        in content
    )
    assert 'href="/blogs/arbeiten/"' in content
    assert "Zur Startseite" in content
    assert "default-portfolio" not in content


def test_https_multisite_index_uses_its_own_request_relative_navigation(
    client, settings
):
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
    assert (
        '<span class="brand site-header__brand">Katharina Wersdörfer</span>' in content
    )
    assert 'href="/blogs/arbeiten/#projekte">Projekte</a>' in content
    assert 'href="/blogs/arbeiten/#about">Über mich</a>' in content
    assert 'href="/blogs/arbeiten/#kontakt">Kontakt</a>' in content
    assert '<a class="tile" href="/blogs/arbeiten/sicheres-projekt/">' in content
    assert "default-portfolio" not in content

    project_response = client.get(
        "/blogs/arbeiten/sicheres-projekt/",
        secure=True,
        HTTP_HOST="secure.test:8443",
    )
    project_content = project_response.content.decode()

    assert project_response.status_code == 200
    assert 'href="/blogs/arbeiten/#projekte">Projekte</a>' in project_content
    assert "default-portfolio" not in project_content
