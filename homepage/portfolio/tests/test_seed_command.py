import threading

import pytest
from django.core.management import CommandError, call_command
from django.db import connection, transaction
from wagtail.models import Locale, Page, Site

from homepage.portfolio.management.commands.seed_portfolio import (
    ABOUT_ITEMS,
    CATEGORIES,
    CLIENTS,
    SERVICES,
    Command,
)
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


def save_editor_draft(pk):
    """What the Wagtail editor does on "Save draft": a new revision from the current page."""
    page = PortfolioIndexPage.objects.get(pk=pk)
    page.hero_heading = "Entwurf der Redakteurin"
    page.clients = [PortfolioClient(name="Kunde der Redakteurin", sort_order=0)]
    return page.save_revision()


def assert_editor_draft_is_latest_and_unpublished(pk, editor_revision):
    index = PortfolioIndexPage.objects.get(pk=pk)
    assert index.latest_revision_id == editor_revision.pk
    assert index.has_unpublished_changes
    assert index.hero_heading == "Moin"
    assert "Kunde der Redakteurin" not in index.clients.values_list("name", flat=True)
    draft = index.get_latest_revision_as_object()
    assert draft.hero_heading == "Entwurf der Redakteurin"
    assert [client.name for client in draft.clients.all()] == ["Kunde der Redakteurin"]
    return index, draft


def test_seed_builds_on_a_draft_saved_after_it_listed_the_pages(monkeypatch):
    """An editor saves a draft between the seed's page query and its revision.

    The page object the seed loaded still says "live, no pending changes". The
    seed must not publish a revision built from that outdated state.
    """
    index = make_portfolio_tree()
    revisions = []
    seed_page = Command.seed_page

    def seed_page_after_editor_saved(self, page):
        revisions.append(save_editor_draft(page.pk))
        return seed_page(self, page)

    monkeypatch.setattr(Command, "seed_page", seed_page_after_editor_saved)

    call_command("seed_portfolio")

    index = PortfolioIndexPage.objects.get(pk=index.pk)
    # Nothing was published: the live page has neither the editor's nor the seed's records.
    assert index.has_unpublished_changes
    assert index.hero_heading == "Moin"
    assert index.clients.count() == 0
    assert index.homepage_services.count() == 0
    # The seed's revision continues the editor's draft instead of replacing it.
    draft = index.get_latest_revision_as_object()
    assert index.latest_revision.created_at >= revisions[0].created_at
    assert draft.hero_heading == "Entwurf der Redakteurin"
    assert [client.name for client in draft.clients.all()] == ["Kunde der Redakteurin"]
    assert len(draft.homepage_services.all()) == len(SERVICES)
    assert len(draft.about_items.all()) == len(ABOUT_ITEMS)


@pytest.mark.django_db(transaction=True)
def test_editor_save_waits_for_a_running_seed_and_stays_the_latest_draft(monkeypatch):
    """Two database connections: the seed is paused right before it saves its revision.

    While the seed holds the page's row lock the editor's save cannot finish.
    It completes after the seed committed and is then the latest draft.
    """
    index = make_portfolio_tree()
    seed_is_saving, release_seed, editor_finished = threading.Event(), threading.Event(), threading.Event()
    results = {}
    save_revision = PortfolioIndexPage.save_revision

    def paused_save_revision(self, *args, **kwargs):
        if threading.current_thread() is seed_thread:
            seed_is_saving.set()
            assert release_seed.wait(30)
        return save_revision(self, *args, **kwargs)

    monkeypatch.setattr(PortfolioIndexPage, "save_revision", paused_save_revision)

    def run(name, function):
        try:
            results[name] = function()
        except BaseException as error:  # reported by the assertions below
            results[name] = error
        finally:
            connection.close()

    def editor():
        assert seed_is_saving.wait(30)
        with transaction.atomic():
            revision = save_editor_draft(index.pk)
        editor_finished.set()
        return revision

    seed_thread = threading.Thread(target=run, args=("seed", lambda: call_command("seed_portfolio")))
    editor_thread = threading.Thread(target=run, args=("editor", editor))
    seed_thread.start()
    editor_thread.start()
    try:
        assert seed_is_saving.wait(30)
        blocked = not editor_finished.wait(1.5)
    finally:
        release_seed.set()
        seed_thread.join(60)
        editor_thread.join(60)

    assert not seed_thread.is_alive() and not editor_thread.is_alive()
    assert not isinstance(results["seed"], BaseException), results["seed"]
    assert not isinstance(results["editor"], BaseException), results["editor"]
    assert blocked, "the editor's save finished while the seed was between its state check and its revision"
    index, _ = assert_editor_draft_is_latest_and_unpublished(index.pk, results["editor"])
    # The seed ran on the state it had locked: it published its records to the live page.
    assert index.homepage_services.count() == len(SERVICES)
    assert index.live_revision_id != results["editor"].pk


def test_seed_after_an_overlapping_editor_save_completes_the_draft():
    index = make_portfolio_tree()
    call_command("seed_portfolio")
    editor_revision = save_editor_draft(index.pk)

    call_command("seed_portfolio")
    call_command("seed_portfolio")

    index = PortfolioIndexPage.objects.get(pk=index.pk)
    assert index.latest_revision_id == editor_revision.pk  # nothing left to add, no new revision
    assert index.has_unpublished_changes
    assert index.homepage_services.count() == len(SERVICES)
