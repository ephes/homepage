"""
Unit tests for webmentions functionality
"""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from homepage.core.templatetags import webmention_filters
from homepage.webmention_config import CastURLResolver


class WebmentionURLResolverTest(SimpleTestCase):
    """Unit tests for CastURLResolver.get_absolute_url.

    URL resolution is covered by the database-backed tests in test_webmention_resolver.py.
    """

    def setUp(self):
        self.resolver = CastURLResolver()

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
