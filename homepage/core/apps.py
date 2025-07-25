from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "homepage.core"
    verbose_name = "Just some management commands."

    def ready(self):
        """Override this to put in:
        Users system checks
        Users signal registration
        """
        # Import webmention integration to register signal handlers
        from . import webmention_integration  # noqa: F401
