"""The React theme (cast-react) is installed and offered in django-cast's theme chooser."""

from pathlib import Path

import cast_react
import pytest
from cast.models.theme import get_template_base_dir_choices
from django.conf import settings
from django.template.loader import get_template


def test_react_theme_is_offered():
    assert "cast_react.apps.CastReactConfig" in settings.INSTALLED_APPS
    assert ("react", "React") in get_template_base_dir_choices()


def test_react_theme_templates_and_bundle_are_available():
    get_template("cast/react/base.html")
    get_template("cast/react/post_body.html")
    manifest = Path(cast_react.__file__).parent / "static" / "cast_react" / "manifest.json"
    assert manifest.is_file()


@pytest.mark.django_db
def test_blog_and_post_render_with_the_react_theme(client):
    from cast import devdata
    from wagtail.models import Locale, Page, Site

    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node() or Page.add_root(instance=Page(title="Root", slug="root"))
    Site.objects.all().delete()
    site = Site.objects.create(hostname="testserver", root_page=root, is_default_site=True)
    blog = devdata.create_blog(owner=devdata.create_user(name="react-theme"), site=site)
    blog.template_base_dir = "react"
    blog.save()
    post = devdata.create_post(blog=blog)

    index = client.get(blog.url)
    assert index.status_code == 200
    assert 'id="cast-react-configuration"' in index.content.decode()
    assert "cast_react/main-" in index.content.decode()
    detail = client.get(post.url)
    assert detail.status_code == 200
    assert 'data-route-name="PostDetail"' in detail.content.decode()
