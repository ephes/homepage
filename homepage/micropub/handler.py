"""
Micropub handler for django-cast integration.

This module provides a Micropub handler that creates django-cast Post objects
from micropub requests, enabling IndieWeb publishing to your blog.
"""

import logging
from collections import Counter
from datetime import datetime
from typing import Any

from cast.models import Blog, Post
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from indieweb.handlers import MicropubContentHandler, MicropubEntry
from wagtail.blocks import StreamValue
from wagtail.log_actions import log as wagtail_log

from homepage.core.page_lookup import find_page_for_url

from .converters import ContentConverter
from .validation import validate_category, validate_title

logger = logging.getLogger(__name__)
User = get_user_model()

# Micropub property a client uses to choose the target blog (Micropub channels
# extension). Its value is a blog slug as advertised by ``q=channel``.
TARGET_BLOG_PROPERTY = "mp-channel"
DEFAULT_MICROPUB_BLOG_SLUG = "ephes_blog"

# Property names that may be named in logs. Property *values* are never logged.
LOGGABLE_PROPERTY_NAMES = frozenset(
    {
        "name",
        "content",
        "summary",
        "published",
        "category",
        "photo",
        "location",
        "in-reply-to",
        "like-of",
        "repost-of",
        "bookmark-of",
        "syndication",
        "mp-slug",
        "mp-syndicate-to",
        TARGET_BLOG_PROPERTY,
    }
)


class MicropubTargetError(ValueError):
    """The requested target blog does not exist or cannot be determined.

    Subclasses ``ValueError`` so django-indieweb answers with ``invalid_request``.
    """


class MicropubContentError(ValueError):
    """A submitted property value cannot be turned into a post.

    Subclasses ``ValueError`` so django-indieweb answers with ``invalid_request``.
    Messages never quote the submitted value: django-indieweb logs them.
    """


class MicropubPermissionError(ValueError):
    """The user lacks the Wagtail page permissions needed to publish into the target blog.

    Subclasses ``ValueError`` so django-indieweb rejects the request instead of
    treating it as a server error.
    """


class MicropubInternalError(RuntimeError):
    """An unexpected failure while creating a post, with the details removed.

    Stands in for the original exception, whose message or traceback could quote
    the submission; it names the original exception class only.
    """


# Errors whose messages are fixed text written in this module.
SAFE_ERRORS = (MicropubTargetError, MicropubContentError, MicropubPermissionError)


def get_default_blog_slug() -> str:
    """Return the slug of the blog used when a request does not select one."""
    return getattr(settings, "MICROPUB_DEFAULT_BLOG_SLUG", DEFAULT_MICROPUB_BLOG_SLUG)


def user_can_publish_into(blog: Blog, user) -> bool:
    """Return whether ``user`` may create and immediately publish a Post below ``blog``."""
    if not Post.can_create_at(blog):
        return False
    permissions = blog.permissions_for_user(user)
    return permissions.can_add_subpage() and permissions.can_publish_subpage()


def publishable_blogs_for_user(user) -> list[Blog]:
    """Return the live blogs ``user`` may publish Micropub posts into.

    Blogs whose slug is shared by another live blog are left out: a slug is the
    channel identifier, and ``_get_target_blog`` rejects ambiguous slugs.
    """
    blogs = list(Blog.objects.live().order_by("path"))
    slug_counts = Counter(blog.slug for blog in blogs)
    return [blog for blog in blogs if slug_counts[blog.slug] == 1 and user_can_publish_into(blog, user)]


