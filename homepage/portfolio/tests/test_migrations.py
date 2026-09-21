import json
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace
from uuid import UUID

import pytest
from django.apps import apps as django_apps
from django.db import connection, migrations
from wagtail.models import PageViewRestriction, Site

from homepage.portfolio.models import (
    LegalPageSettings,
    PortfolioSiteSettings,
    ProjectCategory,
    ProjectService,
)

from .test_models import add_project, make_portfolio_tree

pytestmark = pytest.mark.django_db


def get_migration():
    return import_module(
        "homepage.portfolio.migrations.0004_migrate_legacy_project_content"
    )


def _legal_field_from_operation(migration, field_name):
    for operation in migration.Migration.operations:
        if isinstance(operation, migrations.CreateModel):
            return dict(operation.fields)[field_name]
        if (
            isinstance(operation, migrations.AlterField)
            and operation.model_name == "legalpagesettings"
            and operation.name == field_name
        ):
            return operation.field
    raise AssertionError(f"Migration does not define {field_name}")


@pytest.mark.parametrize(
    "migration_name",
    ["0011_legalpagesettings", "0015_project_value_labels"],
)
@pytest.mark.parametrize(
    ("field_name", "expected_headings"),
    [
        ("imprint_sections", ["Anbieterin", "Kontakt"]),
        (
            "privacy_sections",
            [
                "Verantwortlich",
                "Websiteabruf",
                "E-Mail-Kontakt",
                "Cookies & Tracking",
                "Empfänger & Drittland",
                "Ihre Rechte",
                "Bereitstellung",
            ],
        ),
    ],
)
def test_pre_contact_legal_defaults_are_frozen_and_valid_for_historical_blocks(
    migration_name, field_name, expected_headings
):
    migration = import_module(f"homepage.portfolio.migrations.{migration_name}")
    field = _legal_field_from_operation(migration, field_name)

    assert field.default.__module__ == (
        "homepage.portfolio.migrations._legal_defaults_v1"
    )
    raw_default = field.get_default()
    stream_value = field.to_python(raw_default)
    serialized = field.get_prep_value(stream_value)

    assert [block.value["heading"] for block in stream_value] == expected_headings
    assert all(
        child.block_type in {"paragraph", "address", "note"}
        for section in stream_value
        for child in section.value["copy"]
    )
    serialized_json = json.dumps(serialized)
    assert '"type": "contact"' not in serialized_json
    assert "portfolio-contact@example.invalid" in serialized_json


def test_editorial_copy_source_migration_seeds_contact_and_project_starters_once():
    index = make_portfolio_tree()
    site = Site.objects.get(hostname="testserver")
    index.contact_email = "legacy-index@example.com"
    index.save(update_fields=["contact_email"])
    project = add_project(index, "Leeres Projekt")
    project.content = []
    project.save(update_fields=["content"])
    existing_site = Site.objects.create(
        hostname="existing-global.test",
        root_page=site.root_page,
        site_name="Bestehende globale Einstellungen",
    )
    existing_settings = PortfolioSiteSettings.objects.create(
        site=existing_site,
        contact_email="existing-global@example.com",
    )
    migration = import_module(
        "homepage.portfolio.migrations.0012_editorial_copy_sources"
    )
    schema_editor = SimpleNamespace(connection=connection)

    assert not project.content
    migration.seed_single_contact_source_and_project_content(django_apps, schema_editor)
    project.refresh_from_db()
    created_settings = PortfolioSiteSettings.objects.get(site=site)
    first_starter_content = [
        (
            block.block_type,
            {field_name: str(value) for field_name, value in block.value.items()},
        )
        for block in project.content
    ]
    first_block_ids = [block.id for block in project.content]

    assert created_settings.contact_email == "legacy-index@example.com"
    assert existing_settings.contact_email == "existing-global@example.com"
    assert [block_type for block_type, _value in first_starter_content] == [
        "statement",
        "challenge_solution",
    ]
    assert len(first_starter_content) == 2
    assert first_starter_content == [
        (block["type"], block["value"])
        for block in migration.PROJECT_STARTER_CONTENT
    ]
    assert all(block_id is not None for block_id in first_block_ids)
    assert all(str(UUID(str(block_id))) == str(block_id) for block_id in first_block_ids)

    index.contact_email = "changed-after-first-run@example.com"
    index.save(update_fields=["contact_email"])
    migration.seed_single_contact_source_and_project_content(django_apps, schema_editor)
    created_settings.refresh_from_db()
    existing_settings.refresh_from_db()
    project.refresh_from_db()

    assert created_settings.contact_email == "legacy-index@example.com"
    assert existing_settings.contact_email == "existing-global@example.com"
    second_starter_content = [
        (
            block.block_type,
            {field_name: str(value) for field_name, value in block.value.items()},
        )
        for block in project.content
    ]
    assert second_starter_content == first_starter_content
    assert [block.id for block in project.content] == first_block_ids


