"""Homepage override of django-resume's cover-letter plugin.

Adds the editorial cover-letter fields (closing line + signature) without
changing django-resume. Registered under the name "cover" in ``apps.ready()``;
the plugin registry overrides by name, so this shadows the built-in CoverPlugin.

Rendering the new flat fields needs nothing more — ``ListPlugin.get_context``
copies all of ``plugin_data["flat"]`` into the template context, so each field
is readable as ``{{ cover.<field> }}``. The subclass exists only to (a) make the
fields editable in the inline UI and (b) expose the signature image URL.
"""

from typing import Any

from django import forms
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpRequest

from django_resume.images import (
    UnknownImageFormat,
    get_image_dimensions_from_storage,
)
from django_resume.plugins.cover import CoverFlatForm, CoverItemForm, CoverPlugin


class EditorialCoverFlatForm(CoverFlatForm):
    closing = forms.CharField(
        widget=forms.TextInput(),
        required=False,
        max_length=200,
        initial="Mit freundlichen Grüßen",
    )
    signature_name = forms.CharField(
        label="Signature name (defaults to the resume name)",
        widget=forms.TextInput(),
        required=False,
        max_length=100,
    )
    signature_img = forms.FileField(
        label="Signature image (optional PNG)",
        max_length=100,
        required=False,
    )
    clear_signature = forms.BooleanField(
        widget=forms.CheckboxInput,
        initial=False,
        required=False,
    )
    # processed by ImageFormMixin (save/clear), same as the avatar pair
    image_fields = [("avatar_img", "clear_avatar"), ("signature_img", "clear_signature")]

    @property
    def signature_img_url(self) -> str:
        return self.get_image_url_for_field(self.initial.get("signature_img", ""))

    @staticmethod
    def do_clean_image_field(
        cleaned_data: dict[str, Any], image_field: str, clear_field: str
    ) -> dict[str, Any]:
        """Reimplements ImageFormMixin.do_clean_image_field, fixing an upstream
        bug: the original computes image dimensions from a HARDCODED
        ``cleaned_data["avatar_img"]`` (django_resume/images.py), which crashes
        when saving a second image field (here ``signature_img``) on a cover
        letter that has no avatar. We read the dimensions from the field being
        cleaned instead. (Noted for the django-resume Theme Extraction backlog;
        not fixed upstream to keep zero django-resume changes.)
        """
        image = cleaned_data.get(image_field)
        clear_image = cleaned_data.get(clear_field)

        image_handled = False
        just_clear_the_image = clear_image and not hasattr(
            image, "temporary_file_path"
        )
        if just_clear_the_image:
            cleaned_data[image_field] = None
            image_handled = True

        set_new_image = isinstance(image, InMemoryUploadedFile) and not image_handled
        if set_new_image:
            assert image is not None
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Image file too large ( > 2mb )")
            cleaned_data[image_field] = default_storage.save(
                f"uploads/{image.name}", ContentFile(image.read())
            )
            image_handled = True

            try:
                width, height = get_image_dimensions_from_storage(
                    cleaned_data[image_field]  # the field being cleaned, not avatar_img
                )
            except UnknownImageFormat:
                width, height = None, None
            cleaned_data[f"{image_field}_width"] = width
            cleaned_data[f"{image_field}_height"] = height

        keep_current_image = (
            not clear_image and isinstance(clear_image, str) and not image_handled
        )
        if keep_current_image:
            cleaned_data[image_field] = image

        del cleaned_data[clear_field]
        return cleaned_data


class EditorialCoverPlugin(CoverPlugin):
    @staticmethod
    def get_form_classes() -> dict:
        return {"item": CoverItemForm, "flat": EditorialCoverFlatForm}

    def get_context(
        self,
        _request: HttpRequest,
        plugin_data: dict,
        resume_pk: int,
        *,
        context: dict,
        edit: bool = False,
        theme: str = "plain",
    ) -> dict:
        context = super().get_context(
            _request, plugin_data, resume_pk, context=context, edit=edit, theme=theme
        )
        signature_img = plugin_data.get("flat", {}).get("signature_img", "")
        context["signature_img_url"] = (
            default_storage.url(signature_img) if signature_img else ""
        )
        return context
