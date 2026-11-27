"""
Test settings

- Used to run tests fast on the continuous integration server and locally
"""

from pathlib import Path

import cast_react

from .base import *  # noqa

_CAST_REACT_MANIFEST = Path(cast_react.__file__).parent / "static" / "cast_react" / "manifest.json"

# DEBUG
# ------------------------------------------------------------------------------
# Turn debug off so tests run faster
DEBUG = False
TEMPLATES[0]["OPTIONS"]["debug"] = False

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = env("DJANGO_SECRET_KEY", default="CHANGEME!!!")

# Mail settings
# ------------------------------------------------------------------------------
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025

# In-memory email backend stores messages in django.core.mail.outbox
# for unit testing purposes
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# CACHING
# ------------------------------------------------------------------------------
# Speed advantages of in-memory caching without having to run Memcached
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": ""}}

# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = "django.test.runner.DiscoverRunner"


# PASSWORD HASHING
# ------------------------------------------------------------------------------
# Use fast password hasher so tests run faster
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# TEMPLATE LOADERS
# ------------------------------------------------------------------------------
# Keep templates in memory so tests run faster
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    [
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    ],
]

# DJANGO VITE
# ------------------------------------------------------------------------------
# Configure Django Vite for tests to avoid errors
DJANGO_VITE = {
    "default": {"dev_mode": False, "manifest_path": "test-manifest.json"},
    "cast": {"dev_mode": False, "manifest_path": "test-manifest.json"},
    # Lets views that extend the cast-bootstrap5 base template render in tests
    # without a built manifest (dev mode only emits dev-server script tags).
    "cast-bootstrap5": {"dev_mode": True},
    "cast_react": {"dev_mode": False, "static_url_prefix": "cast_react/", "manifest_path": _CAST_REACT_MANIFEST},
}

# STORAGE
# ------------------------------------------------------------------------------
# Tests must never write to the S3 bucket. Keep all uploads in memory and use
# credentials that S3 rejects, so an accidental S3 access fails loudly.
STORAGES = {
    **STORAGES,
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "production": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
}
MEDIA_URL = "/media/"
AWS_ACCESS_KEY_ID = "test-invalid-access-key"
AWS_SECRET_ACCESS_KEY = "test-invalid-secret-key"
