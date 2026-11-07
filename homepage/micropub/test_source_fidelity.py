from io import BytesIO
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from cast.models import Blog, Post
from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django_vite.core.asset_loader import DjangoViteAssetLoader
from indieweb.models import Token
from PIL import Image as PillowImage
from wagtail.images import get_image_model
from wagtail.models import Collection, Page, Revision

from .handler import CastPostMicropubHandler
from .test_micropub_permissions import blogs, users  # noqa: F401

pytestmark = pytest.mark.django_db


@pytest.fixture
def source(client, users):  # noqa: F811
    issued = Token.objects.create(
        owner=users["admin"], me="http://testserver/", client_id="https://editor.invalid/", scope="update"
    )
    bearer = issued.key

    def query(post):
        return client.get(
            reverse("indieweb:micropub"),
            {"q": "source", "url": post.get_full_url()},
            HTTP_AUTHORIZATION=f"Bearer {bearer}",
        )

    return query


def make_post(blog, blocks):
    post = blog.add_child(
        instance=Post(
            title="Synthetic source", slug="synthetic-source", live=False, body=[{"type": "overview", "value": blocks}]
        )
    )
    post.save_revision().publish()
    post.refresh_from_db()
    return post


def test_source_html_discriminator_and_real_creation_round_trip(source, blogs, users):  # noqa: F811
    original = (
        "<p>A &amp; B <strong>bold</strong> <em>emphasis</em> "
        '<a href="https://example.invalid/">link</a></p><p>Second &lt;paragraph&gt;</p>'
    )
    post = make_post(blogs["alpha"], [{"type": "paragraph", "value": original}])
    revision_pk = post.latest_revision_id
    response = source(post)
    assert response.status_code == 200
    properties = response.json()["properties"]
    value = properties["content"][0]
    assert isinstance(value, dict) and set(value) == {"html"}
    assert BeautifulSoup(value["html"], "html.parser") == BeautifulSoup(original, "html.parser")
    post.refresh_from_db()
    assert post.latest_revision_id == post.live_revision_id == revision_pk
    handler = CastPostMicropubHandler()
    entry = handler.create_entry(
        {"mp-channel": ["alpha"], "name": ["Source round trip"], "content": [value]}, users["admin"]
    )
    created = Post.objects.exclude(pk=post.pk).get()
    assert entry.url == created.get_url()
    rendered = "".join(str(block.value) for section in created.body for block in section.value)
    assert BeautifulSoup(rendered, "html.parser") == BeautifulSoup(original, "html.parser")
    assert "&amp;amp;" not in rendered


@pytest.fixture
def synthetic_image():
    data = BytesIO()
    PillowImage.new("RGB", (2, 2), (10, 20, 30)).save(data, format="PNG")
    collection = Collection.get_first_root_node() or Collection.add_root(instance=Collection(name="Synthetic root"))
    return get_image_model().objects.create(
        title="Synthetic image",
        description="Synthetic alt",
        collection=collection,
        file=SimpleUploadedFile("synthetic.png", data.getvalue(), content_type="image/png"),
        width=2,
        height=2,
    )


def test_source_keeps_headings_lists_code_and_image_in_order(source, blogs, synthetic_image):  # noqa: F811
    code = "if x < 3:\n    print('A & B')"
    post = make_post(
        blogs["alpha"],
        [
            {"type": "paragraph", "value": "<h2>A heading</h2>"},
            {"type": "paragraph", "value": "<ul><li>First</li><li>Second</li></ul>"},
            {"type": "code", "value": {"language": "python", "source": code}},
            {"type": "image", "value": synthetic_image.pk},
            {"type": "paragraph", "value": "<p>End</p>"},
        ],
    )
    response = source(post)
    assert response.status_code == 200
    soup = BeautifulSoup(response.json()["properties"]["content"][0]["html"], "html.parser")
    assert [node.name for node in soup.children if node.name] == ["h2", "ul", "pre", "img", "p"]
    assert soup.code.get_text() == code
    assert soup.code["class"] == ["language-python"]
    assert soup.img["src"] == synthetic_image.file.url
    assert soup.img["alt"] == synthetic_image.default_alt_text
    assert soup.find_all("li")[1].get_text() == "Second"


