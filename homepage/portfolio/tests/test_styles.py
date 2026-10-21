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
                return stylesheet[opening + 1 : index]  # noqa: E203
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
        channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]  # noqa: E203
        linear = [
            channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels
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
    assert tokens["--warm-black"] == "#090d19"
    assert tokens["--tangerine"] == "#eb3d00"
    assert tokens["--bg"] == "light-dark(var(--creme), var(--dark-ground))"
    assert tokens["--ink"] == "light-dark(var(--warm-black), var(--creme))"
    assert tokens["--accent"] == "var(--tangerine)"
    assert tokens["--portfolio-bg"] == "var(--bg)"
    assert tokens["--portfolio-text"] == "var(--ink)"
    assert tokens["--portfolio-accent"] == "var(--accent)"
    assert tokens["--ph"] == "light-dark(rgba(9, 13, 25, 0.06), rgba(240, 236, 226, 0.06))"
    assert tokens["--ph-ink"] == "light-dark(rgba(9, 13, 25, 0.45), rgba(240, 236, 226, 0.45))"
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
    homepage_stylesheet_path = finders.find("portfolio/prototype/portfolio-startseite.css")
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
        "(prefers-color-scheme:dark)",
        "print",
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
    main = declarations_for(layout, {".portfolio-site[data-portfolio-shell] > main"})
    grid_lines = declarations_for(layout, {".pagegrid__pads", ".pagegrid__cols"})
    menu = declarations_for(components, {".site-nav nav"})

    assert main["padding-block-start"] == "var(--header-h, calc(4.6rem + 1px))"
    assert grid_lines["inset-inline"] == ("var(--pad, clamp(1.25rem, 4vw, 4rem))")
    assert menu["inset-block-start"] == ("var(--header-h, calc(4.6rem + 1px))")
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
    project_stylesheet_path = finders.find("portfolio/prototype/projekte/projekt.css")
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

    faces = declaration_blocks_for(font_stylesheet, {"@font-face"})
    saira_face, saira_italic_face, astagina_face = faces
    assert saira_face["font-family"] == '"Saira"'
    assert saira_face["font-weight"] == "100 900"
    assert saira_face["src"].startswith('url("fonts/saira-variable.woff2")')
    assert saira_face["font-display"] == "swap"
    # The real Saira italic (same version, axes and glyphs as the upright file).
    assert saira_italic_face["font-family"] == '"Saira"'
    assert saira_italic_face["font-style"] == "italic"
    assert saira_italic_face["src"].startswith('url("fonts/saira-italic-variable.woff2")')
    saira_italic = Path(finders.find("portfolio/fonts/saira-italic-variable.woff2")).read_bytes()
    assert sha256(saira_italic).hexdigest() == "0f90fe00f487ad10a639bbe80363c479308ee8f03d1b2afd964293f53240423f"
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
    assert wagtail_theme["--w-color-surface-button-default"] == ("var(--portfolio-admin-green)")
    assert wagtail_theme["--w-color-surface-button-hover"] == ("var(--portfolio-admin-green-hover)")
    # The sidebar is dark in every theme, so hovered menu labels must stay light.
    assert wagtail_theme["--w-color-text-label-menus-active"] == "var(--portfolio-admin-cream)"
    assert contrast_ratio(palette["--portfolio-admin-ink"], palette["--portfolio-admin-cream"]) >= 4.5
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
    draftail_stylesheet_path = finders.find("wagtailadmin/css/panels/draftail.css")

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
    no_break = declarations_for(base, {"[data-no-break]"})
    assert no_break["display"] == "inline-block"
    assert "white-space" not in no_break


def test_project_display_headline_hyphenates_words_wider_than_the_line():
    stylesheet_path = finders.find("portfolio/prototype/projekte/projekt.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    headline = declarations_for(stylesheet, {".project-hero h1"})

    assert headline["max-inline-size"] == "min(18ch, 100%)"
    assert headline["line-height"] == "1.03"
    assert headline["-webkit-hyphens"] == "auto"
    assert headline["hyphens"] == "auto"
    assert headline["hyphenate-limit-chars"] == "8 5 4"
    assert headline["overflow-wrap"] == "break-word"


def test_project_details_split_into_four_grid_columns_only_below_the_side_by_side_layout():
    stylesheet = Path(finders.find("portfolio/prototype/projekte/projekt.css")).read_text()
    details_container = stylesheet.index("container: project-meta / inline-size;")
    side_by_side_reset = stylesheet.index(".project-meta { container-type: normal; --meta-space: var(--s1); }")
    four_columns = stylesheet.index("@container project-meta (width >= 40rem)")
    split = declarations_for(
        stylesheet, {".project-meta__services .project-service-list", ".project-meta > .project-meta__facts"}
    )

    # The side-by-side layout must come after the container so that it can switch it off.
    assert details_container < side_by_side_reset < four_columns
    assert split["grid-auto-flow"] == "column"
    assert split["column-gap"] == "calc(2 * var(--inset))"
    assert "repeat(var(--service-rows, 1), auto)" in stylesheet
    assert ".project-meta__facts:has(> :nth-child(3)) { grid-template-rows: repeat(2, auto); }" in stylesheet
    # Details only wrap between whole words, also inside the hyphenated statement text.
    whole_words = declarations_for(stylesheet, {".project-meta", ".project-meta li"})
    assert whole_words["hyphens"] == "manual"
    assert stylesheet.index(".case-copy, .case-copy p, .case-copy li {") < stylesheet.index(
        ".project-meta, .project-meta li {"
    )


def test_project_intro_uses_nested_intrinsic_switchers_and_service_markers():
    stylesheet_path = finders.find("portfolio/prototype/projekte/projekt.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    metadata = next(block for block in declaration_blocks_for(stylesheet, {".project-meta"}) if "display" in block)
    facts = declarations_for(stylesheet, {".project-meta__facts"})
    services = declarations_for(stylesheet, {".marker-list", ".rich-text ul"})
    arrowhead = declarations_for(
        stylesheet,
        {".marker-list > li::before", ".rich-text ul > li::before"},
    )
    live_link = declarations_for(stylesheet, {".project-live-link"})
    lead = declarations_for(stylesheet, {".project-lead"})
    article = declarations_for(stylesheet, {".project"})
    intro = declarations_for(stylesheet, {".project-stage"})
    # The wide layout lifts the column limit in a container query; check the base rule.
    metadata_columns = next(
        block for block in declaration_blocks_for(stylesheet, {".project-meta > dl"}) if "flex-basis" in block
    )
    metadata_labels = declarations_for(stylesheet, {".project-meta dt"})

    assert article["container"] == "project / inline-size"
    assert intro["display"] == "grid"
    assert intro["grid-template-areas"] == '"head" "media" "case" "meta"'
    assert "@container project (width >= 60rem)" in stylesheet
    assert metadata["display"] == "flex"
    assert metadata["flex-wrap"] == "wrap"
    assert metadata_columns["flex-basis"] == ("calc((var(--meta-threshold) - 100%) * 999)")
    assert metadata_labels["translate"] == "0 -.0625rem"
    assert metadata_columns["flex-direction"] == "column"
    assert facts["justify-content"] == "space-between"
    assert services["flex-direction"] == "column"
    assert services["list-style"] == "none"
    assert ".project-service-arrow" not in stylesheet
    assert arrowhead["inline-size"] == "var(--marker-size)"
    assert arrowhead["border-radius"] == "50%"
    assert arrowhead["background"] == "var(--ink)"
    assert live_link["display"] == "inline-flex"
    assert live_link["gap"] == ".7rem"
    assert "font-weight" not in live_link
    assert lead["max-inline-size"] == "100%"


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

    assert row["--motion-enter-distance"] == "2rem"
    assert following_row["margin-block-start"] == "var(--case-gap)"
    assert first_paragraph["margin-block-start"] == "0"
    assert last_paragraph["margin-block-end"] == "0"


def test_staged_case_study_keeps_inactive_stations_readable_for_screen_readers():
    stylesheet = Path(finders.find("portfolio/prototype/projekte/projekt.css")).read_text()
    script = Path(finders.find("portfolio/prototype/motion.js")).read_text()
    rows = declarations_for(stylesheet, {".is-staged .case-stage > .case-row"})
    active_row = declarations_for(stylesheet, {".is-staged .case-row.is-active"})
    parts = declarations_for(stylesheet, {".is-staged .case-copy > .case-part"})
    active_part = declarations_for(stylesheet, {".is-staged .case-part.is-active"})

    # visibility: hidden would drop inactive stations from the accessibility tree.
    for rule in (rows, active_row, parts, active_part):
        assert "visibility" not in rule
        assert "visibility" not in rule.get("transition", "")
    assert rows["opacity"] == parts["opacity"] == "0"
    assert rows["pointer-events"] == parts["pointer-events"] == "none"
    assert active_row["pointer-events"] == active_part["pointer-events"] == "auto"
    # Focus inside an inactive station brings that station forward.
    assert 'study.addEventListener("focusin"' in script
    # A swipe that triggered a step stays blocked until the finger lifts.
    assert "touchStepped = true" in script


def test_main_site_linen_lies_below_dialogs_and_is_not_printed():
    stylesheet = Path(finders.find("css/site-overrides.css")).read_text()
    linen = declarations_for(stylesheet, {".linen"})

    # Above the sticky/fixed navbar (1020/1030), below the theme corner, offcanvas,
    # modals and the search overlay (1040 and up).
    assert 1030 < int(linen["z-index"]) < 1040
    assert linen["pointer-events"] == "none"
    assert re.search(r"@media print\s*\{\s*\.linen\s*\{\s*display:\s*none;", stylesheet)


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
    assert links["font-weight"] == "calc(600 + var(--weight-shift))"
    assert links["background-image"] == ("linear-gradient(var(--tangerine), var(--tangerine))")
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


PORTFOLIO_STYLESHEETS = (
    "portfolio/portfolio.css",
    "portfolio/homepage.css",
    "portfolio/project-wagtail.css",
    "portfolio/prototype/portfolio-startseite.css",
    "portfolio/prototype/motion.css",
    "portfolio/prototype/projekte/projekt.css",
    "portfolio/prototype/legal.css",
    "portfolio/prototype/501.css",
)
TOKEN_STYLESHEETS = (
    "portfolio/portfolio.css",
    "portfolio/prototype/portfolio-startseite.css",
    "portfolio/prototype/projekte/projekt.css",
)


def read_static(path):
    stylesheet_path = finders.find(path)
    assert stylesheet_path is not None
    return Path(stylesheet_path).read_text()


def root_tokens(stylesheet):
    """Return the first plain :root block, also when it sits inside a layer."""

    without_comments = re.sub(r"/\*.*?\*/", "", stylesheet, flags=re.DOTALL)
    for match in re.finditer(r"(?:^|[{}])\s*:root\s*\{([^{}]*)\}", without_comments):
        if "--bg" in match.group(1):
            return {
                name.strip(): value.strip()
                for declaration in match.group(1).split(";")
                if ":" in declaration
                for name, value in [declaration.split(":", 1)]
            }
    raise AssertionError("Missing :root token block")


def compact(value):
    return re.sub(r"\s+", "", value).lower()


def test_dark_mode_swaps_the_role_tokens_and_keeps_the_light_values():
    for path in TOKEN_STYLESHEETS:
        tokens = root_tokens(read_static(path))
        assert compact(tokens["--bg"]) == "light-dark(var(--creme),var(--dark-ground))", path
        assert compact(tokens["--ink"]) == "light-dark(var(--warm-black),var(--creme))", path
        # Kräftige Linien: dunkel Creme mit 50 % Deckkraft statt voll.
        assert compact(tokens["--rule-strong"]) == "light-dark(var(--ink),rgba(240,236,226,0.5))", path
        assert compact(tokens["--dark-bg"]) == "light-dark(var(--warm-black),var(--dark-raised))", path
        for name in ("--rule", "--rule-soft", "--ph", "--ph-ink"):
            light, dark = re.match(r"light-dark\((rgba\([^)]*\)),(rgba\([^)]*\))\)", compact(tokens[name])).groups()
            assert light.startswith("rgba(9,13,25,"), (path, name)
            assert dark.startswith("rgba(240,236,226,"), (path, name)
            # Linien stehen im Dunkeln etwas kräftiger als im Hellen, Platzhalter gleich.
            light_alpha, dark_alpha = (float(value.split(",")[-1].rstrip(")")) for value in (light, dark))
            if name in ("--rule", "--rule-soft"):
                assert dark_alpha > light_alpha, (path, name)
            else:
                assert dark_alpha == light_alpha, (path, name)
        assert "color-scheme" not in tokens or tokens["color-scheme"] == "light", path


def test_dark_mode_switch_lives_once_in_the_token_layer():
    stylesheet = read_static("portfolio/portfolio.css")
    tokens_layer = layer_body(stylesheet, "tokens")
    tokens = declarations_for(tokens_layer, {":root"})
    forced = declarations_for(tokens_layer, {':root[data-theme="dark"]'})
    system = declarations_for(tokens_layer, {':root:not([data-theme="light"])'})

    assert tokens["--weight-shift"] == "0"
    assert tokens["--linen-filter"] == "none"
    assert tokens["--linen-blend"] == "multiply"
    assert tokens["--dark-hue"].isdigit()
    assert tokens["--dark-ground"] == "oklch(0.17 0.025 var(--dark-hue))"
    assert tokens["--dark-raised"] == "oklch(0.33 0.045 var(--dark-hue))"
    for dark in (forced, system):
        assert dark == {
            "--weight-shift": "-30",
            "--linen-filter": "invert(1)",
            "--linen-blend": "screen",
            "color-scheme": "dark",
        }
    assert "@media (prefers-color-scheme: dark)" in tokens_layer
    for path in PORTFOLIO_STYLESHEETS[1:]:
        assert "color-scheme:" not in re.sub(r"/\*.*?\*/", "", read_static(path), flags=re.DOTALL), path
    # Die Leinentextur folgt den Tokens in beiden Fassungen.
    linen = declarations_for(read_static("portfolio/prototype/motion.css"), {".linen"})
    assert linen["filter"] == "var(--linen-filter, none)"
    assert linen["mix-blend-mode"] == "var(--linen-blend, multiply)"


def test_dark_tones_keep_readable_contrast():
    # Petrol-Grund und -Fläche bei --dark-hue 220: oklch(0.17 0.025 220), oklch(0.33 0.045 220).
    ground, raised, creme = "#031217", "#173b45", "#f0ece2"

    assert contrast_ratio(ground, creme) >= 7
    assert contrast_ratio(raised, creme) >= 7
    assert contrast_ratio(ground, "#8f9389") >= 4.5  # --muted im Dunkeln
    assert contrast_ratio(ground, "#a8aba1") >= 4.5  # Verfügbarkeit in der Kopfleiste
    assert contrast_ratio(ground, "#eb3d00") >= 4.5  # Tangerine auf dem Grund


def test_tangerine_on_dark_surfaces_uses_a_lighter_step_in_dark_mode():
    tokens = declarations_for(layer_body(read_static("portfolio/portfolio.css"), "tokens"), {":root"})
    raised, footer, warm_black = "#173b45", "#06262f", "#090d19"
    on_dark = "#f6623d"

    assert compact(tokens["--tangerine-on-dark"]) == f"light-dark(var(--tangerine),{on_dark})"
    # Light: Tangerine on black; dark: the lighter step on the petrol surfaces.
    assert contrast_ratio(warm_black, "#eb3d00") >= 4.5
    assert contrast_ratio(footer, on_dark) >= 4.5  # footer link hover and focus text
    assert contrast_ratio(raised, on_dark) >= 3  # handwriting and asterisks (large text, graphics)

    startseite = read_static("portfolio/prototype/portfolio-startseite.css")
    motion = read_static("portfolio/prototype/motion.css")
    projekt = read_static("portfolio/prototype/projekte/projekt.css")
    assert ".on-dark{ --accent:var(--tangerine-on-dark); }" in startseite
    assert ".on-dark h2.big .lastline .scr text { fill: var(--tangerine-on-dark);" in startseite
    assert declarations_for(motion, {".on-dark .scr.hw-label .hw-svg"})["color"] == "var(--tangerine-on-dark)"
    footer_hover = declarations_for(
        motion,
        {
            ".foot-col a:not(.pill):hover",
            ".foot-col a:not(.pill):focus-visible",
            ".foot-bar a:not(.to-top):hover",
            ".foot-bar a:not(.to-top):focus-visible",
            ".project-footer a:hover",
            ".project-footer a:focus-visible",
        },
    )
    assert footer_hover["color"] == "var(--tangerine-on-dark)"
    assert declarations_for(projekt, {".results .eyebrow::before"})["color"] == "var(--tangerine-on-dark)"


def test_portfolio_always_prints_in_the_light_scheme():
    tokens_layer = layer_body(read_static("portfolio/portfolio.css"), "tokens")
    print_start = tokens_layer.index("@media print")
    printed = declarations_for(
        tokens_layer[print_start:], {":root", ":root[data-theme]", ':root:not([data-theme="light"])'}
    )

    # After both dark rules, so it wins at equal specificity.
    assert tokens_layer.index('@media (prefers-color-scheme: dark)') < print_start
    assert printed == {
        "--weight-shift": "0",
        "--linen-filter": "none",
        "--linen-blend": "multiply",
        "color-scheme": "light",
    }


def test_every_font_weight_follows_the_dark_mode_shift_except_handwriting():
    pattern = re.compile(r"font-weight\s*:\s*([^;}]+)")
    for path in PORTFOLIO_STYLESHEETS:
        stylesheet = read_static(path)
        for match in pattern.finditer(stylesheet):
            value = match.group(1).strip()
            start, end = stylesheet.rfind("{", 0, match.start()), stylesheet.find("}", match.end())
            block = stylesheet[start:end]
            if "Astagina" in block:
                assert value == "400", path
            elif value != "inherit":
                assert value.startswith("calc(") and value.endswith("+ var(--weight-shift))"), (path, value)


def test_shadows_and_hard_coded_ink_follow_the_color_scheme():
    for path in PORTFOLIO_STYLESHEETS:
        stylesheet = re.sub(r"/\*.*?\*/", "", read_static(path), flags=re.DOTALL)
        for line in stylesheet.splitlines():
            if line.strip().startswith("--"):
                continue
            if "rgba(9, 13, 25" in line or "rgba(255, 255, 255, ." in line and "scrollcue" not in line:
                assert "light-dark(" in line, (path, line)
            # Creme bleibt nur als Schrift auf Tangerine fest; Flächen folgen --bg/--ink.
            assert not re.search(r"background(-color)?\s*:\s*var\(--(creme|warm-black)", line), (path, line)
            assert "var(--creme, " not in line and "var(--warm-black, " not in line, (path, line)
