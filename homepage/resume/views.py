from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .models import get_resume


def show_resume(request: HttpRequest) -> HttpResponse:
    resume = get_resume()
    context = {
        "resume": resume,
        "person": resume.person,
        "location": resume.location,
        "contact": resume.contact,
        "timelines": resume.timelines,
        "skills": resume.skills,
        "education": resume.education,
        "projects": resume.projects,
    }
    return render(request, "resume/plain.html", context=context)
