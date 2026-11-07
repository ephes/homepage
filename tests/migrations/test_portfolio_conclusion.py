import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from wagtail.models import Revision

from homepage.portfolio.models import ProjectPage
from homepage.portfolio.tests.test_models import add_project, make_portfolio_tree


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
