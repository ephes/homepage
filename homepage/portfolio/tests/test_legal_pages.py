from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.test import override_settings
from django.urls import get_script_prefix, include, path, reverse, set_script_prefix
from wagtail import urls as wagtail_urls
from wagtail.contrib.settings.registry import registry as settings_registry
from wagtail.fields import StreamField
from wagtail.models import Page, PageViewRestriction, Site

from homepage.portfolio.models import LegalPageSettings, PortfolioSiteSettings
from homepage.portfolio.views import _portfolio_index_for_site, imprint, privacy

from .test_pages import add_project, make_portfolio_tree
from .test_styles import declarations_for, layer_body

pytestmark = pytest.mark.django_db


# A narrow URLConf used to prove that the compatibility routes remain safe if
# Wagtail's catch-all is moved from /blogs/ to the site root.
urlpatterns = [
    path("impressum/", imprint, name="portfolio_imprint"),
    path("datenschutz/", privacy, name="portfolio_privacy"),
    path("", include(wagtail_urls)),
]


def test_legal_route_paths_match_the_site_setting_defaults():
    settings = PortfolioSiteSettings()

    assert settings.imprint_url == reverse("portfolio_imprint")
    assert settings.privacy_url == reverse("portfolio_privacy")


def test_legal_routes_render_the_complete_canonical_server_content(client):
    index = make_portfolio_tree()
    add_project(index)

    imprint = client.get(reverse("portfolio_imprint"))
    privacy = client.get(reverse("portfolio_privacy"))
    imprint_content = imprint.content.decode()
    privacy_content = privacy.content.decode()

    assert imprint.status_code == 200
    assert privacy.status_code == 200
    assert 'class="portfolio-site imprint-page"' in imprint_content
    assert 'class="portfolio-site privacy-page"' in privacy_content
    assert 'data-portfolio-shell data-project="legal"' in imprint_content
    assert 'data-portfolio-shell data-project="legal"' in privacy_content
    assert "Angaben gemäß § 5 Digitale-Dienste-Gesetz (DDG)" in imprint_content
    assert "Augustastraße 6" in imprint_content
    assert "Diese Website setzt keine Cookies ein" in privacy_content
    assert "Stand: September 2026" in privacy_content
    assert 'href="https://www.ldi.nrw.de/"' in privacy_content
    assert 'href="#seitenanfang" aria-label="Zurück nach oben"' in imprint_content
    assert 'href="/impressum/" aria-current="page"' in imprint_content
    assert 'href="/datenschutz/" aria-current="page"' in privacy_content
    assert (
        imprint.context["legal_settings"]
        is imprint.context["portfolio_legal_settings"]
    )
    assert (
        privacy.context["legal_settings"]
        is privacy.context["portfolio_legal_settings"]
    )
    assert not PortfolioSiteSettings.objects.exists()
    assert not LegalPageSettings.objects.exists()


def test_legal_contact_blocks_render_the_single_site_address_without_persisting_it(
    client,
):
    make_portfolio_tree()
    site = Site.objects.get(hostname="testserver")
    PortfolioSiteSettings.objects.create(
        site=site,
        contact_email="legal-contact@example.test",
    )

    imprint = BeautifulSoup(
        client.get(reverse("portfolio_imprint")).content,
        "html.parser",
    )
    privacy = BeautifulSoup(
        client.get(reverse("portfolio_privacy")).content,
        "html.parser",
    )
    default_settings = LegalPageSettings()
    serialized_defaults = str(
        [
            default_settings.imprint_sections.raw_data,
            default_settings.privacy_sections.raw_data,
        ]
    )

    assert {
        link.get("href")
        for link in imprint.select('.legal-content a[href^="mailto:"]')
    } == {"mailto:legal-contact@example.test"}
    assert {
        link.get("href")
        for link in privacy.select('.legal-content a[href^="mailto:"]')
    } == {"mailto:legal-contact@example.test"}
    assert "legal-contact@example.test" not in serialized_defaults
    assert "example.invalid" not in serialized_defaults
    assert "mailto:" not in serialized_defaults
    assert not LegalPageSettings.objects.exists()


def test_imprint_visual_uses_the_editable_label_as_its_accessible_name(client):
    make_portfolio_tree()
    site = Site.objects.get(hostname="testserver")
    LegalPageSettings.objects.create(
        site=site,
        imprint_visual_label="Individuelles Illustrationsmotiv",
    )

    soup = BeautifulSoup(
        client.get(reverse("portfolio_imprint")).content,
        "html.parser",
    )
    visual = soup.select_one(".imprint-visual svg[role='img']")

    assert visual is not None
    assert visual["aria-label"] == "Individuelles Illustrationsmotiv"
    assert visual.select_one(".imprint-visual-label").get_text(strip=True) == (
        "Individuelles Illustrationsmotiv"
    )