class CastPostMicropubHandler(MicropubContentHandler):
    """
    Micropub handler for creating django-cast Post objects.

    This handler integrates micropub requests with django-cast's Wagtail-based
    blogging system, converting h-entry properties to Post model fields and
    StreamField content.
    """

    def __init__(self):
        super().__init__()
        self.converter = ContentConverter()

    def create_entry(self, properties: dict[str, list[Any]], user: User) -> MicropubEntry:
        """
        Create a new blog post from micropub properties.

        Args:
            properties: Normalized micropub properties (values are always lists)
            user: The authenticated user making the request

        Returns:
            MicropubEntry with the created post's URL
        """
        # Operational facts only. Property values (content, categories, photo URLs,
        # titles and slugs derived from them) never go to the logs.
        logger.info(
            "Micropub create: properties=%s categories=%d photos=%d",
            self._loggable_property_names(properties),
            len(properties.get("category", [])),
            len(properties.get("photo", [])),
        )

        # django-indieweb logs the message of a ``ValueError`` and the traceback of
        # anything else. Exceptions raised below (by Wagtail, the database, the
        # converter, ...) can quote the submission, so only this module's own
        # errors, whose messages are fixed text, leave unchanged. Everything else
        # is replaced, outside the ``except`` block, by an error without message
        # details, cause or context.
        failure: Exception
        try:
            # Extract basic properties
            title = self._get_title(properties)
            try:
                validate_title(title)
            except ValidationError:
                raise MicropubContentError("Title is not valid") from None
            content = self._get_content(properties)
            published = self._get_published_date(properties)
            categories = self._get_categories(properties)

            with transaction.atomic():
                return self._create_post(properties, user, title, content, published, categories)
        except SAFE_ERRORS as error:
            logger.warning("Micropub create failed: %s", type(error).__name__)
            raise
        except ValueError as error:
            logger.warning("Micropub create failed: %s", type(error).__name__)
            failure = MicropubContentError("The request could not be processed")
        except Exception as error:
            logger.warning("Micropub create failed: %s", type(error).__name__)
            failure = MicropubInternalError(f"Micropub create failed ({type(error).__name__})")
        raise failure

    @staticmethod
    def _loggable_property_names(properties: dict[str, list[Any]]) -> str:
        """Return the known property names of a request plus a count of the others.

        Unknown names are client-chosen text, so only their number is reported.
        """
        known = sorted(name for name in properties if name in LOGGABLE_PROPERTY_NAMES)
        unknown = len(properties) - len(known)
        return ",".join(known) + (f" (+{unknown} other)" if unknown else "")

    def _get_categories(self, properties: dict[str, list[Any]]) -> list[str]:
        """Return the category names, rejecting values that cannot become tags."""
        categories = []
        for category in properties.get("category", []):
            if not isinstance(category, str):
                raise MicropubContentError("Categories must be given as text")
            if not category.strip():
                continue
            try:
                validate_category(category)
            except ValidationError:
                raise MicropubContentError("Category is not valid") from None
            categories.append(category)
        return categories

    def _create_post(
        self,
        properties: dict[str, list[Any]],
        user: User,
        title: str,
        content: str,
        published: datetime,
        categories: list[str],
    ) -> MicropubEntry:
        """Create and publish the post; runs inside a transaction so failures leave no partial post."""
        # Resolve the explicitly selected (or configured default) blog and make sure
        # the user may add and publish posts there before writing anything.
        blog = self._get_target_blog(properties, user)

        # Create the post as a draft first
        post = Post(
            title=title,
            slug=slugify(title),
            visible_date=published,
            owner=user,
            live=False,  # Start as draft
            has_unpublished_changes=True,
        )

        # Set the body content using StreamField
        post.body = self._create_streamfield_content(content, properties)

        # Add the post as a child of the blog
        blog.add_child(instance=post)

        # Body and categories are complete before the one and only revision is
        # saved, so the revision that goes live is the whole post. A failure here
        # (or anywhere below) rolls the transaction back: nothing is published.
        if categories:
            post.tags.add(*categories)
        revision = post.save_revision(user=user)

        # The "edited" entry makes the post show up in the Wagtail admin's "Your
        # most recent edits". Wagtail itself logs the creation (add_child above)
        # and the publication (publish() below).
        wagtail_log(instance=post, action="wagtail.edit", user=user, data={})

        # Publish through Wagtail's revision API, exactly like the CMS does: it
        # sets the live/first-published fields and the live revision, writes the
        # publish log entry and sends ``page_published`` once.
        try:
            revision.publish(user=user)
        except ValidationError:
            # Publication policy said no; answer as an invalid request, not a 500.
            raise MicropubContentError("The post cannot be published") from None

        # Get the URL - need to refresh from DB to get the correct URL
        post.refresh_from_db()

        # For local development, just return the path instead of full URL
        # The view will handle making it absolute with the correct domain
        post_path = post.get_url()

        logger.info("Micropub create: published post id=%s in blog id=%s", post.pk, blog.pk)

        return MicropubEntry(url=post_path, properties=properties)  # Return path, not full URL

    def _get_title(self, properties: dict[str, list[Any]]) -> str:
        """Extract title from properties or generate from content."""
        name = properties.get("name", [""])
        if name and name[0]:
            return str(name[0])

        # If no name, generate from content
        content = self._get_content(properties)
        if content:
            # Take first 50 characters of content as title
            title = content[:50]
            if len(content) > 50:
                title += "..."
            return title

        return "Untitled Post"

    def _get_content(self, properties: dict[str, list[Any]]) -> str:
        """Extract content from properties."""
        content = properties.get("content", [""])
        if content and content[0]:
            # Handle both plain text and HTML content
            content_value = content[0]
            if isinstance(content_value, dict):
                # Micropub JSON format with html/text keys
                return content_value.get("html", content_value.get("text", ""))
            return str(content_value)
        return ""

    def _get_published_date(self, properties: dict[str, list[Any]]) -> datetime:
        """Extract published date or use current time."""
        published = properties.get("published", [""])
        if published and published[0]:
            try:
                # Parse ISO format date
                return datetime.fromisoformat(str(published[0]).replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                logger.warning("Micropub create: unparseable published date, using the current time")

        return timezone.now()

    def _get_target_blog(self, properties: dict[str, list[Any]], user: User) -> Blog:
        """Return the blog the post should be created in, enforcing page permissions.

        The blog is chosen explicitly via the ``mp-channel`` property (a blog slug) or,
        when absent, the configured ``MICROPUB_DEFAULT_BLOG_SLUG``. There is no fallback
        to an arbitrary blog.

        Raises:
            MicropubTargetError: no unique live blog matches the selection
            MicropubPermissionError: the user may not add and publish posts there
        """
        requested = [value for value in properties.get(TARGET_BLOG_PROPERTY, []) if value]
        if len(requested) > 1:
            raise MicropubTargetError("Only one target blog may be selected")
        if requested:
            if not isinstance(requested[0], str):
                raise MicropubTargetError("Target blog must be given as a blog slug")
            slug = requested[0].strip()
        else:
            slug = get_default_blog_slug()
        if not slug:
            raise MicropubTargetError("No target blog selected")

        blogs = list(Blog.objects.live().filter(slug=slug)[:2])
        if len(blogs) != 1:
            # The slug is request data and this message is logged: keep it out.
            raise MicropubTargetError("No unique live blog matches the selected target")
        blog = blogs[0]

        if not user_can_publish_into(blog, user):
            raise MicropubPermissionError(f"User {user.pk} may not publish posts in blog {blog.pk}")

        return blog

    def _create_streamfield_content(self, content: str, properties: dict[str, list[Any]]) -> StreamValue:
        """
        Create StreamField content from micropub content.

        Converts plain text or HTML content into appropriate StreamField blocks.
        """
        # Use the content converter to process content
        blocks = self.converter.convert_content(content, properties)

        # Create StreamValue for the body field
        # Using 'overview' as the main content area
        return StreamValue(
            stream_block=Post.body.field.stream_block,
            stream_data=[("overview", blocks)],
        )

    def get_entry(self, url: str, user: User) -> MicropubEntry | None:
        """
        Retrieve an existing post by URL.

        Args:
            url: The URL of the post
            user: The authenticated user

        Returns:
            MicropubEntry if found and user has access, None otherwise
        """
        page = find_page_for_url(url)
        if not isinstance(page, Post):
            return None
        # Source queries hand out page content for editing, so require Wagtail edit
        # permission on the page itself rather than ownership or superuser status.
        if not page.permissions_for_user(user).can_edit():
            return None
        return MicropubEntry(url=page.get_full_url(), properties=self._post_to_properties(page))

    def _post_to_properties(self, post: Post) -> dict[str, list[Any]]:
        """Convert a Post object back to micropub properties."""
        properties = {
            "name": [post.title],
            "published": [post.visible_date.isoformat()],
            "category": list(post.tags.values_list("name", flat=True)),
        }

        # Extract content from StreamField
        content_parts = []
        for stream_block in post.body:
            if stream_block.block_type in ["overview", "detail"]:
                for block in stream_block.value:
                    if block.block_type == "paragraph":
                        content_parts.append(str(block.value))

        if content_parts:
            properties["content"] = ["".join(content_parts)]

        return properties

    # Update, delete and undelete are not supported. django-indieweb treats a handler that returns
    # normally as success (``delete`` answers 204, ``update``/``undelete`` read ``entry.url``), so these
    # must raise ``ValueError``; the endpoint then answers ``400 invalid_request`` and leaves the post as is.

    def update_entry(self, url: str, updates: dict[str, Any], user: User) -> MicropubEntry | None:
        """Reject post updates: they are not supported."""
        raise ValueError("Micropub update is not supported")

    def delete_entry(self, url: str, user: User) -> bool:
        """Reject post deletion: it is not supported."""
        raise ValueError("Micropub delete is not supported")

    def undelete_entry(self, url: str, user: User) -> MicropubEntry | None:
        """Reject post undeletion: it is not supported."""
        raise ValueError("Micropub undelete is not supported")

    def get_config(self, user: User) -> dict[str, Any]:
        """
        Return micropub configuration.

        This tells micropub clients what features are supported.
        """
        return {
            "channels": [{"uid": blog.slug, "name": blog.title} for blog in publishable_blogs_for_user(user)],
            "media-endpoint": None,  # TODO: Implement media endpoint
            "syndicate-to": [],  # TODO: Add syndication targets
            "post-types": [
                {
                    "type": "note",
                    "name": "Note",
                },
                {
                    "type": "article",
                    "name": "Article",
                },
                {
                    "type": "photo",
                    "name": "Photo",
                },
            ],
        }
