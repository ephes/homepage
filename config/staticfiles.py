"""Shared production static-file configuration."""

from pathlib import Path, PurePosixPath

from django.conf import settings
from django.contrib.staticfiles.finders import BaseFinder
from django.contrib.staticfiles.utils import matches_patterns
from django.core import checks
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage

PRODUCTION_STATICFILES_BACKEND = "whitenoise.storage.CompressedManifestStaticFilesStorage"

PROTOTYPE_RUNTIME_ASSETS = (
    "501.css",
    "handwriting-contact.js",
    "handwriting-glyphs.js",
    "homepage.js",
    "legal.css",
    "motion.css",
    "motion.js",
    "portfolio-startseite.css",
    "project-teasers.js",
    "projekte/projekt.css",
    "site-shell.js",
)


class PortfolioPrototypeFinder(BaseFinder):
    """Expose only the approved runtime subset of the canonical prototype."""

    prefix = "portfolio/prototype"

    @property
    def root(self):
        """Resolve ROOT_DIR lazily because Django caches finder instances."""

        return Path(settings.ROOT_DIR) / "docs" / "superpowers" / "prototypes"

    @property
    def storage(self):
        """Build storage from the active root so finder state cannot diverge."""

        storage = FileSystemStorage(location=self.root)
        storage.prefix = self.prefix
        return storage

    def _missing_assets(self):
        """Return the canonical runtime assets absent from the active root."""

        return tuple(
            relative_path
            for relative_path in PROTOTYPE_RUNTIME_ASSETS
            if not (self.root / relative_path).is_file()
        )

    @staticmethod
    def _is_ignored(relative_path, ignore_patterns):
        """Apply Django's component and relative-path ignore semantics."""

        patterns = ignore_patterns or ()
        path = PurePosixPath(relative_path)
        return any(
            matches_patterns(component, patterns) for component in path.parts
        ) or matches_patterns(relative_path, patterns)

    def check(self, **kwargs):
        return [
            checks.Warning(
                f"Canonical portfolio prototype asset is missing: {relative_path}",
                hint=(
                    "Restore docs/superpowers/prototypes before collectstatic; "
                    "production collection fails closed without these runtime files."
                ),
                id="portfolio.W001",
            )
            for relative_path in self._missing_assets()
        ]

    def find(self, path, find_all=False):
        prefix = f"{self.prefix}/"
        if not path.startswith(prefix):
            return []

        relative_path = path.removeprefix(prefix)
        if relative_path not in PROTOTYPE_RUNTIME_ASSETS:
            return []

        candidate = self.root / relative_path
        if not candidate.is_file():
            return []
        resolved = str(candidate)
        return [resolved] if find_all else resolved

    def list(self, ignore_patterns):
        missing_assets = self._missing_assets()
        if missing_assets:
            missing_list = ", ".join(missing_assets)
            raise ImproperlyConfigured(
                "Cannot collect the portfolio's canonical prototype assets; "
                f"the following runtime files are missing: {missing_list}"
            )

        storage = self.storage
        return [
            (relative_path, storage)
            for relative_path in PROTOTYPE_RUNTIME_ASSETS
            if not self._is_ignored(relative_path, ignore_patterns)
        ]


def production_staticfiles_storage(storages):
    """Return a copy configured with the deployment's compressed backend."""

    return {
        **storages,
        "staticfiles": {
            **storages.get("staticfiles", {}),
            "BACKEND": PRODUCTION_STATICFILES_BACKEND,
        },
    }
