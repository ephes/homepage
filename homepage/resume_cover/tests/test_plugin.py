"""The homepage cover-plugin override adds closing + signature fields without
touching django-resume. It re-registers under the name "cover", which the
plugin registry overrides by name (see django_resume registry._register)."""


def test_homepage_overrides_cover_plugin_in_registry():
    from django_resume.plugins import plugin_registry

    from homepage.resume_cover.plugin import EditorialCoverPlugin

    plugin = plugin_registry.get_plugin("cover")
    assert isinstance(plugin, EditorialCoverPlugin)


def test_editorial_cover_flat_form_has_new_fields():
    from homepage.resume_cover.plugin import EditorialCoverFlatForm

    form = EditorialCoverFlatForm()
    for name in ("closing", "signature_name", "signature_img", "clear_signature"):
        assert name in form.fields

    # the existing cover fields are still present (subclass, not replacement)
    for name in ("recipient", "place_date", "subject", "salutation"):
        assert name in form.fields


def test_signature_image_clean_reads_signature_field_not_avatar(monkeypatch):
    """Regression: ImageFormMixin.do_clean_image_field hardcodes
    cleaned_data["avatar_img"] for the dimension calc, which crashes when a
    signature image is saved on a cover letter with no avatar. The override must
    compute dimensions from the field being cleaned (signature_img)."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    from homepage.resume_cover import plugin as cover_plugin
    from homepage.resume_cover.plugin import EditorialCoverFlatForm

    captured = {}

    monkeypatch.setattr(
        cover_plugin.default_storage, "save", lambda name, content: "uploads/sig.png"
    )

    def fake_dims(path):
        captured["path"] = path
        return (10, 4)

    monkeypatch.setattr(cover_plugin, "get_image_dimensions_from_storage", fake_dims)

    img = SimpleUploadedFile(
        "sig.png", b"\x89PNG\r\n\x1a\n" + b"0" * 32, content_type="image/png"
    )
    # cleaned_data WITHOUT any "avatar_img" key — the exact crash case upstream
    cleaned = {"signature_img": img, "clear_signature": False}
    result = EditorialCoverFlatForm.do_clean_image_field(
        cleaned, "signature_img", "clear_signature"
    )

    assert result["signature_img"] == "uploads/sig.png"
    # dimensions were read from the saved signature path, not from avatar_img
    assert captured["path"] == "uploads/sig.png"
    assert result["signature_img_width"] == 10
    assert result["signature_img_height"] == 4