def test_project_starter_migration_only_seeds_empty_live_content():
    index = make_portfolio_tree()
    project = add_project(index, "Individuelles Projekt")
    existing_block_id = "4955fae0-49bc-4a31-9a61-66fe06909eb1"
    project.content = [
        {
            "type": "statement",
            "value": {"text": "<p>Eigener, bestehender Projekttext.</p>"},
            "id": existing_block_id,
        }
    ]
    project.save(update_fields=["content"])
    revision = project.save_revision()
    empty_project = add_project(index, "Leeres Projekt")
    empty_project.content = []
    empty_project.save(update_fields=["content"])
    empty_revision = empty_project.save_revision()
    transitional_migration = import_module(
        "homepage.portfolio.migrations.0012_editorial_copy_sources"
    )
    migration = import_module(
        "homepage.portfolio.migrations.0013_project_starter_content"
    )
    schema_editor = SimpleNamespace(connection=connection)

    transitional_migration.seed_single_contact_source_and_project_content(
        django_apps, schema_editor
    )
    empty_project.refresh_from_db()
    transitional_block_ids = [block.id for block in empty_project.content]

    assert [block.block_type for block in empty_project.content] == [
        "statement",
        "challenge_solution",
    ]

    still_empty_project = add_project(index, "Nach 0012 noch leeres Projekt")
    still_empty_project.content = []
    still_empty_project.save(update_fields=["content"])
    edited_transitional_project = add_project(index, "Bearbeiteter Übergangsstarter")
    edited_transitional_content = migration.starter_blocks()[:2]
    edited_transitional_content[0]["value"]["text"] = (
        "<p>Redaktionell geänderter Statement-Text.</p>"
    )
    edited_transitional_project.content = edited_transitional_content
    edited_transitional_project.save(update_fields=["content"])
    edited_transitional_ids = [
        block.id for block in edited_transitional_project.content
    ]

    migration.seed_empty_project_starter_content(django_apps, schema_editor)
    project.refresh_from_db()
    revision.refresh_from_db()
    empty_project.refresh_from_db()
    empty_revision.refresh_from_db()
    still_empty_project.refresh_from_db()
    edited_transitional_project.refresh_from_db()

    assert [block.block_type for block in project.content] == ["statement"]
    assert project.content[0].id == existing_block_id
    assert "Eigener, bestehender Projekttext." in str(project.content[0].value["text"])
    assert [block.block_type for block in empty_project.content] == [
        "statement",
        "challenge_solution",
        "stats",
        "testimonial",
    ]
    assert [block.id for block in empty_project.content[:2]] == transitional_block_ids
    assert [block.block_type for block in still_empty_project.content] == [
        "statement",
        "challenge_solution",
        "stats",
        "testimonial",
    ]
    assert [block.block_type for block in edited_transitional_project.content] == [
        "statement",
        "challenge_solution",
    ]
    assert [block.id for block in edited_transitional_project.content] == (
        edited_transitional_ids
    )

    revision_content = revision.content["content"]
    if isinstance(revision_content, str):
        revision_content = json.loads(revision_content)
    assert [block["type"] for block in revision_content] == ["statement"]
    assert revision_content[0]["id"] == existing_block_id
    empty_revision_content = empty_revision.content["content"]
    if isinstance(empty_revision_content, str):
        empty_revision_content = json.loads(empty_revision_content)
    assert empty_revision_content == []

    first_project_block_ids = [block.id for block in project.content]
    first_empty_project_block_ids = [block.id for block in empty_project.content]

    migration.seed_empty_project_starter_content(django_apps, schema_editor)
    project.refresh_from_db()
    empty_project.refresh_from_db()

    assert [block.id for block in project.content] == first_project_block_ids
    assert [block.id for block in empty_project.content] == first_empty_project_block_ids

    migration.Migration.operations[0].reverse_code(django_apps, schema_editor)
    project.refresh_from_db()
    empty_project.refresh_from_db()

    assert [block.id for block in project.content] == first_project_block_ids
    assert [block.id for block in empty_project.content] == first_empty_project_block_ids


