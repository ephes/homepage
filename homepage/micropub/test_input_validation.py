"""Input rejects impossible storage values before attempting any publication."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from .forms import MicropubPostForm
from .handler import CastPostMicropubHandler, MicropubContentError
from .validation import TAG_NAME_FIELD, TITLE_FIELD


@pytest.mark.parametrize("property_name", ["name", "category"])
@pytest.mark.parametrize("invalid", ["overlong", "nul", "surrogate"])
def test_handler_rejects_invalid_title_or_tag_before_writes(monkeypatch, property_name, invalid):
    field = TITLE_FIELD if property_name == "name" else TAG_NAME_FIELD
    value = {"overlong": "x" * (field.max_length + 1), "nul": "hello\x00world", "surrogate": "hello\ud800"}[invalid]
    handler = CastPostMicropubHandler()
    create_post = Mock()
    monkeypatch.setattr(handler, "_create_post", create_post)
    monkeypatch.setattr("homepage.micropub.handler.transaction.atomic", nullcontext)
    with pytest.raises(MicropubContentError) as error:
        handler.create_entry({"name": ["Title"], "content": ["Body"], property_name: [value]}, SimpleNamespace(pk=1))
    assert str(error.value) == ("Title is not valid" if property_name == "name" else "Category is not valid")
    create_post.assert_not_called()


@pytest.mark.parametrize("form_field", ["name", "category"])
@pytest.mark.parametrize("invalid", ["overlong", "nul", "surrogate"])
def test_form_rejects_invalid_title_or_tag(form_field, invalid):
    field = TITLE_FIELD if form_field == "name" else TAG_NAME_FIELD
    value = {"overlong": "x" * (field.max_length + 1), "nul": "hello\x00world", "surrogate": "hello\ud800"}[invalid]
    form = MicropubPostForm(
        data={"blog": "alpha", "post_type": "article", "content": "Body", form_field: value},
        blogs=[SimpleNamespace(slug="alpha", title="Alpha")],
    )
    assert not form.is_valid()
    assert form_field in form.errors


def test_form_accepts_boundary_lengths_and_multilingual_text():
    form = MicropubPostForm(
        data={
            "blog": "alpha",
            "post_type": "article",
            "content": "Body",
            "name": "ä" * TITLE_FIELD.max_length,
            "category": "猫" * TAG_NAME_FIELD.max_length + ", Grüße 😀",
        },
        blogs=[SimpleNamespace(slug="alpha", title="Alpha")],
    )
    assert form.is_valid(), form.errors


@pytest.mark.parametrize(
    "categories",
    [",".join(["tag"] * 51), "," * 50, " " * 4094 + "tag", ",".join(["猫" * 90] * 46)],
    ids=["count", "empty-entries", "outer-whitespace", "aggregate-text"],
)
def test_form_rejects_category_batch_before_validating_names(monkeypatch, categories):
    validate_category = Mock()
    monkeypatch.setattr("homepage.micropub.forms.validate_category", validate_category)
    form = MicropubPostForm(
        data={"blog": "alpha", "post_type": "article", "content": "Body", "category": categories},
        blogs=[SimpleNamespace(slug="alpha", title="Alpha")],
    )

    assert not form.is_valid()
    assert "category" in form.errors
    validate_category.assert_not_called()


@pytest.mark.parametrize(
    "categories", [["tag"] * 51, ["猫" * 90] * 46, [" " * 4097]], ids=["count", "aggregate-text", "blank-entry"]
)
def test_handler_rejects_category_batch_before_validating_names_or_writing(monkeypatch, categories):
    handler = CastPostMicropubHandler()
    create_post = Mock()
    validate_category = Mock()
    monkeypatch.setattr(handler, "_create_post", create_post)
    monkeypatch.setattr("homepage.micropub.handler.validate_category", validate_category)
    monkeypatch.setattr("homepage.micropub.handler.transaction.atomic", nullcontext)

    with pytest.raises(MicropubContentError, match="Categories"):
        handler.create_entry({"content": ["Body"], "category": categories}, SimpleNamespace(pk=1))

    validate_category.assert_not_called()
    create_post.assert_not_called()


def test_category_batch_accepts_exact_form_and_handler_limits():
    names = ["猫" * 81] * 49 + ["x" * 78]
    assert len(",".join(names)) == 4096
    form = MicropubPostForm(
        data={"blog": "alpha", "post_type": "article", "content": "Body", "category": ",".join(names)},
        blogs=[SimpleNamespace(slug="alpha", title="Alpha")],
    )
    assert form.is_valid(), form.errors
    assert form.to_micropub_properties()["category"] == names

    names = ["猫" * 81] * 47 + ["猫" * 89, "猫" * 100, "x" * 100]
    assert sum(map(len, names)) == 4096
    assert CastPostMicropubHandler()._get_categories({"category": names}) == names
