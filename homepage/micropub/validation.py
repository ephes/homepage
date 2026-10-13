"""Shared model-backed validation for Micropub titles and category names."""

from cast.models import Post
from django.core.exceptions import ValidationError

TITLE_FIELD = Post._meta.get_field("title")
TAG_NAME_FIELD = Post._meta.get_field("tags").remote_field.model._meta.get_field("name")


def validate_title(value: str) -> None:
    _validate_text(value, TITLE_FIELD, "Title is not valid")


def validate_category(value: str) -> None:
    _validate_text(value, TAG_NAME_FIELD, "Category is not valid")


def _validate_text(value, field, message):
    # PostgreSQL text cannot store NUL or unpaired Unicode surrogates.
    try:
        if "\x00" in value:
            raise ValueError
        value.encode("utf-8")
        field.clean(value, None)
    except (ValueError, ValidationError):
        # Model validators may quote input. Only fixed messages leave this boundary.
        raise ValidationError(message) from None
