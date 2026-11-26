from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods

User = get_user_model()


@require_http_methods(["GET", "HEAD"])
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon(request: HttpRequest) -> HttpResponse:
    file = (Path(settings.ROOT_DIR) / "homepage" / "static" / "images" / "favicon.png").open("rb")
    if request.method == "HEAD":
        with file:
            return HttpResponse(headers=FileResponse(file).headers)
    return FileResponse(file)


@require_http_methods(["GET", "HEAD"])
@cache_control(max_age=60 * 60 * 24, public=True)  # one day
def robots_txt(request: HttpRequest) -> HttpResponse:
    content = "\n".join(
        [
            "User-agent: *",
            "Disallow: /admin/",
            "Disallow: /cms/",
            # Every combination of the django-cast blog index filters is its
            # own URL, and crawlers walk them all. Match each filter parameter
            # at a query parameter boundary (first or later parameter), so
            # look-alikes such as utm_tag_facets stay crawlable.
            "Disallow: /*?date_facets=",
            "Disallow: /*?*&date_facets=",
            "Disallow: /*?tag_facets=",
            "Disallow: /*?*&tag_facets=",
            "Disallow: /*?category_facets=",
            "Disallow: /*?*&category_facets=",
        ]
    )
    return HttpResponse(f"{content}\n", content_type="text/plain; charset=utf-8")


def home(request: HttpRequest) -> HttpResponse:
    """View for the homepage with user profiles."""
    profiles = User.objects.in_bulk(["jochen", "katharina"], field_name="username")
    context = {
        "jochen": profiles.get("jochen"),
        "katharina": profiles.get("katharina"),
        "cast_base_template": "cast/bootstrap5/base.html",
    }
    return render(request, "pages/home.html", context)


def jochen_profile(request: HttpRequest) -> HttpResponse:
    """View for Jochen's profile page with h-card."""
    user = get_object_or_404(User, username="jochen")
    context = {
        "user": user,
        "cast_base_template": "cast/bootstrap5/base.html",  # Default template
    }
    return render(request, "pages/jochen.html", context)
