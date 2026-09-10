import base64
import json
import re
from datetime import date
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.urls import reverse
from wagtail.images import get_image_model
from wagtail.models import Collection
from wagtail.models import Locale, Page, Site

from homepage.portfolio.models import PortfolioIndexPage, ProjectPage, ProjectService

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
        hero_heading="Moin, ich bin Katharina",
        hero_intro="Digital Creative aus Düsseldorf",
        about_text="Ich gestalte klare digitale und gedruckte Erlebnisse.",
        contact_email="katharina@example.com",
    )
    folder.add_child(instance=index)
    index.save_revision().publish()
    return index


def add_project(index, *, title="Studio Website", live_url="", publish=True):
    project = ProjectPage(
        title=title,
        slug=title.lower().replace(" ", "-"),
        teaser_text="Strategie, Gestaltung und Umsetzung aus einer Hand.",
        category=ProjectPage.Category.WEB,
        year=date.today().year,
        services="Webdesign, UX",
        live_url=live_url,
        body="<p>Dieser Legacy-Text darf nicht mehr öffentlich erscheinen.</p>",
        content=[
            {
                "type": "statement",
                "value": {"text": "<p>Ein vollständiger, serverseitiger Projekttext.</p>"},
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
    return next(tag for tag in re.findall(r"<img\b[^>]*>", content) if f'alt="{alt}"' in tag)


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
        category=ProjectPage.Category.PRINT,
        year=1899,
        services="Editorial Design",
    )

    with pytest.raises(ValidationError) as error:
        project.full_clean()

    assert "year" in error.value.message_dict


def test_index_is_fully_rendered_without_javascript(client):
    index = make_portfolio_tree()
    project = add_project(index)
    draft = add_project(index, title="Noch nicht veröffentlicht", publish=False)

    assert index.url == "/blogs/portfolio/katharina/"
    response = client.get(index.url)
    content = response.content.decode()

    assert response.status_code == 200
    assert "<script" not in content
    assert content.count('<link rel="stylesheet"') == 1
    assert "/static/portfolio/portfolio.css" in content
    assert "foundation.css" not in content
    assert "/static/portfolio/501.css" not in content
    assert "Moin, ich bin Katharina" in content
    assert project.title in content
    assert draft.title not in content
    assert f'href="{project.url}"' in content
    assert "katharina@example.com" in content
    assert "Zum Inhalt springen" in content
    assert '<nav aria-label="Hauptnavigation">' in content


def test_hash_links_only_target_elements_rendered_by_the_index(client):
    index = make_portfolio_tree()
    add_project(index)

    index_content = client.get(index.url).content.decode()
    rendered_ids = set(re.findall(r'\bid="([^"]+)"', index_content))
    section_fragments = set(re.findall(r'href="[^"]*#([^"]+)"', index_content))

    assert section_fragments == {"main-content", "projekte", "ueber-mich", "kontakt"}
    assert section_fragments <= rendered_ids


def test_wagtail_core_browser_contract_matches_rendered_pages(client):
    index = make_portfolio_tree()
    project = add_project(index)
    add_project(index, title="Zweites Projekt")

    pages = {
        "homepage": client.get(index.url),
        "error": client.get("/portfolio/501/"),
        "project": client.get(project.url),
    }
    expected_statuses = {"homepage": 200, "error": 501, "project": 200}
    contract_path = Path(__file__).parents[3] / "quality" / "portfolio" / "contracts.json"
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
            assert document.select_one(selector) is not None, f"{page_name}: {locator_key} ({selector})"

        menu_contract = contract["menu"]
        menu_selector = locators[menu_contract["root"]]
        menu = document.select_one(menu_selector)
        assert menu is not None, f"{page_name}: menu ({menu_selector})"
        for role, locator_key in menu_contract.items():
            if role == "root":
                continue
            selector = locators[locator_key]
            assert menu.select_one(selector) is not None, f"{page_name}: menu {role} ({selector})"


def test_project_is_served_through_the_existing_wagtail_mount(client):
    index = make_portfolio_tree()
    project = add_project(index)

    assert project.url == "/blogs/portfolio/katharina/studio-website/"
    response = client.get(project.url)

    assert response.status_code == 200
    assert project.teaser_text in response.content.decode()


@pytest.mark.parametrize(
    ("live_url", "expected_link"),
    [("https://example.com/work", True), ("", False)],
)
def test_project_core_content_and_optional_live_link_are_server_rendered(live_url, expected_link):
    index = make_portfolio_tree()
    project = add_project(index, live_url=live_url)

    response = project.serve(RequestFactory().get(project.url))
    response.render()
    content = response.content.decode()

    assert "<script" not in content
    assert project.teaser_text in content
    assert "Ein vollständiger, serverseitiger Projekttext." in content
    assert "Dieser Legacy-Text darf nicht mehr öffentlich erscheinen." not in content
    assert "katharina@example.com" in content
    assert ("Website ansehen" in content) is expected_link


def test_project_renders_ordered_service_items_instead_of_the_legacy_column():
    index = make_portfolio_tree()
    project = add_project(index)
    ProjectService.objects.create(page=project, name="Umsetzung", sort_order=1)
    ProjectService.objects.create(page=project, name="Konzept", sort_order=0)

    response = project.serve(RequestFactory().get(project.url))
    response.render()
    content = response.content.decode()

    assert "Konzept, Umsetzung" in content
    assert "Webdesign, UX" not in content


def test_project_renders_the_optional_client_in_its_metadata():
    index = make_portfolio_tree()
    project = add_project(index)
    project.client = "Studio Beispiel"

    response = project.serve(RequestFactory().get(project.url))
    response.render()
    content = response.content.decode()

    assert "<dt>Kunde</dt><dd>Studio Beispiel</dd>" in content


def test_project_and_index_render_their_distinct_explicit_image_alt_text(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    index = make_portfolio_tree()
    project = add_project(index)
    project.teaser_image = make_image("Teaser")
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
    index_teaser = image_tag_with_alt(index_content, "Teaseransicht des Projekts")
    project_hero = image_tag_with_alt(project_content, "Große Detailansicht des Projekts")
    related_card = project_content.split('class="related-project-card stack"', 1)[1].split("</a>", 1)[0]
    error_card = error_content.split('class="related-project-card stack"', 1)[1].split("</a>", 1)[0]
    related_teaser = image_tag_with_alt(related_card, "")
    error_teaser = image_tag_with_alt(error_card, "")

    assert "srcset=" in index_teaser
    assert 'sizes="(min-width: 94.5rem) 21.5rem' in index_teaser
    assert 'loading="lazy"' in index_teaser
    assert "width=" in index_teaser and "height=" in index_teaser
    assert 'alt="Große Detailansicht des Projekts"' not in index_content
    assert "srcset=" in project_hero
    assert 'sizes="(min-width: 94.5rem) 90rem' in project_hero
    assert 'loading="eager"' in project_hero
    assert 'fetchpriority="high"' in project_hero
    assert "width=" in project_hero and "height=" in project_hero
    assert "srcset=" in related_teaser
    assert 'sizes="(min-width: 94.5rem) 45rem' in related_teaser
    assert 'loading="lazy"' in related_teaser
    assert "width=" in related_teaser and "height=" in related_teaser
    assert 'sizes="(min-width: 42rem) calc(50vw - 2.25rem), calc(100vw - 2rem)"' in error_teaser
    assert "Teaseransicht des Folgeprojekts" not in related_card
    assert "Teaseransicht des Projekts" not in error_card
    assert 'alt="Teaseransicht des Projekts"' not in project_content


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
            "value": stream_image(landscape, "Vollbreites Motiv", caption="Vollbreite Bildunterschrift"),
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
            "value": {"quote": "Die Zusammenarbeit war großartig.", "name": "Ada", "role": "Kundin"},
        },
    ]
    project.save_revision().publish()

    response = project.serve(RequestFactory().get(project.url))
    response.render()
    content = response.content.decode()

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
