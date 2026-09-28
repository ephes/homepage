from django.conf import settings


def test_blog_feed_keeps_only_newest_posts():
    # The complete blog feed was 5 MB raw; feed readers keep older entries.
    assert settings.CAST_BLOG_FEED_ITEM_LIMIT == 50
