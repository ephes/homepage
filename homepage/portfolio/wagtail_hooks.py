from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.urls import reverse
from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks
import wagtail.admin.rich_text.editors.draftail.features as draftail_features
from wagtail.admin.menu import Menu, MenuItem, SubmenuMenuItem
from wagtail.admin.rich_text.converters.html_to_contentstate import (
    InlineStyleElementHandler,
)
from wagtail.admin.ui.sidebar import SubMenuItem as SubMenuItemComponent
from wagtail.contrib.settings.registry import register_setting
from wagtail.permissions import page_permission_policy
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.chooser import SnippetChooserViewSet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import (
    ErrorPageSettings,
    LegalPageSettings,
    PortfolioIndexPage,
    PortfolioSiteSettings,
    ProjectCategory,
    ProjectPage,
)


class ProjectCategoryChooserViewSet(SnippetChooserViewSet):
    """Allow editors to create a category without leaving the project form."""

    form_fields = ["name"]


class ProjectCategoryViewSet(SnippetViewSet):
    model = ProjectCategory
    icon = "tag"
    chooser_viewset_class = ProjectCategoryChooserViewSet


register_snippet(ProjectCategoryViewSet)

register_setting(ErrorPageSettings, icon="warning")
register_setting(PortfolioSiteSettings, icon="site")
register_setting(LegalPageSettings, icon="doc-full")


@hooks.register("register_rich_text_features")
def register_no_break_feature(features):
    """Let editors keep selected brand names together without entering HTML."""

    feature_name = "no-break"
    type_ = "NO_BREAK"
    control = {
        "type": type_,
        "label": "NBSP",
        "description": "Kein Umbruch",
        "style": {
            "whiteSpace": "nowrap",
            "textDecoration": "underline dotted",
            "textUnderlineOffset": "0.2em",
        },
    }
    features.register_editor_plugin(
        "draftail",
        feature_name,
        draftail_features.InlineStyleFeature(control),
    )
    features.register_converter_rule(
        "contentstate",
        feature_name,
        {
            "from_database_format": {
                "span[data-no-break]": InlineStyleElementHandler(type_)
            },
            "to_database_format": {
                "style_map": {
                    type_: {
                        "element": "span",
                        "props": {"data-no-break": True},
                    }
                }
            },
        },
    )


@hooks.register("insert_global_admin_css")
def portfolio_admin_theme():
    """Load the portfolio palette without replacing Wagtail's admin layout."""

    stylesheet_url = static("portfolio/admin.css")
    if settings.DEBUG:
        stylesheet_path = finders.find("portfolio/admin.css")
        if stylesheet_path:
            stylesheet_url = (
                f"{stylesheet_url}?v={Path(stylesheet_path).stat().st_mtime_ns}"
            )

    return format_html(
        '<link rel="stylesheet" href="{}">',
        stylesheet_url,
    )


def editable_portfolio_index(request):
    """Return the first portfolio homepage the current editor may change."""

    cache_name = "_portfolio_admin_index"
    if hasattr(request, cache_name):
        return getattr(request, cache_name)

    index = (
        page_permission_policy.instances_user_has_permission_for(
            request.user, "change"
        )
        .type(PortfolioIndexPage)
        .specific()
        .order_by("path")
        .first()
    )
    setattr(request, cache_name, index)
    return index


class PortfolioHomepageMenuItem(MenuItem):
    """Direct editor shortcut to the portfolio homepage."""

    def is_shown(self, request):
        return editable_portfolio_index(request) is not None

    def render_component(self, request):
        index = editable_portfolio_index(request)
        return MenuItem(
            self.label,
            reverse("wagtailadmin_pages:edit", args=[index.pk]),
            name=self.name,
            icon_name=self.icon_name,
            order=self.order,
        ).render_component(request)


class PortfolioProjectsMenuItem(SubmenuMenuItem):
    """Expandable shortcuts for creating and editing portfolio projects."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, menu=Menu(items=[]), **kwargs)

    def get_project_menu_items(self, request):
        cache_name = "_portfolio_project_menu_items"
        if hasattr(request, cache_name):
            return getattr(request, cache_name)

        index = editable_portfolio_index(request)
        if index is None:
            items = []
            setattr(request, cache_name, items)
            return items

        items = []
        permissions = index.permissions_for_user(request.user)
        if permissions.can_add_subpage() and ProjectPage.can_create_at(index):
            items.append(
                MenuItem(
                    "Neues Projekt",
                    reverse(
                        "wagtailadmin_pages:add",
                        args=["portfolio", "projectpage", index.pk],
                    ),
                    name="portfolio-project-add",
                    icon_name="plus",
                    order=1,
                )
            )

        if permissions.can_reorder_children():
            items.append(
                MenuItem(
                    "Reihenfolge",
                    reverse("wagtailadmin_explore", args=[index.pk])
                    + "?ordering=ord",
                    name="portfolio-project-order",
                    icon_name="list-ul",
                    order=2,
                )
            )

        category_viewset = ProjectCategory.snippet_viewset
        if category_viewset.permission_policy.user_has_any_permission(
            request.user, {"add", "change", "delete", "view"}
        ):
            items.append(
                MenuItem(
                    "Kategorien",
                    reverse(category_viewset.get_url_name("list")),
                    name="portfolio-project-categories",
                    icon_name="tag",
                    order=3,
                )
            )

        projects = (
            page_permission_policy.instances_user_has_permission_for(
                request.user, "change"
            )
            .child_of(index)
            .type(ProjectPage)
            .specific()
            .order_by("path")
        )
        for order, project in enumerate(projects, start=10):
            label = project.title if project.live else f"{project.title} (Entwurf)"
            items.append(
                MenuItem(
                    label,
                    reverse("wagtailadmin_pages:edit", args=[project.pk]),
                    name=f"portfolio-project-{project.pk}",
                    icon_name="doc-empty-inverse",
                    order=order,
                )
            )
        setattr(request, cache_name, items)
        return items

    def is_shown(self, request):
        return bool(self.get_project_menu_items(request))

    def render_component(self, request):
        menu = Menu(items=self.get_project_menu_items(request))
        return SubMenuItemComponent(
            self.name,
            self.label,
            menu.render_component(request),
            icon_name=self.icon_name,
            classname=self.classname,
            attrs=self.attrs,
        )


@hooks.register("register_admin_menu_item")
def register_portfolio_homepage_menu_item():
    return PortfolioHomepageMenuItem(
        "Startseite",
        "#",
        name="portfolio-homepage",
        icon_name="home",
        order=90,
    )


@hooks.register("register_admin_menu_item")
def register_portfolio_projects_menu_item():
    return PortfolioProjectsMenuItem(
        "Projekte",
        name="portfolio-projects",
        icon_name="folder-open-inverse",
        order=91,
    )
