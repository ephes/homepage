from django.urls import path

from .views import error_501

app_name = "portfolio"

urlpatterns = [
    path("501/", error_501, name="error_501"),
]
