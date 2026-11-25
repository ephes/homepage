"""
Webmention configuration for django-indieweb integration
"""

from typing import Any
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.urls import Resolver404, resolve
from indieweb.interfaces import URLResolver

from homepage.core.page_lookup import get_wagtail_site, url_path_parts
from homepage.portfolio.hosts import PORTFOLIO_URLCONF, is_portfolio_host


class CastURLResolver(URLResolver):
    """Resolve URLs to django-cast blog posts, blog overview pages, and personal pages"""

    def resolve(self, target_url: str) -> Any | None:
        """Resolve a URL to a content object (Post, Blog, or Page)."""
        try:
            from cast.models import Blog, Episode, Post
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
                urlconf = PORTFOLIO_URLCONF if is_portfolio_host(parsed.hostname) else settings.ROOT_URLCONF
                try:
                    route = resolve(unquote(parsed.path), urlconf=urlconf)
                except Resolver404:
                    return None
                is_page = route.url_name == "wagtail_serve" and len(path_parts) in (2, 3)
                is_episode_route = route.view_name in {"cast:episode-transcript", "cast:twitter-player"}
                if not (is_page or is_episode_route):
                    return None

                site = get_wagtail_site(parsed)
                if site is None:
                    return None
                blog = Blog.objects.live().public().child_of(site.root_page).filter(slug=path_parts[1]).first()
                if blog is None:
                    return None

                # Handle blog overview page (/blogs/{blog_slug}/)
                if len(path_parts) == 2:
                    return blog

                post = Post.objects.live().public().child_of(blog).filter(slug=path_parts[2]).first()
                if post is None or is_page:
                    return post

                # The registered Cast subroutes serve episodes only. The transcript
                # view also requires a Podlove transcript artifact.
                episode = (
                    Episode.objects.using(post._state.db)
                    .select_related("podcast_audio__transcript")
                    .filter(pk=post.pk)
                    .first()
                )
                if episode is None:
                    return None
                if route.view_name == "cast:episode-transcript":
                    transcript = episode.get_transcript_or_none()
                    if transcript is None or not transcript.podlove:
                        return None
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
