"""Custom template filters for webmention presentation."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from django import template

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


def _type_for_sorting(webmention: Any) -> tuple[int, str]:
    mention_type = getattr(webmention, "mention_type", "")
    return MENTION_TYPE_ORDER.get(mention_type, len(MENTION_TYPE_ORDER)), mention_type


def _timestamp_for_sorting(webmention: Any) -> tuple[bool, datetime | None]:
    """Rank dated mentions first when sorting newest first."""
    timestamp = getattr(webmention, "published", None) or getattr(webmention, "created", None)
    return timestamp is not None, timestamp


@register.filter
def sort_webmentions_for_grouping(webmentions: Iterable[Any]) -> list[Any]:
    """
    Sort webmentions so regrouping by mention_type yields a single block per type.

    The data is first ordered newest-first so each block preserves reverse-chronological
    order, with undated mentions last and ties in input order. A stable type sort
    then groups legacy types by their type key after the preferred types.
    """
    sorted_mentions = list(webmentions)
    if not sorted_mentions:
        return sorted_mentions

    sorted_mentions.sort(key=_timestamp_for_sorting, reverse=True)
    sorted_mentions.sort(key=_type_for_sorting)
    return sorted_mentions
