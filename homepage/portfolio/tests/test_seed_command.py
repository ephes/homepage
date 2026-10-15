import pytest
from django.core.management import CommandError, call_command
from wagtail.models import Locale, Page, Site

from homepage.portfolio.management.commands.seed_portfolio import CATEGORIES
from homepage.portfolio.models import PortfolioIndexPage, ProjectCategory

from .test_pages import make_portfolio_tree

pytestmark = pytest.mark.django_db


def make_default_site():
    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node() or Page.add_root(instance=Page(title="Root", slug="root"))
    Site.objects.update_or_create(hostname="testserver", defaults={"root_page": root, "is_default_site": True})
    return root


def test_seed_without_page_requires_create():
    with pytest.raises(CommandError):
        call_command("seed_portfolio")


def test_seed_create_adds_an_empty_unpublished_page_below_the_default_site_root():
    root = make_default_site()

    call_command("seed_portfolio", create=True)

    page = PortfolioIndexPage.objects.get()
    assert not page.live
    assert page.get_parent().pk == root.pk
    draft = page.get_latest_revision_as_object()
    assert not draft.homepage_services.all()
    assert not draft.about_items.all()
    assert not draft.clients.all()


def test_seed_creates_the_categories_once():
    make_default_site()

    call_command("seed_portfolio", create=True)
    call_command("seed_portfolio")

    assert sorted(ProjectCategory.objects.values_list("name", flat=True)) == sorted(CATEGORIES)


def test_seed_leaves_an_existing_page_unchanged():
    index = make_portfolio_tree()
    revision_id = index.latest_revision_id

    call_command("seed_portfolio", create=True)

    assert PortfolioIndexPage.objects.get().pk == index.pk
    index.refresh_from_db()
    assert index.latest_revision_id == revision_id


def test_seed_page_defaults_contain_no_personal_content():
    make_default_site()

    call_command("seed_portfolio", create=True)

    page = PortfolioIndexPage.objects.get()
    assert page.title == "Portfolio"
    assert page.about_name == "[Name]"
    assert "Katharina" not in str(page.get_latest_revision().content)
