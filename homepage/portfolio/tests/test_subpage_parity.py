from pathlib import Path

import pytest
from django.contrib.staticfiles import finders
from django.test import RequestFactory

from homepage.portfolio.models import default_project_content

from .test_pages import add_project, make_portfolio_tree
from .test_styles import declarations_for, layer_body

pytestmark = pytest.mark.django_db


def test_project_uses_canonical_prototype_assets_without_the_destructive_prototype_renderer():
    index = make_portfolio_tree()
    project = add_project(index)
    project.content = default_project_content()
    project.save_revision().publish()
    add_project(index, title="Zweites Projekt")

    response = project.serve(RequestFactory().get(project.url))
    response.render()
    content = response.content.decode()

    assert 'data-project="studio-website"' in content
    assert "/static/portfolio/prototype/projekte/projekt.css" in content
    assert "/static/portfolio/prototype/motion.css" in content
    assert "/static/portfolio/prototype/motion.js" in content
    assert "/static/portfolio/prototype/project-teasers.js" in content
    assert "/static/portfolio/prototype/site-shell.js" in content
    assert "/static/portfolio/project-wagtail.js" in content
    assert "/static/portfolio/prototype/projekte/projekt.js" not in content
    assert "/static/portfolio/prototype/portfolio-startseite.css" not in content
    assert "/static/portfolio/prototype/homepage.js" not in content
    assert "/static/portfolio/homepage.css" not in content
    assert 'class="project-hero" id="projektstart"' in content
    assert 'class="project-index-link sr-only"' in content
    assert content.count('document.documentElement.classList.add("has-js")') == 1
    assert 'class="motion-heading"' in content
    assert 'class="intro-grid"' in content
    assert 'class="project-summary"' in content
    assert 'class="project-meta__facts"' in content
    assert 'class="project-meta__services"' in content
    assert '<aside class="project-meta" aria-label="Projektdetails">' in content
    assert 'class="marker-list project-service-list"' in content
    assert 'class="block project-content"' in content
    assert 'class="media-placeholder hero-media"' in content
    assert 'class="gallery project-gallery" id="galerie"' in content
    assert 'class="block results on-dark project-results" id="ergebnisse"' in content
    assert 'class="block project-testimonial"' in content
    assert ">Mehrwert</p>" in content
    assert ">Kundenstimmen</p>" in content
    assert "Optionales Kundenstatement zum Projekt." in content
    assert 'id="other-projects-title">Weiterse\u00adhen.</h2>' in content
    assert 'class="block contact" id="kontakt"' in content
    assert "<text>tell me more</text>" in content
    assert (
        content.index('class="gallery project-gallery" id="galerie"')
        < content.index('class="block results on-dark project-results" id="ergebnisse"')
        < content.index('class="block project-testimonial"')
    )


def test_screen_reader_project_index_link_becomes_visible_on_keyboard_focus():
    stylesheet_path = finders.find("portfolio/portfolio.css")

    assert stylesheet_path is not None
    stylesheet = Path(stylesheet_path).read_text()
    assert ".project-index-link.sr-only:focus-visible" in stylesheet
    assert "position: fixed" in stylesheet
    assert "clip-path: none" in stylesheet


def test_project_contact_handwriting_uses_the_editable_homepage_annotation():
    index = make_portfolio_tree()
    index.contact_annotation = "eigene Notiz"
    index.save_revision().publish()
    project = add_project(index)

    response = project.serve(RequestFactory().get(project.url))
    response.render()

    assert "<text>eigene Notiz</text>" in response.content.decode()


def test_error_page_uses_the_approved_cover_and_shared_related_card_markup(client):
    index = make_portfolio_tree()
    add_project(index)
    add_project(index, title="Zweites Projekt")

    content = client.get("/portfolio/501/").content.decode()

    assert 'data-project="error"' in content
    assert "/static/portfolio/prototype/501.css" in content
    assert "/static/portfolio/prototype/motion.js" in content
    assert 'class="error-cover"' in content
    assert 'class="error-composition"' in content
    assert 'class="more-grid"' in content
    assert content.count('class="more-card related-project-card"') == 2
    assert 'class="pill error-home-link"' in content


def test_project_adapter_contains_only_wagtail_markup_and_measurement_bridges():
    css_path = finders.find("portfolio/project-wagtail.css")
    js_path = finders.find("portfolio/project-wagtail.js")
    canonical_css = finders.find("portfolio/prototype/projekte/projekt.css")
    error_css = finders.find("portfolio/prototype/501.css")

    assert css_path is not None
    assert js_path is not None
    assert canonical_css is not None
    assert error_css is not None
    css = Path(css_path).read_text()
    javascript = Path(js_path).read_text()
    canonical = Path(canonical_css).read_text()
    error = Path(error_css).read_text()
    pages = layer_body(css, "pages")

    assert ".project-hero-media" in css
    assert ".pagegrid__cols" in css
    related_title = declarations_for(css, {".more-projects .block-title"})
    assert related_title["-webkit-hyphens"] == "manual !important"
    assert related_title["hyphens"] == "manual !important"
    canonical_grids = declarations_for(
        canonical, {".case-row", ".result-grid", ".more-grid", ".footer-grid"}
    )
    canonical_card = declarations_for(canonical, {".more-card"})
    canonical_frame_cross = declarations_for(
        canonical, {".more-card .frame::before", ".more-card .frame::after"}
    )
    wagtail_image_frame = declarations_for(
        pages, {".related-project-card__frame.frame--image"}
    )
    error_grid = declarations_for(pages, {".error-projects .more-grid"})
    error_card = declarations_for(pages, {".error-projects .more-card"})
    no_js_grid = declarations_for(
        error, {"html:not(.has-js) .error-projects .more-grid"}
    )
    no_js_card = declarations_for(
        error, {"html:not(.has-js) .error-projects .more-card"}
    )

    assert canonical_grids["grid-template-columns"] == (
        "var(--project-grid-columns, repeat(4, 1fr))"
    )
    assert canonical_card["grid-column"] == (
        "var(--more-card-grid-column, span 2)"
    )
    assert canonical_frame_cross["content"] == (
        'var(--frame-placeholder-content, "")'
    )
    assert wagtail_image_frame["--frame-placeholder-content"] == "none"
    assert error_grid["--project-grid-columns"] == "repeat(2, minmax(0, 1fr))"
    assert error_card["--more-card-grid-column"] == "auto"
    assert no_js_grid["--project-grid-columns"] == (
        "repeat(auto-fit, minmax(min(100%, 18rem), 1fr))"
    )
    assert no_js_card["--more-card-grid-column"] == "auto"
    assert "result-grid-stacked" in javascript
    assert "document.body.innerHTML" not in javascript
