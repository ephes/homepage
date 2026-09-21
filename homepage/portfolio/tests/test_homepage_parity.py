import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.contrib.staticfiles import finders
from django.db import connection
from django.test.utils import CaptureQueriesContext

from homepage.portfolio.models import PortfolioAboutItem, PortfolioClient, PortfolioService

from .test_pages import add_project, make_portfolio_tree
from .test_styles import contrast_ratio, declarations_for, layer_body


pytestmark = pytest.mark.django_db


def media_conditions(stylesheet):
    """Return normalized media conditions without coupling to formatting."""

    return {
        re.sub(r"\s*,\s*", ", ", re.sub(r"\s*:\s*", ":", " ".join(raw.split())))
        for raw in re.findall(r"@media\s*([^\{]+)\{", stylesheet)
    }


def balanced_block(source, opening):
    depth = 1
    for index in range(opening + 1, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise AssertionError("Unclosed source block")


def media_bodies(stylesheet, condition_pattern):
    bodies = []
    pattern = rf"@media\s*\(\s*{condition_pattern}\s*\)\s*\{{"
    for match in re.finditer(pattern, stylesheet):
        bodies.append(balanced_block(stylesheet, match.end() - 1))
    return bodies


def javascript_function_body(script, name):
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", script)
    assert match is not None, f"Missing JavaScript function: {name}"
    return balanced_block(script, match.end() - 1)


def test_homepage_renders_the_canonical_prototype_composition_from_wagtail(client):
    index = make_portfolio_tree()
    project = add_project(index, title="Editierbares Projekt")
    PortfolioService.objects.create(
        page=index,
        icon=PortfolioService.Icon.WEB,
        title="Editierbare Leistung",
        description="Serverseitig gerenderter Leistungstext.",
    )
    PortfolioAboutItem.objects.create(
        page=index,
        title="Editierbarer Abschnitt",
        lead="Editierbare Subline.",
        text="Serverseitig gerenderter Akkordeontext.",
    )
    PortfolioClient.objects.create(page=index, name="Editierbarer Kunde")

    response = client.get(index.url)
    content = response.content.decode()
    document = BeautifulSoup(content, "html.parser")

    assert response.status_code == 200
    assert document.body["class"] == ["portfolio-site", "portfolio-homepage"]
    for section_id in ("stage", "projekte", "leistungen", "about", "kunden", "kontakt"):
        assert document.select_one(f"main > section#{section_id}") is not None
    assert document.select_one("#stage canvas#fluid") is not None
    assert document.select_one("#stage .fallback h1").get_text(strip=True) == "Moin"
    assert document.select_one("#stage .scrollcue") is not None
    assert document.select_one("#projekte .tile[href='{}']".format(project.url)) is not None
    assert document.select_one("#leistungen .svc h3").get_text(strip=True) == "Editierbare Leistung"
    assert document.select_one("#about details.me-row p").get_text(strip=True) == (
        "Serverseitig gerenderter Akkordeontext."
    )
    assert document.select_one("#kunden .marquee-primary .item").get_text(strip=True) == (
        "Editierbarer Kunde"
    )
    assert 'href="mailto:katharina@wersdoerfer.de"' in content
    assert "projekte/studio-website-relaunch.html" not in content

    stylesheet_urls = [node["href"] for node in document.select("link[rel='stylesheet']")]
    assert "/static/portfolio/prototype/portfolio-startseite.css" in stylesheet_urls
    assert "/static/portfolio/prototype/motion.css" in stylesheet_urls
    assert "/static/portfolio/homepage.css" in stylesheet_urls
    script_urls = [node.get("src") for node in document.select("script[src]")]
    assert "/static/portfolio/prototype/homepage.js" in script_urls
    assert "/static/portfolio/prototype/motion.js" in script_urls
    assert "/static/portfolio/prototype/site-shell.js" not in script_urls
    homepage_script = document.select_one("script[src$='/homepage.js']")
    motion_script = document.select_one("script[src$='/motion.js']")
    assert homepage_script.has_attr("defer")
    assert motion_script.has_attr("defer")
    assert script_urls.index(homepage_script["src"]) < script_urls.index(
        motion_script["src"]
    )
    assert motion_script["data-handwriting-src"].endswith(
        "/static/portfolio/prototype/handwriting-glyphs.js"
    )
    assert content.index("Serverseitig gerenderter Akkordeontext.") < content.index(
        "/static/portfolio/prototype/homepage.js"
    )
    assert content.count('document.documentElement.classList.add("has-js")') == 1
    assert content.index('document.documentElement.classList.add("has-js")') < content.index(
        "/static/portfolio/portfolio.css"
    )


def test_homepage_reuses_one_client_query_for_all_accessible_marquee_copies(client):
    index = make_portfolio_tree()
    PortfolioClient.objects.create(page=index, name="Einmal geladener Kunde")

    with CaptureQueriesContext(connection) as queries:
        response = client.get(index.url)

    client_queries = [
        query["sql"]
        for query in queries.captured_queries
        if "portfolio_portfolioclient" in query["sql"].lower()
    ]
    document = BeautifulSoup(response.content, "html.parser")

    assert response.status_code == 200
    assert len(client_queries) == 1
    assert len(document.select("#kunden .item")) == 4


def test_homepage_adapter_only_bridges_wagtail_markup_to_the_canonical_assets():
    stylesheet_path = finders.find("portfolio/homepage.css")
    foundation_path = finders.find("portfolio/portfolio.css")
    canonical_path = finders.find("portfolio/prototype/portfolio-startseite.css")
    motion_path = finders.find("portfolio/prototype/motion.css")

    assert stylesheet_path is not None
    assert foundation_path is not None
    assert canonical_path is not None
    assert motion_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    foundation = Path(foundation_path).read_text()
    canonical = Path(canonical_path).read_text()
    motion = Path(motion_path).read_text()
    pages = layer_body(stylesheet, "pages")
    foundation_tokens = declarations_for(layer_body(foundation, "tokens"), {":root"})
    foundation_html = declarations_for(layer_body(foundation, "base"), {"html"})
    hidden_canvas = declarations_for(
        canonical, {".no-webgl #fluid", "html:not(.has-js) #fluid"}
    )
    visible_fallback = declarations_for(
        canonical, {".no-webgl .fallback", "html:not(.has-js) .fallback"}
    )
    canonical_frame_cross = declarations_for(
        canonical, {".frame::before", ".frame::after"}
    )
    wagtail_image_frame = declarations_for(
        pages, {".portfolio-homepage .frame--image"}
    )
    image_content = declarations_for(
        pages,
        {
            ".portfolio-homepage .frame--image > picture",
            ".portfolio-homepage .frame--image > img",
            ".portfolio-homepage .frame--image > picture > img",
        },
    )
    image = declarations_for(
        pages,
        {
            ".portfolio-homepage .frame--image > img",
            ".portfolio-homepage .frame--image > picture > img",
        },
    )
    footer_brand = declarations_for(pages, {".portfolio-homepage .foot-profile > .brand"})
    footer_project = declarations_for(
        pages, {".portfolio-homepage .foot-projects li > a"}
    )
    inquiry_fill = declarations_for(
        canonical, {".project-inquiry:is(:hover, :focus-visible) strong::before"}
    )
    inquiry_background = declarations_for(canonical, {".project-inquiry strong::before"})
    inquiry_interaction = declarations_for(
        motion, {".project-inquiry:is(:hover, :focus-visible) strong"}
    )
    inquiry_arrow = declarations_for(motion, {".project-inquiry .ar"})

    assert foundation_html["background"] == "transparent"
    assert hidden_canvas["display"] == "none"
    assert visible_fallback["display"] == "grid"
    assert declarations_for(
        pages, {".portfolio-homepage .contact .stack > * + *"}
    )["margin-block-start"] == "0"
    assert canonical_frame_cross["content"] == (
        'var(--frame-placeholder-content, "")'
    )
    assert wagtail_image_frame["--frame-placeholder-content"] == "none"
    assert image_content == {"display": "block", "inline-size": "100%", "block-size": "100%"}
    assert image["object-fit"] == "cover"
    assert footer_brand["line-height"] == "1.5"
    assert footer_project["inline-size"] == "fit-content"
    assert footer_project["max-inline-size"] == "100%"
    assert footer_project["line-height"] == "1.5"
    assert re.sub(r"\s+", "", footer_project["padding-block-end"]) == (
        "max(0px,calc(1.5rem-1.5em))"
    )
    assert inquiry_fill["animation"] == "project-inquiry-fill 6.4s linear forwards"
    assert inquiry_fill["opacity"] == "1"
    assert inquiry_background["background"] == "var(--tangerine)"
    assert inquiry_background["opacity"] == "0"
    assert inquiry_background["transition"] == "inline-size 640ms linear"
    assert inquiry_interaction["color"] == "var(--warm-black)"
    assert inquiry_arrow["color"] == "inherit"
    assert inquiry_arrow["transition"] == (
        "transform var(--motion-hover) var(--motion-ease)"
    )
    assert contrast_ratio(
        foundation_tokens["--tangerine"], foundation_tokens["--warm-black"]
    ) >= 4.5
    assert declarations_for(canonical, {"0%", "4%"})["inline-size"] == (
        "calc(100% + var(--project-inquiry-pad-inline))"
    )
    assert declarations_for(canonical, {".tile.tile--hero"})["grid-column"] == "span 2"
    assert declarations_for(canonical, {".tile.tile--hero .frame"})["aspect-ratio"] == "21 / 9"
    assert "nth-child(6n)" not in canonical
    assert media_conditions(canonical) == {
        "(hover:none), (pointer:coarse)",
        "(hover:hover) and (pointer:fine)",
        "(max-width:46rem), (max-height:34rem)",
        "(max-width:20rem) and (orientation:portrait)",
        "(max-width:25.625rem)",
        "(max-width:35rem) and (orientation:portrait)",
        (
            "(max-width:35rem) and (orientation:portrait) and "
            "(prefers-reduced-motion:reduce)"
        ),
        "(max-width:36rem)",
        "(max-width:36rem) and (orientation:portrait)",
        "(max-width:46rem)",
        "(max-width:52rem)",
        "(min-width:14.375rem)",
        "(prefers-reduced-motion:reduce)",
    }
    arrow = declarations_for(
        motion, {".tile-arrow", ".pill .ar", ".project-inquiry .ar"}
    )
    arrow_line = declarations_for(
        motion,
        {".tile-arrow::before", ".pill .ar::before", ".project-inquiry .ar::before"},
    )
    arrow_head = declarations_for(
        motion,
        {".tile-arrow::after", ".pill .ar::after", ".project-inquiry .ar::after"},
    )
    interactive_arrow = declarations_for(
        motion,
        {
            ".pill:hover .ar",
            ".pill:focus-visible .ar",
            ".project-inquiry:hover .ar",
            ".project-inquiry:focus-visible .ar",
        },
    )
    assert arrow["position"] == "relative"
    assert arrow_line["background"] == "currentColor"
    assert arrow_head["border-inline-start"] == ".42rem solid currentColor"
    assert interactive_arrow["transform"] == "translateX(.38rem)"
    assert any(
        ".project-inquiry .ar" in reduced_motion
        for reduced_motion in media_bodies(
            motion, r"prefers-reduced-motion\s*:\s*reduce"
        )
    )


def test_homepage_webgl_failure_keeps_the_progressive_enhancement_fallback():
    script_path = finders.find("portfolio/prototype/homepage.js")

    assert script_path is not None
    script = Path(script_path).read_text()
    assert re.search(
        r"try\s*\{\s*initWebGL\(\);\s*\}\s*catch\s*\(error\)\s*\{\s*disableWebGL\(\);\s*\}",
        script,
    )
    webgl = javascript_function_body(script, "initWebGL")
    assert re.search(
        r"if\s*\(\s*!canvas\s*\|\|\s*!stage\s*\)\s*\{\s*disableWebGL\(\);\s*return;\s*\}",
        webgl,
    )
    assert "document.documentElement.classList.add('no-webgl')" in script
    assert "Promise.resolve(document.fonts.load('800 40px Saira'))" in script
    assert ".then(start, start);" in script
    assert "if(startAttempted)return;" in script
    assert script.index("resize(); render();") < script.index("simulationReady=true;")
    assert "function disableSimulation()" in script
    assert script.count("disableSimulation();") >= 3
    assert script.index("initWebGL();") < script.index("Navigation und Scroll-Lock")


def test_homepage_optional_enhancements_have_independent_error_boundaries():
    script_path = finders.find("portfolio/prototype/homepage.js")

    assert script_path is not None
    script = Path(script_path).read_text()
    enhancement_names = (
        "navigation",
        "header",
        "reels",
        "about-lines",
        "about-tiles",
        "custom-cursor",
        "reduced-motion-shapes",
    )

    enhancement_runner = javascript_function_body(script, "runPortfolioEnhancement")
    assert re.search(
        r"try\s*\{\s*initialize\(\);\s*\}\s*catch\s*\(error\)",
        enhancement_runner,
    )
    registrations = re.findall(
        r"runPortfolioEnhancement\(\s*['\"]([^'\"]+)['\"]\s*,\s*function\s*\(\s*\)",
        script,
    )
    assert registrations == list(enhancement_names)

    post_webgl = script.split("Navigation und Scroll-Lock", maxsplit=1)[1]
    assert re.search(r"(?m)^\s*\(\s*function\s*\(\s*\)", post_webgl) is None
