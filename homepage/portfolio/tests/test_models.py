from datetime import date
from importlib import import_module
from unittest.mock import patch

import pytest
from django.apps import apps as django_apps
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from wagtail.admin.panels import InlinePanel
from wagtail.fields import StreamField
from wagtail.images import get_image_model
from wagtail.models import Collection, Locale, Page, PageViewRestriction, Site

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
    index = PortfolioIndexPage(
        title="Katharina Wersdörfer",
        slug="portfolio-data-test",
        hero_heading="Moin",
        contact_email="katharina@example.com",
    )
    root.add_child(instance=index)
    index.save_revision().publish()
    return index


def add_project(index, title, *, publish=True):
    project = ProjectPage(
        title=title,
        slug=title.lower().replace(" ", "-"),
        teaser_text=f"Teaser für {title}",
        category=ProjectPage.Category.WEB,
        year=date.today().year,
        services="Strategie, Design",
        body="<p>Bestehender Projekttext.</p>",
        live=False,
    )
    index.add_child(instance=project)
    revision = project.save_revision()
    if publish:
        revision.publish()
    return project


def make_image(title="Motiv", *, width=1200, height=800):
    collection = Collection.get_first_root_node()
    if collection is None:
        collection = Collection.add_root(instance=Collection(name="Root"))
    return get_image_model().objects.create(
        collection=collection,
        title=title,
        file=f"original_images/{title.lower()}.jpg",
        width=width,
        height=height,
    )


def test_portfolio_projects_are_only_live_public_project_pages_in_tree_order():
    index = make_portfolio_tree()
    first = add_project(index, "Erstes Projekt")
    draft = add_project(index, "Entwurf", publish=False)
    private = add_project(index, "Privates Projekt")
    last = add_project(index, "Letztes Projekt")
    PageViewRestriction.objects.create(page=private, restriction_type=PageViewRestriction.LOGIN)

    unrelated = Page(title="Keine Projektseite", slug="keine-projektseite", live=True)
    index.add_child(instance=unrelated)

    projects = list(index.get_portfolio_projects())

    assert [project.pk for project in projects] == [first.pk, last.pk]
    assert all(isinstance(project, ProjectPage) for project in projects)
    assert draft.pk not in [project.pk for project in projects]


def test_successor_projects_wrap_in_tree_order_without_duplicates():
    index = make_portfolio_tree()
    first = add_project(index, "Eins")
    second = add_project(index, "Zwei")
    third = add_project(index, "Drei")
    fourth = add_project(index, "Vier")

    assert [project.pk for project in first.get_other_projects()] == [second.pk, third.pk]
    assert [project.pk for project in third.get_other_projects()] == [fourth.pk, first.pk]
    assert [project.pk for project in fourth.get_other_projects()] == [first.pk, second.pk]


def test_successor_projects_handle_zero_or_one_alternative():
    index = make_portfolio_tree()
    only = add_project(index, "Allein")

    assert only.get_other_projects() == []

    second = add_project(index, "Zu zweit")
    assert [project.pk for project in only.get_other_projects()] == [second.pk]
    assert [project.pk for project in second.get_other_projects()] == [only.pk]


def test_context_uses_the_same_wrapped_successor_contract():
    index = make_portfolio_tree()
    first = add_project(index, "Eins")
    second = add_project(index, "Zwei")
    third = add_project(index, "Drei")

    context = third.get_context(RequestFactory().get("/"))

    assert [project.pk for project in context["other_projects"]] == [first.pk, second.pk]


def test_project_context_resolves_its_portfolio_index_once():
    index = make_portfolio_tree()
    project = add_project(index, "Einmaliger Index")

    with patch.object(project, "get_portfolio_index", wraps=project.get_portfolio_index) as resolver:
        context = project.get_context(RequestFactory().get("/"))

    assert resolver.call_count == 1
    assert context["portfolio_index"].pk == index.pk


def test_services_are_editor_sortable_and_have_a_legacy_fallback():
    index = make_portfolio_tree()
    project = add_project(index, "Sortierte Leistungen")

    assert project.get_service_names() == ["Strategie", "Design"]

    ProjectService.objects.create(page=project, name="Umsetzung", sort_order=2)
    ProjectService.objects.create(page=project, name="Konzept", sort_order=0)
    ProjectService.objects.create(page=project, name="Gestaltung", sort_order=1)

    assert project.get_service_names() == ["Konzept", "Gestaltung", "Umsetzung"]


def test_wagtail_editor_uses_structured_fields_and_hides_legacy_fields():
    services_panel = next(panel for panel in ProjectPage.content_panels if isinstance(panel, InlinePanel))
    content_field = ProjectPage._meta.get_field("content")

    assert services_panel.relation_name == "service_items"
    assert services_panel.min_num == 1
    assert isinstance(content_field, StreamField)
    assert content_field.stream_block.meta.block_counts == {
        "statement": {"max_num": 1},
        "challenge_solution": {"max_num": 1},
        "stats": {"max_num": 1},
        "testimonial": {"max_num": 1},
    }
    assert ProjectPage._meta.get_field("services").editable is False
    assert ProjectPage._meta.get_field("body").editable is False


def test_unsaved_project_preview_reads_in_memory_service_items():
    project = ProjectPage(
        title="Noch ungespeichert",
        teaser_text="Vorschau",
        category=ProjectPage.Category.WEB,
        year=date.today().year,
    )
    project.service_items.add(ProjectService(name="Konzept"), ProjectService(name="Umsetzung"))

    assert project.pk is None
    assert project.get_service_names() == ["Konzept", "Umsetzung"]


def test_project_images_need_explicit_alt_text_when_selected():
    index = make_portfolio_tree()
    project = add_project(index, "Bildvalidierung")
    image = make_image()
    project.teaser_image = image
    project.hero_image = image

    with pytest.raises(ValidationError) as error:
        project.full_clean()

    assert ProjectPage._meta.get_field("teaser_image").blank is True
    assert ProjectPage._meta.get_field("hero_image").blank is True
    assert "teaser_image_alt" in error.value.message_dict
    assert "hero_image_alt" in error.value.message_dict

    project.teaser_image_alt = "Plakatentwurf auf orangefarbenem Grund"
    project.hero_image_alt = "Detailansicht des gestalteten Plakats"
    project.full_clean()


def test_legacy_data_migration_preserves_source_and_populates_new_contract():
    index = make_portfolio_tree()
    project = add_project(index, "Migration")
    migration = import_module("homepage.portfolio.migrations.0004_migrate_legacy_project_content")

    migration.migrate_legacy_project_content(django_apps, None)
    migration.migrate_legacy_project_content(django_apps, None)
    project.refresh_from_db()

    assert list(project.service_items.values_list("name", "sort_order")) == [
        ("Strategie", 0),
        ("Design", 1),
    ]
    assert project.services == "Strategie, Design"
    assert project.body == "<p>Bestehender Projekttext.</p>"
    assert len(project.content) == 1
    assert project.content[0].block_type == "statement"
    assert "Bestehender Projekttext." in str(project.content[0].value["text"])


def test_legacy_service_migration_does_not_truncate_a_valid_old_value():
    index = make_portfolio_tree()
    project = add_project(index, "Lange Leistung")
    long_service = "A" * 240
    ProjectPage.objects.filter(pk=project.pk).update(services=long_service, body="")
    migration = import_module("homepage.portfolio.migrations.0004_migrate_legacy_project_content")

    migration.migrate_legacy_project_content(django_apps, None)

    assert ProjectService.objects.get(page=project).name == long_service
