"""Literal code and location data through publication and source queries."""

from decimal import Decimal
from html import escape
from urllib.parse import parse_qs, unquote, urlsplit

import pytest
from bs4 import BeautifulSoup
from cast.models import Post
from django.urls import reverse
from taggit.models import Tag
from wagtail.models import Page, PageLogEntry, Revision

from .handler import CastPostMicropubHandler, MicropubContentError
from .test_micropub_permissions import blogs, users  # noqa: F401
from .test_micropub_publication import micropub_json
from .test_source_fidelity import source  # noqa: F401

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("content_format", ["bare", "text", "html"])
def test_code_whitespace_survives_publication_preview_and_source(
    client, blogs, users, source, content_format  # noqa: F811
):
    code = "\n    print('A & B')\n\tprint('<T>')  \n\n"
    if content_format == "html":
        content = f'<p>Before</p><pre><code class="language-python">{escape(code)}</code></pre><p>After</p>'
        value = {"html": content}
    else:
        content = f"Before\n\n```python\n{code}\n```\n\nAfter"
        value = {"text": content} if content_format == "text" else content
    handler = CastPostMicropubHandler()
    handler.create_entry({"mp-channel": ["alpha"], "name": ["Synthetic code"], "content": [value]}, users["admin"])
    post = Post.objects.get()
    for saved in [post, post.latest_revision.as_object()]:
        blocks = list(saved.body[0].value)
        assert [block.block_type for block in blocks] == ["paragraph", "code", "paragraph"]
        assert blocks[1].value == {"language": "python", "source": code}
        assert BeautifulSoup(str(blocks[0].value), "html.parser").get_text() == "Before"
        assert BeautifulSoup(str(blocks[2].value), "html.parser").get_text() == "After"
    response = source(post)
    assert response.status_code == 200
    exported = response.json()["properties"]["content"][0]
    assert BeautifulSoup(exported["html"], "html.parser").code.get_text() == code
    assert handler.converter.convert_content(exported["html"], {"content": [exported]})[1] == (
        "code",
        {"language": "python", "source": code},
    )
    client.force_login(users["admin"])
    preview = client.post(reverse("micropub-preview"), {"content": content})
    assert preview.status_code == 200
    assert BeautifulSoup(preview.context["preview_html"], "html.parser").code.get_text() == code


def location_value(shape, latitude, longitude):
    if shape == "direct":
        return {"latitude": latitude, "longitude": longitude}
    if shape == "h-geo":
        return {"type": ["h-geo"], "properties": {"latitude": [latitude], "longitude": [longitude]}}
    return f"geo:{latitude},{longitude}"


def assert_map_link(html, latitude, longitude):
    soup = BeautifulSoup(html, "html.parser")
    [anchor] = soup.find_all("a")
    assert set(anchor.attrs) == {"href"}
    url = urlsplit(anchor["href"])
    assert (url.scheme, url.netloc, url.path) == ("https", "www.openstreetmap.org", "/")
    assert {key: [Decimal(value) for value in values] for key, values in parse_qs(url.query).items()} == {
        "mlat": [Decimal(str(latitude))],
        "mlon": [Decimal(str(longitude))],
    }
    zoom, lat, lon = unquote(url.fragment).removeprefix("map=").split("/")
    assert zoom == "15"
    assert (Decimal(lat), Decimal(lon)) == (Decimal(str(latitude)), Decimal(str(longitude)))


@pytest.mark.parametrize("shape", ["direct", "h-geo", "geo"])
@pytest.mark.parametrize("latitude,longitude", [(0, 0), (0, 12), (12, 0), ("+12.50", "-0.25"), (-90, -180), (90, 180)])
def test_coordinates_survive_create_and_source(client, blogs, users, source, shape, latitude, longitude):  # noqa: F811
    response = micropub_json(
        client,
        users["admin"],
        {
            "mp-channel": ["alpha"],
            "content": ["Synthetic location"],
            "location": [location_value(shape, latitude, longitude)],
        },
    )
    assert response.status_code == 201
    post = Post.objects.get()
    assert_map_link(str(post.latest_revision.as_object().body[0].value[-1].value), latitude, longitude)
    exported = source(post)
    assert exported.status_code == 200
    assert_map_link(exported.json()["properties"]["content"][0]["html"], latitude, longitude)


