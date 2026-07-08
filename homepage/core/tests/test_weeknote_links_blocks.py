import uuid

import pytest
from cast.post_body_blocks import configured_content_blocks, validate_post_body_block_setting
from wagtail.blocks.list_block import ListBlockValidationError
from wagtail.blocks.struct_block import StructBlockValidationError

from homepage.core.weeknotes.blocks import WeeknoteLinkItemBlock, WeeknoteLinksBlock, weeknote_links_block


def link_item(**overrides):
    item = {
        "category": "articles",
        "kind": "article",
        "title": "Grid Security at Scale",
        "url": "https://lfenergy.org/grid-security-at-scale-tennet-powsybl/",
        "source": "LF Energy",
        "source_url": "https://lfenergy.org/",
        "description": "<p>TenneT got a 10x speedup.</p>",
    }
    item.update(overrides)
    return item


def test_weeknote_links_block_factory_returns_stable_name():
    name, block = weeknote_links_block()

    assert name == "weeknote_links"
    assert isinstance(block, WeeknoteLinksBlock)


def test_weeknote_links_block_is_registered_for_overview_only():
    overview_block_names = [name for name, _ in configured_content_blocks("overview")]
    detail_block_names = [name for name, _ in configured_content_blocks("detail")]

    assert "weeknote_links" in overview_block_names
    assert "weeknote_links" not in detail_block_names


def test_post_body_block_setting_validates_without_errors():
    assert validate_post_body_block_setting() == []


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("category", "invalid-category"),
        ("kind", "invalid-kind"),
        ("url", "not a url"),
        ("source_url", "not a url"),
    ],
)
def test_weeknote_link_item_rejects_invalid_field_values(field_name, value):
    block = WeeknoteLinkItemBlock()

    with pytest.raises(StructBlockValidationError) as exc_info:
        block.clean(block.to_python(link_item(**{field_name: value})))

    assert field_name in exc_info.value.block_errors


def test_weeknote_link_item_rejects_source_url_without_source():
    block = WeeknoteLinkItemBlock()

    with pytest.raises(StructBlockValidationError) as exc_info:
        block.clean(block.to_python(link_item(source="", source_url="https://example.com/source/")))

    assert "source_url" in exc_info.value.block_errors


def test_weeknote_links_block_rejects_invalid_child_field_values():
    block = WeeknoteLinksBlock()

    with pytest.raises(ListBlockValidationError) as exc_info:
        block.clean(block.to_python([link_item(category="invalid-category")]))

    child_error = exc_info.value.block_errors[0]
    assert isinstance(child_error, StructBlockValidationError)
    assert "category" in child_error.block_errors


def test_weeknote_links_block_context_groups_by_fixed_category_order_and_omits_empty_groups():
    block = WeeknoteLinksBlock()
    value = block.to_python(
        [
            link_item(category="links", kind="link", title="Later link"),
            link_item(category="articles", title="First article"),
            link_item(category="software", kind="link", title="Tool"),
            link_item(category="articles", title="Second article"),
        ]
    )

    context = block.get_context(value)

    assert list(context["category_labels"].items())[:3] == [
        ("articles", "Articles"),
        ("software", "Software"),
        ("videos", "Videos"),
    ]
    assert [group["key"] for group in context["grouped_categories"]] == ["articles", "software", "links"]
    assert [item["title"] for item in context["grouped_categories"][0]["items"]] == [
        "First article",
        "Second article",
    ]


def test_weeknote_links_block_get_prep_value_uses_list_block_item_wrapper_shape():
    block = WeeknoteLinksBlock()

    value = block.clean(block.to_python([link_item()]))

    prep_value = block.get_prep_value(value)

    assert len(prep_value) == 1
    item = prep_value[0]
    assert set(item) == {"type", "value", "id"}
    assert item["type"] == "item"
    uuid.UUID(item["id"])
    assert item["value"] == link_item()
