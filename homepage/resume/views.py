from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .cv import get_cv


def show_cv(request: HttpRequest) -> HttpResponse:
    cv = get_cv()
    context = {
        "resume": cv,
        "person": cv.person,
        "location": cv.location,
        "contact": cv.contact,
        "timelines": cv.timelines,
        "skills": cv.skills,
        "education": cv.education,
        "projects": cv.projects,
    }
    return render(request, "resume/plain.html", context=context)
