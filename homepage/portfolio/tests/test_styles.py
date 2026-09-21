import re
from hashlib import sha256
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


def split_css_selectors(selector_source):
    """Split a selector list without treating functional-pseudo commas as separators."""

    selectors = []
    start = 0
    depth = 0
    for index, character in enumerate(selector_source):
        if character in "([":
            depth += 1
        elif character in ")]":
            depth -= 1
        elif character == "," and depth == 0:
            selectors.append(selector_source[start:index].strip())
            start = index + 1
    selectors.append(selector_source[start:].strip())
    return {selector for selector in selectors if selector}


def declaration_blocks_for(layer, expected_selectors):
    without_comments = re.sub(r"/\*.*?\*/", "", layer, flags=re.DOTALL)
    matches = []
    for selector_source, declaration_source in re.findall(r"([^{}]+)\{([^{}]*)\}", without_comments):
        selectors = split_css_selectors(selector_source)
        if selectors != set(expected_selectors):
            continue
        matches.append(
            {
                name.strip(): value.strip()
                for declaration in declaration_source.split(";")
                if ":" in declaration
                for name, value in [declaration.split(":", 1)]
            }
        )
    return matches


def declarations_for(layer, expected_selectors):
    matches = declaration_blocks_for(layer, expected_selectors)
    if matches:
        return matches[0]
    raise AssertionError(f"Missing CSS rule for selectors: {expected_selectors}")


def media_conditions(stylesheet):
    """Return normalized media conditions without coupling to formatting."""

    return {
        re.sub(r"\s*,\s*", ", ", re.sub(r"\s*:\s*", ":", " ".join(raw.split())))
        for raw in re.findall(r"@media\s*([^\{]+)\{", stylesheet)
    }


