from io import BytesIO

import pytest
from bs4 import BeautifulSoup
from cast.models import Post
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from indieweb.models import Token
from PIL import Image as PillowImage
from wagtail.images import get_image_model
from wagtail.models import Collection, Revision

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
