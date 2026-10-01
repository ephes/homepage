from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import InMemoryStorage, default_storage, storages


def test_test_settings_never_use_s3_storage():
    for alias, config in settings.STORAGES.items():
        assert "S3" not in config["BACKEND"], f"storage {alias!r} must not use S3 in tests"


def test_uploads_stay_in_memory():
    name = default_storage.save("test-storage-check.txt", ContentFile(b"test"))
    try:
        assert isinstance(storages["default"], InMemoryStorage)
        assert default_storage.exists(name)
    finally:
        default_storage.delete(name)
