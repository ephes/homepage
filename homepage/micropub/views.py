"""
Views for local micropub posting interface.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from indieweb.models import Token

from .forms import MicropubPostForm

# Import handler after Token to avoid circular imports
from .handler import CastPostMicropubHandler


@login_required
def micropub_form_view(request):
    """Local form for creating micropub posts."""
    if request.method == "POST":
        form = MicropubPostForm(request.POST)
        if form.is_valid():
            # Convert form data to micropub properties
            properties = form.to_micropub_properties()

            # Create the post using the micropub handler
            handler = CastPostMicropubHandler()
            try:
                entry = handler.create_entry(properties, request.user)

                # Try to build absolute URL
                post_url = entry.url
                if not post_url.startswith("http"):
                    post_url = request.build_absolute_uri(post_url)

                messages.success(
                    request,
                    f'Post created successfully! <a href="{post_url}" class="alert-link">View post</a>',
                    extra_tags="safe",
                )

                # Log for debugging
                import logging

                logger = logging.getLogger(__name__)
                logger.info(f"Created post with URL: {entry.url}")
                logger.info(f"Absolute URL: {post_url}")

                # Redirect to create another post
                return redirect("micropub-form")
            except Exception as e:
                messages.error(request, f"Error creating post: {str(e)}")
    else:
        form = MicropubPostForm()

    # Get available blogs for display
    from cast.models import Blog

    blogs = Blog.objects.live()

    context = {
        "form": form,
        "micropub_endpoint": request.build_absolute_uri(reverse("indieweb:micropub")),
        "site_url": getattr(settings, "INDIEWEB_ME_URL", request.build_absolute_uri("/")),
        "blogs": blogs,
        "blog_count": blogs.count(),
    }

    return render(request, "micropub/form.html", context)


def _get_or_create_local_token(user):
    """Get or create a local token for the user."""
    # Try to find an existing token with 'post' scope
    me_url = getattr(settings, "INDIEWEB_ME_URL", "http://localhost:8000")
    client_id = "local-micropub-form"
    scope = "post"

    token = Token.objects.filter(owner=user, me=me_url, client_id=client_id, scope=scope).first()

    if not token:
        # Create a new token for local posting
        token = Token.objects.create(owner=user, me=me_url, client_id=client_id, scope=scope)

    return token


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

    # Format blocks for display
    preview_html = []
    for block_type, value in blocks:
        if block_type == "heading":
            preview_html.append(f"<h3>{value}</h3>")
        elif block_type == "paragraph":
            preview_html.append(value)
        elif block_type == "code":
            lang = value.get("language", "")
            code = value.get("code", "")
            preview_html.append(f'<pre><code class="language-{lang}">{code}</code></pre>')

    return render(
        request,
        "micropub/preview.html",
        {
            "preview_html": "\n".join(preview_html),
            "blocks": blocks,
        },
    )
