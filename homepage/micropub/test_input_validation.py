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
