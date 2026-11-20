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


def test_seed_creates_requested_site_alongside_existing_portfolio():
    make_default_site()
    call_command("seed_portfolio", create=True, hostname="first.example.test")
    first = Site.objects.get(hostname="first.example.test")
    first_revision = first.root_page.latest_revision_id

    call_command("seed_portfolio", create=True, hostname="second.example.test")
    second = Site.objects.get(hostname="second.example.test")
    second_revision = second.root_page.latest_revision_id
    call_command("seed_portfolio", create=True, hostname="second.example.test")

    assert first.root_page_id != second.root_page_id
    assert PortfolioIndexPage.objects.count() == 2
    assert Site.objects.filter(hostname="second.example.test").count() == 1
    first.root_page.refresh_from_db()
    second.root_page.refresh_from_db()
    assert first.root_page.latest_revision_id == first_revision
    assert second.root_page.latest_revision_id == second_revision
    assert sorted(ProjectCategory.objects.values_list("name", flat=True)) == sorted(CATEGORIES)


def test_seed_default_site_uses_the_requested_parent_and_slug():
    root = make_default_site()
    call_command("seed_portfolio", create=True, hostname="separate.example.test", slug="separate")
    call_command("seed_portfolio", create=True, slug="local")
    local = PortfolioIndexPage.objects.child_of(root).get(slug="local")
    revision = local.latest_revision_id
    call_command("seed_portfolio", create=True, slug="local")

    local.refresh_from_db()
    assert local.latest_revision_id == revision
    assert PortfolioIndexPage.objects.count() == 2


def test_seed_uses_host_and_port_and_refuses_an_occupied_pair():
    root = make_default_site()
    host = "design.example.test"
    Site.objects.create(hostname=host, port=8000, root_page=root)

    with pytest.raises(CommandError, match=r"design\.example\.test:8000 already exists"):
        call_command("seed_portfolio", create=True, hostname=host, port=8000)
    assert not ProjectCategory.objects.exists()
    assert not PortfolioIndexPage.objects.exists()

    for port in (8001, 8002):
        call_command("seed_portfolio", create=True, hostname=host, port=port)

    roots = dict(Site.objects.filter(hostname=host).values_list("port", "root_page_id"))
    assert set(roots) == {8000, 8001, 8002}
    assert roots[8000] == root.pk
    assert len(set(roots.values())) == 3

    with pytest.raises(CommandError, match=r"design\.example\.test:8001 already exists"):
        call_command("seed_portfolio", create=True, hostname=host, port=8001, slug="different")
    assert PortfolioIndexPage.objects.count() == 2
    assert dict(Site.objects.filter(hostname=host).values_list("port", "root_page_id")) == roots