def test_project_value_label_migration_only_updates_the_previous_default():
    index = make_portfolio_tree()
    site = index.get_site()
    default_settings = PortfolioSiteSettings.for_site(site)
    default_settings.results_label = "Ergebnisse"
    default_settings.project_testimonial_label = "Rückmeldung"
    default_settings.save(
        update_fields=["results_label", "project_testimonial_label"]
    )
    custom_site = Site.objects.create(
        hostname="custom-value-label.test",
        root_page=site.root_page,
        site_name="Eigene Mehrwertbezeichnung",
    )
    custom_settings = PortfolioSiteSettings.objects.create(
        site=custom_site,
        results_label="Wirkung",
        project_testimonial_label="Resonanz",
    )
    migration = import_module(
        "homepage.portfolio.migrations.0015_project_value_labels"
    )

    migration.rename_default_results_label(django_apps, None)
    default_settings.refresh_from_db()
    custom_settings.refresh_from_db()

    assert default_settings.results_label == "Mehrwert"
    assert default_settings.project_testimonial_label == "Kundenstimmen"
    assert custom_settings.results_label == "Wirkung"
    assert custom_settings.project_testimonial_label == "Resonanz"


def test_structural_legal_contact_migration_removes_persisted_mail_placeholders():
    index = make_portfolio_tree()
    site = index.get_site()
    PortfolioSiteSettings.objects.create(
        site=site,
        contact_email="single-source@example.test",
    )
    legal_settings = LegalPageSettings.objects.create(
        site=site,
        imprint_sections=[
            (
                "section",
                {
                    "heading": "Kontakt",
                    "copy": [
                        (
                            "paragraph",
                            '<p>E-Mail: <a href="mailto:portfolio-contact@example.invalid">'
                            "Kontakt per E-Mail</a></p>",
                        )
                    ],
                },
            )
        ],
        privacy_sections=[
            (
                "section",
                {
                    "heading": "Verantwortlich",
                    "copy": [
                        (
                            "address",
                            "<p>Katharina Wersdörfer<br>Deutschland<br><br>E-Mail: "
                            '<a href="mailto:single-source@example.test">'
                            "single-source@example.test</a></p>",
                        )
                    ],
                },
            )
        ],
    )
    migration = import_module(
        "homepage.portfolio.migrations.0022_structural_legal_contact"
    )
    schema_editor = SimpleNamespace(connection=connection)

    migration.migrate_legal_contacts(django_apps, schema_editor)
    legal_settings.refresh_from_db()
    imprint_raw = legal_settings.imprint_sections.raw_data
    privacy_raw = legal_settings.privacy_sections.raw_data
    serialized = json.dumps([list(imprint_raw), list(privacy_raw)])

    assert imprint_raw[0]["value"]["copy"][0]["type"] == "contact"
    assert imprint_raw[0]["value"]["copy"][0]["value"] == {
        "prefix": "E-Mail:",
        "label": "Kontakt per E-Mail",
        "suffix": "",
    }
    assert [item["type"] for item in privacy_raw[0]["value"]["copy"]] == [
        "address",
        "contact",
    ]
    assert "Katharina Wersdörfer<br>Deutschland" in privacy_raw[0]["value"][
        "copy"
    ][0]["value"]
    assert "example.invalid" not in serialized
    assert "single-source@example.test" not in serialized
    assert "mailto:" not in serialized

    first_result = serialized
    migration.migrate_legal_contacts(django_apps, schema_editor)
    legal_settings.refresh_from_db()
    assert (
        json.dumps(
            [
                list(legal_settings.imprint_sections.raw_data),
                list(legal_settings.privacy_sections.raw_data),
            ]
        )
        == first_result
    )

    migration.restore_embedded_legal_contacts(django_apps, schema_editor)
    legal_settings.refresh_from_db()
    restored_imprint = legal_settings.imprint_sections.raw_data
    restored_privacy = legal_settings.privacy_sections.raw_data
    restored_serialized = json.dumps(
        [list(restored_imprint), list(restored_privacy)]
    )

    assert [item["type"] for item in restored_imprint[0]["value"]["copy"]] == [
        "paragraph"
    ]
    assert [item["type"] for item in restored_privacy[0]["value"]["copy"]] == [
        "address",
    ]
    assert restored_privacy[0]["value"]["copy"][0]["value"] == (
        "<p>Katharina Wersdörfer<br>Deutschland<br><br>E-Mail: "
        '<a href="mailto:single-source@example.test">'
        "single-source@example.test</a></p>"
    )
    assert "single-source@example.test" in restored_serialized
    assert "portfolio-contact@example.invalid" not in restored_serialized


