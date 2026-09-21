from copy import deepcopy
import uuid

import homepage.portfolio.models
import wagtail.fields
from django.db import migrations


TRANSITIONAL_STARTER_CONTENT = [
    {
        "type": "statement",
        "value": {
            "text": (
                "<p>[Ein prägnanter Satz, der das Projekt und seinen "
                "gestalterischen Kern erklärt.]</p>"
            )
        },
    },
    {
        "type": "challenge_solution",
        "value": {
            "challenge": (
                "<p>[Ausgangslage, Ziel und Rahmenbedingungen. Dieser Bereich "
                "wird später als redaktionelles Wagtail-Feld gepflegt.]</p>"
            ),
            "solution": (
                "<p>[Konzept, gestalterische Entscheidungen und Umsetzung. "
                "Bilder und Textblöcke können im späteren Template einzeln ein- "
                "oder ausgeblendet werden.]</p>"
            ),
        },
    },
]


def serialized_blocks(content):
    """Return mutable raw block data from a historical StreamField value."""

    return deepcopy(list(getattr(content, "raw_data", content)))


def is_transitional_starter(content):
    """Identify only the exact two-block placeholder written by migration 0012."""

    blocks = serialized_blocks(content)
    return [
        {"type": block.get("type"), "value": block.get("value")}
        for block in blocks
    ] == TRANSITIONAL_STARTER_CONTENT


def starter_blocks():
    """Return fresh serialized blocks for every required starter section."""

    return [
        {
            "type": "statement",
            "value": {
                "text": (
                    "<p>[Ein prägnanter Satz, der das Projekt und seinen "
                    "gestalterischen Kern erklärt.]</p>"
                )
            },
            "id": str(uuid.uuid4()),
        },
        {
            "type": "challenge_solution",
            "value": {
                "challenge": (
                    "<p>[Ausgangslage, Ziel und Rahmenbedingungen. Dieser Bereich "
                    "wird später als redaktionelles Wagtail-Feld gepflegt.]</p>"
                ),
                "solution": (
                    "<p>[Konzept, gestalterische Entscheidungen und Umsetzung. "
                    "Bilder und Textblöcke können im späteren Template einzeln ein- "
                    "oder ausgeblendet werden.]</p>"
                ),
            },
            "id": str(uuid.uuid4()),
        },
        {
            "type": "stats",
            "value": {
                "items": [
                    {
                        "type": "item",
                        "value": {
                            "value": f"0{number}",
                            "label": "[Ergebnis oder Kennzahl]",
                        },
                        "id": str(uuid.uuid4()),
                    }
                    for number in range(1, 5)
                ]
            },
            "id": str(uuid.uuid4()),
        },
        {
            "type": "testimonial",
            "value": {
                "quote": "[Optionales Kundenstatement zum Projekt.]",
                "name": "[Name]",
                "role": "[Rolle]",
            },
            "id": str(uuid.uuid4()),
        },
    ]


def seed_empty_project_starter_content(apps, schema_editor):
    """Complete 0012 placeholders or seed empty streams without touching revisions."""

    ProjectPage = apps.get_model("portfolio", "ProjectPage")
    database = schema_editor.connection.alias if schema_editor is not None else "default"

    for project in ProjectPage.objects.using(database).all().iterator():
        existing_blocks = serialized_blocks(project.content)
        if existing_blocks and not is_transitional_starter(project.content):
            continue
        complete_starter = starter_blocks()
        if existing_blocks:
            # Preserve the persistent IDs written by 0012 and append only the two
            # missing sections. Any edited or otherwise non-empty stream was rejected
            # by the exact comparison above.
            complete_starter[:2] = existing_blocks
        project.content = complete_starter
        project.save(using=database, update_fields=["content"])