def test_unsupported_source_is_explicit_and_read_only(source, blogs):  # noqa: F811
    post = make_post(
        blogs["alpha"],
        [
            {"type": "paragraph", "value": "<p>Before</p>"},
            {
                "type": "weeknote_links",
                "value": [
                    {
                        "category": "articles",
                        "kind": "article",
                        "title": "Example",
                        "url": "https://example.invalid/",
                        "source": "",
                        "source_url": "",
                        "description": "<p>Example</p>",
                    }
                ],
            },
            {"type": "paragraph", "value": "<p>After</p>"},
        ],
    )
    before = Post.objects.values("body", "latest_revision_id", "live_revision_id").get(pk=post.pk)
    count = Revision.objects.count()
    response = source(post)
    assert response.status_code == 400
    assert Post.objects.values("body", "latest_revision_id", "live_revision_id").get(pk=post.pk) == before
    assert Revision.objects.count() == count


def test_source_code_round_trip_uses_real_cast_block_schema(source, blogs, users):  # noqa: F811
    post = make_post(blogs["alpha"], [{"type": "code", "value": {"language": "python", "source": "  x < y & z\n\n"}}])
    response = source(post)
    assert response.status_code == 200
    value = response.json()["properties"]["content"][0]
    handler = CastPostMicropubHandler()
    handler.create_entry({"mp-channel": ["alpha"], "name": ["Code round trip"], "content": [value]}, users["admin"])
    created = Post.objects.exclude(pk=post.pk).get()
    block = created.body[0].value[0]
    assert block.block_type == "code"
    assert block.value["source"] == "  x < y & z\n\n"


def test_source_image_can_be_imported_without_fetching_media(source, blogs, users, synthetic_image):  # noqa: F811
    post = make_post(blogs["alpha"], [{"type": "image", "value": synthetic_image.pk}])
    response = source(post)
    assert response.status_code == 200
    value = response.json()["properties"]["content"][0]
    CastPostMicropubHandler().create_entry(
        {"mp-channel": ["alpha"], "name": ["Image round trip"], "content": [value]}, users["admin"]
    )
    created = Post.objects.exclude(pk=post.pk).get()
    soup = BeautifulSoup(str(created.body[0].value[0].value), "html.parser")
    assert soup.img["src"] == synthetic_image.file.url
    assert soup.img["alt"] == synthetic_image.default_alt_text


def test_deleted_image_source_is_explicitly_unsupported(source, blogs, synthetic_image):  # noqa: F811
    post = make_post(blogs["alpha"], [{"type": "image", "value": synthetic_image.pk}])
    synthetic_image.delete()
    assert source(post).status_code == 400


def test_unknown_stored_block_cannot_disappear_from_source(source, blogs):  # noqa: F811
    post = make_post(blogs["alpha"], [{"type": "paragraph", "value": "<p>Before</p>"}])
    # Simulate a stored block whose schema was removed, without using personal data.
    Post.objects.filter(pk=post.pk).update(
        body=[
            {
                "type": "overview",
                "value": [
                    {"type": "paragraph", "value": "<p>Before</p>"},
                    {"type": "removed_synthetic_block", "value": "Must not disappear"},
                ],
            }
        ]
    )
    assert source(post).status_code == 400


def test_source_preserves_overview_then_detail_order(source, blogs):  # noqa: F811
    post = make_post(blogs["alpha"], [{"type": "paragraph", "value": "<p>Overview</p>"}])
    post.body = [
        {"type": "overview", "value": [{"type": "paragraph", "value": "<p>Overview</p>"}]},
        {"type": "detail", "value": [{"type": "code", "value": {"language": "text", "source": "Detail"}}]},
    ]
    post.save_revision().publish()
    response = source(post)
    assert response.status_code == 200
    soup = BeautifulSoup(response.json()["properties"]["content"][0]["html"], "html.parser")
    assert [tag.name for tag in soup.children if tag.name] == ["p", "pre"]
    assert soup.pre.get_text() == "Detail"


