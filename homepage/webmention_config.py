"""
Webmention configuration for django-indieweb integration
"""

from typing import Any
from urllib.parse import urlparse

from indieweb.interfaces import URLResolver


class CastURLResolver(URLResolver):
    """Resolve URLs to django-cast blog posts, blog overview pages, and personal pages"""

    def resolve(self, target_url: str) -> Any | None:
        """Resolve a URL to a content object (Post, Blog, or Page)."""
        try:
            from cast.models import Blog, Post
            from django.contrib.sites.models import Site

            parsed = urlparse(target_url)
            path = parsed.path

            # Verify domain matches current site
            current_site = Site.objects.get_current()
            expected_domain = (
                f"{current_site.domain}:{8000}" if current_site.domain == "localhost" else current_site.domain
            )

            if parsed.netloc != expected_domain:
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"Domain mismatch: {parsed.netloc} != {expected_domain}")
                return None

            # Extract parts from URL
            path_parts = [p for p in path.strip("/").split("/") if p]

            # Handle personal page (/jochen/)
            if len(path_parts) == 1 and path_parts[0] == "jochen":
                # Return a simple dictionary to represent the personal page
                return {"type": "personal_page", "url": target_url}

            # Handle blog URLs
            if len(path_parts) >= 2 and path_parts[0] == "blogs":
                blog_slug = path_parts[1]

                # Handle blog overview page (/blogs/{blog_slug}/)
                if len(path_parts) == 2:
                    blog = Blog.objects.filter(slug=blog_slug).first()
                    if blog:
                        return blog

                # Handle individual blog post (/blogs/{blog_slug}/{post_slug}/)
                elif len(path_parts) >= 3:
                    post_slug = path_parts[2]
                    post = Post.objects.filter(slug=post_slug).first()
                    if post:
                        return post

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error resolving URL {target_url}: {e}")

        return None

    def get_absolute_url(self, content_object: Any) -> str:
        """Get the absolute URL for a content object."""
        if hasattr(content_object, "get_full_url"):
            return content_object.get_full_url()
        elif hasattr(content_object, "get_absolute_url"):
            return content_object.get_absolute_url()
        return ""
