from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from wagtail import blocks

RICH_TEXT_FEATURES = ["bold", "italic", "code", "link"]

CATEGORY_CHOICES = [
    ("articles", "Articles"),
    ("software", "Software"),
    ("videos", "Videos"),
    ("podcasts", "Podcasts"),
    ("social", "Social"),
    ("weeknotes", "Weeknotes"),
    ("books", "Books"),
    ("papers", "Papers"),
    ("links", "Links"),
]

KIND_CHOICES = [
    ("article", "Article"),
    ("video", "Video"),
    ("podcast_episode", "Podcast episode"),
    ("social_post", "Social post"),
    ("link", "Link"),
]

CATEGORY_LABELS = dict(CATEGORY_CHOICES)


class WeeknoteLinkItemBlock(blocks.StructBlock):
    category = blocks.ChoiceBlock(choices=CATEGORY_CHOICES, required=True)
    kind = blocks.ChoiceBlock(choices=KIND_CHOICES, required=True, default="link")
    title = blocks.CharBlock(required=True)
    url = blocks.URLBlock(required=True)
    source = blocks.CharBlock(required=False)
    source_url = blocks.URLBlock(required=False)
    description = blocks.RichTextBlock(features=RICH_TEXT_FEATURES, required=False)

    def clean(self, value: Any) -> blocks.StructValue:
        cleaned_value = super().clean(value)
        if cleaned_value.get("source_url") and not cleaned_value.get("source"):
            raise blocks.StructBlockValidationError(
                block_errors={
                    "source_url": ValidationError("Source URL requires a source label."),
                }
            )
        return cleaned_value


class WeeknoteLinksBlock(blocks.ListBlock):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(WeeknoteLinkItemBlock(), min_num=1, **kwargs)

    def get_context(self, value: Any, parent_context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = super().get_context(value, parent_context=parent_context)
        grouped_categories = []
        for category_key, category_label in CATEGORY_CHOICES:
            items = [item for item in value if item.get("category") == category_key]
            if items:
                grouped_categories.append({"key": category_key, "label": category_label, "items": items})
        context.update(
            {
                "category_labels": CATEGORY_LABELS,
                "grouped_categories": grouped_categories,
            }
        )
        return context

    class Meta:
        template = "cast/weeknotes/links.html"
        label = "Weeknote links"


def weeknote_links_block() -> tuple[str, blocks.Block]:
    return "weeknote_links", WeeknoteLinksBlock()
