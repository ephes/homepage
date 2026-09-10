from wagtail.contrib.settings.registry import register_setting

from .models import ErrorPageSettings, PortfolioSiteSettings

register_setting(ErrorPageSettings, icon="warning")
register_setting(PortfolioSiteSettings, icon="site")
