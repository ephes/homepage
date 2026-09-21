import uuid
from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError
from wagtail.images import get_image_model
from wagtail.models import Collection

from homepage.portfolio.blocks import (
    BODY_RICH_TEXT_FEATURES,
    INLINE_RICH_TEXT_FEATURES,
    PROJECT_BLOCK_REGIONS,
    CaptionedImageBlock,
    ChallengeSolutionBlock,
    GalleryBlock,
    LegalCopyBlock,
    PortraitDuoBlock,
    ProjectBodyBlock,
    ProjectGalleryImageBlock,
    StatementBlock,
    get_project_block_region,
)

pytestmark = pytest.mark.django_db


def test_legal_contact_is_a_structural_reference_without_an_email_field():
    contact = LegalCopyBlock().child_blocks["contact"]

    assert list(contact.child_blocks) == ["prefix", "label", "suffix"]
    assert contact.meta.label == "Globale Kontaktadresse"
    assert all("email" not in name for name in contact.child_blocks)


def make_image(title, *, width, height):
    collection = Collection.get_first_root_node()
    if collection is None:
        collection = Collection.add_root(instance=Collection(name="Root"))
    return get_image_model().objects.create(
        collection=collection,
        title=title,
        file=f"original_images/{title.lower()}.jpg",
        width=width,
        height=height,
    )


def image_value(block, image, *, alt="Ein aussagekräftiger Alternativtext", large=False):
    return block.to_python(
        {
            "image": {
                "image": image.pk,
                "decorative": False,
                "alt_text": alt,
            },
            "caption": "",
            "large": large,
        }
    )


def test_gallery_images_require_alt_text_or_an_explicit_decorative_choice():
    image = make_image("Ohne Alt", width=1200, height=800)
    block = ProjectGalleryImageBlock()
    value = image_value(block, image, alt="")

    with pytest.raises(StructBlockValidationError) as error:
        block.clean(value)

    assert "image" in error.value.block_errors

    decorative = block.to_python(
        {
            "image": {"image": image.pk, "decorative": True, "alt_text": ""},
            "caption": "",
            "large": False,
        }
    )
    block.clean(decorative)


@pytest.mark.parametrize(
    ("width", "height", "orientation"),
    [(1200, 800, "landscape"), (800, 1200, "portrait"), (900, 900, "landscape")],
)
def test_gallery_orientation_is_derived_from_source_dimensions(width, height, orientation):
    image = make_image(f"Motiv {width}x{height}", width=width, height=height)
    value = image_value(ProjectGalleryImageBlock(), image)

    assert value.orientation == orientation
    assert value.is_portrait is (orientation == "portrait")


def test_gallery_requires_at_least_two_images():
    block = GalleryBlock()
    value = block.to_python({"images": []})

    with pytest.raises(StructBlockValidationError) as error:
        block.clean(value)

    assert "images" in error.value.block_errors


def test_mobile_gallery_rows_only_pair_adjacent_ordinary_portraits():
    portrait_a = make_image("Portrait A", width=800, height=1200)
    portrait_b = make_image("Portrait B", width=800, height=1200)
    portrait_c = make_image("Portrait C", width=800, height=1200)
    landscape = make_image("Landscape", width=1200, height=800)
    child = ProjectGalleryImageBlock()
    block = GalleryBlock()
    value = block.normalize(
        {
            "images": [
                image_value(child, portrait_a),
                image_value(child, portrait_b),
                image_value(child, landscape),
                image_value(child, portrait_c),
                image_value(child, portrait_a, large=True),
                image_value(child, portrait_b),
            ]
        }
    )

    rows = value.mobile_rows

    assert [len(row) for row in rows] == [2, 1, 1, 1, 1]
    assert all(item.block is block.child_blocks["images"].child_block for row in rows for item in row)
    assert rows[0][0].value.is_portrait and rows[0][1].value.is_portrait
    assert rows[3][0].value.is_large


def test_gallery_renders_bound_images_through_the_child_block_template_contract(
    monkeypatch,
):
    portrait_a = make_image("Bound Portrait A", width=800, height=1200)
    portrait_b = make_image("Bound Portrait B", width=800, height=1200)
    block = GalleryBlock()
    child = block.child_blocks["images"].child_block
    value = block.normalize(
        {
            "images": [
                image_value(child, portrait_a),
                image_value(child, portrait_b),
            ]
        }
    )
    render = Mock(side_effect=lambda _value, context=None: context.get("modifier", "single"))
    monkeypatch.setattr(child, "render", render)

    rendered = block.render(value)

    assert rendered.count("portrait-paired") == 2
    assert render.call_count == 2
    for call in render.call_args_list:
        context = call.kwargs["context"]
        assert context["modifier"] == "portrait-paired"
        assert context["image_sizes"].endswith("100vw")


