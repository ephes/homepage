import re
from pathlib import Path

from django.contrib.staticfiles import finders


LAYER_ORDER = (
    "reset",
    "tokens",
    "base",
    "layout",
    "components",
    "pages",
    "motion",
    "utilities",
)


def layer_body(stylesheet, name):
    start = stylesheet.index(f"@layer {name} {{")
    opening = stylesheet.index("{", start)
    depth = 1
    for index in range(opening + 1, len(stylesheet)):
        if stylesheet[index] == "{":
            depth += 1
        elif stylesheet[index] == "}":
            depth -= 1
            if depth == 0:
                return stylesheet[opening + 1 : index]
    raise AssertionError(f"Unclosed CSS layer: {name}")


def declarations_for(layer, expected_selectors):
    without_comments = re.sub(r"/\*.*?\*/", "", layer, flags=re.DOTALL)
    for selector_source, declaration_source in re.findall(r"([^{}]+)\{([^{}]*)\}", without_comments):
        selectors = {selector.strip() for selector in selector_source.split(",")}
        if selectors != set(expected_selectors):
            continue
        return {
            name.strip(): value.strip()
            for declaration in declaration_source.split(";")
            if ":" in declaration
            for name, value in [declaration.split(":", 1)]
        }
    raise AssertionError(f"Missing CSS rule for selectors: {expected_selectors}")


def test_portfolio_stylesheet_declares_the_stable_layer_order():
    stylesheet_path = finders.find("portfolio/portfolio.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    declaration = "@layer reset, tokens, base, layout, components, pages, motion, utilities;"

    assert stylesheet.count(declaration) == 1
    layer_positions = [stylesheet.index(f"@layer {layer} {{") for layer in LAYER_ORDER]
    assert layer_positions == sorted(layer_positions)


def test_retired_split_stylesheets_are_not_shipped():
    assert finders.find("portfolio/foundation.css") is None
    assert finders.find("portfolio/501.css") is None


def test_error_cover_uses_the_shared_header_height_contract():
    stylesheet_path = finders.find("portfolio/portfolio.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()

    assert "--site-header-block-size:" in stylesheet
    assert stylesheet.count("100svh - var(--site-header-block-size)") == 2
    assert "100svh - 3.5rem - 2px" not in stylesheet


def test_content_elements_keep_semantic_lists_and_neutral_browser_margins():
    stylesheet_path = finders.find("portfolio/portfolio.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()

    reset = layer_body(stylesheet, "reset")
    base = layer_body(stylesheet, "base")
    pages = layer_body(stylesheet, "pages")

    assert declarations_for(reset, {"figure", "blockquote", "dd"})["margin"] == "0"
    assert declarations_for(base, {"img"})["block-size"] == "auto"
    rich_text_lists = declarations_for(base, {".rich-text ul", ".rich-text ol"})
    assert rich_text_lists["margin-block"] == "1em"
    assert rich_text_lists["padding-inline-start"] == "1.2em"
    assert declarations_for(base, {".rich-text ul"})["list-style"] == "disc"
    assert declarations_for(base, {".rich-text ol"})["list-style"] == "decimal"
    assert declarations_for(pages, {".error-heading"})["overflow-wrap"] == "anywhere"
