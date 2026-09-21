from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import RequestFactory
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest
from wagtail.rich_text.feature_registry import FeatureRegistry
from wagtail.models import GroupPagePermission

from homepage.portfolio.models import ProjectCategory, ProjectPage
from homepage.portfolio.wagtail_hooks import (
    PortfolioHomepageMenuItem,
    PortfolioProjectsMenuItem,
    portfolio_admin_theme,
    register_no_break_feature,
)

from .test_models import add_project, make_portfolio_tree

pytestmark = pytest.mark.django_db


@override_settings(DEBUG=False)
def test_portfolio_admin_theme_uses_a_manifest_safe_static_url():
    stylesheet = str(portfolio_admin_theme())

    assert stylesheet.startswith('<link rel="stylesheet"')
    assert 'href="/static/portfolio/admin.css"' in stylesheet


@override_settings(DEBUG=True)
def test_portfolio_admin_theme_cache_busts_local_css_changes():
    stylesheet = str(portfolio_admin_theme())

    assert 'href="/static/portfolio/admin.css?v=' in stylesheet


def test_no_break_feature_has_a_draftail_control_and_stable_html_conversion():
    features = FeatureRegistry()

    register_no_break_feature(features)

    plugin = features.plugins_by_editor["draftail"]["no-break"]
    conversion = features.converter_rules_by_converter["contentstate"]["no-break"]
    assert plugin.data["type"] == "NO_BREAK"
    assert plugin.data["label"] == "NBSP"
    assert plugin.data["description"] == "Kein Umbruch"
    assert "span[data-no-break]" in conversion["from_database_format"]
    assert conversion["to_database_format"]["style_map"]["NO_BREAK"] == {
        "element": "span",
        "props": {"data-no-break": True},
    }


def make_admin_request():
    user = get_user_model().objects.create_superuser(
        username="portfolio-editor",
        email="editor@example.com",
        password="password",
    )
    request = RequestFactory().get("/cms/")
    request.user = user
    return request


def test_portfolio_admin_menu_links_directly_to_the_homepage_editor():
    index = make_portfolio_tree()
    request = make_admin_request()
    item = PortfolioHomepageMenuItem("Startseite", "#", name="portfolio-homepage")

    component = item.render_component(request)

    assert item.is_shown(request) is True
    assert component.label == "Startseite"
    assert component.url == reverse("wagtailadmin_pages:edit", args=[index.pk])


def test_project_admin_menu_lists_drafts_and_exposes_direct_creation():
    index = make_portfolio_tree()
    live_project = add_project(index, "Veröffentlicht")
    draft_project = add_project(index, "Noch nicht öffentlich", publish=False)
    request = make_admin_request()
    item = PortfolioProjectsMenuItem("Projekte", name="portfolio-projects")

    children = item.get_project_menu_items(request)

    assert [(child.label, child.url) for child in children] == [
        (
            "Neues Projekt",
            reverse(
                "wagtailadmin_pages:add",
                args=["portfolio", "projectpage", index.pk],
            ),
        ),
        (
            "Reihenfolge",
            reverse("wagtailadmin_explore", args=[index.pk]) + "?ordering=ord",
        ),
        (
            "Kategorien",
            reverse(ProjectCategory.snippet_viewset.get_url_name("list")),
        ),
        (
            live_project.title,
            reverse("wagtailadmin_pages:edit", args=[live_project.pk]),
        ),
        (
            f"{draft_project.title} (Entwurf)",
            reverse("wagtailadmin_pages:edit", args=[draft_project.pk]),
        ),
    ]


def test_project_admin_menu_items_are_cached_for_one_request(django_assert_num_queries):
    index = make_portfolio_tree()
    add_project(index, "Projekt")
    request = make_admin_request()
    item = PortfolioProjectsMenuItem("Projekte", name="portfolio-projects")

    assert item.is_shown(request) is True
    children = request._portfolio_project_menu_items

    with django_assert_num_queries(0):
        component = item.render_component(request)

    assert request._portfolio_project_menu_items is children
    assert component.label == "Projekte"


def test_project_admin_menu_permission_queries_do_not_scale_with_project_count():
    index = make_portfolio_tree()
    user = get_user_model().objects.create_user(
        username="portfolio-owner",
        email="owner@example.com",
        password="password",
        is_staff=True,
    )
    index.owner = user
    index.save(update_fields=["owner"])
    group = Group.objects.create(name="Portfolio project creators")
    user.groups.add(group)
    GroupPagePermission.objects.create(
        group=group,
        page=index,
        permission=Permission.objects.get(
            content_type__app_label="wagtailcore",
            codename="add_page",
        ),
    )

    def menu_query_count():
        request = RequestFactory().get("/cms/")
        request.user = get_user_model().objects.get(pk=user.pk)
        item = PortfolioProjectsMenuItem("Projekte", name="portfolio-projects")
        with CaptureQueriesContext(connection) as queries:
            labels = [child.label for child in item.get_project_menu_items(request)]
        return len(queries), labels

    add_project(index, "Nicht eigenes Projekt")
    baseline_queries, baseline_labels = menu_query_count()
    for number in range(12):
        add_project(index, f"Weiteres fremdes Projekt {number}")
    scaled_queries, scaled_labels = menu_query_count()

    assert scaled_queries == baseline_queries
    assert baseline_labels == scaled_labels
    assert "Neues Projekt" in scaled_labels
    assert not any(label.startswith("Weiteres fremdes Projekt") for label in scaled_labels)


def test_project_category_chooser_allows_inline_creation():
    chooser_viewset = ProjectCategory.snippet_viewset.chooser_viewset

    assert chooser_viewset.form_fields == ["name"]


def test_project_editor_exposes_an_optional_end_year_for_periods():
    form = ProjectPage.get_edit_handler().get_form_class()()

    assert form.fields["year"].label == "Jahr / Startjahr"
    assert form.fields["end_year"].label == "Endjahr (optional)"
    assert form.fields["end_year"].required is False
    assert "2021–2024" in form.fields["end_year"].help_text


def test_project_editor_exposes_the_homepage_hero_choice():
    form = ProjectPage.get_edit_handler().get_form_class()()

    assert form.fields["homepage_is_hero"].label == "Hero-Kachel auf der Startseite"
    assert form.fields["homepage_is_hero"].required is False
    assert "Desktop-Raster" in form.fields["homepage_is_hero"].help_text
    assert "Mobil" in form.fields["homepage_is_hero"].help_text
