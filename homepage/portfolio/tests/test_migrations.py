import json
from importlib import import_module

import pytest
from django.apps import apps as django_apps

from homepage.portfolio.models import ProjectService

from .test_models import add_project, make_portfolio_tree

pytestmark = pytest.mark.django_db


def get_migration():
    return import_module("homepage.portfolio.migrations.0004_migrate_legacy_project_content")


def test_legacy_revision_is_migrated_from_its_own_historic_values():
    index = make_portfolio_tree()
    project = add_project(index, "Revisionsmigration")
    revision = project.get_latest_revision()
    revision_content = dict(revision.content)
    revision_content.pop("content")
    revision_content.pop("service_items")
    revision_content["services"] = "Historische Strategie, Art Direction"
    revision_content["body"] = "<p>Historischer Projekttext.</p>"
    revision.content = revision_content
    revision.save(update_fields=["content"])

    migration = get_migration()
    migration.migrate_legacy_project_content(django_apps, None)
    revision.refresh_from_db()

    assert [
        (item["name"], item["sort_order"], item["page"])
        for item in revision.content["service_items"]
    ] == [
        ("Historische Strategie", 0, project.pk),
        ("Art Direction", 1, project.pk),
    ]
    migrated_content = json.loads(revision.content["content"])
    assert len(migrated_content) == 1
    assert migrated_content[0]["type"] == "statement"
    assert migrated_content[0]["value"]["text"] == "<p>Historischer Projekttext.</p>"

    # Publishing the old revision must restore its historic structured values,
    # rather than blanking the fields introduced after the revision was saved.
    revision.publish(log_action=False)
    project.refresh_from_db()

    assert list(project.service_items.values_list("name", "sort_order")) == [
        ("Historische Strategie", 0),
        ("Art Direction", 1),
    ]
    assert len(project.content) == 1
    assert project.content[0].block_type == "statement"
    assert "Historischer Projekttext." in str(project.content[0].value["text"])


def test_legacy_revision_migration_is_idempotent_and_preserves_structured_values():
    index = make_portfolio_tree()
    project = add_project(index, "Strukturierte Revision")
    ProjectService.objects.create(page=project, name="Redaktion", sort_order=0)
    project.content = [
        {
            "type": "statement",
            "value": {"text": "<p>Bereits strukturiert.</p>"},
            "id": "4955fae0-49bc-4a31-9a61-66fe06909eb1",
        }
    ]
    revision = project.save_revision()
    structured_services = revision.content["service_items"]
    structured_content = revision.content["content"]

    migration = get_migration()
    migration.migrate_legacy_project_content(django_apps, None)
    migration.migrate_legacy_project_content(django_apps, None)
    revision.refresh_from_db()

    assert revision.content["service_items"] == structured_services
    assert revision.content["content"] == structured_content
