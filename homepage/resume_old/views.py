import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .cv import get_cv
from .forms import CVTokenForm
from .models import Person

logger = logging.getLogger(__name__)


def cv_old(request: HttpRequest) -> HttpResponse:
    form = CVTokenForm(request.GET)
    if not form.is_valid():
        # If the form is not valid, return the form with a 403 status code
        return render(request, "resume/cv_token.html", {"form": form}, status=403)
    logger.info("CV token form is valid for %s", form.cleaned_data["token"].receiver)
    cv_data = get_cv()
    context = {
        "resume": cv_data,
        "person": cv_data.person,
        "location": cv_data.location,
        "contact": cv_data.contact,
        "timelines": cv_data.timelines,
        "skills": cv_data.skills,
        "education": cv_data.education,
        "projects": cv_data.projects,
    }
    return render(request, "resume/cv_plain.html", context=context)


def cv(request: HttpRequest, slug: str) -> HttpResponse:
    form = CVTokenForm(request.GET)
    if not form.is_valid():
        # If the form is not valid, return the form with a 403 status code
        return render(request, "resume/cv_token.html", {"form": form}, status=403)
    logger.info("CV token form is valid for %s", form.cleaned_data["token"].receiver)
    person = get_obj<ect_or_404(Person, slug=slug)
    timelines = person.timelines.all().order_by("position")
    projects = person.projects.all().order_by("position")
    context = {
        "person": person,
        "timelines": timelines,
        "projects": projects,
    }
    return render(request, "resume/cv_plain.html", context=context)


def index(request: HttpRequest) -> HttpResponse:
    return render(request, "resume/index.html")
