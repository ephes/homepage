from datetime import date
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from wagtail.admin.panels import InlinePanel
from wagtail.fields import RichTextField, StreamField
from wagtail.images import get_image_model
from wagtail.models import Collection, Locale, Page, PageViewRestriction, Site

from homepage.portfolio.models import (
    LegalPageSettings,
    PortfolioAboutItem,
    PortfolioClient,
    PortfolioIndexPage,
    PortfolioService,
    PortfolioSiteSettings,
    ProjectCategory,
    ProjectPage,
    ProjectService,
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
    index = PortfolioIndexPage(
        title="Katharina Wersdörfer",
        slug="portfolio-data-test",
        hero_heading="Moin",
    )
    root.add_child(instance=index)
    index.save_revision().publish()
    return index


def add_project(index, title, *, publish=True):
    project = ProjectPage(
        title=title,
        slug=title.lower().replace(" ", "-"),
        teaser_text=f"Teaser für {title}",
        category=ProjectCategory.objects.get_or_create(name="Web")[0],
        year=date.today().year,
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


def test_native_page_reordering_controls_the_public_project_order():
    index = make_portfolio_tree()
    first = add_project(index, "Erstes Projekt")
    second = add_project(index, "Zweites Projekt")
    third = add_project(index, "Drittes Projekt")

    third.move(first, pos="left")

    assert PortfolioIndexPage.admin_default_ordering == "ord"
    assert [project.pk for project in index.get_portfolio_projects()] == [
        third.pk,
        first.pk,
        second.pk,
    ]


def test_nine_projects_are_independent_editable_children_of_the_portfolio_index():
    index = make_portfolio_tree()
    projects = []
    for number in range(1, 10):
        project = add_project(index, f"Projekt {number}")
        assert [block.block_type for block in project.content] == [
            "statement",
            "challenge_solution",
            "stats",
            "testimonial",
        ]
        project.teaser_text = f"Eigenständiger Teaser {number}"
        project.content = [
            {
                "type": "statement",
                "value": {"text": f"<p>Eigenständiger Projekttext {number}</p>"},
            }
        ]
        project.save_revision().publish()
        projects.append(project)

    rendered_projects = list(index.get_portfolio_projects())

    assert ProjectPage.can_create_at(index) is True
    assert len(rendered_projects) == 9
    assert [project.pk for project in rendered_projects] == [project.pk for project in projects]
    assert {project.teaser_text for project in rendered_projects} == {
        f"Eigenständiger Teaser {number}" for number in range(1, 10)
    }
    assert {str(project.content[0].value["text"]) for project in rendered_projects} == {
        f"<p>Eigenständiger Projekttext {number}</p>" for number in range(1, 10)
    }


def test_portfolio_hero_copy_defaults_match_the_approved_current_prototype():
    index = make_portfolio_tree()

    assert index.hero_intro_emphasis == "Web & Digital Design ist mein Zuhause"
    assert index.hero_intro_secondary.startswith("Ich denke über Medien hinweg")
    assert index.hero_note_heading == "15+ years in branding."
    assert index.hero_note_text == "Zwischen Kopfkino, Konzept\u00a0und\u00a0Feinschliff."


def test_project_categories_are_central_editable_records():
    index = make_portfolio_tree()
    category = ProjectCategory.objects.create(name="Experience Design")
    project = add_project(index, "Eigene Kategorie")

    project.category = category
    project.save_revision().publish()
    project.refresh_from_db()

    assert project.get_category_display() == "Experience Design"
    assert list(category.projects.values_list("pk", flat=True)) == [project.pk]

    with pytest.raises(ProtectedError):
        category.delete()


def test_homepage_parity_copy_is_semantic_and_editor_sortable():
    index = make_portfolio_tree()

    assert index.projects_heading == "Projekte"
    assert index.services_annotation == "let's talk about"
    assert index.about_statement_intro == "Ich bin"
    assert index.about_name == "Katharina"
    assert index.clients_heading_secondary == "& Menschen"
    assert index.contact_heading_primary == "Ein Projekt im Kopf?"
    assert index.contact_heading_secondary == "Schreib"
    assert index.contact_heading_emphasis == "mir."

    PortfolioService.objects.create(
        page=index,
        sort_order=1,
        icon=PortfolioService.Icon.PRODUCT,
        title="Product Design",
        description="Digitale Produkte",
    )
    PortfolioService.objects.create(
        page=index,
        sort_order=0,
        icon=PortfolioService.Icon.WEB,
        title="Webdesign",
        description="Websites",
    )
    PortfolioAboutItem.objects.create(
        page=index,
        sort_order=0,
        title="Verstehen",
        lead="Marken und Menschen.",
        text="Beschreibung",
    )
    PortfolioClient.objects.create(page=index, sort_order=0, name="ALDI Nord")

    assert list(index.homepage_services.values_list("title", flat=True)) == [
        "Webdesign",
        "Product Design",
    ]
    assert list(index.about_items.values_list("title", flat=True)) == ["Verstehen"]
    assert list(index.clients.values_list("name", flat=True)) == ["ALDI Nord"]


def test_successor_projects_wrap_in_tree_order_without_duplicates():
    index = make_portfolio_tree()
    first = add_project(index, "Eins")
    second = add_project(index, "Zwei")
    third = add_project(index, "Drei")
    fourth = add_project(index, "Vier")

    assert [project.pk for project in first.get_other_projects()] == [
        second.pk,
        third.pk,
    ]
    assert [project.pk for project in third.get_other_projects()] == [
        fourth.pk,
        first.pk,
    ]
    assert [project.pk for project in fourth.get_other_projects()] == [
        first.pk,
        second.pk,
    ]


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

    assert [project.pk for project in context["other_projects"]] == [
        first.pk,
        second.pk,
    ]


def test_project_context_resolves_its_portfolio_index_once():
    index = make_portfolio_tree()
    project = add_project(index, "Einmaliger Index")

    with patch.object(project, "get_portfolio_index", wraps=project.get_portfolio_index) as resolver:
        context = project.get_context(RequestFactory().get("/"))

    assert resolver.call_count == 1
    assert context["portfolio_index"].pk == index.pk


def test_project_context_materializes_the_shared_project_collection_once():
    index = make_portfolio_tree()
    project = add_project(index, "Einmalige Projektliste")
    add_project(index, "Zweites Projekt")

    with CaptureQueriesContext(connection) as queries:
        context = project.get_context(RequestFactory().get("/"))

    project_rows = [
        query["sql"] for query in queries.captured_queries if "portfolio_projectpage" in query["sql"].lower()
    ]

    assert isinstance(context["portfolio_projects"], list)
    assert len(project_rows) == 1
    assert [item.pk for item in context["portfolio_projects"]] == [
        project.pk,
        context["other_projects"][0].pk,
    ]


def test_services_are_editor_sortable():
    index = make_portfolio_tree()
    project = add_project(index, "Sortierte Leistungen")

    assert project.get_service_names() == []

    ProjectService.objects.create(page=project, name="Umsetzung", sort_order=2)
    ProjectService.objects.create(page=project, name="Konzept", sort_order=0)
    ProjectService.objects.create(page=project, name="Gestaltung", sort_order=1)

    assert project.get_service_names() == ["Konzept", "Gestaltung", "Umsetzung"]


def test_wagtail_editor_uses_structured_fields_and_has_no_legacy_fields():
    services_panel = next(panel for panel in ProjectPage.content_panels if isinstance(panel, InlinePanel))
    content_field = ProjectPage._meta.get_field("content")
    teaser_field = ProjectPage._meta.get_field("teaser_text")
    live_link_label_field = ProjectPage._meta.get_field("live_link_label")
    direct_panels = []
    for panel in ProjectPage.content_panels:
        direct_panels.extend(getattr(panel, "children", [panel]))
    editor_field_names = {panel.field_name for panel in direct_panels if hasattr(panel, "field_name")}

    assert services_panel.relation_name == "service_items"
    assert services_panel.min_num == 1
    assert isinstance(content_field, StreamField)
    assert isinstance(teaser_field, RichTextField)
    assert teaser_field.features == ["bold", "link", "no-break"]
    assert teaser_field.max_length == 320
    assert "verlinkt" in teaser_field.help_text
    assert "Kein Umbruch" in teaser_field.help_text
    assert live_link_label_field.blank is True
    assert live_link_label_field.default == ""
    assert live_link_label_field.max_length == 120
    assert {"live_url", "live_link_label"}.issubset(editor_field_names)
    assert content_field.stream_block.meta.block_counts == {
        "statement": {"max_num": 1},
        "challenge_solution": {"max_num": 1},
        "stats": {"max_num": 1},
        "testimonial": {"max_num": 1},
    }
    project_field_names = {field.name for field in ProjectPage._meta.get_fields()}
    assert {"services", "body", "category_legacy"}.isdisjoint(project_field_names)


def test_project_teaser_accepts_320_visible_characters_with_rich_text_markup():
    index = make_portfolio_tree()
    project = add_project(index, "Exakt begrenzter Teaser")
    project.teaser_text = (
        f'<p>{"A" * 100} '
        f'<a href="https://example.com">{"B" * 100}</a> '
        f'<span data-no-break="true">{"C" * 118}</span></p>'
    )

    project.full_clean()


def test_project_teaser_rejects_more_than_320_visible_characters():
    index = make_portfolio_tree()
    project = add_project(index, "Zu langer Teaser")
    project.teaser_text = (
        f'<p>{"A" * 100} '
        f'<a href="https://example.com">{"B" * 100}</a> '
        f'<span data-no-break="true">{"C" * 119}</span></p>'
    )

    with pytest.raises(ValidationError) as error:
        project.full_clean()

    assert "teaser_text" in error.value.message_dict
    assert len(error.value.message_dict["teaser_text"]) == 1


def test_project_teaser_error_is_merged_with_base_field_errors():
    index = make_portfolio_tree()
    project = add_project(index, "Mehrere Feldfehler")
    project.year = 1899
    project.teaser_text = f'<p>{"A" * 321}</p>'

    with pytest.raises(ValidationError) as error:
        project.full_clean()

    assert {"year", "teaser_text"}.issubset(error.value.message_dict)
    assert len(error.value.message_dict["teaser_text"]) == 1


def test_project_teaser_model_validation_honors_form_exclusions():
    index = make_portfolio_tree()
    project = add_project(index, "Im Formular bereits beanstandet")
    project.year = 1899
    project.teaser_text = f'<p>{"A" * 321}</p>'

    with pytest.raises(ValidationError) as error:
        project.full_clean(exclude={"teaser_text"})

    assert "year" in error.value.message_dict
    assert "teaser_text" not in error.value.message_dict


def test_homepage_editor_hides_fixed_moin_and_handwriting_fields():
    direct_panels = []
    for panel in PortfolioIndexPage.content_panels:
        direct_panels.extend(getattr(panel, "children", [panel]))
    editor_field_names = {panel.field_name for panel in direct_panels if hasattr(panel, "field_name")}

    assert PortfolioIndexPage._meta.get_field("hero_heading").editable is False
    index_field_names = {field.name for field in PortfolioIndexPage._meta.get_fields()}
    assert {"contact_email", "about_heading", "about_text", "contact_heading"}.isdisjoint(index_field_names)
    for field_name in (
        "projects_annotation",
        "services_annotation",
        "about_annotation",
        "clients_annotation",
        "contact_annotation",
    ):
        assert PortfolioIndexPage._meta.get_field(field_name).editable is False
    assert {
        "hero_heading",
        "projects_annotation",
        "services_annotation",
        "about_annotation",
        "clients_annotation",
        "contact_annotation",
    }.isdisjoint(editor_field_names)


def test_site_image_fields_are_editorial_and_keep_the_approved_fallbacks_optional():
    direct_panels = []
    for panel in PortfolioIndexPage.content_panels:
        direct_panels.extend(getattr(panel, "children", [panel]))
    homepage_fields = {panel.field_name for panel in direct_panels if hasattr(panel, "field_name")}
    legal_fields = {
        panel.field_name
        for panel_group in LegalPageSettings.panels
        for panel in getattr(panel_group, "children", [panel_group])
        if hasattr(panel, "field_name")
    }

    assert {"hero_background_image", "about_portrait_image"}.issubset(homepage_fields)
    assert "imprint_visual_image" in legal_fields
    assert PortfolioIndexPage._meta.get_field("hero_background_image").blank is True
    assert PortfolioIndexPage._meta.get_field("about_portrait_image").blank is True
    assert LegalPageSettings._meta.get_field("imprint_visual_image").blank is True


def test_homepage_portrait_needs_explicit_alt_text_when_selected():
    index = make_portfolio_tree()
    index.about_portrait_image = make_image("Porträt")

    with pytest.raises(ValidationError) as error:
        index.full_clean()

    assert "about_portrait_image_alt" in error.value.message_dict

    index.about_portrait_image_alt = "Katharina Wersdörfer im Porträt"
    index.full_clean()


def test_homepage_portrait_alt_validation_honors_form_exclusions():
    index = make_portfolio_tree()
    index.about_portrait_image = make_image("Porträt mit Formularfehler")

    index.full_clean(exclude={"about_portrait_image_alt"})


def test_draft_project_context_has_a_complete_project_counter():
    index = make_portfolio_tree()
    add_project(index, title="Erstes Projekt")
    add_project(index, title="Zweites Projekt")
    draft = add_project(index, title="Neuer Entwurf", publish=False)

    context = draft.get_context(RequestFactory().get("/preview/"))

    assert context["project_number"] == 3
    assert context["project_total"] == 3


def test_draft_project_counter_excludes_unrelated_drafts():
    index = make_portfolio_tree()
    add_project(index, title="Veröffentlichtes Projekt")
    draft = add_project(index, title="Aktueller Entwurf", publish=False)
    add_project(index, title="Anderer Entwurf", publish=False)

    context = draft.get_context(RequestFactory().get("/preview/"))

    assert context["project_number"] == 2
    assert context["project_total"] == 2


def test_portfolio_shell_settings_keep_shared_content_per_site():
    index = make_portfolio_tree()
    site = Site.objects.get(hostname="testserver")
    settings = PortfolioSiteSettings.for_site(site)

    assert index.get_site() == site
    assert settings.pk is not None
    assert settings.brand_name == "Katharina Wersdörfer"
    assert settings.availability_text == "Verfügbar für Projekte"
    assert settings.show_availability is True
    assert settings.profile_text == "Web & Digital Design, Illustration und Print — aus Düsseldorf."
    assert settings.contact_email == "katharina@wersdoerfer.de"
    assert settings.linkedin_url.startswith("https://www.linkedin.com/")
    assert settings.github_url == "https://github.com/federfuxx"
    assert settings.mastodon_url == "https://fedi.wersdoerfer.de/@katharina"
    assert settings.copyright_text == "© 2026 Katharina Wersdörfer"
    assert settings.location_text == "Designed in Düsseldorf"

    settings.brand_name = "Eigenständige Portfolio-Site"
    settings.save()

    assert PortfolioSiteSettings.for_site(site).brand_name == "Eigenständige Portfolio-Site"

    second_site = Site.objects.create(
        hostname="secondary.test",
        port=443,
        root_page=site.root_page,
        site_name="Zweite Site",
    )
    second_settings = PortfolioSiteSettings.for_site(second_site)

    assert second_settings.pk != settings.pk
    assert second_settings.brand_name == "Katharina Wersdörfer"


def test_portfolio_site_settings_do_not_own_project_specific_placeholder_copy():
    global_field_names = {field.name for field in PortfolioSiteSettings._meta.get_fields()}

    assert {
        "project_statement_placeholder",
        "project_challenge_placeholder",
        "project_solution_placeholder",
        "project_result_placeholder",
        "project_testimonial_placeholder",
        "project_testimonial_name_placeholder",
        "project_testimonial_role_placeholder",
    }.isdisjoint(global_field_names)


def test_legal_page_urls_are_not_stored_in_site_settings():
    settings_field_names = {field.name for field in PortfolioSiteSettings._meta.get_fields()}

    assert {"imprint_url", "privacy_url"}.isdisjoint(settings_field_names)


def test_unsaved_project_preview_reads_in_memory_service_items():
    project = ProjectPage(
        title="Noch ungespeichert",
        teaser_text="Vorschau",
        category=ProjectCategory.objects.get_or_create(name="Web")[0],
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
