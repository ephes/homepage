import pytest


@pytest.fixture(autouse=True)
def local_media_storage(settings, tmp_path):
    """Keep test uploads out of the configured S3 bucket."""

    settings.STORAGES = {
        **settings.STORAGES,
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(tmp_path / "media")},
        },
    }
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.MEDIA_URL = "/media/"
