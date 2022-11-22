from django.apps import AppConfig


class FediConfig(AppConfig):
    name = "homepage.fedi"
    verbose_name = "Fediverse redirects etc."

    def ready(self):
        """Override this to put in:
        Users system checks
        Users signal registration
        """
        pass