def test_authored_legal_mail_link_remains_independent_from_the_global_contact(client):
    make_portfolio_tree()
    site = Site.objects.get(hostname="testserver")
    PortfolioSiteSettings.objects.create(
        site=site,
        contact_email="global@example.test",
    )
    LegalPageSettings.objects.create(
        site=site,
        imprint_sections=[
            (
                "section",
                {
                    "heading": "Weitere Stelle",
                    "copy": [
                        (
                            "paragraph",
                            '<p><a href="mailto:editorial@example.test">'
                            "Redaktioneller Kontakt</a></p>",
                        ),
                        (
                            "contact",
                            {
                                "prefix": "Allgemein:",
                                "label": "Kontakt per E-Mail",
                                "suffix": ".",
                            },
                        ),
                    ],
                },
            )
        ],
    )

    soup = BeautifulSoup(
        client.get(reverse("portfolio_imprint")).content,
        "html.parser",
    )

    assert soup.select_one('a[href="mailto:editorial@example.test"]') is not None
    global_link = soup.select_one(
        '.legal-contact a[href="mailto:global@example.test"]'
    )
    assert global_link is not None
    assert global_link.get_text() == "Kontakt per E-Mail"
    assert global_link.parent.get_text() == "Allgemein: Kontakt per E-Mail."


def make_foreign_site():
    root = Page.get_first_root_node()
    foreign_root = Page(title="Andere Site", slug="andere-site")
    root.add_child(instance=foreign_root)
    return Site.objects.create(
        hostname="foreign.test",
        root_page=foreign_root,
        site_name="Andere Site",
    )


@pytest.mark.parametrize("route_name", ["portfolio_imprint", "portfolio_privacy"])
@override_settings(ALLOWED_HOSTS=["testserver", "foreign.test"])
def test_legal_routes_do_not_expose_defaults_on_a_non_portfolio_site(
    client, route_name
):
    make_portfolio_tree()
    foreign_site = make_foreign_site()
    LegalPageSettings.objects.create(
        site=foreign_site,
        imprint_title="Nicht oeffentliches Fremd-Impressum",
        privacy_title="Nicht oeffentlicher Fremd-Datenschutz",
    )

    response = client.get(reverse(route_name), HTTP_HOST="foreign.test")

    assert response.status_code == 404
    assert b"Katharina Wersd" not in response.content
    assert b"Digitale-Dienste-Gesetz" not in response.content
    assert b"Nicht oeffentliches Fremd" not in response.content


@override_settings(ALLOWED_HOSTS=["testserver", "foreign.test"])
def test_legal_routes_defer_slug_collisions_to_the_foreign_wagtail_site(
    client,
):
    make_portfolio_tree()
    foreign_site = make_foreign_site()
    wagtail_imprint = Page(title="Rechtsseite der anderen Site", slug="impressum")
    foreign_site.root_page.add_child(instance=wagtail_imprint)
    wagtail_imprint.save_revision().publish()

    response = client.get(reverse("portfolio_imprint"), HTTP_HOST="foreign.test")

    assert response.status_code == 302
    assert response.url == "/blogs/impressum/"
    assert not LegalPageSettings.objects.filter(site__hostname="foreign.test").exists()


@pytest.mark.parametrize(
    ("route_name", "slug"),
    [
        ("portfolio_imprint", "impressum"),
        ("portfolio_privacy", "datenschutz"),
    ],
)
def test_legal_routes_defer_slug_collisions_on_the_portfolio_site(
    client, route_name, slug
):
    make_portfolio_tree()
    site = Site.objects.get(hostname="testserver")
    wagtail_legal_page = Page(title="Eigene Rechtsseite", slug=slug)
    site.root_page.add_child(instance=wagtail_legal_page)
    wagtail_legal_page.save_revision().publish()
    response = client.get(reverse(route_name))

    assert response.status_code == 302
    assert response.url == f"/blogs/{slug}/"
    assert not LegalPageSettings.objects.exists()


def test_legal_routes_delegate_live_view_restricted_pages(client):
    make_portfolio_tree()
    site = Site.objects.get(hostname="testserver")
    restricted_page = Page(title="Geschütztes Impressum", slug="impressum")
    site.root_page.add_child(instance=restricted_page)
    restricted_page.save_revision().publish()
    PageViewRestriction.objects.create(
        page=restricted_page,
        restriction_type=PageViewRestriction.LOGIN,
    )
    response = client.get(reverse("portfolio_imprint"))

    assert response.status_code == 302
    assert response.url == "/blogs/impressum/"
    restricted_response = client.get(response.url)
    assert restricted_response.status_code == 302
    assert restricted_response.url.startswith(f'{reverse("wagtailcore_login")}?next=')
    assert "Digitale-Dienste-Gesetz" not in response.content.decode()
    assert not LegalPageSettings.objects.exists()


