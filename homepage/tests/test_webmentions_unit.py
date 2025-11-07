"""
Unit tests for webmentions functionality
"""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils import timezone

from homepage.core.templatetags import webmention_filters
from homepage.webmention_config import CastURLResolver


class WebmentionURLResolverTest(TestCase):
    """Unit tests for the CastURLResolver"""

    def setUp(self):
        self.resolver = CastURLResolver()
        self.factory = RequestFactory()

    @patch("django.contrib.sites.models.Site.objects.get_current")
    @patch("cast.models.Post.objects.filter")
    def test_resolve_valid_url(self, mock_post_filter, mock_get_current):
        """Test resolving a valid blog post URL"""
        # Mock the current site
        mock_site = Mock()
        mock_site.domain = "localhost"
        mock_get_current.return_value = mock_site

        # Mock a post
        mock_post = Mock()
        mock_post.slug = "test-post"
        mock_post_filter.return_value.first.return_value = mock_post

        # Test URL resolution
        result = self.resolver.resolve("http://localhost:8000/blogs/test-blog/test-post/")

        self.assertEqual(result, mock_post)
        mock_post_filter.assert_called_once_with(slug="test-post")

    @patch("django.contrib.sites.models.Site.objects.get_current")
    def test_resolve_invalid_domain(self, mock_get_current):
        """Test that URLs with wrong domain return None"""
        # Mock the current site
        mock_site = Mock()
        mock_site.domain = "localhost"
        mock_get_current.return_value = mock_site

        # Test with wrong domain
        result = self.resolver.resolve("http://wrongdomain.com/blogs/test-blog/test-post/")

        self.assertIsNone(result)

    @patch("django.contrib.sites.models.Site.objects.get_current")
    @patch("cast.models.Post.objects.filter")
    def test_resolve_non_existent_post(self, mock_post_filter, mock_get_current):
        """Test that non-existent posts return None"""
        # Mock the current site
        mock_site = Mock()
        mock_site.domain = "localhost"
        mock_get_current.return_value = mock_site

        # Mock no post found
        mock_post_filter.return_value.first.return_value = None

        # Test URL resolution
        result = self.resolver.resolve("http://localhost:8000/blogs/test-blog/non-existent/")

        self.assertIsNone(result)

    def test_resolve_invalid_url_format(self):
        """Test that invalid URL formats return None"""
        # Test various invalid formats
        invalid_urls = [
            "not-a-url",
            "http://localhost:8000/",  # No blog post path
            "http://localhost:8000/something/else/",  # Not a blog URL
            "http://localhost:8000/blogs/",  # Missing post slug
        ]

        for url in invalid_urls:
            with self.subTest(url=url):
                result = self.resolver.resolve(url)
                self.assertIsNone(result)

    @patch("django.contrib.sites.models.Site.objects.get_current")
    @patch("cast.models.Blog.objects.filter")
    def test_resolve_blog_overview_url(self, mock_blog_filter, mock_get_current):
        """Test resolving a blog overview URL"""
        # Mock the current site
        mock_site = Mock()
        mock_site.domain = "localhost"
        mock_get_current.return_value = mock_site

        # Mock a blog
        mock_blog = Mock()
        mock_blog.slug = "ephes-blog"
        mock_blog_filter.return_value.first.return_value = mock_blog

        # Test URL resolution for blog overview
        result = self.resolver.resolve("http://localhost:8000/blogs/ephes-blog/")

        self.assertEqual(result, mock_blog)
        mock_blog_filter.assert_called_once_with(slug="ephes-blog")

    @patch("django.contrib.sites.models.Site.objects.get_current")
    def test_resolve_personal_page_url(self, mock_get_current):
        """Test resolving the personal page URL"""
        # Mock the current site
        mock_site = Mock()
        mock_site.domain = "wersdoerfer.de"
        mock_get_current.return_value = mock_site

        # Test URL resolution for personal page
        result = self.resolver.resolve("https://wersdoerfer.de/jochen/")

        # Should return a dictionary representing the personal page
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["type"], "personal_page")
        self.assertEqual(result["url"], "https://wersdoerfer.de/jochen/")

    def test_get_absolute_url_with_full_url_method(self):
        """Test getting absolute URL when object has get_full_url method"""
        mock_object = Mock()
        mock_object.get_full_url.return_value = "http://example.com/post/"

        result = self.resolver.get_absolute_url(mock_object)

        self.assertEqual(result, "http://example.com/post/")
        mock_object.get_full_url.assert_called_once()

    def test_get_absolute_url_with_absolute_url_method(self):
        """Test getting absolute URL when object only has get_absolute_url method"""
        mock_object = Mock(spec=["get_absolute_url"])
        mock_object.get_absolute_url.return_value = "/post/"

        result = self.resolver.get_absolute_url(mock_object)

        self.assertEqual(result, "/post/")
        mock_object.get_absolute_url.assert_called_once()

    def test_get_absolute_url_no_methods(self):
        """Test getting absolute URL when object has no URL methods"""
        mock_object = Mock(spec=[])

        result = self.resolver.get_absolute_url(mock_object)

        self.assertEqual(result, "")