def contrast_ratio(background, foreground):
    def relative_luminance(color):
        channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lighter, darker = sorted(
        (relative_luminance(background), relative_luminance(foreground)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def test_portfolio_stylesheet_declares_the_stable_layer_order():
    stylesheet_path = finders.find("portfolio/portfolio.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    declaration = "@layer reset, tokens, base, layout, components, pages, motion, utilities;"

    assert stylesheet.count(declaration) == 1
    layer_positions = [stylesheet.index(f"@layer {layer} {{") for layer in LAYER_ORDER]
    assert layer_positions == sorted(layer_positions)


def test_prototype_typography_tokens_are_global_and_page_geometry_stays_local():
    stylesheet_path = finders.find("portfolio/portfolio.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    tokens = declarations_for(layer_body(stylesheet, "tokens"), {":root"})
    base = layer_body(stylesheet, "base")

    assert tokens["--creme"] == "#f0ece2"
    assert tokens["--warm-black"] == "#171410"
    assert tokens["--tangerine"] == "#eb3d00"
    assert tokens["--bg"] == "var(--creme)"
    assert tokens["--ink"] == "var(--warm-black)"
    assert tokens["--accent"] == "var(--tangerine)"
    assert tokens["--portfolio-bg"] == "var(--bg)"
    assert tokens["--portfolio-text"] == "var(--ink)"
    assert tokens["--portfolio-accent"] == "var(--accent)"
    assert tokens["--ph"] == "rgba(23, 20, 16, 0.06)"
    assert tokens["--ph-ink"] == "rgba(23, 20, 16, 0.45)"
    assert tokens["color-scheme"] == "light"
    assert tokens["--font-sans"] == '"Saira", system-ui, sans-serif'
    assert tokens["--font-handwriting"] == '"Astagina", cursive'
    for name in (
        "--headline-xl",
        "--headline-l",
        "--headline-m",
        "--headline-s",
        "--type-eyebrow",
        "--type-subline",
        "--type-lead",
        "--type-case-large",
        "--scr-size",
        "--space-section",
        "--space-eyebrow-title",
        "--space-title-content",
        "--tracking-display",
        "--tracking-action",
        "--tracking-label",
    ):
        assert name in tokens
    html = declarations_for(base, {"html"})
    layout = layer_body(stylesheet, "layout")
    shell = declarations_for(layout, {".portfolio-site"})
    homepage_stylesheet_path = finders.find(
        "portfolio/prototype/portfolio-startseite.css"
    )
    assert homepage_stylesheet_path is not None
    homepage_stylesheet = Path(homepage_stylesheet_path).read_text()
    assert html["font-family"] == "var(--font-sans)"
    assert html["overflow-x"] == "clip"
    balanced_headings = declarations_for(
        base,
        {
            "h1",
            "h2",
            "h3",
            "h4",
            ".site-header__brand",
            ".site-menu summary",
            ".case-label",
        },
    )
    assert balanced_headings["-webkit-hyphens"] == "manual"
    assert balanced_headings["hyphens"] == "manual"
    assert "2.5168" in homepage_stylesheet
    assert shell == {"position": "relative"}
    assert "--pad:" not in layout
    assert "--hero-inset:" not in layout
    assert "--header-h:" not in layout
    assert ".portfolio-hero__title" not in stylesheet
    assert ".portfolio-stage" not in stylesheet
    assert not declaration_blocks_for(stylesheet, {".project-card"})
    assert ".site-footer" not in stylesheet
    assert media_conditions(stylesheet) == {
        "(max-width:36rem)",
        "(max-width:52rem)",
        "(prefers-reduced-motion:reduce)",
    }


def test_shared_shell_consumers_keep_local_geometry_fallbacks():
    stylesheet_path = finders.find("portfolio/portfolio.css")
    adapter_path = finders.find("portfolio/project-wagtail.css")

    assert stylesheet_path is not None
    assert adapter_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    adapter = Path(adapter_path).read_text()
    layout = layer_body(stylesheet, "layout")
    components = layer_body(stylesheet, "components")
    main = declarations_for(
        layout, {".portfolio-site[data-portfolio-shell] > main"}
    )
    grid_lines = declarations_for(layout, {".pagegrid__pads", ".pagegrid__cols"})
    menu = declarations_for(components, {".site-nav nav"})

    assert main["padding-block-start"] == "var(--header-h, calc(4.6rem + 1px))"
    assert grid_lines["inset-inline"] == (
        "var(--pad, clamp(1.25rem, 4vw, 4rem))"
    )
    assert menu["inset-block-start"] == (
        "var(--header-h, calc(4.6rem + 1px))"
    )
    assert "var(--header-h)" not in stylesheet
    assert "var(--pad)" not in stylesheet
    assert "var(--header-h)" not in adapter
    assert "var(--pad)" not in adapter


def test_shared_component_rules_are_not_declared_twice():
    stylesheet_path = finders.find("portfolio/portfolio.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()

    assert len(declaration_blocks_for(stylesheet, {".project-results__title"})) == 1
    assert len(declaration_blocks_for(stylesheet, {".related-project-card__details"})) == 1


def test_result_list_keeps_value_first_in_dom_and_visual_order():
    stylesheet_path = finders.find("portfolio/portfolio.css")
    project_stylesheet_path = finders.find(
        "portfolio/prototype/projekte/projekt.css"
    )
    adapter_path = finders.find("portfolio/project-wagtail.css")

    assert stylesheet_path is not None
    assert project_stylesheet_path is not None
    assert adapter_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    project_stylesheet = Path(project_stylesheet_path).read_text()
    adapter = Path(adapter_path).read_text()
    components = layer_body(stylesheet, "components")
    result = declarations_for(project_stylesheet, {".result"})
    value = declarations_for(components, {".project-results .result-value"})
    result_list = declarations_for(adapter, {".project-results .result-grid"})

    assert result["display"] == "flex"
    assert result["flex-direction"] == "column"
    assert "order" not in value
    assert result_list == {"margin": "0", "padding": "0", "list-style": "none"}


def test_local_font_faces_preserve_the_approved_prototype_files():
    font_stylesheet_path = finders.find("portfolio/fonts.css")
    saira_path = finders.find("portfolio/fonts/saira-variable.woff2")
    astagina_path = finders.find("portfolio/fonts/astagina.woff2")

    assert font_stylesheet_path is not None
    assert saira_path is not None
    assert astagina_path is not None
    font_stylesheet = Path(font_stylesheet_path).read_text()
    saira = Path(saira_path).read_bytes()
    astagina = Path(astagina_path).read_bytes()

    saira_face = declarations_for(font_stylesheet, {"@font-face"})
    astagina_face = declaration_blocks_for(font_stylesheet, {"@font-face"})[1]
    assert saira_face["font-family"] == '"Saira"'
    assert saira_face["font-weight"] == "100 900"
    assert saira_face["src"].startswith('url("fonts/saira-variable.woff2")')
    assert saira_face["font-display"] == "swap"
    assert astagina_face["font-family"] == '"Astagina"'
    assert astagina_face["font-weight"] == "400"
    assert astagina_face["src"].startswith('url("fonts/astagina.woff2")')
    assert astagina_face["font-display"] == "swap"
    assert sha256(saira).hexdigest() == "a3507bf941f003c0cfc8f5abe49bd97b0ae7765429d1e27daa8ff652db348a6a"
    assert sha256(astagina).hexdigest() == "c45da2e960130f837ddd5bf903141e960a83cf12760d00228179d7038a5e1794"


def test_wagtail_admin_theme_uses_the_portfolio_palette_without_layout_overrides():
    stylesheet_path = finders.find("portfolio/admin.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    for color in ("#f0ece2", "#171410", "#eb3d00", "#1c995c"):
        assert color in stylesheet
    for variable in (
        "--w-color-surface-page",
        "--w-color-surface-menus",
        "--w-color-surface-menu-item-active",
        "--w-color-surface-button-default",
        "--w-color-text-label-menus-active",
        "--w-color-focus",
    ):
        assert variable in stylesheet
    assert "(prefers-color-scheme:dark)" in media_conditions(stylesheet)
    assert "(forced-colors:active)" in media_conditions(stylesheet)
    palette = declarations_for(stylesheet, {":root"})
    wagtail_theme = declarations_for(
        stylesheet,
        {":root", ".w-theme-light", ".w-theme-dark", ".w-theme-system"},
    )
    assert wagtail_theme["--w-color-surface-button-default"] == (
        "var(--portfolio-admin-green)"
    )
    assert wagtail_theme["--w-color-surface-button-hover"] == (
        "var(--portfolio-admin-green-hover)"
    )
    assert palette["--portfolio-admin-menu-surface"] == "#393734"
    assert palette["--portfolio-admin-menu-muted"] == "#b7ab9d"
    assert contrast_ratio("#393734", "#f0ece2") >= 4.5
    assert contrast_ratio("#393734", "#b7ab9d") >= 4.5
    assert ".sidebar-sub-menu-panel .sidebar-menu-item--active" in stylesheet
    assert "border-inline-start-color: var(--portfolio-admin-orange);" in stylesheet
    assert ".Draftail-FloatingToolbar" in stylesheet
    assert "--w-color-text-button: var(--portfolio-admin-cream);" in stylesheet
    assert not any(
        property_name in stylesheet
        for property_name in (
            "grid-template",
            "position:",
            "inline-size:",
            "block-size:",
        )
    )


def test_wagtail_admin_theme_dependencies_exist_in_the_installed_wagtail_css():
    core_stylesheet_path = finders.find("wagtailadmin/css/core.css")
    draftail_stylesheet_path = finders.find(
        "wagtailadmin/css/panels/draftail.css"
    )

    assert core_stylesheet_path is not None
    assert draftail_stylesheet_path is not None
    core_stylesheet = Path(core_stylesheet_path).read_text()
    draftail_stylesheet = Path(draftail_stylesheet_path).read_text()
    for variable in (
        "--w-color-surface-page",
        "--w-color-surface-menus",
        "--w-color-surface-menu-item-active",
        "--w-color-surface-button-default",
        "--w-color-surface-button-hover",
        "--w-color-text-label-menus-default",
        "--w-color-text-label-menus-active",
        "--w-color-focus",
    ):
        assert variable in core_stylesheet, (
            f"Wagtail removed or renamed {variable}; update portfolio/admin.css "
            "before accepting the Wagtail upgrade."
        )
    for selector in (
        ".sidebar-sub-menu-panel",
        ".sidebar-menu-item__link",
        ".sidebar-menu-item--active",
    ):
        assert selector in core_stylesheet, (
            f"Wagtail removed or renamed {selector}; visually revalidate the "
            "portfolio admin submenu before accepting the Wagtail upgrade."
        )
    for selector in (".Draftail-Toolbar", ".Draftail-FloatingToolbar"):
        assert selector in draftail_stylesheet, (
            f"Wagtail removed or renamed {selector}; visually revalidate the "
            "portfolio rich-text controls before accepting the Wagtail upgrade."
        )


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
    assert declarations_for(base, {"[data-no-break]"})["white-space"] == "nowrap"


def test_project_display_headline_uses_available_columns_without_word_hyphenation():
    stylesheet_path = finders.find("portfolio/prototype/projekte/projekt.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    headline = declarations_for(stylesheet, {".project-hero h1"})

    assert headline["max-inline-size"] == "min(18ch, 100%)"
    assert headline["line-height"] == "1.03"
    assert headline["-webkit-hyphens"] == "manual"
    assert headline["hyphens"] == "manual"


def test_project_intro_uses_nested_intrinsic_switchers_and_service_markers():
    stylesheet_path = finders.find("portfolio/prototype/projekte/projekt.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    metadata = declarations_for(stylesheet, {".project-meta"})
    facts = declarations_for(stylesheet, {".project-meta__facts"})
    services = declarations_for(stylesheet, {".marker-list", ".rich-text ul"})
    arrowhead = declarations_for(
        stylesheet,
        {".marker-list > li::before", ".rich-text ul > li::before"},
    )
    live_link = declarations_for(stylesheet, {".project-live-link"})
    summary = declarations_for(stylesheet, {".project-summary"})
    lead = declarations_for(stylesheet, {".project-lead"})
    intro = declarations_for(stylesheet, {".intro-grid"})
    intro_children = declarations_for(stylesheet, {".intro-grid > *"})
    metadata_columns = declarations_for(stylesheet, {".project-meta > dl"})
    metadata_labels = declarations_for(stylesheet, {".project-meta dt"})

    assert intro["display"] == "flex"
    assert intro["flex-wrap"] == "wrap"
    assert intro["container-type"] == "inline-size"
    assert intro_children["flex-basis"] == (
        "calc((var(--intro-threshold) - 100%) * 999)"
    )
    assert metadata["display"] == "flex"
    assert metadata["flex-wrap"] == "wrap"
    assert metadata_columns["flex-basis"] == (
        "calc((var(--meta-threshold) - 100%) * 999)"
    )
    assert metadata_labels["translate"] == "0 -.0625rem"
    assert facts["flex-direction"] == "column"
    assert services["flex-direction"] == "column"
    assert services["list-style"] == "none"
    assert ".project-service-arrow" not in stylesheet
    assert arrowhead["inline-size"] == "0"
    assert arrowhead["border-inline-start"] == ".34rem solid var(--ink)"
    assert live_link["display"] == "inline-flex"
    assert live_link["gap"] == ".7rem"
    assert live_link["margin-block-start"] == "auto"
    assert live_link["padding-block"] == ".425rem"
    assert live_link["font-size"] == "1.2rem"
    assert live_link["font-weight"] == "700"
    assert summary["display"] == "flex"
    assert summary["flex-direction"] == "column"
    assert summary["gap"] == "1.875rem"
    assert lead["max-inline-size"] == (
        "calc(100% - clamp(0rem, calc((100cqi - var(--intro-threshold)) * 999), 2rem))"
    )


def test_project_case_rows_align_labels_and_copy_without_rich_text_margin_drift():
    prototype_path = finders.find("portfolio/prototype/projekte/projekt.css")
    adapter_path = finders.find("portfolio/project-wagtail.css")

    assert prototype_path is not None
    assert adapter_path is not None
    prototype = Path(prototype_path).read_text()
    adapter = Path(adapter_path).read_text()
    row = declarations_for(prototype, {".case-row"})
    following_row = declarations_for(prototype, {".case-row + .case-row"})
    first_paragraph = declarations_for(adapter, {".case-copy > :first-child"})
    last_paragraph = declarations_for(adapter, {".case-copy > :last-child"})

    assert row["align-items"] == "start"
    assert following_row["margin-block-start"] == "clamp(2rem, 3.5vw, 3rem)"
    assert first_paragraph["margin-block-start"] == "0"
    assert last_paragraph["margin-block-end"] == "0"


def test_editorial_inline_links_use_service_weight_and_tangerine_hover_treatment():
    stylesheet_path = finders.find("portfolio/prototype/motion.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    links = declarations_for(
        stylesheet,
        {".project-lead a", ".rich-text a"},
    )
    interactive_links = declarations_for(
        stylesheet,
        {
            ".project-lead a:hover",
            ".project-lead a:focus-visible",
            ".rich-text a:hover",
            ".rich-text a:focus-visible",
        },
    )
    nested_emphasis = declarations_for(
        stylesheet,
        {
            ".project-lead a b",
            ".project-lead a strong",
            ".rich-text a b",
            ".rich-text a strong",
        },
    )

    assert links["color"] == "inherit"
    assert links["font-weight"] == "600"
    assert links["background-image"] == (
        "linear-gradient(var(--tangerine), var(--tangerine))"
    )
    assert links["background-size"] == "0 1px"
    assert nested_emphasis["font-weight"] == "inherit"
    assert interactive_links["color"] == "var(--tangerine)"
    assert interactive_links["background-size"] == "100% 1px"


def test_shared_shell_does_not_override_the_canonical_menu_geometry():
    stylesheet_path = finders.find("portfolio/portfolio.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    components = layer_body(stylesheet, "components")

    header = declarations_for(components, {".site-header"})
    primary = declarations_for(components, {".menu-primary"})
    socials = declarations_for(components, {".menu-socials"})
    social_links = declarations_for(components, {".menu-social-links"})
    social_button = declarations_for(components, {".menu-social-links a"})

    assert "min-block-size" not in header
    assert "justify-self" not in primary
    assert "border-block-start" not in socials
    assert "grid-template-columns" not in social_links
    assert "min-block-size" not in social_button
