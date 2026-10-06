"""
Views for local micropub posting interface.
"""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .converters import ContentConverter
from .forms import MicropubPostForm
from .handler import (
    CastPostMicropubHandler,
    MicropubPermissionError,
    MicropubTargetError,
    get_default_blog_slug,
    publishable_blogs_for_user,
)

logger = logging.getLogger(__name__)


def _sanitize_preview_html(html: str) -> str:
    """Re-sanitize preview paragraph HTML with the converter's block allow-list."""
    return ContentConverter.sanitize_html(
        html, ContentConverter.BLOCK_ALLOWED_TAGS, ContentConverter.BLOCK_ALLOWED_ATTRIBUTES
    )


@login_required
def micropub_form_view(request):
    """Local form for creating micropub posts."""
    blogs = publishable_blogs_for_user(request.user)
    form_kwargs = {"blogs": blogs, "default_blog_slug": get_default_blog_slug()}

    if request.method == "POST":
        form = MicropubPostForm(request.POST, **form_kwargs)
        if form.is_valid():
            # Convert form data to micropub properties
            properties = form.to_micropub_properties()

            # Create the post using the micropub handler (which enforces page permissions)
            handler = CastPostMicropubHandler()
            try:
                entry = handler.create_entry(properties, request.user)
            except MicropubPermissionError:
                logger.warning("Micropub form: user %s may not publish into the selected blog", request.user.pk)
                messages.error(request, "You do not have permission to publish posts in the selected blog.")
            except MicropubTargetError:
                logger.warning("Micropub form: target blog could not be resolved", exc_info=True)
                messages.error(request, "The selected blog is not available.")
            except Exception:
                logger.exception("Micropub form: error creating post")
                messages.error(request, "Error creating post. Details have been logged.")
            else:
                # Try to build absolute URL
                post_url = entry.url
                if not post_url.startswith("http"):
                    post_url = request.build_absolute_uri(post_url)

                messages.success(
                    request,
                    format_html(
                        'Post created successfully! <a href="{}" class="alert-link">View post</a>',
                        post_url,
                    ),
                )
                logger.info(f"Created post with URL: {entry.url}")
                logger.info(f"Absolute URL: {post_url}")

                # Redirect to create another post
                return redirect("micropub-form")
    else:
        form = MicropubPostForm(**form_kwargs)

    context = {
        "form": form,
        "micropub_endpoint": request.build_absolute_uri(reverse("indieweb:micropub")),
        "site_url": getattr(settings, "INDIEWEB_ME_URL", request.build_absolute_uri("/")),
        "blogs": blogs,
        "blog_count": len(blogs),
    }

    return render(request, "micropub/form.html", context)


@login_required
def micropub_preview_view(request):
    """Preview how content will be converted."""
    content = request.POST.get("content", "")
    post_type = request.POST.get("post_type", "note")

    # Create a temporary handler to use the converter
    handler = CastPostMicropubHandler()

    # Create properties from the preview data
    properties = {"content": [content]}
    if post_type == "article" and request.POST.get("name"):
        properties["name"] = [request.POST.get("name")]

    # Convert content to blocks
    blocks = handler.converter.convert_content(content, properties)

    # Format blocks for display. Everything derived from POST data is sanitized or
    # escaped here, so the template does not need (and must not use) ``|safe``.
    preview_parts = []
    for block_type, value in blocks:
        if block_type == "paragraph":
            preview_parts.append(_sanitize_preview_html(value))
        elif block_type == "code":
            preview_parts.append(
                format_html(
                    '<pre><code class="language-{}">{}</code></pre>',
                    value.get("language", ""),
                    value.get("code", ""),
                )
            )

    return render(
        request,
        "micropub/preview.html",
        {
            "preview_html": mark_safe("\n".join(preview_parts)),  # nosec: parts are sanitized/escaped above
            "blocks": blocks,
        },
    )