INVALID_COORDINATES = [
    (91, 0),
    (-91, 0),
    (0, 181),
    (0, -181),
    ("90.000000000000001", 0),
    ("NaN", 0),
    (0, "Infinity"),
    ("-inf", 0),
    ("", 0),
    (None, 0),
    (True, 0),
    ([], 0),
    ('1" target="blank', 0),
    ("1&mlon=9", 0),
]


@pytest.mark.parametrize("shape", ["direct", "h-geo", "geo"])
@pytest.mark.parametrize("latitude,longitude", INVALID_COORDINATES)
def test_invalid_coordinates_refuse_without_writes(client, blogs, users, shape, latitude, longitude):  # noqa: F811
    before = [model.objects.count() for model in (Page, Revision, PageLogEntry)]
    response = micropub_json(
        client,
        users["admin"],
        {
            "mp-channel": ["alpha"],
            "content": ["Synthetic location"],
            "category": ["must-not-be-created"],
            "location": [location_value(shape, latitude, longitude)],
        },
    )
    assert response.status_code == 400
    assert b"invalid_request" in response.content
    assert not Post.objects.exists()
    assert [model.objects.count() for model in (Page, Revision, PageLogEntry)] == before
    assert not Tag.objects.filter(name="must-not-be-created").exists()


@pytest.mark.parametrize(
    "location",
    [
        {},
        {"latitude": 0},
        {"properties": {}},
        {"properties": {"latitude": [], "longitude": [0]}},
        {"properties": {"latitude": [0], "longitude": []}},
        {"properties": []},
        "geo:",
        "geo:1",
    ],
)
def test_malformed_location_shape_is_controlled(blogs, users, location):  # noqa: F811
    with pytest.raises(MicropubContentError):
        CastPostMicropubHandler().create_entry(
            {"mp-channel": ["alpha"], "content": ["Synthetic location"], "location": [location]}, users["admin"]
        )
    assert not Post.objects.exists()


@pytest.mark.parametrize(
    "location,valid",
    [
        ("geo:0,0", True),
        ("geo:+90,-180;u=10", True),
        ("geo:NaN,0", False),
        ('geo:1" target="blank,0', False),
        ("geo:91,0", False),
    ],
)
def test_preview_uses_coordinate_admission(client, users, location, valid):  # noqa: F811
    client.force_login(users["admin"])
    response = client.post(reverse("micropub-preview"), {"content": "Synthetic preview", "location": location})
    assert response.status_code == (200 if valid else 400)
    if valid:
        latitude, longitude = location[4:].split(";")[0].split(",")
        assert_map_link(response.context["preview_html"], latitude, longitude)
    else:
        assert response.content == b"Location coordinates are invalid"
    assert not Post.objects.exists()


@pytest.mark.parametrize("shape", ["plain", "direct", "h-geo"])
@pytest.mark.parametrize(
    "label",
    [
        "<b>literal location</b>",
        '<a href="https://example.invalid/">link</a><img src="https://example.invalid/a.png">',
        "\"Quotes\" & 'apostrophes' &amp; 東京 📍",
    ],
)
def test_location_labels_remain_literal_through_publication_and_source(
    client, blogs, users, source, shape, label  # noqa: F811
):
    if shape == "plain":
        location = label
    else:
        location = location_value(shape, 0, 12)
        if shape == "direct":
            location["name"] = label
        else:
            location["properties"]["name"] = [label]
    response = micropub_json(
        client, users["admin"], {"mp-channel": ["alpha"], "content": ["Synthetic body"], "location": [location]}
    )
    assert response.status_code == 201
    post = Post.objects.get()

    def assert_label(html):
        paragraph = BeautifulSoup(html, "html.parser").find_all("p")[-1]
        assert paragraph.get_text() == f"📍 {label}"
        assert [tag.name for tag in paragraph.find_all()] == ([] if shape == "plain" else ["a"])
        if shape != "plain":
            assert_map_link(str(paragraph), 0, 12)

    for saved in [post, post.latest_revision.as_object()]:
        assert_label(str(saved.body[0].value[-1].value))
    response = source(post)
    assert response.status_code == 200
    exported = response.json()["properties"]["content"][0]
    assert_label(exported["html"])
    reimported = CastPostMicropubHandler().converter.convert_content(exported["html"], {"content": [exported]})
    assert_label(reimported[-1][1])
    if shape == "plain":
        client.force_login(users["admin"])
        preview = client.post(reverse("micropub-preview"), {"content": "Synthetic body", "location": label})
        assert preview.status_code == 200
        assert_label(preview.context["preview_html"])
