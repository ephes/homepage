"""
Database-backed tests for Micropub authorization, target-blog selection and safe output.
"""

import json
from unittest.mock import patch

import pytest
from cast.models import Blog, Post
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.test import override_settings
from django.urls import reverse
from indieweb.models import Token
from wagtail.models import GroupPagePermission, Locale, Page
from wagtail.models import Site as WagtailSite

from .forms import MicropubPostForm
from .handler import CastPostMicropubHandler, MicropubPermissionError, MicropubTargetError

pytestmark = pytest.mark.django_db

User = get_user_model()
HOST = "testserver"


def get_or_create_root():
    root = Page.get_first_root_node()
    if root is None:
        Locale.objects.get_or_create(language_code="en")
        root = Page.add_root(instance=Page(title="Root", slug="root"))
    return root


def grant(user, page, *codenames):
    group = Group.objects.create(name=f"{user.username}-{page.slug}")
    for codename in codenames:
        GroupPagePermission.objects.create(
            group=group,
            page=page,
            permission=Permission.objects.get(content_type__app_label="wagtailcore", codename=codename),
        )
    user.groups.add(group)


@pytest.fixture
def blogs():
    home = get_or_create_root().add_child(instance=Page(title="Home", slug="micropub-home"))
    WagtailSite.objects.all().delete()
    WagtailSite.objects.create(hostname=HOST, port=80, root_page=home, is_default_site=True)
    alpha = home.add_child(instance=Blog(title="Alpha", slug="alpha"))
    beta = home.add_child(instance=Blog(title="Beta", slug="beta"))
    return {"alpha": alpha, "beta": beta}


@pytest.fixture
def users(blogs):
    publisher = User.objects.create_user(username="publisher", password="x")
    grant(publisher, blogs["alpha"], "add_page", "publish_page")
    adder = User.objects.create_user(username="adder", password="x")
    grant(adder, blogs["alpha"], "add_page")
    editor = User.objects.create_user(username="editor", password="x")
    grant(editor, blogs["alpha"], "change_page")
    nobody = User.objects.create_user(username="nobody", password="x")
    admin = User.objects.create_superuser(username="admin", password="x", email="admin@example.com")
    inactive_admin = User.objects.create_superuser(username="inactive", password="x", email="i@example.com")
    inactive_admin.is_active = False
    inactive_admin.save()
    return {
        "publisher": publisher,
        "adder": adder,
        "editor": editor,
        "nobody": nobody,
        "admin": admin,
        "inactive_admin": inactive_admin,
    }


def create(user, **extra):
    properties = {"name": ["Hello"], "content": ["Hello world"], **extra}
    return CastPostMicropubHandler().create_entry(properties, user)


# create_entry: permissions and blog selection


@override_settings(MICROPUB_DEFAULT_BLOG_SLUG="alpha")
def test_publisher_creates_live_post_in_default_blog(blogs, users):
    entry = create(users["publisher"])

    post = Post.objects.get(slug="hello")
    assert post.live
    assert post.get_parent().pk == blogs["alpha"].pk
    assert entry.url == post.get_url()


def test_publisher_selects_blog_explicitly(blogs, users):
    with override_settings(MICROPUB_DEFAULT_BLOG_SLUG="beta"):
        create(users["publisher"], **{"mp-channel": ["alpha"]})

    assert Post.objects.get(slug="hello").get_parent().pk == blogs["alpha"].pk


def test_superuser_may_publish_into_any_blog(blogs, users):
    create(users["admin"], **{"mp-channel": ["beta"]})

    assert Post.objects.get(slug="hello").get_parent().pk == blogs["beta"].pk


@pytest.mark.parametrize(
    "username, channel",
    [
        ("publisher", "beta"),  # permissions only on alpha
        ("adder", "alpha"),  # add without publish
        ("editor", "alpha"),  # change without add/publish
        ("nobody", "alpha"),
        ("inactive_admin", "alpha"),
    ],
)
def test_users_without_add_and_publish_permission_are_rejected(blogs, users, username, channel):
    with pytest.raises(MicropubPermissionError):
        create(users[username], **{"mp-channel": [channel]})

    assert not Post.objects.exists()


