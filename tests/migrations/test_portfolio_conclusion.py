import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from wagtail.models import Revision

from homepage.portfolio.models import ProjectPage
from homepage.portfolio.tests.test_models import add_project, make_portfolio_tree


@pytest.mark.django_db(transaction=True)
def test_executor_converts_draft_independently_of_existing_live_conclusion():
    import json

    page = add_project(make_portfolio_tree(), "Independent conclusion")
    page.refresh_from_db()
    executor = MigrationExecutor(connection)
    leaves = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("portfolio", "0010_project_conclusion")])
        apps = executor.loader.project_state([("portfolio", "0010_project_conclusion")]).apps
        HistoricalPage = apps.get_model("portfolio", "ProjectPage")
        HistoricalRevision = apps.get_model("wagtailcore", "Revision")
        live_stream = [{"type": "challenge_solution", "value": {"solution": "<p>Live body</p>"}}]
        draft_stream = [{"type": "challenge_solution", "value": {"solution": "<p>Draft</p><p><b>Draft end</b></p>"}}]
        HistoricalPage.objects.filter(pk=page.pk).update(content=live_stream, conclusion="<p><b>Live end</b></p>")
        live = HistoricalRevision.objects.get(pk=page.live_revision_id)
        live.content.update(content=live_stream, conclusion="<p><b>Revision end</b></p>")
        live.save(update_fields=["content"])
        draft = HistoricalRevision.objects.create(
            content_type_id=live.content_type_id,
            base_content_type_id=live.base_content_type_id,
            object_id=live.object_id,
            created_at=live.created_at,
            content={**live.content, "content": json.dumps(draft_stream), "conclusion": ""},
        )
        HistoricalPage.objects.filter(pk=page.pk).update(latest_revision_id=draft.pk)
        MigrationExecutor(connection).migrate([("portfolio", "0011_move_conclusion_from_solution")])
        current = HistoricalPage.objects.get(pk=page.pk)
        live.refresh_from_db()
        draft.refresh_from_db()
        assert current.conclusion == "<p><b>Live end</b></p>"
        assert list(current.content.raw_data) == live_stream
        assert live.content["conclusion"] == "<p><b>Revision end</b></p>"
        assert draft.content["conclusion"] == "<p><b>Draft end</b></p>"
        assert json.loads(draft.content["content"])[0]["value"]["solution"] == "<p>Draft</p>"
        MigrationExecutor(connection).migrate([("portfolio", "0010_project_conclusion")])
        draft.refresh_from_db()
        assert json.loads(draft.content["content"]) == draft_stream
    finally:
        MigrationExecutor(connection).migrate(leaves)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("unrepresentable", ["page", "latest", "live", None])
def test_executor_rollback_refuses_unrepresentable_conclusion(unrepresentable):
    index = make_portfolio_tree()
    page = add_project(index, "Synthetic migration")
    page.content = [{"type": "challenge_solution", "value": {"solution": "<p>Body</p>"}}]
    page.conclusion = "<p><strong>Live end</strong></p>"
    page.save()
    live = page.save_revision()
    live.publish()
    page.conclusion = "<p><strong>Draft end</strong></p>"
    draft = page.save_revision()
    page.refresh_from_db()
    if unrepresentable == "page":
        page.content = []
        page.save(update_fields=["content"])
    elif unrepresentable:
        revision = draft if unrepresentable == "latest" else live
        data = revision.content
        data["content"] = []
        revision.content = data
        revision.save(update_fields=["content"])
    before_page = ProjectPage.objects.values("content", "conclusion").get(pk=page.pk)
    before_revisions = list(Revision.objects.filter(pk__in=[live.pk, draft.pk]).values("id", "content").order_by("id"))
    executor = MigrationExecutor(connection)
    leaves = executor.loader.graph.leaf_nodes()
    try:
        if unrepresentable:
            with pytest.raises(RuntimeError, match="challenge_solution"):
                executor.migrate([("portfolio", "0009_case_study_part_counter")])
            assert ProjectPage.objects.values("content", "conclusion").get(pk=page.pk) == before_page
            assert (
                list(Revision.objects.filter(pk__in=[live.pk, draft.pk]).values("id", "content").order_by("id"))
                == before_revisions
            )
        else:
            executor.migrate([("portfolio", "0010_project_conclusion")])
            historical_page = (
                executor.loader.project_state([("portfolio", "0010_project_conclusion")])
                .apps.get_model("portfolio", "ProjectPage")
                .objects.get(pk=page.pk)
            )
            assert historical_page.conclusion == ""
            assert "Live end" in historical_page.content.raw_data[0]["value"]["solution"]
            draft.refresh_from_db()
            assert "Draft end" in str(draft.content["content"])
    finally:
        MigrationExecutor(connection).migrate(leaves)
    if not unrepresentable:
        page.refresh_from_db()
        assert page.conclusion == "<p><strong>Live end</strong></p>"


@pytest.mark.django_db
@pytest.mark.parametrize("direction", ["forwards", "backwards"])
def test_migration_hydrates_pages_without_retaining_the_inventory(monkeypatch, direction):
    import importlib
    import weakref
    from types import SimpleNamespace

    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    from homepage.portfolio.tests.test_models import add_project, make_portfolio_tree

    index = make_portfolio_tree()
    for number in range(9):
        page = add_project(index, f"Bounded {number}", publish=False)
        page.content = [{"type": "challenge_solution", "value": {"solution": "<p>" + "x" * 50000 + "</p>"}}]
        page.conclusion = "<p><b>End</b></p>" if direction == "backwards" else ""
        page.save(update_fields=["content", "conclusion"])
    apps = MigrationExecutor(connection).loader.project_state().apps
    Page = apps.get_model("portfolio", "ProjectPage")
    original = Page.from_db
    retained = weakref.WeakSet()
    peak = 0
    loaded = 0

    def from_db(cls, *args, **kwargs):
        nonlocal peak, loaded
        instance = original(*args, **kwargs)
        retained.add(instance)
        loaded += 1
        peak = max(peak, len(retained))
        return instance

    monkeypatch.setattr(Page, "from_db", classmethod(from_db))
    migration = importlib.import_module("homepage.portfolio.migrations.0011_move_conclusion_from_solution")
    getattr(migration, direction)(apps, SimpleNamespace(connection=connection))
    assert loaded == (18 if direction == "backwards" else 9)
    assert peak <= 2, f"Retained {peak} complete page bodies instead of streaming them"
