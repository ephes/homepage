from django.urls import path

from . import views

app_name = "resume"
urlpatterns = [
    path("resume", views.show_resume, name="show_resume"),
]
