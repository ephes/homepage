"""
Webmention configuration for django-indieweb integration
"""

from typing import Any
from urllib.parse import urlparse

from indieweb.interfaces import URLResolver

from homepage.core.page_lookup import get_wagtail_site, url_path_parts


class CastURLResolver(URLResolver):
    """Resolve URLs to django-cast blog posts, blog overview pages, and personal pages"""

    def resolve(self, target_url: str) -> Any | None:
        """Resolve a URL to a content object (Post, Blog, or Page)."""
        try:
            from cast.models import Blog, Post
            from django.contrib.sites.models import Site

            parsed = urlparse(target_url)

            # Verify domain matches current site. The local development server is
            # addressed as localhost:8000 while the Django site domain is "localhost".
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
            path_parts = url_path_parts(parsed)

            # Handle personal page (/jochen/)
            if len(path_parts) == 1 and path_parts[0] == "jochen":
                # Return a simple dictionary to represent the personal page
                return {"type": "personal_page", "url": target_url}

            # Handle blog URLs (/blogs/{blog_slug}/ and /blogs/{blog_slug}/{post_slug}/...).
            # Lookups are scoped through the page tree: the blog must be a live, public
            # child of the site's root page and the post a live, public child of that
            # blog. Drafts, private pages and same-slug posts in other blogs never match.
            if len(path_parts) >= 2 and path_parts[0] == "blogs":
                site = get_wagtail_site(parsed)
                if site is None:
                    return None
                blog = Blog.objects.live().public().child_of(site.root_page).filter(slug=path_parts[1]).first()
                if blog is None:
                    return None

                # Handle blog overview page (/blogs/{blog_slug}/)
                if len(path_parts) == 2:
                    return blog

                # Handle individual blog post (/blogs/{blog_slug}/{post_slug}/), including
                # sub-routes such as /blogs/{blog_slug}/{episode_slug}/transcript/
                return Post.objects.live().public().child_of(blog).filter(slug=path_parts[2]).first()

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
