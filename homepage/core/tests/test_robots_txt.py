import re

import pytest
from django.test import RequestFactory
from django.urls import resolve

URLCONFS = ["config.urls", "config.urls_portfolio"]


def disallows(urlconf: str, path: str) -> bool:
    """Match like RFC 9309 crawlers do (``*`` is a wildcard, rules are prefixes).

    ``urllib.robotparser`` treats ``*`` literally before Python 3.14, so the
    rules are matched here. robots.txt has one group and only Disallow rules.
    """
    view = resolve("/robots.txt", urlconf=urlconf).func
    response = view(RequestFactory().get("/robots.txt"))
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    group, *rules = response.content.decode().splitlines()
    assert group == "User-agent: *"
    assert all(rule.startswith("Disallow: /") and "$" not in rule for rule in rules)
    patterns = [rule.removeprefix("Disallow: ") for rule in rules]
    return any(re.match(".*".join(map(re.escape, pattern.split("*"))), path) for pattern in patterns)


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
    assert disallows(urlconf, path)


@pytest.mark.parametrize("urlconf", URLCONFS)
@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/blogs/ephes_blog/",
        "/blogs/ephes_blog/?page=2",
        "/blogs/ephes_blog/?page=2&utm_tag_facets=python",
        "/blogs/ephes_blog/?xcategory_facets=weeknotes",
        "/blogs/ephes_blog/weeknotes/",
        "/blogs/ephes_blog/feed/rss.xml",
    ],
)
def test_robots_txt_keeps_blogs_pagination_posts_and_feeds_crawlable(urlconf, path):
    assert not disallows(urlconf, path)
