from django.urls import path

from . import views

app_name = "resume"
urlpatterns = [
    path("", views.index, name="index"),
    # path("cv/", views.cv, name="cv"),
    path("cv/<slug:slug>/", views.cv, name="cv"),
]
