from wagtail.contrib.settings.registry import register_setting

from .models import ErrorPageSettings

register_setting(ErrorPageSettings, icon="warning")
