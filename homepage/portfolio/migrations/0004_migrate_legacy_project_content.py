import json
import uuid

from django.db import migrations


def split_services(value):
    return [name.strip() for name in (value or "").split(",") if name.strip()]


def statement_content(body):
    if not body:
        return []
    return [
        {
            "type": "statement",
            "value": {"text": body},
            "id": str(uuid.uuid4()),
        }
    ]


def migrate_project_revisions(apps, database):
    Revision = apps.get_model("wagtailcore", "Revision")
    revisions = Revision.objects.using(database).filter(
        content_type__app_label="portfolio",
        content_type__model="projectpage",
    )

    for revision in revisions.iterator():
        revision_content = dict(revision.content)
        changed = False

        # Old revisions need their own historic values, not the current live
        # page's values. Otherwise reverting or publishing one later could wipe
        # the structured fields introduced by migration 0003.
        if "service_items" not in revision_content:
            revision_content["service_items"] = [
                {
                    "pk": None,
                    "sort_order": index,
                    "page": revision_content["pk"],
                    "name": name,
                }
                for index, name in enumerate(split_services(revision_content.get("services")))
            ]
            changed = True

        if "content" not in revision_content:
            # StreamFields remain JSON strings inside Wagtail revision JSON.
            revision_content["content"] = json.dumps(statement_content(revision_content.get("body")))
            changed = True

        if changed:
            Revision.objects.using(database).filter(pk=revision.pk).update(content=revision_content)


def migrate_legacy_project_content(apps, schema_editor):
    ProjectPage = apps.get_model("portfolio", "ProjectPage")
    ProjectService = apps.get_model("portfolio", "ProjectService")
    database = schema_editor.connection.alias if schema_editor is not None else "default"

    for project in ProjectPage.objects.using(database).all().iterator():
        services = split_services(project.services)
        service_objects = ProjectService.objects.using(database)
        if services and not service_objects.filter(page_id=project.pk).exists():
            service_objects.bulk_create(
                [
                    ProjectService(page_id=project.pk, name=name, sort_order=index)
                    for index, name in enumerate(services)
                ]
            )

        if project.body and not project.content:
            project.content = statement_content(project.body)
            project.save(using=database, update_fields=["content"])

    migrate_project_revisions(apps, database)


class Migration(migrations.Migration):

    dependencies = [("portfolio", "0003_project_content_schema")]

    operations = [
        migrations.RunPython(migrate_legacy_project_content, migrations.RunPython.noop),
    ]