class Migration(migrations.Migration):
    dependencies = [("portfolio", "0012_editorial_copy_sources")]

    operations = [
        migrations.RunPython(
            seed_empty_project_starter_content,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="projectpage",
            name="content",
            field=wagtail.fields.StreamField(
                [
                    ("statement", 1),
                    ("challenge_solution", 4),
                    ("full_width_image", 7),
                    ("image_pair", 10),
                    ("portrait_duo", 10),
                    ("gallery", 14),
                    ("stats", 19),
                    ("testimonial", 23),
                ],
                blank=True,
                block_counts={
                    "statement": {"max_num": 1},
                    "challenge_solution": {"max_num": 1},
                    "stats": {"max_num": 1},
                    "testimonial": {"max_num": 1},
                },
                block_lookup={
                    0: (
                        "wagtail.blocks.RichTextBlock",
                        (),
                        {"features": ["bold", "italic", "link"], "label": "Text"},
                    ),
                    1: ("wagtail.blocks.StructBlock", [[("text", 0)]], {}),
                    2: (
                        "wagtail.blocks.RichTextBlock",
                        (),
                        {
                            "features": ["bold", "italic", "ol", "ul", "link"],
                            "label": "Aufgabe",
                        },
                    ),
                    3: (
                        "wagtail.blocks.RichTextBlock",
                        (),
                        {
                            "features": ["bold", "italic", "ol", "ul", "link"],
                            "label": "Lösung",
                        },
                    ),
                    4: (
                        "wagtail.blocks.StructBlock",
                        [[("challenge", 2), ("solution", 3)]],
                        {},
                    ),
                    5: ("wagtail.images.blocks.ImageBlock", [], {"label": "Bild"}),
                    6: (
                        "wagtail.blocks.CharBlock",
                        (),
                        {
                            "label": "Bildunterschrift",
                            "max_length": 240,
                            "required": False,
                        },
                    ),
                    7: (
                        "wagtail.blocks.StructBlock",
                        [[("image", 5), ("caption", 6)]],
                        {},
                    ),
                    8: (
                        "wagtail.blocks.StructBlock",
                        [[("image", 5), ("caption", 6)]],
                        {"label": "Bild links"},
                    ),
                    9: (
                        "wagtail.blocks.StructBlock",
                        [[("image", 5), ("caption", 6)]],
                        {"label": "Bild rechts"},
                    ),
                    10: (
                        "wagtail.blocks.StructBlock",
                        [[("left", 8), ("right", 9)]],
                        {},
                    ),
                    11: (
                        "wagtail.blocks.BooleanBlock",
                        (),
                        {
                            "default": False,
                            "help_text": "Beginnt eine eigene, vollbreite Galeriezeile.",
                            "label": "Großes Motiv",
                            "required": False,
                        },
                    ),
                    12: (
                        "wagtail.blocks.StructBlock",
                        [[("image", 5), ("caption", 6), ("large", 11)]],
                        {},
                    ),
                    13: (
                        "wagtail.blocks.ListBlock",
                        (12,),
                        {
                            "help_text": (
                                "Mindestens zwei Bilder; die Reihenfolge kann frei "
                                "geändert werden."
                            ),
                            "label": "Bilder",
                            "min_num": 2,
                        },
                    ),
                    14: (
                        "wagtail.blocks.StructBlock",
                        [[("images", 13)]],
                        {},
                    ),
                    15: (
                        "wagtail.blocks.CharBlock",
                        (),
                        {"label": "Wert", "max_length": 80},
                    ),
                    16: (
                        "wagtail.blocks.CharBlock",
                        (),
                        {"label": "Bezeichnung", "max_length": 160},
                    ),
                    17: (
                        "wagtail.blocks.StructBlock",
                        [[("value", 15), ("label", 16)]],
                        {},
                    ),
                    18: (
                        "wagtail.blocks.ListBlock",
                        (17,),
                        {"label": "Ergebnisse", "min_num": 1},
                    ),
                    19: (
                        "wagtail.blocks.StructBlock",
                        [[("items", 18)]],
                        {},
                    ),
                    20: ("wagtail.blocks.TextBlock", (), {"label": "Zitat"}),
                    21: (
                        "wagtail.blocks.CharBlock",
                        (),
                        {"label": "Name", "max_length": 120},
                    ),
                    22: (
                        "wagtail.blocks.CharBlock",
                        (),
                        {"label": "Rolle", "max_length": 160, "required": False},
                    ),
                    23: (
                        "wagtail.blocks.StructBlock",
                        [[("quote", 20), ("name", 21), ("role", 22)]],
                        {},
                    ),
                },
                default=homepage.portfolio.models.default_project_content,
                verbose_name="Projektinhalt",
            ),
        ),
    ]
