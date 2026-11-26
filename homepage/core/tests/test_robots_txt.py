from urllib.robotparser import RobotFileParser

import pytest
from django.test import RequestFactory
from django.urls import resolve

URLCONFS = ["config.urls", "config.urls_portfolio"]


def robots_for(urlconf):
    view = resolve("/robots.txt", urlconf=urlconf).func
    response = view(RequestFactory().get("/robots.txt"))
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    parser = RobotFileParser()
    parser.parse(response.content.decode().splitlines())
    return parser


@pytest.mark.parametrize("urlconf", URLCONFS)
@pytest.mark.parametrize(
    "path",
    [
        "/blogs/ephes_blog/?tag_facets=weeknotes",
        "/blogs/ephes_blog/?date_facets=2023-02&category_facets=weeknotes",
        "/blogs/ephes_blog/?page=2&tag_facets=python",
        "/admin/",
        "/cms/pages/",
    ],
)
def test_robots_txt_disallows_blog_filters_and_admin(urlconf, path):
    assert not robots_for(urlconf).can_fetch("PetalBot", f"https://wersdoerfer.de{path}")


@pytest.mark.parametrize("urlconf", URLCONFS)
@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/blogs/ephes_blog/",
        "/blogs/ephes_blog/?page=2",
        "/blogs/ephes_blog/weeknotes/",
        "/blogs/ephes_blog/feed/rss.xml",
    ],
)
def test_robots_txt_keeps_blogs_pagination_posts_and_feeds_crawlable(urlconf, path):
    assert robots_for(urlconf).can_fetch("PetalBot", f"https://wersdoerfer.de{path}")
