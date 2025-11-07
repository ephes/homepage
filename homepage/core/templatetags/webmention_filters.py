"""Custom template filters for webmention presentation."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from django import template
from django.utils import timezone

register = template.Library()

# Keep likes/reposts ahead of conversational types for homepage display.
# Order rationale:
#   - Interactions first (like, repost) so quick reactions surface together
#   - Conversations later (reply, mention) for longer-form responses
MENTION_TYPE_ORDER: dict[str, int] = {
    "like": 0,
    "repost": 1,
    "reply": 2,
    "mention": 3,
}


def _timestamp_for_sorting(webmention: Any) -> datetime:
    """Return the datetime used for ordering (published fallback to created)."""
    published = getattr(webmention, "published", None)
    created = getattr(webmention, "created", None)
    return published or created or timezone.now()


@register.filter
def sort_webmentions_for_grouping(webmentions: Iterable[Any]) -> list[Any]:
    """
    Sort webmentions so regrouping by mention_type yields a single block per type.

    The data is first ordered newest-first so each block preserves reverse-chronological
    order, then stably sorted by mention type using the preferred ordering above.
    """
    sorted_mentions = list(webmentions)
    if not sorted_mentions:
        return sorted_mentions

    sorted_mentions.sort(key=_timestamp_for_sorting, reverse=True)
    sorted_mentions.sort(key=lambda wm: MENTION_TYPE_ORDER.get(getattr(wm, "mention_type", ""), len(MENTION_TYPE_ORDER)))
    return sorted_mentions
