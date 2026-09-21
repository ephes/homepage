import base64
import json
import re
from datetime import date
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.contrib.staticfiles import finders
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.urls import reverse
from wagtail.images import get_image_model
from wagtail.images.models import Filter
from wagtail.models import Collection
from wagtail.models import Locale, Page, Site

from homepage.portfolio.models import (
    LegalPageSettings,
    PortfolioIndexPage,
    PortfolioSiteSettings,
    ProjectCategory,
    ProjectPage,
    ProjectService,
    default_project_content,
)

pytestmark = pytest.mark.django_db


def make_portfolio_tree():
    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node()
    if root is None:
        root = Page.add_root(instance=Page(title="Root", slug="root"))
    Site.objects.update_or_create(
        hostname="testserver",
        defaults={"root_page": root, "is_default_site": True, "site_name": "Test"},
    )
    folder = Page(title="Portfolio", slug="portfolio")
    root.add_child(instance=folder)
    index = PortfolioIndexPage(
        title="Katharina Wersdörfer",
        slug="katharina",
        hero_heading="Moin",
        hero_intro=(
            "Print habe ich im Gepäck, Illustration im Kopf und gerade ziemlich viel "
            "Interface Design für Software und Apps auf dem Tisch."
        ),
        about_text="Ich gestalte klare digitale und gedruckte Erlebnisse.",
        contact_email="katharina@example.com",
    )
    folder.add_child(instance=index)
    index.save_revision().publish()
    return index


def add_project(
    index, *, title="Studio Website", live_url="", live_link_label="", publish=True
):
    project = ProjectPage(
        title=title,
        slug=title.lower().replace(" ", "-"),
        teaser_text="Strategie, Gestaltung und Umsetzung aus einer Hand.",
        category=ProjectCategory.objects.get_or_create(name="Web")[0],
        year=date.today().year,
        services="Webdesign, UX",
        live_url=live_url,
        live_link_label=live_link_label,
        body="<p>Dieser Legacy-Text darf nicht mehr öffentlich erscheinen.</p>",
        content=[
            {
                "type": "statement",
                "value": {
                    "text": "<p>Ein vollständiger, serverseitiger Projekttext.</p>"
                },
            }
        ],
        live=False,
    )
    index.add_child(instance=project)
    revision = project.save_revision()
    if publish:
        revision.publish()
    return project


def make_image(title):
    collection = Collection.get_first_root_node()
    if collection is None:
        collection = Collection.add_root(instance=Collection(name="Root"))
    image_data = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==")
    return get_image_model().objects.create(
        collection=collection,
        title=title,
        file=SimpleUploadedFile(f"{title}.gif", image_data, content_type="image/gif"),
    )


def stream_image(image, alt, *, caption="", large=False):
    return {
        "image": {"image": image.pk, "decorative": False, "alt_text": alt},
        "caption": caption,
        "large": large,
    }


def image_tag_with_alt(content, alt):
    return next(
        tag for tag in re.findall(r"<img\b[^>]*>", content) if f'alt="{alt}"' in tag
    )


def test_page_type_constraints_match_the_portfolio_tree():
    assert PortfolioIndexPage.subpage_types == ["portfolio.ProjectPage"]
    assert ProjectPage.parent_page_types == ["portfolio.PortfolioIndexPage"]
    assert ProjectPage.subpage_types == []


def test_wagtail_pages_keep_the_existing_blogs_mount():
    """The portfolio shares the established Wagtail mount; it must not add a root catch-all."""

    assert reverse("wagtail_serve", args=["existing/page/"]) == "/blogs/existing/page/"


def test_project_year_rejects_out_of_range_values():
    Locale.objects.get_or_create(language_code="en")
    project = ProjectPage(
        title="Historisch unmöglich",
        teaser_text="Test",
        category=ProjectCategory.objects.get_or_create(name="Print")[0],
        year=1899,
        services="Editorial Design",
    )

    with pytest.raises(ValidationError) as error:
        project.full_clean()

    assert "year" in error.value.message_dict


def test_project_period_accepts_an_optional_end_year_and_rejects_reverse_order():
    index = make_portfolio_tree()
    project = add_project(index, title="Mehrjähriges Projekt")
    project.year = 2021
    project.end_year = 2024

    project.full_clean()
    assert project.year_display == "2021–2024"

    project.end_year = None
    assert project.year_display == "2021"

    project.end_year = 2020
    with pytest.raises(ValidationError) as error:
        project.full_clean()

    assert "end_year" in error.value.message_dict