def test_legal_delegation_respects_the_request_script_prefix(client):
    make_portfolio_tree()
    site = Site.objects.get(hostname="testserver")
    wagtail_imprint = Page(title="Eigenes Impressum", slug="impressum")
    site.root_page.add_child(instance=wagtail_imprint)
    wagtail_imprint.save_revision().publish()

    original_prefix = get_script_prefix()
    try:
        set_script_prefix("/website/")
        response = client.get("/impressum/", SCRIPT_NAME="/website")
    finally:
        set_script_prefix(original_prefix)

    assert response.status_code == 302
    assert response.url == "/website/blogs/impressum/"


def test_legal_routes_preserve_a_routable_page_subroute(client):
    make_portfolio_tree()
    routed_page = Mock()
    routed_page.get_url.return_value = "/blogs/"

    with (
        patch(
            "homepage.portfolio.views.Page.route_for_request",
            return_value=(routed_page, ("impressum",), {"language": "de"}),
        ) as route_for_request,
        patch(
            "homepage.portfolio.views.wagtail_views.serve",
            return_value=HttpResponse("Routable Impressumsansicht"),
        ) as wagtail_serve,
    ):
        response = client.get(reverse("portfolio_imprint"))

    assert response.status_code == 200
    assert response.content == b"Routable Impressumsansicht"
    route_request, route_path = route_for_request.call_args.args
    assert route_request.path == "/impressum/"
    assert route_path == "impressum/"
    serve_request, serve_path = wagtail_serve.call_args.args
    assert serve_request is route_request
    assert serve_path == "impressum/"
    routed_page.get_url.assert_not_called()


@override_settings(ROOT_URLCONF=__name__)
def test_root_mounted_wagtail_page_is_served_instead_of_redirecting_in_a_loop(client):
    make_portfolio_tree()
    site = Site.objects.get(hostname="testserver")
    wagtail_imprint = Page(title="Eigenes Impressum", slug="impressum")
    site.root_page.add_child(instance=wagtail_imprint)
    wagtail_imprint.save_revision().publish()
    PageViewRestriction.objects.create(
        page=wagtail_imprint,
        restriction_type=PageViewRestriction.LOGIN,
    )

    response = client.get("/impressum/")

    assert response.status_code == 302
    assert response.url.startswith(f'{reverse("wagtailcore_login")}?next=')
    assert response.url != "/impressum/"
    assert "Digitale-Dienste-Gesetz" not in response.content.decode()


def test_portfolio_index_lookup_is_deterministic_for_multiple_site_indices():
    first_index = make_portfolio_tree()
    site = Site.objects.get(hostname="testserver")
    second_folder = Page(title="Weiteres Portfolio", slug="weiteres-portfolio")
    site.root_page.add_child(instance=second_folder)
    second_index = first_index.__class__(
        title="Zweite Portfolio-Startseite",
        slug="zweite-startseite",
    )
    second_folder.add_child(instance=second_index)
    second_index.save_revision().publish()

    expected = min((first_index, second_index), key=lambda page: page.path)

    assert _portfolio_index_for_site(site).pk == expected.pk


@pytest.mark.parametrize("route_name", ["portfolio_imprint", "portfolio_privacy"])
def test_legal_pages_reuse_manifest_safe_canonical_shell_assets(client, route_name):
    make_portfolio_tree()

    content = client.get(reverse(route_name)).content.decode()

    assert '/static/portfolio/prototype/projekte/projekt.css' in content
    assert '/static/portfolio/prototype/motion.css' in content
    assert '/static/portfolio/prototype/legal.css' in content
    assert '/static/portfolio/project-wagtail.css' in content
    assert '/static/portfolio/prototype/motion.js' in content
    assert '/static/portfolio/prototype/site-shell.js' in content
    assert "handwriting-glyphs.js" not in content
    assert "handwriting-contact.js" not in content
    assert "homepage.js" not in content


def test_legal_copy_is_editable_per_wagtail_site(client):
    make_portfolio_tree()
    site = Site.objects.get(hostname="testserver")
    LegalPageSettings.objects.create(
        site=site,
        eyebrow="Hinweise",
        imprint_title="Anbieterkennzeichnung",
        imprint_sections=[
            (
                "section",
                {
                    "heading": "Eigene Angaben",
                    "copy": [("paragraph", "<p>Redaktionell gepflegter Text.</p>")],
                },
            )
        ],
    )

    content = client.get(reverse("portfolio_imprint")).content.decode()

    assert "Anbieterkennzeichnung" in content
    assert "Eigene Angaben" in content
    assert "Redaktionell gepflegter Text." in content
    assert "Digitale-Dienste-Gesetz" not in content


