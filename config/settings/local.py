"""
Local settings

- Run in Debug mode

- Use console backend for emails

- Add Django Debug Toolbar
- Add django-extensions as app
"""

from .base import *  # noqa

# DEBUG
# ------------------------------------------------------------------------------
DEBUG = env.bool("DJANGO_DEBUG", default=True)
TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env("DJANGO_SECRET_KEY", default="4O#eX5fk:<k{G6R~<[g9WblV4*<HjVHFyHm.$HQkq~/#x8`CW+")

# Mail settings
# ------------------------------------------------------------------------------

EMAIL_PORT = 1025

EMAIL_HOST = "localhost"
EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")


# CACHING
# ------------------------------------------------------------------------------
# CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": ""}}
# CACHES = {
#     "default": {
#         "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
#         "LOCATION": "/var/tmp/django_cache",
#         "TIMEOUT": 600,
#         "OPTIONS": {"MAX_ENTRIES": 10000},
#     }
# }
# CACHE_MIDDLEWARE_ALIAS = "default"
# CACHE_MIDDLEWARE_SECONDS = 600
# CACHE_MIDDLEWARE_KEY_PREFIX = "homepage"


# django-debug-toolbar
# ------------------------------------------------------------------------------
# MIDDLEWARE += [
#     "debug_toolbar.middleware.DebugToolbarMiddleware",
# ]
# INSTALLED_APPS += [
#     "debug_toolbar",
# ]
INTERNAL_IPS = [
    "127.0.0.1",
    "10.0.2.2",
]


import os
import socket

DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": [
        "debug_toolbar.panels.redirects.RedirectsPanel",
    ],
    "SHOW_TEMPLATE_CONTEXT": True,
}

# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Your local stuff: Below this line define 3rd party library settings
# ------------------------------------------------------------------------------

# logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
        "homepage": {
            "handlers": [
                "console",
            ],
            "propagate": True,
            "level": "DEBUG",
        },
        "cast": {
            "handlers": [
                "console",
            ],
            "propagate": True,
            "level": "DEBUG",
        },
        "indieweb": {
            "handlers": [
                "console",
            ],
            "propagate": True,
            "level": "DEBUG",
        },
    },
}

# SITE CONFIGURATION
# ------------------------------------------------------------------------------
# Hosts/domain names that are valid for this site
# See https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=[
        "*",
    ],
)
# END SITE CONFIGURATION

# Django Vite
DJANGO_VITE_ASSETS_PATH = "need to be set but doesn't matter"

DJANGO_VITE = {
    "cast_vue": {
        "dev_mode": True,
    },
    "cast-bootstrap5": {
        "dev_mode": True,
        "dev_server_port": 5174,
    },
    "cast": {
        "dev_mode": True,
    },
}

# post data
CAST_USE_POST_DATA = True

# Override INDIEWEB_ME_URL for local development
INDIEWEB_ME_URL = env("INDIEWEB_ME_URL", default="http://localhost:8000")
