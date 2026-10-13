"""django-resume JSON Resume theme settings."""

from pathlib import Path

from django.conf import settings
from django_resume.formats.json_resume import themes

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_theme_cache_is_the_directory_the_deploy_keeps():
    # ops-control excludes this directory from the rsync and fills it with
    # ``manage.py install_json_resume_catalog_themes``.
    assert Path(settings.DJANGO_RESUME_JSON_RESUME_THEME_DIR) == REPO_ROOT / ".django-resume-jsonresume-themes"
    assert themes._cache_path() == REPO_ROOT / ".django-resume-jsonresume-themes"


def test_owners_cannot_trigger_npm_installs():
    assert themes.catalog_theme_install_allowed() is False
    assert themes.dynamic_theme_install_allowed() is False
