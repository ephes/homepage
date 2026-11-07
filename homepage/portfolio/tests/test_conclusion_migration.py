import importlib

import pytest
from bs4 import BeautifulSoup

migration = importlib.import_module("homepage.portfolio.migrations.0011_move_conclusion_from_solution")


@pytest.mark.parametrize(
    "body, extracted",
    [
        ('<p>Body</p><p><strong>End</strong></p><p><img src="keep.jpg"></p>', False),
        ('<p>Body</p><p><img src="keep.jpg"></p><p><strong>End</strong></p>', True),
        ('<p>Body</p><p><strong>End</strong></p><iframe src="https://embed.invalid/"></iframe>', False),
        ('<p>Body</p><iframe src="https://embed.invalid/"></iframe><p><strong>End</strong></p>', True),
        ("<p>Body</p><p><strong>End</strong></p>tail text", False),
        ("<p>Body</p><p><strong>End</strong></p>  <p> </p>", True),
    ],
)
def test_split_preserves_every_other_semantic_node(body, extracted):
    remaining, conclusion = migration.split_conclusion(body)
    if not extracted:
        assert (remaining, conclusion) == (body, "")
        return
    assert conclusion == "<p><strong>End</strong></p>"
    expected = body.replace(conclusion, "").strip()
    if expected.endswith("<p> </p>"):
        expected = expected[:-8].strip()
    assert BeautifulSoup(remaining, "html.parser") == BeautifulSoup(expected, "html.parser")