def test_legal_settings_are_registered_and_semantically_structured():
    assert LegalPageSettings in settings_registry
    assert isinstance(
        LegalPageSettings._meta.get_field("imprint_sections"), StreamField
    )
    assert isinstance(
        LegalPageSettings._meta.get_field("privacy_sections"), StreamField
    )

    settings = LegalPageSettings()

    assert [block.value["heading"] for block in settings.imprint_sections] == [
        "Anbieterin",
        "Kontakt",
    ]
    assert [block.value["heading"] for block in settings.privacy_sections] == [
        "Verantwortlich",
        "Websiteabruf",
        "E-Mail-Kontakt",
        "Cookies & Tracking",
        "Empfänger & Drittland",
        "Ihre Rechte",
        "Bereitstellung",
    ]


def test_legal_template_keeps_native_disclosure_and_heading_landmarks(client):
    make_portfolio_tree()

    soup = BeautifulSoup(
        client.get(reverse("portfolio_privacy")).content,
        "html.parser",
    )

    assert soup.select_one('a.skip-link[href="#main-content"]') is not None
    assert soup.select_one("details.site-nav > summary.menu-toggle") is not None
    assert soup.select_one('main#main-content[tabindex="-1"]') is not None
    assert len(soup.select("main h1")) == 1
    assert len(soup.select("main section.legal-section > h2")) == 7
    assert all(
        section.get("aria-labelledby") == heading.get("id")
        for section, heading in zip(
            soup.select("main section.legal-section"),
            soup.select("main section.legal-section > h2"),
            strict=True,
        )
    )


def test_wagtail_legal_adapter_owns_server_rendered_address_rhythm():
    canonical = finders.find("portfolio/prototype/legal.css")
    adapter = finders.find("portfolio/project-wagtail.css")

    assert canonical is not None
    assert adapter is not None
    with open(canonical) as css_file:
        canonical_css = css_file.read()
    with open(adapter) as css_file:
        adapter_css = css_file.read()
    canonical_paragraph = declarations_for(
        canonical_css,
        {".privacy-page .legal-copy > p"},
    )
    adapter_pages = layer_body(adapter_css, "pages")
    address_paragraph = declarations_for(adapter_pages, {".legal-copy address p"})
    privacy_address_paragraph = declarations_for(
        adapter_pages,
        {".privacy-page .legal-copy address p"},
    )
    contact_after_address = declarations_for(
        adapter_pages,
        {".privacy-page .legal-copy address + .legal-contact"},
    )

    assert ".legal-copy address p {" not in canonical_css
    assert ".privacy-page .legal-copy address p {" not in canonical_css
    assert ".privacy-page .legal-copy address + .legal-contact {" not in canonical_css
    assert canonical_paragraph["margin-block"] == (
        "var(--legal-copy-paragraph-margin, 0 .8em)"
    )
    assert address_paragraph == {"margin-block": "0"}
    assert privacy_address_paragraph == {"margin-block": "0"}
    assert contact_after_address == {
        "--legal-copy-paragraph-margin": "1.5em 0",
        "margin-block": "1.5em 0",
    }


@pytest.mark.parametrize("filename", ["impressum.html", "datenschutz.html"])
def test_canonical_legal_copy_has_no_nested_paragraphs(filename):
    document = BeautifulSoup(
        (
            Path(settings.ROOT_DIR)
            / "docs"
            / "superpowers"
            / "prototypes"
            / filename
        ).read_text(),
        "html.parser",
    )
    paragraphs = document.select(".legal-copy p")

    assert paragraphs
    assert all("legal-copy" in paragraph.parent.get("class", []) for paragraph in paragraphs)


def test_shared_site_shell_controls_organic_smil_for_reduced_motion():
    shell_path = finders.find("portfolio/prototype/site-shell.js")
    motion_path = finders.find("portfolio/prototype/motion.js")

    assert shell_path is not None
    assert motion_path is not None
    with open(shell_path) as shell_file:
        shell = shell_file.read()
    with open(motion_path) as motion_file:
        motion = motion_file.read()

    assert 'document.querySelectorAll("svg.organic-shape")' in shell
    assert 'matchMedia("(prefers-reduced-motion: reduce)")' in shell
    assert "shape.pauseAnimations()" in shell
    assert "shape.unpauseAnimations()" in shell
    assert 'addEventListener("change", syncOrganicMotion)' in shell
    assert "svg.organic-shape" not in motion
