from django.apps import AppConfig


class ResumeConfig(AppConfig):
    name = "homepage.resume"
    verbose_name = "Resume stuff"

    def ready(self):
        """Override this to put in:
        Users system checks
        Users signal registration
        """
        pass
