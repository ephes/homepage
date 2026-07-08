import uuid
from datetime import date
from types import SimpleNamespace

import pytest
from cast.models.pages import ContentBlock
from cast.post_body_blocks import configured_content_blocks, validate_post_body_block_setting
from django.template.loader import render_to_string
from wagtail import blocks
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


def test_weeknote_links_block_renders_grouped_plain_markup():
    block = WeeknoteLinksBlock()
    value = block.to_python(
        [
            link_item(category="links", kind="link", title="Later link", source="", source_url="", description=""),
            link_item(category="articles", kind="article", title="Article A", source="Plain source", source_url=""),
            link_item(
                category="software",
                kind="link",
                title="Tool",
                source="Tool source",
                source_url="https://example.com/source/",
                description="<p>Useful <strong>tool</strong>.</p>",
            ),
            link_item(category="articles", kind="article", title="Article B", source="", source_url=""),
        ]
    )

    html = block.render(value, context={"render_for_feed": False})

    assert (
        html.index('<h2 class="weeknote-link-heading">Articles</h2>')
        < html.index('<h2 class="weeknote-link-heading">Software</h2>')
        < html.index('<h2 class="weeknote-link-heading">Links</h2>')
    )
    assert "Videos" not in html
    assert html.index("Article A") < html.index("Article B")
    assert '<li class="weeknote-link-item weeknote-link-item--article" data-kind="article">' in html
    assert '<p class="weeknote-link-head">' in html
    assert '<span class="weeknote-link-source">' in html
    assert "Plain source" in " ".join(html.split())
    assert "(Plain source)" not in " ".join(html.split())
    assert '<a href="https://example.com/source/">Tool source</a>' in html
    assert "weeknote-link-separator" not in html
    assert '<div class="weeknote-link-description">' in html
    assert "Useful <b>tool</b>." in html or "Useful <strong>tool</strong>." in html


def _post_body_with_weeknote_links(items):
    body_block = blocks.StreamBlock(
        [
            ("overview", ContentBlock(section="overview")),
            ("detail", ContentBlock(section="detail")),
        ]
    )
    weeknote_block = WeeknoteLinksBlock()
    value = weeknote_block.clean(weeknote_block.to_python(items))
    return body_block.to_python(
        [
            {
                "type": "overview",
                "value": [
                    {
                        "type": "weeknote_links",
                        "value": weeknote_block.get_prep_value(value),
                    }
                ],
            }
        ]
    )


def _render_post_body_template(template_name, *, render_detail=True, render_for_feed=False):
    page = SimpleNamespace(
        body=_post_body_with_weeknote_links([link_item(title="Rendered through theme")]),
        owner=SimpleNamespace(username="jochen", profile=None),
        page_url="/blogs/ephes_blog/weeknotes-2026-04-27/",
        title="Weeknotes 2026-04-27",
        visible_date=date(2026, 4, 27),
    )
    return render_to_string(
        template_name,
        {
            "blog": SimpleNamespace(author="Jochen"),
            "comments_are_enabled": False,
            "episode_contributors": None,
            "page": page,
            "render_detail": render_detail,
            "render_for_feed": render_for_feed,
        },
    )


@pytest.mark.parametrize(
    "template_name",
    [
        "cast/bootstrap5/post_body.html",
        "cast/bootstrap4/post_body.html",
        "cast/plain/post_body.html",
        "cast/vue/post_body.html",
    ],
)
def test_weeknote_links_render_through_post_body_themes(template_name):
    html = _render_post_body_template(template_name)

    assert "Rendered through theme" in html
    assert "weeknote-link-item--article" in html
    assert '<h2 class="weeknote-link-heading">Articles</h2>' in html


def test_weeknote_links_render_card_context_with_subordinate_heading():
    html = _render_post_body_template("cast/bootstrap5/post_body.html", render_detail=False)

    assert "Rendered through theme" in html
    assert '<h3 class="weeknote-link-heading">Articles</h3>' in html
    assert '<h2 class="weeknote-link-heading">Articles</h2>' not in html


def test_weeknote_links_render_for_feed_context():
    html = _render_post_body_template("cast/bootstrap5/post_body.html", render_for_feed=True)

    assert "Rendered through theme" in html
    assert "weeknote-link-item--article" in html
