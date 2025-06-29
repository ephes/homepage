"""
Micropub handler for django-cast integration.

This module provides a Micropub handler that creates django-cast Post objects
from micropub requests, enabling IndieWeb publishing to your blog.
"""

import logging
from datetime import datetime
from typing import Any

from cast.models import Blog, Post
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify
from indieweb.handlers import MicropubContentHandler, MicropubEntry
from wagtail.blocks import StreamValue
from wagtail.log_actions import log as wagtail_log
from wagtail.models import PageLogEntry

from .converters import ContentConverter

logger = logging.getLogger(__name__)
User = get_user_model()


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
        # Extract basic properties
        title = self._get_title(properties)
        content = self._get_content(properties)
        published = self._get_published_date(properties)
        categories = properties.get("category", [])

        # Debug logging for properties
        logger.info(f"Received properties: {properties}")
        logger.info(f"Categories/tags: {categories}")

        # Get the first blog as parent (you might want to make this configurable)
        blog = self._get_default_blog()
        if not blog:
            raise ValueError("No blog found to create post in")

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
        try:
            blog.add_child(instance=post)
        except Exception as e:
            logger.error(f"Error adding post as child of blog: {e}")
            logger.error(f"Post data: title={title}, slug={post.slug}")
            raise

        # Create a revision with the user
        revision = post.save_revision(user=user)

        # Publish the revision
        post.live = True
        post.has_unpublished_changes = False
        post.first_published_at = post.first_published_at or timezone.now()
        post.last_published_at = timezone.now()
        post.latest_revision = revision
        post.latest_revision_created_at = revision.created_at
        post.live_revision = revision
        post.save()

        # Create PageLogEntry to make the post appear in "Your most recent edits"
        # Using Wagtail's proper log function ensures correct metadata
        try:
            # Log creation
            wagtail_log(instance=post, action="wagtail.create", user=user, data={})

            # Log edit (this is what shows in "Your most recent edits")
            wagtail_log(instance=post, action="wagtail.edit", user=user, data={})

            # Log publish since we're publishing immediately
            wagtail_log(instance=post, action="wagtail.publish", user=user, data={})

            logger.info("Created log entries for post")

            # Debug: verify entries were created
            entries = PageLogEntry.objects.filter(page=post, user=user).order_by("-timestamp")
            logger.debug(f"Log entries for post {post.id}: {[(e.action, e.timestamp) for e in entries]}")
        except Exception as e:
            logger.warning(f"Could not create log entries: {e}")
            # Don't fail the whole request if log entry fails

        # Handle tags/categories after publishing
        if categories:
            logger.info(f"Adding tags to post {post.id}: {categories}")
            try:
                post.tags.add(*categories)
                logger.info(
                    "Tags added successfully. Post now has tags: "
                    f"{list(post.tags.all().values_list('name', flat=True))}"
                )
                # Create another revision to track the tag addition
                new_revision = post.save_revision(user=user)
                post.latest_revision = new_revision
                post.latest_revision_created_at = new_revision.created_at
                post.save()
            except Exception as e:
                logger.error(f"Error adding tags: {e}")
        else:
            logger.info("No categories/tags to add")

        # Handle photos if present
        photo_urls = properties.get("photo", [])
        if photo_urls:
            # For now, we'll add photo URLs to the content
            # In the future, you might want to download and create Image objects
            logger.info(f"Photo URLs received: {photo_urls}")
            # TODO: Implement photo handling

        # Get the URL - need to refresh from DB to get the correct URL
        post.refresh_from_db()

        # For local development, just return the path instead of full URL
        # The view will handle making it absolute with the correct domain
        post_path = post.get_url()

        logger.info(f"Created post '{title}' with slug '{post.slug}'")
        logger.info(f"Post path: {post_path}")
        logger.info(f"Parent blog: {post.get_parent()}")

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
                logger.warning(f"Could not parse published date: {published[0]}")

        return timezone.now()

    def _get_default_blog(self) -> Blog | None:
        """Get the default blog to post to."""
        # Try to get ephes_blog first
        try:
            blog = Blog.objects.live().filter(slug="ephes_blog").first()
            if blog:
                logger.info(f"Using blog: {blog.title} (id: {blog.id}, slug: {blog.slug})")
                return blog

            # Fallback to first available blog if ephes_blog not found
            blog = Blog.objects.live().first()
            if blog:
                logger.warning(f"Blog 'ephes_blog' not found, using: {blog.title} (slug: {blog.slug})")
                return blog

            return None
        except Blog.DoesNotExist:
            return None

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
        # Parse the URL to find the post
        # This is a simplified implementation
        try:
            # Try to find post by URL path
            from django.urls import resolve

            match = resolve(url)
            if "pk" in match.kwargs:
                post = Post.objects.get(pk=match.kwargs["pk"])
                if post.owner == user or user.is_superuser:
                    return MicropubEntry(url=post.get_full_url(), properties=self._post_to_properties(post))
        except Exception as e:
            logger.error(f"Error retrieving post: {e}")

        return None

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

    def update_entry(self, url: str, updates: dict[str, Any], user: User) -> MicropubEntry | None:
        """Update an existing post (not implemented yet)."""
        # TODO: Implement post updates
        logger.warning("Post updates not yet implemented")
        return None

    def delete_entry(self, url: str, user: User) -> bool:
        """Delete a post (not implemented yet)."""
        # TODO: Implement post deletion
        logger.warning("Post deletion not yet implemented")
        return False

    def undelete_entry(self, url: str, user: User) -> MicropubEntry | None:
        """Undelete a post (not implemented yet)."""
        # TODO: Implement post undeletion
        logger.warning("Post undeletion not yet implemented")
        return None

    def get_config(self, user: User) -> dict[str, Any]:
        """
        Return micropub configuration.

        This tells micropub clients what features are supported.
        """
        return {
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
