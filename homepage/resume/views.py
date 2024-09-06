from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .cv import get_cv


def cv(request: HttpRequest) -> HttpResponse:
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


def index(request: HttpRequest) -> HttpResponse:
    return render(request, "resume/index.html")
