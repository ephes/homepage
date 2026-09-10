"""Shared production static-file configuration."""

PRODUCTION_STATICFILES_BACKEND = "whitenoise.storage.CompressedManifestStaticFilesStorage"


def production_staticfiles_storage(storages):
    """Return a copy configured with the deployment's compressed backend."""

    return {
        **storages,
        "staticfiles": {
            **storages.get("staticfiles", {}),
            "BACKEND": PRODUCTION_STATICFILES_BACKEND,
        },
    }
