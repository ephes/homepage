from django.urls import path

from .views import admin_theme_css, error_501

app_name = "portfolio"

urlpatterns = [
    path("501/", error_501, name="error_501"),
    path("admin-theme.css", admin_theme_css, name="admin_theme_css"),
]
