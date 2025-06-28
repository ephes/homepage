"""
Micropub app configuration.
"""

from django.apps import AppConfig


class MicropubConfig(AppConfig):
    """Configuration for the micropub app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "homepage.micropub"
    verbose_name = "Micropub"
