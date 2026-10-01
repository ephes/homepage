"""
Test settings

- Used to run tests fast on the continuous integration server and locally
"""

from .base import *  # noqa

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