def test_portrait_duo_rejects_a_landscape_source():
    portrait = make_image("Portrait", width=800, height=1200)
    landscape = make_image("Landscape Duo", width=1200, height=800)
    image_block = CaptionedImageBlock()
    block = PortraitDuoBlock()
    value = block.normalize(
        {
            "left": image_value(image_block, portrait),
            "right": image_value(image_block, landscape),
        }
    )

    with pytest.raises(StructBlockValidationError) as error:
        block.clean(value)

    assert "right" in error.value.block_errors


def test_rich_text_features_exclude_editor_control_of_heading_hierarchy():
    statement_features = StatementBlock().child_blocks["text"].features
    challenge_features = ChallengeSolutionBlock().child_blocks["challenge"].features

    assert statement_features == INLINE_RICH_TEXT_FEATURES
    assert challenge_features == BODY_RICH_TEXT_FEATURES
    assert "no-break" in statement_features
    assert "no-break" in challenge_features
    assert "h2" not in statement_features
    assert "h2" not in challenge_features
    assert "h3" not in challenge_features


def test_project_body_exposes_only_the_approved_structured_block_types():
    block = ProjectBodyBlock()

    assert list(block.child_blocks) == [
        "statement",
        "challenge_solution",
        "full_width_image",
        "image_pair",
        "portrait_duo",
        "gallery",
        "stats",
        "testimonial",
    ]


def test_project_body_render_regions_cover_every_type_and_default_to_visible_copy():
    block = ProjectBodyBlock()

    assert set(PROJECT_BLOCK_REGIONS) == set(block.child_blocks)
    assert set(PROJECT_BLOCK_REGIONS.values()) == {
        "case-study",
        "media",
        "results",
        "testimonial",
    }
    assert get_project_block_region("future_editorial_block") == "case-study"


def test_project_body_children_own_their_rendering_templates():
    block = ProjectBodyBlock()

    assert {name: child.meta.template for name, child in block.child_blocks.items()} == {
        "statement": "portfolio/blocks/statement.html",
        "challenge_solution": "portfolio/blocks/challenge_solution.html",
        "full_width_image": "portfolio/blocks/full_width_image.html",
        "image_pair": "portfolio/blocks/image_pair.html",
        "portrait_duo": "portfolio/blocks/portrait_duo.html",
        "gallery": "portfolio/blocks/gallery.html",
        "stats": "portfolio/blocks/stats.html",
        "testimonial": "portfolio/blocks/testimonial.html",
    }
    assert (
        block.child_blocks["image_pair"].child_blocks["left"].meta.template
        == "portfolio/blocks/captioned_image.html"
    )
    assert (
        block.child_blocks["gallery"].child_blocks["images"].child_block.meta.template
        == "portfolio/blocks/captioned_image.html"
    )


def test_project_value_block_uses_the_approved_editorial_label():
    stats = ProjectBodyBlock().child_blocks["stats"]

    assert stats.label == "Mehrwert"
    assert stats.child_blocks["items"].label == "Mehrwert"
    assert stats.child_blocks["items"].child_block.label == "Mehrwert"


def test_project_testimonial_uses_the_approved_editorial_label():
    testimonial = ProjectBodyBlock().child_blocks["testimonial"]

    assert testimonial.label == "Kundenstimmen"


def test_singleton_case_study_sections_are_enforced_by_stream_validation():
    from homepage.portfolio.models import ProjectPage

    block = ProjectPage._meta.get_field("content").stream_block
    value = block.to_python(
        [
            {
                "type": "statement",
                "value": {"text": "Das erste Projektstatement."},
                "id": str(uuid.uuid4()),
            },
            {
                "type": "statement",
                "value": {"text": "Ein zweites, semantisch mehrdeutiges Statement."},
                "id": str(uuid.uuid4()),
            },
        ]
    )

    with pytest.raises(StreamBlockValidationError) as error:
        block.clean(value)

    messages = [message for item in error.value.non_block_errors.as_data() for message in item.messages]
    assert any("Statement" in message for message in messages)


def test_required_structured_copy_reports_field_level_errors():
    block = ChallengeSolutionBlock()
    value = block.to_python({"challenge": "", "solution": "<p>Gelöst.</p>"})

    with pytest.raises(ValidationError) as error:
        block.clean(value)

    assert isinstance(error.value, StructBlockValidationError)
    assert "challenge" in error.value.block_errors