def test_project_period_renders_consistently_on_every_project_surface(client):
    index = make_portfolio_tree()
    ranged_project = add_project(index, title="Projekt mit Zeitraum")
    ranged_project.year = 2021
    ranged_project.end_year = 2024
    ranged_project.save_revision().publish()
    following_project = add_project(index, title="Folgeprojekt")

    homepage = BeautifulSoup(client.get(index.url).content, "html.parser")
    project_page = BeautifulSoup(client.get(ranged_project.url).content, "html.parser")
    following_page = BeautifulSoup(client.get(following_project.url).content, "html.parser")

    homepage_details = homepage.select_one(
        f'a.tile[href="{ranged_project.url}"] .row2'
    ).get_text(" ", strip=True)
    project_year = project_page.select_one(
        ".project-meta__facts > div:last-child dd"
    ).get_text(" ", strip=True)
    related_details = following_page.select_one(
        ".related-project-card__details"
    ).get_text(" ", strip=True)

    assert homepage_details.endswith("2021–2024")
    assert project_year == "2021–2024"
    assert related_details.endswith("2021–2024")


def test_index_is_fully_server_rendered_before_progressive_enhancement(client):
    index = make_portfolio_tree()
    project = add_project(index)
    draft = add_project(index, title="Noch nicht veröffentlicht", publish=False)

    assert index.url == "/blogs/portfolio/katharina/"
    response = client.get(index.url)
    content = response.content.decode()
    document = BeautifulSoup(content, "html.parser")
    stylesheet_hrefs = {
        link["href"] for link in document.select('link[rel="stylesheet"][href]')
    }

    assert response.status_code == 200
    assert stylesheet_hrefs == {
        "/static/portfolio/fonts.css",
        "/static/portfolio/portfolio.css",
        "/static/portfolio/prototype/portfolio-startseite.css",
        "/static/portfolio/prototype/motion.css",
        "/static/portfolio/homepage.css",
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
    assert "/static/portfolio/prototype/portfolio-startseite.css" in content
    assert "/static/portfolio/prototype/motion.css" in content
    assert "/static/portfolio/homepage.css" in content
    assert "/static/portfolio/prototype/homepage.js" in content
    assert "/static/portfolio/prototype/motion.js" in content
    assert "/static/portfolio/prototype/handwriting-glyphs.js" in content
    assert "foundation.css" not in content
    assert "/static/portfolio/501.css" not in content
    assert "15+ years in branding." in content
    assert "Web &amp; Digital Design ist mein Zuhause" in content
    assert "Ich denke über Medien hinweg" in content
    assert project.title in content
    assert draft.title not in content
    assert f'href="{project.url}"' in content
    assert "katharina@wersdoerfer.de" in content
    assert "Zum Hauptinhalt" in content
    assert '<nav aria-label="Seitennavigation">' in content
    assert 'class="stage" id="stage"' in content
    assert '<canvas id="fluid" aria-hidden="true"></canvas>' in content
    assert '<div class="fallback" aria-hidden="true"><h1>Moin</h1></div>' in content
    assert 'class="pagegrid" aria-hidden="true"' in content
    assert 'class="linen" aria-hidden="true"' in content
    for section_id in ("projekte", "leistungen", "about", "kunden", "kontakt"):
        assert f'id="{section_id}"' in content


@pytest.mark.parametrize("page_kind", ["index", "project"])
def test_public_page_get_does_not_persist_default_site_settings(client, page_kind):
    index = make_portfolio_tree()
    project = add_project(index)
    site = index.get_site()
    page = index if page_kind == "index" else project

    assert not PortfolioSiteSettings.objects.filter(site=site).exists()
    assert not LegalPageSettings.objects.filter(site=site).exists()

    response = client.get(page.url)

    assert response.status_code == 200
    assert not PortfolioSiteSettings.objects.filter(site=site).exists()
    assert not LegalPageSettings.objects.filter(site=site).exists()
    legal_navigation = response.context["portfolio_legal_settings"]
    assert legal_navigation.imprint_title == "Impressum"
    assert legal_navigation.privacy_title == "Datenschutz"
    assert not legal_navigation.imprint_sections
    assert not legal_navigation.privacy_sections


def test_fresh_portfolio_omits_an_empty_project_footer_navigation(client):
    index = make_portfolio_tree()

    response = client.get(index.url)

    assert response.status_code == 200
    assert 'class="foot-col foot-projects"' not in response.content.decode()


def test_project_without_case_study_blocks_omits_landmark_and_navigation_link(client):
    index = make_portfolio_tree()
    project = add_project(index)
    project.content = []
    project.save_revision().publish()

    response = client.get(project.url)
    content = response.content.decode()

    assert response.status_code == 200
    assert response.context["project_has_case_study"] is False
    assert 'id="case-study"' not in content
    assert 'href="#case-study"' not in content


def test_project_context_reports_populated_case_study_region(client):
    index = make_portfolio_tree()
    project = add_project(index)

    response = client.get(project.url)

    assert response.status_code == 200
    assert response.context["project_has_case_study"] is True
    assert 'id="case-study"' in response.content.decode()


def test_project_gallery_fallback_uses_the_editable_navigation_label(client):
    index = make_portfolio_tree()
    project = add_project(index)
    shell = PortfolioSiteSettings.for_site(index.get_site())
    shell.gallery_label = "Sentinel Galerie"
    shell.save()

    soup = BeautifulSoup(client.get(project.url).content, "html.parser")

    assert soup.select_one("#galerie")["aria-label"] == "Sentinel Galerie"


def test_public_pages_use_site_settings_as_the_only_contact_and_social_source(client):
    index = make_portfolio_tree()
    index.contact_email = "legacy-index@example.invalid"
    index.save_revision().publish()
    project = add_project(index)
    shell = PortfolioSiteSettings.for_site(index.get_site())
    shell.contact_email = "global-contact@example.invalid"
    shell.linkedin_url = "https://social.example/linkedin-single-source"
    shell.github_url = "https://social.example/github-single-source"
    shell.mastodon_url = "https://social.example/mastodon-single-source"
    shell.save()

    responses = {
        "homepage": client.get(index.url),
        "project": client.get(project.url),
        "error": client.get("/portfolio/501/"),
        "imprint": client.get("/impressum/"),
        "privacy": client.get("/datenschutz/"),
    }

    expected_statuses = {
        "homepage": 200,
        "project": 200,
        "error": 501,
        "imprint": 200,
        "privacy": 200,
    }
    for page_name, response in responses.items():
        assert response.status_code == expected_statuses[page_name]
        content = response.content.decode()
        document = BeautifulSoup(content, "html.parser")
        public_email_addresses = {
            link["href"].removeprefix("mailto:").split("?", 1)[0]
            for link in document.select('a[href^="mailto:"]')
        }

        assert public_email_addresses == {"global-contact@example.invalid"}, page_name
        assert "legacy-index@example.invalid" not in content, page_name
        assert "katharina@wersdoerfer.de" not in content, page_name
        assert 'href="https://social.example/linkedin-single-source"' in content
        assert 'href="https://social.example/github-single-source"' in content
        assert 'href="https://social.example/mastodon-single-source"' in content


def test_sitewide_editorial_labels_render_from_site_settings(client):
    index = make_portfolio_tree()
    project = add_project(index, live_url="https://example.com/live")
    project.client = "Beispielkunde"
    project.content = default_project_content()
    project.save_revision().publish()
    add_project(index, title="Weiteres Projekt")
    shell = PortfolioSiteSettings.for_site(index.get_site())
    sentinels = {
        "contact_label": "Sentinel Kontakt",
        "projects_label": "Sentinel Projekte",
        "all_projects_label": "Sentinel Alle Projekte",
        "services_label": "Sentinel Leistungen",
        "about_label": "Sentinel Ueber Mich",
        "clients_label": "Sentinel Kunden",
        "case_study_label": "Sentinel Fallstudie",
        "gallery_label": "Sentinel Galerie",
        "results_label": "Sentinel Ergebnisse",
        "footer_pages_heading": "Sentinel Seiten",
        "project_kicker": "Sentinel Projektzaehler",
        "project_meta_category_label": "Sentinel Bereich",
        "project_meta_year_label": "Sentinel Jahr",
        "project_meta_client_label": "Sentinel Kunde",
        "project_meta_services_label": "Sentinel Projektleistungen",
        "project_live_link_label": "Sentinel Website",
        "project_statement_heading": "Sentinel Projektstatement",
        "project_challenge_heading": "Sentinel Aufgabe",
        "project_solution_heading": "Sentinel Loesung",
        "project_results_heading": "Sentinel Resultatkopf",
        "project_testimonial_label": "Sentinel Rueckmeldung",
        "related_projects_eyebrow": "Sentinel Weitere Projekte",
        "related_projects_heading": "Sentinel Weitersehen",
    }
    for field_name, value in sentinels.items():
        setattr(shell, field_name, value)
    shell.save()

    rendered_text = " ".join(
        BeautifulSoup(response.content, "html.parser").get_text(" ", strip=True)
        for response in (client.get(index.url), client.get(project.url))
    )

    for field_name, sentinel in sentinels.items():
        assert sentinel in rendered_text, field_name


def test_homepage_renders_fixed_moin_instead_of_the_legacy_hero_field(client):
    index = make_portfolio_tree()
    index.hero_heading = "Dieser Altwert darf nicht erscheinen"
    index.save_revision().publish()

    content = client.get(index.url).content.decode()
    document = BeautifulSoup(content, "html.parser")

    assert document.select_one("#stage > h1").get_text(strip=True) == "Moin"
    assert document.select_one("#stage .fallback h1").get_text(strip=True) == "Moin"
    assert "Dieser Altwert darf nicht erscheinen" not in content


def test_unpublished_project_disappears_from_every_public_project_collection(client):
    index = make_portfolio_tree()
    current = add_project(index, title="Aktuelles Projekt")
    unpublished = add_project(index, title="Wird zurückgezogen")
    first_successor = add_project(index, title="Erster Nachfolger")
    second_successor = add_project(index, title="Zweiter Nachfolger")

    unpublished.refresh_from_db()
    assert unpublished.live is True
    unpublished.unpublish()
    unpublished.refresh_from_db()

    homepage = BeautifulSoup(client.get(index.url).content, "html.parser")
    project_page = BeautifulSoup(client.get(current.url).content, "html.parser")
    homepage_tiles = {
        heading.get_text(strip=True) for heading in homepage.select("a.tile h3")
    }
    menu_projects = {
        link.get_text(strip=True)
        for link in homepage.select(".project-menu-links a:not(.project-overview-link)")
    }
    footer_projects = {
        link.get_text(strip=True) for link in homepage.select(".foot-projects li a")
    }
    related_projects = {
        heading.get_text(strip=True)
        for heading in project_page.select(".more-projects .related-project-card h3")
    }

    assert unpublished.live is False
    for public_collection in (homepage_tiles, menu_projects, footer_projects):
        assert unpublished.title not in public_collection
        assert current.title in public_collection
        assert first_successor.title in public_collection
        assert second_successor.title in public_collection
    assert related_projects == {first_successor.title, second_successor.title}
    assert unpublished.title not in project_page.get_text(" ", strip=True)


def test_homepage_project_teaser_is_derived_from_the_project_page(
    client, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    index = make_portfolio_tree()
    project = add_project(index, title="Automatischer Teaser")
    project.category = ProjectCategory.objects.get_or_create(name="Digital")[0]
    project.year = 2024
    project.homepage_is_hero = True
    project.teaser_image = make_image("Automatisches Teaserbild")
    project.teaser_image_alt = "Eigenständiges Teaserbild der Projektseite"
    project.save_revision().publish()

    homepage = BeautifulSoup(client.get(index.url).content, "html.parser")
    teaser = homepage.select_one(f'a.tile[href="{project.url}"]')

    assert teaser is not None
    assert "tile--hero" in teaser.get("class", [])
    assert teaser.select_one("h3").get_text(strip=True) == project.title
    assert teaser.select_one(".row2").get_text(" ", strip=True) == "Digital · 2024"
    desktop_source = teaser.select_one("picture source")
    mobile_image = teaser.select_one("picture img")
    assert desktop_source["media"] == "(min-width: 52.001rem)"
    assert desktop_source["sizes"] == "50vw"
    assert "fill-2100x900" in desktop_source["srcset"]
    assert mobile_image["alt"] == project.teaser_image_alt
    assert "fill-400x225" in mobile_image["src"]
    mobile_fallback = project.teaser_image.get_rendition("fill-400x225")
    assert mobile_image["width"] == str(mobile_fallback.width)
    assert mobile_image["height"] == str(mobile_fallback.height)
    assert "fill-1200x675" in mobile_image["srcset"]
    assert mobile_image["sizes"] == (
        "calc(100vw - 2 * clamp(1.25rem, 4vw, 4rem))"
    )


def test_non_lead_hero_teaser_uses_an_explicit_small_mobile_fallback(
    client, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    index = make_portfolio_tree()
    add_project(index, title="Erstes Projekt")
    project = add_project(index, title="Zweiter Hero")
    project.homepage_is_hero = True
    project.teaser_image = make_image("Zweites Hero-Teaserbild")
    project.teaser_image_alt = "Eigenständiges zweites Hero-Teaserbild"
    project.save_revision().publish()

    homepage = BeautifulSoup(client.get(index.url).content, "html.parser")
    image = homepage.select_one(f'a.tile[href="{project.url}"] picture img')

    assert image is not None
    assert "fill-480x320" in image["src"]
    mobile_fallback = project.teaser_image.get_rendition("fill-480x320")
    assert image["width"] == str(mobile_fallback.width)
    assert image["height"] == str(mobile_fallback.height)
    assert "fill-1440x960" in image["srcset"]
    project_card_template = (
        Path(__file__).parents[1]
        / "templates"
        / "portfolio"
        / "components"
        / "project_card.html"
    ).read_text()
    assert "renditions.0" not in project_card_template
    assert "{% for rendition in" not in project_card_template
    assert project_card_template.count("|responsive_image_srcset") == 2


def test_mobile_header_offset_remains_when_the_availability_strip_is_disabled(client):
    index = make_portfolio_tree()
    site = index.get_site()
    PortfolioSiteSettings.objects.create(site=site, show_availability=False)

    response = client.get(index.url)
    document = BeautifulSoup(response.content, "html.parser")
    stylesheet_path = finders.find("portfolio/portfolio.css")

    assert response.status_code == 200
    assert document.select_one(".availability-strip") is None
    assert document.select_one(".site-header + main#main-content") is not None
    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    mobile_contract = stylesheet.split("@media (max-width: 36rem)", maxsplit=1)[1]
    assert (
        ".portfolio-site[data-portfolio-shell] > .availability-strip + main"
        in mobile_contract
    )
    assert (
        ".portfolio-site[data-portfolio-shell] > main {\n"
        "      padding-block-start: 0;"
        not in mobile_contract
    )


def test_hash_links_only_target_elements_rendered_by_the_index(client):
    index = make_portfolio_tree()
    add_project(index)

    index_content = client.get(index.url).content.decode()
    rendered_ids = set(re.findall(r'\bid="([^"]+)"', index_content))
    section_fragments = set(re.findall(r'<a\b[^>]*href="[^"]*#([^"]+)"', index_content))

    assert section_fragments == {
        "main-content",
        "stage",
        "projekte",
        "leistungen",
        "about",
        "kunden",
        "kontakt",
    }
    assert section_fragments <= rendered_ids


def test_project_menu_omits_optional_results_link_when_results_are_absent(client):
    index = make_portfolio_tree()
    project = add_project(index)

    content = client.get(project.url).content.decode()
    rendered_ids = set(re.findall(r'\bid="([^"]+)"', content))
    section_fragments = set(re.findall(r'<a\b[^>]*href="#([^"]+)"', content))

    assert "ergebnisse" not in section_fragments
    assert section_fragments <= rendered_ids


def test_wagtail_core_browser_contract_matches_rendered_pages(client):
    index = make_portfolio_tree()
    project = add_project(index)
    add_project(index, title="Zweites Projekt")

    pages = {
        "homepage": client.get(index.url),
        "error": client.get("/portfolio/501/"),
        "project": client.get(project.url),
        "imprint": client.get("/impressum/"),
        "privacy": client.get("/datenschutz/"),
    }
    expected_statuses = {
        "homepage": 200,
        "error": 501,
        "project": 200,
        "imprint": 200,
        "privacy": 200,
    }
    contract_path = (
        Path(__file__).parents[3] / "quality" / "portfolio" / "contracts.json"
    )
    contract_data = json.loads(contract_path.read_text())
    locators = contract_data["locators"]
    contracts = contract_data["profiles"]["wagtail"]

    assert pages.keys() == contracts.keys()
    for page_name, response in pages.items():
        assert response.status_code == expected_statuses[page_name]
        document = BeautifulSoup(response.content, "html.parser")
        contract = contracts[page_name]
        locator_keys = [
            *(requirement["locator"] for requirement in contract["essentials"]),
            *contract["keyboardTargets"],
        ]
        for locator_key in locator_keys:
            selector = locators[locator_key]
            assert document.select_one(selector) is not None, (
                f"{page_name}: {locator_key} ({selector})"
            )

        menu_contract = contract["menu"]
        menu_selector = locators[menu_contract["root"]]
        menu = document.select_one(menu_selector)
        assert menu is not None, f"{page_name}: menu ({menu_selector})"
        for role, locator_key in menu_contract.items():
            if role == "root":
                continue
            selector = locators[locator_key]
            assert menu.select_one(selector) is not None, (
                f"{page_name}: menu {role} ({selector})"
            )


def test_project_is_served_through_the_existing_wagtail_mount(client):
    index = make_portfolio_tree()
    project = add_project(index)

    assert project.url == "/blogs/portfolio/katharina/studio-website/"
    response = client.get(project.url)

    assert response.status_code == 200
    assert project.teaser_text in response.content.decode()


def test_project_teaser_renders_bold_inline_link_without_markup_in_metadata(client):
    index = make_portfolio_tree()
    project = add_project(index)
    project.teaser_text = (
        '<p>Atmosphäre <strong>entsteht</strong> im '
        '<a href="https://example.com/eindruck">ersten Eindruck</a> für '
        '<span data-no-break="true">Studio Name</span> &amp; Partner.</p>'
    )
    project.save_revision().publish()

    response = client.get(project.url)
    document = BeautifulSoup(response.content, "html.parser")
    lead = document.select_one(".project-lead")
    description = document.select_one('meta[name="description"]')

    assert response.status_code == 200
    assert lead is not None, str(document.select_one(".project-lead"))
    assert lead.strong.get_text(strip=True) == "entsteht"
    assert lead.a["href"] == "https://example.com/eindruck"
    assert lead.select_one("[data-no-break]").get_text(strip=True) == "Studio Name"
    assert description["content"] == (
        "Atmosphäre entsteht im ersten Eindruck für Studio Name & Partner."
    )


@pytest.mark.parametrize(
    ("live_url", "expected_link"),
    [("https://example.com/work", True), ("", False)],
)
def test_project_core_content_and_optional_live_link_are_server_rendered(
    live_url, expected_link
):
    index = make_portfolio_tree()
    project = add_project(index, live_url=live_url)

    response = project.serve(RequestFactory().get(project.url))
    response.render()
    content = response.content.decode()

    assert "/static/portfolio/prototype/motion.js" in content
    assert "/static/portfolio/prototype/site-shell.js" in content
    assert "/static/portfolio/prototype/project-teasers.js" in content
    assert "/static/portfolio/project-wagtail.js" in content
    assert "/static/portfolio/prototype/projekte/projekt.js" not in content
    assert project.teaser_text in content
    assert "Ein vollständiger, serverseitiger Projekttext." in content
    assert "Dieser Legacy-Text darf nicht mehr öffentlich erscheinen." not in content
    assert "katharina@wersdoerfer.de" in content
    assert ("Website ansehen" in content) is expected_link


def test_project_live_link_uses_its_own_editable_label_over_the_global_default():
    index = make_portfolio_tree()
    project = add_project(
        index,
        live_url="https://example.com/work",
        live_link_label="Projekt besuchen",
    )
    settings = PortfolioSiteSettings.for_site(index.get_site())
    settings.project_live_link_label = "Globaler Standard"
    settings.save()

    response = project.serve(RequestFactory().get(project.url))
    response.render()
    document = BeautifulSoup(response.content, "html.parser")
    link = document.select_one(".project-live-link")

    assert link is not None
    assert link["href"] == "https://example.com/work"
    assert str(link.select_one(".pill-label").contents[0]).strip() == "Projekt besuchen"
    assert link.select_one(".ar")["aria-hidden"] == "true"
    assert "Globaler Standard" not in link.get_text()


def test_project_renders_ordered_service_items_instead_of_the_legacy_column():
    index = make_portfolio_tree()
    project = add_project(index)
    ProjectService.objects.create(page=project, name="Umsetzung", sort_order=1)
    ProjectService.objects.create(page=project, name="Konzept", sort_order=0)

    response = project.serve(RequestFactory().get(project.url))
    response.render()
    document = BeautifulSoup(response.content, "html.parser")
    services = document.select(".project-service-list li")

    assert [item.get_text(" ", strip=True) for item in services] == [
        "Konzept",
        "Umsetzung",
    ]
    assert document.select_one(".marker-list.project-service-list") is not None
    assert not document.select(".project-service-arrow")
    assert "Konzept | Umsetzung" not in response.content.decode()


def test_project_renders_the_optional_client_in_its_metadata():
    index = make_portfolio_tree()
    project = add_project(index)
    project.client = "Studio Beispiel"

    response = project.serve(RequestFactory().get(project.url))
    response.render()
    content = response.content.decode()

    assert "<dt>Kunde</dt><dd>Studio Beispiel</dd>" in content


def test_project_and_index_render_their_distinct_explicit_image_alt_text(
    client, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    index = make_portfolio_tree()
    project = add_project(index)
    teaser_image = make_image("Teaser")
    teaser_image.focal_point_x = 1
    teaser_image.focal_point_y = 1
    teaser_image.focal_point_width = 1
    teaser_image.focal_point_height = 1
    teaser_image.save(
        update_fields=[
            "focal_point_x",
            "focal_point_y",
            "focal_point_width",
            "focal_point_height",
        ]
    )
    project.teaser_image = teaser_image
    project.teaser_image_alt = "Teaseransicht des Projekts"
    project.hero_image = make_image("Hero")
    project.hero_image_alt = "Große Detailansicht des Projekts"
    project.save_revision().publish()
    related = add_project(index, title="Weiteres Projekt")
    related.teaser_image = make_image("Weiterer Teaser")
    related.teaser_image_alt = "Teaseransicht des Folgeprojekts"
    related.save_revision().publish()

    index_content = client.get(index.url).content.decode()
    project_content = client.get(project.url).content.decode()
    error_content = client.get("/portfolio/501/").content.decode()
    index_document = BeautifulSoup(index_content, "html.parser")
    index_teaser = image_tag_with_alt(index_content, "Teaseransicht des Projekts")
    index_picture = index_document.select_one(
        f'a.tile[href="{project.url}"] picture'
    )
    related_homepage_teaser = index_document.select_one(
        f'a.tile[href="{related.url}"] img'
    )
    project_hero = image_tag_with_alt(
        project_content, "Große Detailansicht des Projekts"
    )
    related_card = project_content.split('class="more-card related-project-card"', 1)[
        1
    ].split("</a>", 1)[0]
    error_card = error_content.split('class="more-card related-project-card"', 1)[
        1
    ].split("</a>", 1)[0]
    related_teaser = image_tag_with_alt(related_card, "")
    error_teaser = image_tag_with_alt(error_card, "")

    assert 'class="frame related-project-card__frame frame--image"' in related_card
    assert 'class="frame related-project-card__frame frame--image"' in error_card
    assert "srcset=" in index_teaser
    assert "fill-1200x675" in index_teaser
    assert index_picture.select_one("source")["sizes"] == "25vw"
    assert "fill-1440x960" in index_picture.select_one("source")["srcset"]
    assert (
        'sizes="calc(100vw - 2 * clamp(1.25rem, 4vw, 4rem))"'
        in index_teaser
    )
    assert "fill-1440x960" in related_homepage_teaser["srcset"]
    assert related_homepage_teaser["sizes"] == (
        "(min-width: 52.001rem) 25vw, 82vw"
    )
    assert 'loading="lazy"' in index_teaser
    assert "width=" in index_teaser and "height=" in index_teaser
    assert 'alt="Große Detailansicht des Projekts"' not in index_content
    assert "srcset=" in project_hero
    assert "fill-2100x900" in project_hero
    assert 'sizes="100vw"' in project_hero
    assert 'loading="eager"' in project_hero
    assert 'fetchpriority="high"' in project_hero
    assert "width=" in project_hero and "height=" in project_hero
    assert "srcset=" in related_teaser
    assert (
        'sizes="(min-width: 100rem) calc(50vw - 4rem), (min-width: 52rem) 46vw, '
        '(min-width: 31.25rem) 92vw, calc(100vw - 2.5rem)"'
        in related_teaser
    )
    assert 'loading="lazy"' in related_teaser
    assert "width=" in related_teaser and "height=" in related_teaser
    assert (
        'sizes="(min-width: 100rem) calc(50vw - 4rem), (min-width: 52rem) 46vw, '
        '(min-width: 31.25rem) 92vw, calc(100vw - 2.5rem)"'
        in error_teaser
    )
    assert "Teaseransicht des Folgeprojekts" not in related_card
    assert "Teaseransicht des Projekts" not in error_card
    assert 'alt="Teaseransicht des Projekts"' not in project_content
    for filter_spec in ("fill-1200x675", "fill-1440x960"):
        expected_focal_key = Filter(spec=filter_spec).get_cache_key(teaser_image)
        assert expected_focal_key
        assert teaser_image.renditions.filter(
            filter_spec=filter_spec,
            focal_point_key=expected_focal_key,
        ).exists()


def test_gallery_marks_only_paired_portraits_for_the_mobile_two_up_layout(
    client, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    index = make_portfolio_tree()
    project = add_project(index)
    portraits = [make_image(f"Portrait {number}") for number in range(1, 4)]
    for image in portraits:
        image.width = 800
        image.height = 1200
        image.save(update_fields=["width", "height"])
    project.content = [
        {
            "type": "gallery",
            "value": {
                "images": [
                    stream_image(image, f"Portraitmotiv {number}")
                    for number, image in enumerate(portraits, start=1)
                ]
            },
        }
    ]
    project.save_revision().publish()

    document = BeautifulSoup(client.get(project.url).content, "html.parser")
    gallery_images = document.select(".project-gallery > .project-image")

    assert len(gallery_images) == 3
    assert all(
        {"portrait", "portrait-paired"} <= set(image.get("class", []))
        for image in gallery_images[:2]
    )
    assert "portrait" in gallery_images[2].get("class", [])
    assert "portrait-paired" not in gallery_images[2].get("class", [])


def test_all_structured_project_blocks_are_server_rendered(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    index = make_portfolio_tree()
    project = add_project(index)
    landscape = make_image("Querformat")
    portrait = make_image("Hochformat")
    project.content = [
        {
            "type": "statement",
            "value": {"text": "<p>Ein prägnantes Projektstatement.</p>"},
        },
        {
            "type": "challenge_solution",
            "value": {
                "challenge": "<p>Eine anspruchsvolle Aufgabe.</p>",
                "solution": "<p>Eine klare Lösung.</p>",
            },
        },
        {
            "type": "full_width_image",
            "value": stream_image(
                landscape, "Vollbreites Motiv", caption="Vollbreite Bildunterschrift"
            ),
        },
        {
            "type": "image_pair",
            "value": {
                "left": stream_image(landscape, "Linkes Motiv"),
                "right": stream_image(landscape, "Rechtes Motiv"),
            },
        },
        {
            "type": "portrait_duo",
            "value": {
                "left": stream_image(portrait, "Linkes Porträt"),
                "right": stream_image(portrait, "Rechtes Porträt"),
            },
        },
        {
            "type": "gallery",
            "value": {
                "images": [
                    stream_image(landscape, "Galeriebild eins"),
                    stream_image(portrait, "Galeriebild zwei", large=True),
                ]
            },
        },
        {
            "type": "stats",
            "value": {"items": [{"value": "42 %", "label": "Mehr Anfragen"}]},
        },
        {
            "type": "testimonial",
            "value": {
                "quote": "Die Zusammenarbeit war großartig.",
                "name": "Ada",
                "role": "Kundin",
            },
        },
    ]
    project.save_revision().publish()

    response = project.serve(RequestFactory().get(project.url))
    response.render()
    content = response.content.decode()
    document = BeautifulSoup(content, "html.parser")

    for expected in (
        "Ein prägnantes Projektstatement.",
        "Eine anspruchsvolle Aufgabe.",
        "Eine klare Lösung.",
        "Vollbreite Bildunterschrift",
        'alt="Linkes Motiv"',
        'alt="Galeriebild zwei"',
        "42 %",
        "Mehr Anfragen",
        "Die Zusammenarbeit war großartig.",
        "Ada",
        "Kundin",
    ):
        assert expected in content

    full_width_image = image_tag_with_alt(content, "Vollbreites Motiv")
    paired_image = image_tag_with_alt(content, "Linkes Motiv")
    gallery_image = image_tag_with_alt(content, "Galeriebild eins")
    for image_tag in (full_width_image, paired_image, gallery_image):
        assert "srcset=" in image_tag
        assert 'loading="lazy"' in image_tag
        assert "width=" in image_tag and "height=" in image_tag
    assert 'sizes="(min-width: 94.5rem) 90rem' in full_width_image
    assert 'sizes="(min-width: 94.5rem) 45rem' in paired_image
    assert 'sizes="(min-width: 94.5rem) 21.5rem' in gallery_image
    assert content.count('id="galerie"') == 1
    assert "Projektbild · 3:2" not in content
    assert "Projektbild · 4:5" not in content
    result = document.select_one(".project-results .result")
    assert result.name == "li"
    assert [node.name for node in result.find_all(["div", "span"], recursive=False)] == [
        "div",
        "span",
    ]
    assert result.select_one(".result-value").get_text(strip=True) == "42 %"
    assert result.select_one(".result-label").get_text(strip=True) == "Mehr Anfragen"
    assert "<figcaption>Ada · Kundin</figcaption>" in content
    assert "<blockquote><p>„Die Zusammenarbeit war großartig.“</p></blockquote>" in content
