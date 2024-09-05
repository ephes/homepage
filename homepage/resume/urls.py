from django.urls import path

from . import views

app_name = "resume"
urlpatterns = [
    path("cv/", views.show_cv, name="show_cv"),
]
