import pytest
from django.core.management import CommandError, call_command
from wagtail.models import Locale, Page, Site

from homepage.portfolio.management.commands.seed_portfolio import ABOUT_ITEMS, CATEGORIES, CLIENTS, SERVICES
from homepage.portfolio.models import PortfolioClient, PortfolioIndexPage, ProjectCategory

from .test_pages import make_portfolio_tree

pytestmark = pytest.mark.django_db


def test_seed_publishes_collections_into_a_live_page_once():
    index = make_portfolio_tree()

    call_command("seed_portfolio")
    call_command("seed_portfolio")

    index = PortfolioIndexPage.objects.get(pk=index.pk)
    assert index.homepage_services.count() == len(SERVICES)
    assert index.about_items.count() == len(ABOUT_ITEMS)
    assert list(index.clients.values_list("name", flat=True)) == list(CLIENTS)
    assert not index.has_unpublished_changes
    assert set(ProjectCategory.objects.values_list("name", flat=True)) >= set(CATEGORIES)


def test_seeded_collections_survive_publishing_the_latest_revision():
    index = make_portfolio_tree()
    call_command("seed_portfolio")

    PortfolioIndexPage.objects.get(pk=index.pk).get_latest_revision().publish()

    assert PortfolioIndexPage.objects.get(pk=index.pk).homepage_services.count() == len(SERVICES)


def test_seed_keeps_existing_content():
    index = make_portfolio_tree()
    index.clients.create(name="Eigener Kunde", sort_order=0)
    index.save_revision().publish()

    call_command("seed_portfolio")

    index = PortfolioIndexPage.objects.get(pk=index.pk)
    assert list(index.clients.values_list("name", flat=True)) == ["Eigener Kunde"]
    assert index.homepage_services.count() == len(SERVICES)


def test_seed_does_not_publish_a_pending_draft():
    index = make_portfolio_tree()
    index.title = "Unveröffentlichter Entwurf"
    index.save_revision()

    call_command("seed_portfolio")

    index = PortfolioIndexPage.objects.get(pk=index.pk)
    assert index.title != "Unveröffentlichter Entwurf"
    draft = index.get_latest_revision_as_object()
    assert draft.title == "Unveröffentlichter Entwurf"
    assert len(draft.homepage_services.all()) == len(SERVICES)


def test_seed_keeps_live_records_that_no_revision_contains():
    index = make_portfolio_tree()
    PortfolioClient.objects.create(page=index, name="Nur in der Datenbank", sort_order=0)

    call_command("seed_portfolio")

    index = PortfolioIndexPage.objects.get(pk=index.pk)
    assert list(index.clients.values_list("name", flat=True)) == ["Nur in der Datenbank"]
    assert index.homepage_services.count() == len(SERVICES)


def test_seed_without_page_requires_create():
    with pytest.raises(CommandError):
        call_command("seed_portfolio")


def test_seed_create_adds_an_unpublished_page_below_the_default_site_root():
    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node() or Page.add_root(instance=Page(title="Root", slug="root"))
    Site.objects.update_or_create(hostname="testserver", defaults={"root_page": root, "is_default_site": True})

    call_command("seed_portfolio", create=True)

    page = PortfolioIndexPage.objects.get()
    assert not page.live
    assert page.get_parent().pk == root.pk
    assert len(page.get_latest_revision_as_object().homepage_services.all()) == len(SERVICES)