class WebmentionSettingsTest(TestCase):
    """Test that webmention settings are properly configured"""

    def test_url_resolver_setting(self):
        """Test that URL resolver is configured"""
        from django.conf import settings

        self.assertTrue(hasattr(settings, "INDIEWEB_URL_RESOLVER"))
        self.assertEqual(settings.INDIEWEB_URL_RESOLVER, "homepage.webmention_config.CastURLResolver")

    def test_spam_checker_setting(self):
        """Test that spam checker is configured"""
        from django.conf import settings

        self.assertTrue(hasattr(settings, "INDIEWEB_SPAM_CHECKER"))
        self.assertEqual(settings.INDIEWEB_SPAM_CHECKER, "indieweb.interfaces.NoOpSpamChecker")


class WebmentionTemplateFilterTests(SimpleTestCase):
    """Tests for the template filter that sorts webmentions before regrouping."""

    def test_sort_webmentions_for_grouping_orders_types_and_dates(self):
        """Likes/reposts appear first, preserving newest-first order per type."""
        now = timezone.now()
        earlier = now - timedelta(days=1)
        much_earlier = now - timedelta(days=2)

        webmentions = [
            SimpleNamespace(mention_type="reply", published=earlier, created=earlier),
            SimpleNamespace(mention_type="like", published=much_earlier, created=much_earlier),
            SimpleNamespace(mention_type="repost", published=now, created=now),
            SimpleNamespace(mention_type="like", published=now, created=now),
            SimpleNamespace(mention_type="mention", published=earlier, created=earlier),
        ]

        sorted_mentions = webmention_filters.sort_webmentions_for_grouping(webmentions)

        self.assertEqual(
            [wm.mention_type for wm in sorted_mentions],
            ["like", "like", "repost", "reply", "mention"],
        )
        # Likes should remain newest-first within their group
        like_dates = [wm.published for wm in sorted_mentions if wm.mention_type == "like"]
        self.assertGreaterEqual(like_dates[0], like_dates[1])

    def test_sort_webmentions_handles_missing_published(self):
        """Filter falls back to created timestamps when published is missing."""
        now = timezone.now()
        later = now + timedelta(hours=1)

        webmentions = [
            SimpleNamespace(mention_type="repost", published=None, created=now),
            SimpleNamespace(mention_type="repost", published=None, created=later),
        ]

        sorted_mentions = webmention_filters.sort_webmentions_for_grouping(webmentions)

        self.assertEqual([wm.created for wm in sorted_mentions], [later, now])

    def test_sort_webmentions_empty_list(self):
        """Empty input returns empty output."""
        self.assertEqual(webmention_filters.sort_webmentions_for_grouping([]), [])

    def test_sort_webmentions_unknown_type(self):
        """Unknown mention types are pushed to the end."""
        now = timezone.now()
        webmentions = [
            SimpleNamespace(mention_type="unknown", published=now, created=now),
            SimpleNamespace(mention_type="like", published=now, created=now),
        ]

        sorted_mentions = webmention_filters.sort_webmentions_for_grouping(webmentions)

        self.assertEqual(sorted_mentions[0].mention_type, "like")
        self.assertEqual(sorted_mentions[1].mention_type, "unknown")
