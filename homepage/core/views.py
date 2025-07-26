from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

User = get_user_model()


@require_GET
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon(request: HttpRequest) -> HttpResponse:
    file = (Path(settings.ROOT_DIR) / "homepage" / "static" / "images" / "favicon.png").open("rb")
    return FileResponse(file)


def home(request: HttpRequest) -> HttpResponse:
    """View for the homepage with user profiles."""
    try:
        jochen = User.objects.get(username="jochen")
    except User.DoesNotExist:
        jochen = None

    try:
        katharina = User.objects.get(username="katharina")
    except User.DoesNotExist:
        katharina = None

    context = {
        "jochen": jochen,
        "katharina": katharina,
        "cast_base_template": "cast/bootstrap5/base.html",
    }
    return render(request, "pages/home.html", context)


def jochen_profile(request: HttpRequest) -> HttpResponse:
    """View for Jochen's profile page with h-card."""
    user = User.objects.get(username="jochen")
    context = {
        "user": user,
        "cast_base_template": "cast/bootstrap5/base.html",  # Default template
    }
    return render(request, "pages/jochen.html", context)