def test_structural_legal_contact_reverse_preserves_an_authored_address_contact_pair():
    migration = import_module(
        "homepage.portfolio.migrations.0022_structural_legal_contact"
    )
    raw_sections = [
        {
            "type": "section",
            "value": {
                "heading": "Kontakt",
                "copy": [
                    {
                        "type": "address",
                        "value": "<p>Eigene Adresse</p>",
                        "id": "authored-address",
                    },
                    {
                        "type": "contact",
                        "value": {"prefix": "E-Mail:", "label": "", "suffix": ""},
                        "id": "authored-contact",
                    },
                ],
            },
        }
    ]

    assert migration._restore_stream(raw_sections, "contact@example.test") is True
    assert [item["type"] for item in raw_sections[0]["value"]["copy"]] == [
        "address",
        "paragraph",
    ]
    assert raw_sections[0]["value"]["copy"][0] == {
        "type": "address",
        "value": "<p>Eigene Adresse</p>",
        "id": "authored-address",
    }


def test_structural_legal_contact_migration_skips_lossy_contact_candidates():
    migration = import_module(
        "homepage.portfolio.migrations.0022_structural_legal_contact"
    )
    email = "single-source@example.test"
    link = f'<a href="mailto:{email}">Kontakt</a>'
    candidates = [
        ("paragraph", f"E-Mail: {link}"),
        ("paragraph", f"<p>E-Mail: {link}</p><p>Weiterer Absatz.</p>"),
        ("paragraph", f"<p><strong>E-Mail:</strong> {link}</p>"),
        ("paragraph", f"<p>E-Mail: {link}<em>.</em></p>"),
        ("paragraph", f"<p>{'V' * 241}{link}</p>"),
        (
            "paragraph",
            f'<p>E-Mail: <a href="mailto:{email}">{"L" * 161}</a></p>',
        ),
        ("paragraph", f"<p>E-Mail: {link}{'N' * 121}</p>"),
        (
            "address",
            f"<p>Katharina<br><br><strong>E-Mail:</strong> {link}</p>",
        ),
    ]
    raw_sections = [
        {
            "type": "section",
            "value": {
                "heading": "Kontakt",
                "copy": [
                    {"type": block_type, "value": candidate, "id": str(index)}
                    for index, (block_type, candidate) in enumerate(candidates)
                ],
            },
        }
    ]
    original = deepcopy(raw_sections)

    assert migration._migrate_stream(raw_sections, email) is False
    assert raw_sections == original


def test_structural_legal_contact_stream_helpers_do_not_add_or_replace_copy():
    migration = import_module(
        "homepage.portfolio.migrations.0022_structural_legal_contact"
    )
    unchanged_copy = [
        {"type": "note", "value": "Unveränderter Hinweis", "id": "note"}
    ]
    raw_sections = [
        {"type": "section", "value": {"heading": "Ohne Text"}},
        {
            "type": "section",
            "value": {"heading": "Mit Hinweis", "copy": unchanged_copy},
        },
    ]
    original = deepcopy(raw_sections)

    assert migration._migrate_stream(raw_sections, "contact@example.test") is False
    assert raw_sections == original
    assert "copy" not in raw_sections[0]["value"]
    assert raw_sections[1]["value"]["copy"] is unchanged_copy

    assert migration._restore_stream(raw_sections, "contact@example.test") is False
    assert raw_sections == original
    assert "copy" not in raw_sections[0]["value"]
    assert raw_sections[1]["value"]["copy"] is unchanged_copy


def test_structural_legal_contact_migration_skips_malformed_section_values():
    migration = import_module(
        "homepage.portfolio.migrations.0022_structural_legal_contact"
    )
    raw_sections = [{"type": "section", "id": "missing-value"}]

    assert migration._migrate_stream(raw_sections, "contact@example.test") is False
    assert raw_sections == [{"type": "section", "id": "missing-value"}]


