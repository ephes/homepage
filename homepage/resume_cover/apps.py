from django.apps import AppConfig


class ResumeCoverConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "homepage.resume_cover"

    def ready(self) -> None:
        # Re-register the cover plugin under its existing name; the registry
        # overrides by name. Must load after "django_resume" (it lives in
        # LOCAL_APPS, which is concatenated after THIRD_PARTY_APPS).
        from django_resume.plugins import plugin_registry

        from .plugin import EditorialCoverPlugin

        plugin_registry.register(EditorialCoverPlugin)
