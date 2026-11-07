import json

import pytest
from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone


@pytest.mark.django_db(databases=["default", "legacy"], transaction=True)
def test_conclusion_migration_changes_only_selected_database():
    recorder = MigrationRecorder(connections["legacy"])
    # Copy actual applied history, including squashed/replaced migration records.
    applied = MigrationRecorder(connections["default"]).applied_migrations()
    for app_label, migration_name in applied:
        recorder.record_applied(app_label, migration_name)

    def seed(alias):
        executor = MigrationExecutor(connections[alias])
        apps = executor.loader.project_state(executor.loader.graph.leaf_nodes()).apps
        Page = apps.get_model("portfolio", "ProjectPage")
        Category = apps.get_model("portfolio", "ProjectCategory")
        Locale = apps.get_model("wagtailcore", "Locale")
        Revision = apps.get_model("wagtailcore", "Revision")
        ContentType = apps.get_model("contenttypes", "ContentType")
        category = Category.objects.using(alias).create(name="Synthetic category")
        page_type = ContentType.objects.using(alias).get(app_label="portfolio", model="projectpage")
        base_type = ContentType.objects.using(alias).get(app_label="wagtailcore", model="page")
        stream = [{"type": "challenge_solution", "value": {"solution": f"<p>{alias} body</p><p><b>End</b></p>"}}]
        page = Page.objects.using(alias).create(
            title="Synthetic page",
            slug="synthetic",
            path="9999",
            depth=1,
            numchild=0,
            locale_id=Locale.objects.using(alias).get_or_create(language_code="en")[0].pk,
            content_type_id=page_type.pk,
            category_id=category.pk,
            year=2026,
            content=stream,
            conclusion="",
        )
        revisions = []
        for raw in (stream, json.dumps(stream)):
            revisions.append(
                Revision.objects.using(alias).create(
                    content_type_id=page_type.pk,
                    base_content_type_id=base_type.pk,
                    object_id=str(page.pk),
                    created_at=timezone.now(),
                    content={"content": raw, "conclusion": ""},
                )
            )
        page.latest_revision_id = revisions[0].pk
        page.live_revision_id = revisions[1].pk
        page.save(using=alias, update_fields=["latest_revision", "live_revision"])
        return Page, Revision, page.pk, [revision.pk for revision in revisions]

    default_page, default_revision, default_pk, default_ids = seed("default")
    selected_page, selected_revision, selected_pk, selected_ids = seed("legacy")

    def snapshot(alias, page_model, revision_model, pk, ids):
        return (
            page_model.objects.using(alias).values("content", "conclusion").get(pk=pk),
            list(revision_model.objects.using(alias).filter(pk__in=ids).order_by("pk").values("content")),
        )

    original_default = snapshot("default", default_page, default_revision, default_pk, default_ids)
    original_selected = snapshot("legacy", selected_page, selected_revision, selected_pk, selected_ids)
    executor = MigrationExecutor(connections["legacy"])
    leaves = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("portfolio", "0010_project_conclusion")])
        MigrationExecutor(connections["legacy"]).migrate([("portfolio", "0011_move_conclusion_from_solution")])
        changed = snapshot("legacy", selected_page, selected_revision, selected_pk, selected_ids)
        assert changed[0]["conclusion"] == "<p><b>End</b></p>"
        assert all(revision["content"]["conclusion"] == "<p><b>End</b></p>" for revision in changed[1])
        assert snapshot("default", default_page, default_revision, default_pk, default_ids) == original_default
        MigrationExecutor(connections["legacy"]).migrate([("portfolio", "0010_project_conclusion")])
        assert snapshot("legacy", selected_page, selected_revision, selected_pk, selected_ids) == original_selected
        assert snapshot("default", default_page, default_revision, default_pk, default_ids) == original_default
    finally:
        MigrationExecutor(connections["legacy"]).migrate(leaves)