def test_unknown_target_blog_is_rejected(blogs, users):
    with pytest.raises(MicropubTargetError):
        create(users["admin"], **{"mp-channel": ["missing"]})
    assert not Post.objects.exists()


def test_multiple_target_blogs_are_rejected(blogs, users):
    with pytest.raises(MicropubTargetError):
        create(users["admin"], **{"mp-channel": ["alpha", "beta"]})
    assert not Post.objects.exists()


@override_settings(MICROPUB_DEFAULT_BLOG_SLUG="missing")
def test_no_fallback_to_arbitrary_blog_when_default_is_missing(blogs, users):
    with pytest.raises(MicropubTargetError):
        create(users["admin"])
    assert not Post.objects.exists()


def test_draft_blog_is_not_a_valid_target(blogs, users):
    blogs["beta"].unpublish()

    with pytest.raises(MicropubTargetError):
        create(users["admin"], **{"mp-channel": ["beta"]})


def test_failure_after_page_creation_rolls_back(blogs, users):
    with patch.object(Post, "save_revision", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            create(users["admin"], **{"mp-channel": ["alpha"]})

    assert not Post.objects.exists()


# get_config: channels advertise only publishable blogs


def test_config_channels_list_only_publishable_blogs(blogs, users):
    handler = CastPostMicropubHandler()

    assert handler.get_config(users["publisher"])["channels"] == [{"uid": "alpha", "name": "Alpha"}]
    assert handler.get_config(users["nobody"])["channels"] == []
    assert [c["uid"] for c in handler.get_config(users["admin"])["channels"]] == ["alpha", "beta"]


# get_entry: page permissions instead of owner/superuser


@pytest.fixture
def existing_post(blogs, users):
    post = blogs["alpha"].add_child(instance=Post(title="Existing", slug="existing", owner=users["admin"]))
    return post


def test_get_entry_allowed_with_edit_permission(existing_post, users):
    entry = CastPostMicropubHandler().get_entry(f"http://{HOST}/blogs/alpha/existing/", users["editor"])

    assert entry is not None
    assert entry.properties["name"] == ["Existing"]


@pytest.mark.parametrize("username", ["nobody", "inactive_admin"])
def test_get_entry_denied_without_edit_permission(existing_post, users, username):
    assert CastPostMicropubHandler().get_entry(f"http://{HOST}/blogs/alpha/existing/", users[username]) is None


def test_get_entry_denied_for_owner_without_page_permissions(existing_post, users):
    existing_post.owner = users["nobody"]
    existing_post.save()

    assert CastPostMicropubHandler().get_entry(f"http://{HOST}/blogs/alpha/existing/", users["nobody"]) is None


@pytest.mark.parametrize(
    "url",
    [
        f"http://{HOST}/blogs/beta/existing/",  # same slug, wrong blog
        f"http://{HOST}/blogs/alpha/",  # a blog, not a post
        f"http://{HOST}/blogs/alpha/missing/",
        f"http://{HOST}/not-wagtail/",
    ],
)
def test_get_entry_returns_none_for_non_post_urls(existing_post, users, url):
    assert CastPostMicropubHandler().get_entry(url, users["admin"]) is None


# Micropub endpoint (IndieAuth token path)


def micropub_post(client, user, data):
    token = Token.objects.create(owner=user, me=f"http://{HOST}/", client_id="https://client.example/", scope="create")
    return client.post(reverse("indieweb:micropub"), data, HTTP_AUTHORIZATION=f"Bearer {token.key}")


def test_endpoint_rejects_token_owner_without_page_permissions(client, blogs, users):
    response = micropub_post(client, users["nobody"], {"h": "entry", "content": "hi", "mp-channel": "alpha"})

    assert response.status_code == 400
    assert not Post.objects.exists()


def test_endpoint_creates_post_for_permitted_token_owner(client, blogs, users):
    response = micropub_post(client, users["publisher"], {"h": "entry", "content": "hi", "mp-channel": "alpha"})

    assert response.status_code == 201
    assert Post.objects.get().get_parent().pk == blogs["alpha"].pk


# Local form and preview views


def test_form_only_offers_publishable_blogs(client, blogs, users):
    client.force_login(users["publisher"])

    response = client.get(reverse("micropub-form"))

    assert [choice[0] for choice in response.context["form"].fields["blog"].choices] == ["alpha"]


def test_form_rejects_blog_without_permission(client, blogs, users):
    client.force_login(users["publisher"])

    response = client.post(reverse("micropub-form"), {"blog": "beta", "post_type": "note", "content": "hi"})

    assert response.status_code == 200
    assert "blog" in response.context["form"].errors
    assert not Post.objects.exists()


def test_form_creates_post_and_renders_escaped_link_message(client, blogs, users):
    client.force_login(users["publisher"])

    response = client.post(
        reverse("micropub-form"), {"blog": "alpha", "post_type": "note", "content": "hi"}, follow=True
    )

    post = Post.objects.get()
    assert post.get_parent().pk == blogs["alpha"].pk
    content = response.content.decode()
    assert 'Post created successfully! <a href="http://testserver/blogs/alpha/' in content


def test_form_does_not_echo_exception_text(client, blogs, users):
    client.force_login(users["publisher"])

    with patch.object(CastPostMicropubHandler, "create_entry", side_effect=RuntimeError("<b>db secret</b>")):
        response = client.post(
            reverse("micropub-form"), {"blog": "alpha", "post_type": "note", "content": "hi"}, follow=True
        )

    content = response.content.decode()
    assert "db secret" not in content
    assert "Error creating post." in content


def test_form_template_autoescapes_messages(rf, users):
    """Messages are rendered without ``|safe``, so markup from any message source is escaped."""
    request = rf.get("/")
    request.user = users["nobody"]
    html = render_to_string(
        "micropub/form.html",
        {
            "form": MicropubPostForm(blogs=[]),
            "messages": [Message(constants.ERROR, "<script>alert(1)</script>")],
            "blogs": [],
            "blog_count": 0,
        },
        request=request,
    )

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_preview_escapes_code_and_sanitizes_paragraphs(client, users):
    client.force_login(users["nobody"])
    content = (
        '<p>Hi <img src="x" onerror="alert(1)"></p>'
        '<pre><code class="language-html">&lt;script&gt;alert(2)&lt;/script&gt;</code></pre>'
    )

    response = client.post(reverse("micropub-preview"), {"content": content, "post_type": "note"})

    html = response.content.decode()
    assert "onerror" not in html
    assert "<script>alert(2)</script>" not in html
    assert "&lt;script&gt;alert(2)&lt;/script&gt;" in html


def test_preview_escapes_code_language(client, users):
    client.force_login(users["nobody"])
    content = """<pre><code class='language-"><svg/onload=alert(6)>'>x</code></pre>"""

    response = client.post(reverse("micropub-preview"), {"content": content, "post_type": "note"})

    html = response.content.decode()
    assert "<svg/onload" not in html
    assert 'class="language-&quot;&gt;&lt;svg/onload=alert(6)&gt;"' in html


def test_preview_escapes_plain_text_code_block(client, users):
    client.force_login(users["nobody"])
    content = "```html\n<script>alert(4)</script>\n```\n\n<script>alert(5)</script>"

    response = client.post(reverse("micropub-preview"), {"content": content, "post_type": "note"})

    html = response.content.decode()
    assert "<script>alert(4)</script>" not in html
    assert "<script>alert(5)</script>" not in html
    assert "&lt;script&gt;alert(4)&lt;/script&gt;" in html


def test_get_entry_resolves_percent_encoded_unicode_slug(blogs, users):
    post = blogs["alpha"].add_child(instance=Post(title="Grüße", slug="grüße"))

    entry = CastPostMicropubHandler().get_entry(post.get_full_url(), users["admin"])

    assert entry is not None
    assert entry.properties["name"] == ["Grüße"]


def test_get_entry_respects_site_port(blogs, users):
    """A URL on another Wagtail site (same hostname, other port) is looked up in that site's tree."""
    other_home = get_or_create_root().add_child(instance=Page(title="Other", slug="other-home"))
    WagtailSite.objects.create(hostname=HOST, port=8080, root_page=other_home)
    other_alpha = other_home.add_child(instance=Blog(title="Other Alpha", slug="alpha"))
    other_alpha.add_child(instance=Post(title="Other", slug="existing"))
    blogs["alpha"].add_child(instance=Post(title="Default", slug="existing"))
    handler = CastPostMicropubHandler()

    assert handler.get_entry(f"http://{HOST}/blogs/alpha/existing/", users["admin"]).properties["name"] == ["Default"]
    assert handler.get_entry(f"http://{HOST}:8080/blogs/alpha/existing/", users["admin"]).properties["name"] == [
        "Other"
    ]


def test_ambiguous_blog_slugs_are_not_offered_as_channels(blogs, users):
    other_home = get_or_create_root().add_child(instance=Page(title="Other", slug="other-home"))
    other_home.add_child(instance=Blog(title="Other Alpha", slug="alpha"))

    assert CastPostMicropubHandler().get_config(users["admin"])["channels"] == [{"uid": "beta", "name": "Beta"}]
    with pytest.raises(MicropubTargetError):
        create(users["admin"], **{"mp-channel": ["alpha"]})


def test_get_entry_returns_none_when_no_site_matches(existing_post, users):
    WagtailSite.objects.update(is_default_site=False)

    assert CastPostMicropubHandler().get_entry("http://unknown.example/blogs/alpha/existing/", users["admin"]) is None


# Update, delete and undelete are not supported: the endpoint must say so instead of reporting success


def micropub_action(client, user, data, *, as_json=False):
    token = Token.objects.create(
        owner=user,
        me=f"http://{HOST}/",
        client_id="https://client.example/",
        scope="create update delete undelete",
    )
    kwargs = {"HTTP_AUTHORIZATION": f"Bearer {token.key}"}
    if as_json:
        return client.post(reverse("indieweb:micropub"), json.dumps(data), content_type="application/json", **kwargs)
    return client.post(reverse("indieweb:micropub"), data, **kwargs)


def test_endpoint_rejects_delete_and_keeps_post_live(client, existing_post, users):
    url = f"http://{HOST}/blogs/alpha/existing/"

    response = micropub_action(client, users["admin"], {"action": "delete", "url": url})

    assert response.status_code == 400
    existing_post.refresh_from_db()
    assert existing_post.live


def test_endpoint_rejects_update_without_server_error(client, existing_post, users):
    url = f"http://{HOST}/blogs/alpha/existing/"
    data = {"action": "update", "url": url, "replace": {"name": ["Changed"]}}

    response = micropub_action(client, users["admin"], data, as_json=True)

    assert response.status_code == 400
    existing_post.refresh_from_db()
    assert existing_post.title == "Existing"


def test_endpoint_rejects_undelete(client, existing_post, users):
    url = f"http://{HOST}/blogs/alpha/existing/"

    response = micropub_action(client, users["admin"], {"action": "undelete", "url": url})

    assert response.status_code == 400


@pytest.mark.parametrize(
    "call",
    [
        lambda handler, url, user: handler.update_entry(url, {"replace": {"name": ["x"]}}, user),
        lambda handler, url, user: handler.delete_entry(url, user),
        lambda handler, url, user: handler.undelete_entry(url, user),
    ],
    ids=["update", "delete", "undelete"],
)
def test_handler_raises_for_unsupported_actions(existing_post, users, call):
    with pytest.raises(ValueError, match="not supported"):
        call(CastPostMicropubHandler(), f"http://{HOST}/blogs/alpha/existing/", users["admin"])
