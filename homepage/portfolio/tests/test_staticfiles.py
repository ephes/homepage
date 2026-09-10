import gzip
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import call_command
from django.test import override_settings
from whitenoise.compress import brotli_installed

from config.staticfiles import PRODUCTION_STATICFILES_BACKEND, production_staticfiles_storage


def test_production_static_storage_collects_gzip_and_brotli(tmp_path):
    """Exercise the production static pipeline without touching project assets."""
    assert brotli_installed, (
        "WhiteNoise cannot create Brotli assets: install the project's "
        "whitenoise[brotli] dependency in this environment."
    )

    import brotli

    source_root = tmp_path / "source"
    static_root = tmp_path / "collected"
    asset_name = "portfolio/compression-fixture.js"
    source_asset = source_root / asset_name
    source_asset.parent.mkdir(parents=True)
    source_asset.write_bytes(b"const portfolioEnhancement = 'progressive';\n" * 1024)

    storages = production_staticfiles_storage(settings.STORAGES)
    assert storages["staticfiles"]["BACKEND"] == PRODUCTION_STATICFILES_BACKEND
    with override_settings(
        STATIC_ROOT=static_root,
        STATIC_URL="/static/",
        STATICFILES_DIRS=[source_root],
        STATICFILES_FINDERS=["django.contrib.staticfiles.finders.FileSystemFinder"],
        STORAGES=storages,
    ):
        call_command("collectstatic", interactive=False, verbosity=0)

        collected_name = staticfiles_storage.stored_name(asset_name)
        collected_asset = static_root / collected_name
        original = collected_asset.read_bytes()
        gzip_asset = collected_asset.with_name(f"{collected_asset.name}.gz")
        brotli_asset = collected_asset.with_name(f"{collected_asset.name}.br")

        assert collected_name != asset_name
        assert gzip_asset.is_file()
        assert brotli_asset.is_file()
        assert gzip.decompress(gzip_asset.read_bytes()) == original
        assert brotli.decompress(brotli_asset.read_bytes()) == original
