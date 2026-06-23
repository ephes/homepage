"""Homepage override of django-resume's cover-letter plugin.

Adds the editorial cover-letter fields (closing line + signature) without
changing django-resume. Registered under the name "cover" in ``apps.ready()``;
the plugin registry overrides by name, so this shadows the built-in CoverPlugin.

Rendering the new flat fields needs nothing more — ``ListPlugin.get_context``
copies all of ``plugin_data["flat"]`` into the template context, so each field
is readable as ``{{ cover.<field> }}``. The subclass exists only to (a) make the
fields editable in the inline UI and (b) expose the signature image URL.
"""

from django import forms
from django.core.files.storage import default_storage
from django.http import HttpRequest

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
