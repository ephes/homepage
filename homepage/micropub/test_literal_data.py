"""Literal code and location data through publication and source queries."""

from html import escape

import pytest
from bs4 import BeautifulSoup
from cast.models import Post
from django.urls import reverse

from .handler import CastPostMicropubHandler
from .test_micropub_permissions import blogs, users  # noqa: F401
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
