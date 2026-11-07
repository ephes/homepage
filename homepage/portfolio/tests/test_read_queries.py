"""Cold-cache budgets around the real project-card and shell templates."""

import pytest
from bs4 import BeautifulSoup
from cast.models import TemplateBaseDirectory
from django.core.cache import caches
from django.template.loader import render_to_string
from django.test import RequestFactory
from wagtail.images.models import Filter
from wagtail.models import PageViewRestriction, Site

from homepage.portfolio.models import ProjectPage
from homepage.portfolio.views import _portfolio_shell_context, error_501

from .test_pages import add_project, make_image, make_portfolio_tree

pytestmark = pytest.mark.django_db

CARD_FILTERS = (
    "fill-2100x900",
    "fill-700x300",
    "fill-1400x600",
    "fill-1440x960",
    "fill-480x320",
    "fill-960x640",
    "fill-1200x675",
    "fill-400x225",
    "fill-800x450",
    "fill-1260x540",
    "fill-420x180",
    "fill-840x360",
)


def prepare_projects(count):
    index = make_portfolio_tree()
    expected = []
    for number in range(count):
        project = add_project(index, title=f"Synthetic {number:02}")
        image = make_image(f"synthetic-{number}")
        # Synthetic existing derivatives: no large source files or external storage.
        image.width, image.height = 2400, 1600
        image.save()
        for spec in CARD_FILTERS:
            width, height = map(int, spec.removeprefix("fill-").split("x"))
            image.renditions.create(
                filter_spec=spec,
                file=image.file.name,
                width=width,
                height=height,
                focal_point_key=Filter(spec).get_cache_key(image),
            )
        image.renditions.create(filter_spec="width-16", file=image.file.name, width=16, height=16)
        project.teaser_image = image
        project.teaser_image_alt = f"Synthetic alt {number}"
        project.homepage_is_hero = True
        project.content = [("statement", {"text": "<p>" + "Large synthetic body. " * 1000 + "</p>"})]
        project.save_revision().publish()
        expected.append((project.title, project.url))
    for cache in caches.all():
        cache.clear()
    # URL generation uses a separate site-root cache; keep it outside the card budget.
    Site.get_site_root_paths()
    request = RequestFactory().get("/")
    site = Site.find_for_request(request)
    TemplateBaseDirectory.objects.get_or_create(site=site, defaults={"name": "bootstrap4"})
    return index, expected, request


@pytest.mark.parametrize("count", [1, 20])
@pytest.mark.parametrize(
    "template,hero,mobile_lead",
    [
        ("project_card", False, False),
        ("project_card", True, False),
        ("project_card", True, True),
        ("related_project_card", False, False),
    ],
)
def test_card_queries_are_batched(count, template, hero, mobile_lead, django_assert_num_queries):
    index, expected, request = prepare_projects(count)
    with django_assert_num_queries(4):
        projects = list(index.get_portfolio_projects())
        for project in projects:
            assert {r.filter_spec for r in project.teaser_image.prefetched_renditions} == set(CARD_FILTERS)
            project.homepage_is_hero = hero
        html = "".join(
            render_to_string(
                f"portfolio/components/{template}.html",
                {"project": project, "request": request, "mobile_lead": mobile_lead},
            )
            for project in projects
        )
    soup = BeautifulSoup(html, "html.parser")
    assert [(a.h3.get_text(), a["href"]) for a in soup.select("a")] == expected
    assert len(soup.select("img")) == count
    if template == "project_card":
        assert [img["alt"] for img in soup.select("img")] == [f"Synthetic alt {n}" for n in range(count)]
        assert "400w" in html if mobile_lead else "480w" in html
    else:
        assert "420w" in html


@pytest.mark.parametrize("count", [1, 20])
def test_shell_and_card_queries_omit_case_study_content(count, django_assert_num_queries):
    index, expected, request = prepare_projects(count)
    site = Site.find_for_request(request)
    with django_assert_num_queries(4) as queries:
        context = _portfolio_shell_context(site=site, portfolio_index=index)
    project_select = next(q["sql"] for q in queries if 'FROM "portfolio_projectpage"' in q["sql"])
    assert '"content"' not in project_select
    projects = context["portfolio_projects"]
    assert len(projects) == count
    assert all("content" in project.get_deferred_fields() for project in projects)
    with django_assert_num_queries(0):
        for template in ("components/site_header", "components/site_footer", "legal_page", "http_error"):
            render_to_string(f"portfolio/{template}.html", {**context, "request": request})
        assert [(p.title, p.get_url(request)) for p in projects] == expected
    with django_assert_num_queries(4) as card_queries:
        cards = list(index.get_portfolio_projects())
    assert all('"content"' not in q["sql"] for q in card_queries.captured_queries)
    # Exercise the production view, including its bounded featured-card query.
    with django_assert_num_queries(12):
        response = error_501(request)
    assert response.status_code == 501
    featured = BeautifulSoup(response.content, "html.parser").select(".related-project-card")
    assert [(a.h3.get_text(), a["href"]) for a in featured] == expected[:2]
    assert all("content" in card.get_deferred_fields() for card in cards)
    # The current case study is still complete, and neither drafts nor restricted
    # projects leak into menus/cards.
    current = ProjectPage.objects.get(pk=cards[0].pk)
    assert "Large synthetic body." in str(current.content)
    draft = add_project(index, title="Draft", publish=False)
    restricted = add_project(index, title="Restricted")
    PageViewRestriction.objects.create(page=restricted, restriction_type="login")
    for queryset in (index.get_portfolio_navigation_projects(), index.get_portfolio_projects()):
        assert {draft.pk, restricted.pk}.isdisjoint({p.pk for p in queryset})


def test_card_prefetch_still_creates_missing_small_source_renditions():
    index = make_portfolio_tree()
    project = add_project(index)
    project.teaser_image = make_image("small-source")
    project.teaser_image_alt = "Small synthetic source"
    project.save_revision().publish()
    request = RequestFactory().get("/")
    for template in ("project_card", "related_project_card"):
        card = index.get_portfolio_projects().get(pk=project.pk)
        html = render_to_string(f"portfolio/components/{template}.html", {"project": card, "request": request})
        img = BeautifulSoup(html, "html.parser").img
        assert img["width"] == "1"
        assert all(candidate.strip().endswith("1w") for candidate in img["srcset"].split(","))
        assert card.teaser_image.renditions.exists()
    project.teaser_image = None
    project.save_revision().publish()
    card = index.get_portfolio_projects().get(pk=project.pk)
    assert "<img" not in render_to_string("portfolio/components/project_card.html", {"project": card})
