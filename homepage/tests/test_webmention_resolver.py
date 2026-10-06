"""
Database-backed tests for the Webmention target URL resolver.

The resolver must only return live, public pages and must scope post lookups to
the blog named in the URL, so same-slug posts in other blogs never match.
"""

import pytest
from cast.models import Blog, Post
from django.contrib.sites.models import Site
from wagtail.models import Locale, Page, PageViewRestriction
from wagtail.models import Site as WagtailSite

from homepage.webmention_config import CastURLResolver

pytestmark = pytest.mark.django_db

DOMAIN = "example.com"


def get_or_create_root():
    root = Page.get_first_root_node()
    if root is None:
        Locale.objects.get_or_create(language_code="en")
        root = Page.add_root(instance=Page(title="Root", slug="root"))
    return root


@pytest.fixture
def tree():
    """Two blogs sharing a post slug, plus draft and private pages."""
    site = Site.objects.get_current()
    site.domain = DOMAIN
    site.save()
    Site.objects.clear_cache()

    root = get_or_create_root()
    home = root.add_child(instance=Page(title="Home", slug="resolver-home"))
    WagtailSite.objects.all().delete()
    WagtailSite.objects.create(hostname=DOMAIN, port=443, root_page=home, is_default_site=True)

    def add_blog(slug, **kwargs):
        return home.add_child(instance=Blog(title=slug.title(), slug=slug, **kwargs))

    def add_post(blog, slug, **kwargs):
        return blog.add_child(instance=Post(title=slug.title(), slug=slug, **kwargs))

    alpha = add_blog("alpha")
    beta = add_blog("beta")
    draft_blog = add_blog("draft-blog", live=False)
    private_blog = add_blog("private-blog")
    PageViewRestriction.objects.create(page=private_blog, restriction_type="password", password="secret")

    pages = {
        "alpha": alpha,
        "beta": beta,
        "draft_blog": draft_blog,
        "private_blog": private_blog,
        "alpha_shared": add_post(alpha, "shared"),
        "beta_shared": add_post(beta, "shared"),
        "beta_only": add_post(beta, "only-in-beta"),
        "alpha_draft": add_post(alpha, "draft-post", live=False),
        "alpha_private": add_post(alpha, "private-post"),
        "draft_blog_post": add_post(draft_blog, "in-draft-blog"),
        "private_blog_post": add_post(private_blog, "in-private-blog"),
    }
    PageViewRestriction.objects.create(page=pages["alpha_private"], restriction_type="login")
    return pages


def resolve(path, domain=DOMAIN, scheme="https"):
    return CastURLResolver().resolve(f"{scheme}://{domain}{path}")


def test_colliding_post_slugs_resolve_within_their_own_blog(tree):
    assert resolve("/blogs/alpha/shared/") == tree["alpha_shared"]
    assert resolve("/blogs/beta/shared/") == tree["beta_shared"]


def test_post_from_another_blog_does_not_resolve(tree):
    assert resolve("/blogs/alpha/only-in-beta/") is None


def test_post_sub_route_resolves_to_post_of_that_blog(tree):
    assert resolve("/blogs/beta/shared/transcript/") == tree["beta_shared"]


def test_draft_post_does_not_resolve(tree):
    assert resolve("/blogs/alpha/draft-post/") is None


def test_private_post_does_not_resolve(tree):
    assert resolve("/blogs/alpha/private-post/") is None


def test_posts_below_draft_or_private_blog_do_not_resolve(tree):
    assert resolve("/blogs/draft-blog/in-draft-blog/") is None
    assert resolve("/blogs/private-blog/in-private-blog/") is None


def test_blog_overview_resolves_only_for_live_public_blog(tree):
    assert resolve("/blogs/alpha/") == tree["alpha"]
    assert resolve("/blogs/draft-blog/") is None
    assert resolve("/blogs/private-blog/") is None
    assert resolve("/blogs/unknown/") is None


def test_unknown_post_and_invalid_paths_do_not_resolve(tree):
    assert resolve("/blogs/alpha/missing/") is None
    assert resolve("/blogs/") is None
    assert resolve("/") is None
    assert resolve("/something/else/") is None
    assert CastURLResolver().resolve("not-a-url") is None


def test_wrong_domain_does_not_resolve(tree):
    assert resolve("/blogs/alpha/shared/", domain="wrongdomain.com") is None


def test_blog_outside_site_root_does_not_resolve(tree):
    """A blog with a matching slug elsewhere in the page tree is not served under /blogs/."""
    other_home = get_or_create_root().add_child(instance=Page(title="Other", slug="other-home"))
    elsewhere = other_home.add_child(instance=Blog(title="Elsewhere", slug="elsewhere"))
    elsewhere.add_child(instance=Post(title="Hidden", slug="hidden"))

    assert resolve("/blogs/elsewhere/") is None
    assert resolve("/blogs/elsewhere/hidden/") is None


def test_localhost_development_port(tree):
    site = Site.objects.get_current()
    site.domain = "localhost"
    site.save()
    Site.objects.clear_cache()

    assert resolve("/blogs/alpha/shared/", domain="localhost:8000", scheme="http") == tree["alpha_shared"]
    assert resolve("/blogs/alpha/shared/", domain="localhost", scheme="http") is None


def test_personal_page(tree):
    assert resolve("/jochen/") == {"type": "personal_page", "url": f"https://{DOMAIN}/jochen/"}


def test_percent_encoded_unicode_slugs_resolve(tree):
    post = tree["alpha"].add_child(instance=Post(title="Grüße", slug="grüße"))

    assert post.get_full_url().endswith("/blogs/alpha/gr%C3%BC%C3%9Fe/")
    assert resolve("/blogs/alpha/gr%C3%BC%C3%9Fe/") == post


def test_no_matching_wagtail_site_does_not_resolve(tree):
    WagtailSite.objects.update(hostname="other.example", is_default_site=False)

    assert resolve("/blogs/alpha/shared/") is None