def test_editable_category_migration_preserves_pages_and_revision_content():
    index = make_portfolio_tree()
    project = add_project(index, "Migrierte Kategorie")
    placeholder = ProjectCategory.objects.create(name="Vor der Migration")
    project.category = placeholder
    project.category_legacy = "web"
    project.save(update_fields=["category", "category_legacy"])
    revision = project.save_revision()
    revision_content = dict(revision.content)
    revision_content["category"] = "web"
    revision_content.pop("category_legacy", None)
    revision.content = revision_content
    revision.save(update_fields=["content"])
    migration = import_module(
        "homepage.portfolio.migrations.0017_editable_project_categories"
    )
    schema_editor = SimpleNamespace(connection=connection)

    migration.migrate_project_categories(django_apps, schema_editor)
    project.refresh_from_db()
    revision.refresh_from_db()

    assert set(
        ProjectCategory.objects.filter(
            name__in={"Web", "Digital", "Print", "Illustration"}
        ).values_list("name", flat=True)
    ) == {"Web", "Digital", "Print", "Illustration"}
    assert project.category.name == "Web"
    assert project.category_legacy == "web"
    assert revision.content["category"] == project.category_id
    assert revision.content["category_legacy"] == "web"

    migration.restore_fixed_project_categories(django_apps, schema_editor)
    project.refresh_from_db()
    revision.refresh_from_db()

    assert project.category_legacy == "web"
    assert revision.content["category"] == "web"
    assert "category_legacy" not in revision.content


def test_editable_category_migration_preserves_unexpected_legacy_values():
    index = make_portfolio_tree()
    project = add_project(index, "Freie Altkategorie")
    project.category_legacy = "spatial-design"
    project.save(update_fields=["category_legacy"])
    migration = import_module(
        "homepage.portfolio.migrations.0017_editable_project_categories"
    )
    schema_editor = SimpleNamespace(connection=connection)

    migration.migrate_project_categories(django_apps, schema_editor)
    project.refresh_from_db()

    assert project.category.name == "Spatial Design"
    assert project.category_legacy == "spatial-design"


def test_homepage_tile_migration_preserves_the_approved_hero_rhythm_and_revisions():
    index = make_portfolio_tree()
    projects = [add_project(index, f"Projekt {number}") for number in range(1, 10)]
    migration = import_module(
        "homepage.portfolio.migrations.0019_homepage_project_tiles"
    )
    schema_editor = SimpleNamespace(connection=connection)

    migration.seed_homepage_hero_tiles(django_apps, schema_editor)
    for project in projects:
        project.refresh_from_db()

    assert [project.homepage_is_hero for project in projects] == [
        True,
        False,
        False,
        False,
        False,
        True,
        True,
        False,
        False,
    ]
    for project in projects:
        revision = project.get_latest_revision()
        assert revision.content["homepage_is_hero"] is project.homepage_is_hero

    migration.remove_homepage_hero_tiles_from_revisions(django_apps, schema_editor)
    for project in projects:
        revision = project.get_latest_revision()
        revision.refresh_from_db()
        assert "homepage_is_hero" not in revision.content


def test_homepage_tile_migration_ignores_draft_and_restricted_projects():
    index = make_portfolio_tree()
    public_projects = [add_project(index, "Öffentlich 1")]
    draft = add_project(index, "Entwurf", publish=False)
    public_projects.append(add_project(index, "Öffentlich 2"))
    private = add_project(index, "Privat")
    PageViewRestriction.objects.create(
        page=private,
        restriction_type=PageViewRestriction.LOGIN,
    )
    public_projects.extend(
        add_project(index, f"Öffentlich {number}") for number in range(3, 10)
    )
    migration = import_module(
        "homepage.portfolio.migrations.0019_homepage_project_tiles"
    )
    schema_editor = SimpleNamespace(connection=connection)

    migration.seed_homepage_hero_tiles(django_apps, schema_editor)

    for project in [*public_projects, draft, private]:
        project.refresh_from_db()
    assert [project.homepage_is_hero for project in public_projects] == [
        True,
        False,
        False,
        False,
        False,
        True,
        True,
        False,
        False,
    ]
    assert draft.homepage_is_hero is False
    assert private.homepage_is_hero is False
    assert draft.get_latest_revision().content["homepage_is_hero"] is False
    assert private.get_latest_revision().content["homepage_is_hero"] is False


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
