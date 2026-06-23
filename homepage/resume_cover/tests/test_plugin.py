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
