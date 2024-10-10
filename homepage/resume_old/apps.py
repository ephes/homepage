from django.apps import AppConfig


class ResumeConfig(AppConfig):
    name = "homepage.resume"
    verbose_name = "Resume stuff"


    def register_admin_for_plugins(self):
        from .admin import register_person_admin_after_plugins_are_registered
        register_person_admin_after_plugins_are_registered()

    def register_plugins(self):
        from .plugins import plugin_registry
        from .timelines import FreelanceTimelinePlugin, EmployedTimelinePlugin
        plugin_registry.register(FreelanceTimelinePlugin)
        plugin_registry.register(EmployedTimelinePlugin)
        print("Registering plugins")

    def ready(self):
        """Override this to put in:
        Users system checks
        Users signal registration
        """
        self.register_plugins()  # make sure the plugins are registered before the admin view is registered
        self.register_admin_for_plugins()  # register the admin view for the plugins after the plugins are registered
