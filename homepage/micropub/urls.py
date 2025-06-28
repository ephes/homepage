"""
URL patterns for the local micropub interface.
"""

from django.urls import path

from .views import micropub_form_view, micropub_preview_view

urlpatterns = [
    # Local form interface for creating micropub posts
    path("", micropub_form_view, name="micropub-form"),
    path("preview/", micropub_preview_view, name="micropub-preview"),
]
