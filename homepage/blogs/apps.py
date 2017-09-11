from django.apps import AppConfig


class BlogsConfig(AppConfig):
    name = 'homepage.blogs'
    verbose_name = "Blogs"

    def ready(self):
        """Override this to put in:
            Users system checks
            Users signal registration
        """
        pass