@pytest.mark.parametrize("count", [1, 20])
@pytest.mark.parametrize("resolved", [False, True])
def test_source_image_queries_reuse_wagtail_chooser_resolution(
    source, blogs, synthetic_image, count, resolved, django_assert_num_queries  # noqa: F811
):
    images = [synthetic_image]
    for number in range(1, count):
        images.append(
            get_image_model().objects.create(
                title=f"Synthetic image {number}",
                description=f'Alt <{number}> & "quoted"',
                collection=synthetic_image.collection,
                file=SimpleUploadedFile(
                    f"synthetic-{number}.png", synthetic_image.file.read(), content_type="image/png"
                ),
                width=2,
                height=2,
            )
        )
        synthetic_image.file.seek(0)
    post = make_post(blogs["alpha"], [{"type": "image", "value": image.pk} for image in images])
    for cache in caches.all():
        cache.clear()
    ContentType.objects.clear_cache()
    ContentType.objects.get_for_models(Page, Blog, Post)
    if resolved:
        # Chooser callers may already have resolved model instances.
        blocks = [block for section in post.body for block in section.value]
        for block, image in zip(blocks, images, strict=True):
            block.value = image
    # One tag query plus, for an unresolved saved body, one bulk image query.
    with django_assert_num_queries(1 if resolved else 2):
        properties = CastPostMicropubHandler()._post_to_properties(post)
    soup = BeautifulSoup(properties["content"][0]["html"], "html.parser")
    assert [img["src"] for img in soup.select("img")] == [image.file.url for image in images]
    assert [img["alt"] for img in soup.select("img")] == [image.default_alt_text for image in images]
    with django_assert_num_queries(9):
        response = source(post)
    assert response.status_code == 200
    assert response.json()["properties"] == properties


def test_source_returns_latest_saved_draft_without_changing_live_post(source, blogs, users, client):  # noqa: F811
    post = make_post(blogs["alpha"], [{"type": "paragraph", "value": "<p>Published body A</p>"}])
    post.tags.add("published-a")
    post.save_revision().publish()
    post.refresh_from_db()
    live_revision = post.live_revision_id
    canonical_url = post.get_full_url()
    draft = post.live_revision.as_object()
    draft.title = "Unpublished title B"
    draft.slug = "unpublished-slug-b"
    draft.body = [{"type": "overview", "value": [{"type": "paragraph", "value": "<p>Draft body B</p>"}]}]
    draft.tags.set(["draft-b"])
    revision = draft.save_revision(user=users["editor"])
    before = Post.objects.values("title", "body", "live_revision_id", "latest_revision_id").get(pk=post.pk)
    revision_count = Revision.objects.count()
    response = source(post)
    assert response.status_code == 200
    properties = response.json()["properties"]
    assert properties["name"] == ["Unpublished title B"]
    assert properties["category"] == ["draft-b"]
    assert properties["content"] == [{"html": "<p>Draft body B</p>"}]
    entry = CastPostMicropubHandler().get_entry(canonical_url, users["editor"])
    assert entry.url == canonical_url
    assert entry.properties == properties
    assert Post.objects.values("title", "body", "live_revision_id", "latest_revision_id").get(pk=post.pk) == before
    post.refresh_from_db()
    assert post.live_revision_id == live_revision
    assert post.latest_revision_id == revision.pk
    assert list(post.tags.names()) == ["published-a"]
    assert Revision.objects.count() == revision_count
    # Exercise anonymous serving/rendering without requiring a frontend asset build.
    with patch.object(DjangoViteAssetLoader, "generate_vite_asset", return_value=""):
        public = client.get(post.get_url())
    assert public.status_code == 200
    assert b"Published body A" in public.content
    assert b"Draft body B" not in public.content
    assert b"Unpublished title B" not in public.content


@pytest.mark.parametrize("username", ["nobody", "inactive_admin"])
def test_source_denies_draft_access_before_loading_revision(blogs, users, username):  # noqa: F811
    post = make_post(blogs["alpha"], [{"type": "paragraph", "value": "<p>Public</p>"}])
    draft = post.live_revision.as_object()
    draft.title = "Private draft"
    draft.save_revision()
    with patch.object(Post, "get_latest_revision_as_object", side_effect=AssertionError("unauthorized draft read")):
        assert CastPostMicropubHandler().get_entry(post.get_full_url(), users[username]) is None


def test_latest_draft_keeps_strict_unsupported_block_refusal(source, blogs):  # noqa: F811
    post = make_post(blogs["alpha"], [{"type": "paragraph", "value": "<p>Public</p>"}])
    draft = post.live_revision.as_object()
    draft.title = "Draft with a removed block schema"
    revision = draft.save_revision()
    content = revision.content
    content["body"] = [{"type": "overview", "value": [{"type": "removed_synthetic_block", "value": "Keep me"}]}]
    revision.content = content
    revision.save(update_fields=["content"])
    assert source(post).status_code == 400
    post.refresh_from_db()
    assert post.live_revision_id != revision.pk
