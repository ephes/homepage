import gzip
import inspect
import os
import re
import subprocess
import warnings
from pathlib import Path
from shutil import copyfile, which

import pytest
from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.checks import Warning
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import override_settings
from whitenoise.compress import brotli_installed

from config.staticfiles import (
    PRODUCTION_STATICFILES_BACKEND,
    PROTOTYPE_RUNTIME_ASSETS,
    PortfolioPrototypeFinder,
    production_staticfiles_storage,
)


WAGTAIL_PARITY_ADAPTERS = (
    "portfolio/admin.css",
    "portfolio/homepage.css",
    "portfolio/project-wagtail.css",
    "portfolio/project-wagtail.js",
)

PROTOTYPE_PARITY_ASSETS = tuple(
    f"{PortfolioPrototypeFinder.prefix}/{relative_path}"
    for relative_path in PROTOTYPE_RUNTIME_ASSETS
)

PROTOTYPE_STATIC_REFERENCE = re.compile(
    r"{%\s*(?:versioned_)?static\s+['\"]"
    r"(?P<path>portfolio/prototype/[^'\"]+)['\"]"
)


def _prototype_root(root_dir):
    return Path(root_dir) / "docs" / "superpowers" / "prototypes"


def test_canonical_prototype_assets_are_available_under_one_static_namespace():
    """Wagtail consumes the approved source files instead of copied derivatives."""

    prototype_root = Path(settings.ROOT_DIR) / "docs" / "superpowers" / "prototypes"

    for asset_name in PROTOTYPE_PARITY_ASSETS:
        source_path = finders.find(asset_name)

        assert source_path is not None
        assert Path(source_path).is_relative_to(prototype_root)


def test_prototype_finder_exposes_only_approved_runtime_assets():
    assert finders.find("portfolio/prototype/MEMORY.md") is None
    assert finders.find("portfolio/prototype/portfolio-startseite.html") is None
    assert finders.find("portfolio/prototype/fonts.css") is None


def test_prototype_finder_uses_only_the_supported_find_signature():
    finder = PortfolioPrototypeFinder()
    signature = inspect.signature(PortfolioPrototypeFinder.find)

    assert list(signature.parameters) == ["self", "path", "find_all"]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert finder.find("portfolio/prototype/501.css", find_all=True) == [
            str(_prototype_root(settings.ROOT_DIR) / "501.css")
        ]
    with pytest.raises(TypeError, match="unexpected keyword argument 'all'"):
        finder.find("portfolio/prototype/501.css", all=True)


def test_templates_only_reference_approved_prototype_runtime_assets():
    """Every prototype static reference must be backed by the finder allowlist."""

    template_root = Path(settings.ROOT_DIR) / "homepage" / "portfolio" / "templates"
    references = {
        match.group("path").removeprefix(f"{PortfolioPrototypeFinder.prefix}/")
        for template_path in template_root.rglob("*.html")
        for match in PROTOTYPE_STATIC_REFERENCE.finditer(template_path.read_text())
    }

    assert references
    assert references <= set(PROTOTYPE_RUNTIME_ASSETS)


def _deployment_rules(repository_root):
    dockerignore = (repository_root / ".dockerignore").read_text()
    deploy_playbook = (repository_root / "deploy" / "deploy.yml").read_text()
    dockerignore_rules = [
        line.strip()
        for line in dockerignore.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    rsync_rules = re.findall(
        r'^\s*-\s+"(--(?:include|exclude)=[^"]+)"',
        deploy_playbook,
        flags=re.MULTILINE,
    )
    return dockerignore_rules, rsync_rules


def test_deployment_payloads_declare_canonical_prototype_includes_in_order():
    """Keep explicit Docker and rsync policy beside each production path."""

    repository_root = Path(settings.ROOT_DIR)
    dockerignore_rules, rsync_rules = _deployment_rules(repository_root)
    required_docker_includes = (
        "!/docs/",
        "!/docs/superpowers/",
        "!/docs/superpowers/prototypes/",
        "!/docs/superpowers/prototypes/**",
    )
    required_rsync_includes = (
        "--include=/docs/",
        "--include=/docs/superpowers/",
        "--include=/docs/superpowers/prototypes/",
        "--include=/docs/superpowers/prototypes/***",
    )

    assert all(rule in dockerignore_rules for rule in required_docker_includes)
    assert [
        dockerignore_rules.index(rule) for rule in required_docker_includes
    ] == sorted(dockerignore_rules.index(rule) for rule in required_docker_includes)
    assert all(rule in rsync_rules for rule in required_rsync_includes)
    assert [rsync_rules.index(rule) for rule in required_rsync_includes] == sorted(
        rsync_rules.index(rule) for rule in required_rsync_includes
    )


def test_rsync_deployment_filters_include_canonical_prototype_assets(tmp_path):
    """Exercise Ansible's rsync filters with rsync's own matcher."""

    rsync = which("rsync")
    if rsync is None:
        pytest.skip("rsync is not installed")

    repository_root = Path(settings.ROOT_DIR)
    _dockerignore_rules, rsync_rules = _deployment_rules(repository_root)
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    prototype_root = _prototype_root(source_root)
    destination_root.mkdir()

    for relative_path in PROTOTYPE_RUNTIME_ASSETS:
        asset = prototype_root / relative_path
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_text(f"canonical:{relative_path}")
    excluded_fixture = source_root / "not-in-runtime.txt"
    excluded_fixture.write_text("must stay excluded")

    result = subprocess.run(
        [
            rsync,
            "--recursive",
            "--dry-run",
            "--itemize-changes",
            "--out-format=%n",
            *rsync_rules,
            "--exclude=*",
            f"{source_root}/",
            f"{destination_root}/",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    transferred_paths = set(result.stdout.splitlines())

    for relative_path in PROTOTYPE_RUNTIME_ASSETS:
        assert f"docs/superpowers/prototypes/{relative_path}" in transferred_paths
    assert excluded_fixture.name not in transferred_paths


def test_docker_build_context_includes_canonical_prototype_assets(tmp_path):
    """Build real source bytes with the shipped .dockerignore verbatim."""

    docker = which("docker")
    if docker is None:
        pytest.skip("Docker CLI is not installed")

    server = subprocess.run(
        [docker, "info", "--format", "{{.ServerVersion}}"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if server.returncode:
        pytest.skip(f"Docker daemon is unavailable: {server.stderr.strip()}")

    repository_root = Path(settings.ROOT_DIR)
    source_root = tmp_path / "docker-source"
    output_root = tmp_path / "docker-context"
    source_root.mkdir()
    copyfile(repository_root / ".dockerignore", source_root / ".dockerignore")

    dockerfile = ["FROM scratch"]
    for relative_path in PROTOTYPE_RUNTIME_ASSETS:
        canonical_asset = _prototype_root(repository_root) / relative_path
        context_asset = _prototype_root(source_root) / relative_path
        context_asset.parent.mkdir(parents=True, exist_ok=True)
        copyfile(canonical_asset, context_asset)
        source_path = f"docs/superpowers/prototypes/{relative_path}"
        dockerfile.append(f"COPY {source_path} /prototype/{relative_path}")

    environment = os.environ.copy()
    environment["DOCKER_BUILDKIT"] = "1"
    result = subprocess.run(
        [
            docker,
            "build",
            "--progress=plain",
            "--output",
            f"type=local,dest={output_root}",
            "--file",
            "-",
            str(source_root),
        ],
        input="\n".join(dockerfile),
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr

    for relative_path in PROTOTYPE_RUNTIME_ASSETS:
        assert (output_root / "prototype" / relative_path).read_bytes() == (
            _prototype_root(repository_root) / relative_path
        ).read_bytes()


def test_docker_negations_reopen_prototype_under_a_broad_exclude(tmp_path):
    """Exercise the include chain independently against a synthetic broad ignore."""

    docker = which("docker")
    if docker is None:
        pytest.skip("Docker CLI is not installed")

    server = subprocess.run(
        [docker, "info", "--format", "{{.ServerVersion}}"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if server.returncode:
        pytest.skip(f"Docker daemon is unavailable: {server.stderr.strip()}")

    repository_root = Path(settings.ROOT_DIR)
    dockerignore_rules, _rsync_rules = _deployment_rules(repository_root)
    source_root = tmp_path / "docker-source"
    output_root = tmp_path / "docker-context"
    prototype_root = _prototype_root(source_root)
    source_root.mkdir()
    (source_root / ".dockerignore").write_text(
        "\n".join(("*", *dockerignore_rules, ""))
    )

    dockerfile = ["FROM scratch"]
    for relative_path in PROTOTYPE_RUNTIME_ASSETS:
        asset = prototype_root / relative_path
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_text(f"canonical:{relative_path}")
        source_path = f"docs/superpowers/prototypes/{relative_path}"
        dockerfile.append(f"COPY {source_path} /prototype/{relative_path}")

    environment = os.environ.copy()
    environment["DOCKER_BUILDKIT"] = "1"
    result = subprocess.run(
        [
            docker,
            "build",
            "--progress=plain",
            "--output",
            f"type=local,dest={output_root}",
            "--file",
            "-",
            str(source_root),
        ],
        input="\n".join(dockerfile),
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr

    for relative_path in PROTOTYPE_RUNTIME_ASSETS:
        assert (output_root / "prototype" / relative_path).read_bytes() == (
            prototype_root / relative_path
        ).read_bytes()


def test_prototype_finder_warns_before_collectstatic_fails_closed(tmp_path):
    with override_settings(ROOT_DIR=tmp_path):
        finder = PortfolioPrototypeFinder()
        warnings = finder.check()

    assert len(warnings) == len(PROTOTYPE_RUNTIME_ASSETS)
    assert all(isinstance(message, Warning) for message in warnings)
    assert {message.id for message in warnings} == {"portfolio.W001"}
    assert all("collectstatic" in message.hint for message in warnings)
    assert "portfolio-startseite.css" in " ".join(message.msg for message in warnings)


def test_prototype_finder_list_fails_closed_when_runtime_assets_are_missing(
    tmp_path,
):
    with override_settings(ROOT_DIR=tmp_path):
        finder = PortfolioPrototypeFinder()
        with pytest.raises(
            ImproperlyConfigured,
            match=r"Cannot collect.*501\.css.*portfolio-startseite\.css",
        ):
            finder.list(ignore_patterns=[])


def test_prototype_finder_check_and_list_share_missing_asset_inventory(
    tmp_path, monkeypatch
):
    finder = PortfolioPrototypeFinder()
    missing_assets = ("shared-missing-one.css", "nested/shared-missing-two.js")
    monkeypatch.setattr(finder, "_missing_assets", lambda: missing_assets)

    warnings = finder.check()

    assert [message.msg.rsplit(": ", 1)[-1] for message in warnings] == list(
        missing_assets
    )
    with pytest.raises(ImproperlyConfigured) as error:
        list(finder.list(ignore_patterns=[]))
    assert all(asset in str(error.value) for asset in missing_assets)


def test_collectstatic_fails_closed_when_canonical_runtime_assets_are_missing(
    tmp_path,
):
    with override_settings(
        ROOT_DIR=tmp_path,
        STATIC_ROOT=tmp_path / "collected",
        STATICFILES_FINDERS=["config.staticfiles.PortfolioPrototypeFinder"],
    ):
        with pytest.raises(
            ImproperlyConfigured,
            match="canonical prototype assets",
        ):
            call_command("collectstatic", interactive=False, verbosity=0)


def test_cached_prototype_finder_resolves_root_dir_lazily(tmp_path):
    finder = PortfolioPrototypeFinder()

    with override_settings(ROOT_DIR=tmp_path):
        assert finder.root == tmp_path / "docs" / "superpowers" / "prototypes"
        assert Path(finder.storage.location) == finder.root


def test_prototype_finder_list_honors_collectstatic_ignore_patterns(tmp_path):
    prototype_root = _prototype_root(tmp_path)
    for relative_path in PROTOTYPE_RUNTIME_ASSETS:
        asset = prototype_root / relative_path
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(f"canonical:{relative_path}".encode())

    with override_settings(ROOT_DIR=tmp_path):
        finder = PortfolioPrototypeFinder()
        listed_assets = {
            relative_path: storage
            for relative_path, storage in finder.list(
                ignore_patterns=["homepage.js", "projekte/*"]
            )
        }

    assert "homepage.js" not in listed_assets
    assert "projekte/projekt.css" not in listed_assets
    assert set(listed_assets) == set(PROTOTYPE_RUNTIME_ASSETS) - {
        "homepage.js",
        "projekte/projekt.css",
    }
    storage = listed_assets["portfolio-startseite.css"]
    assert Path(storage.location) == prototype_root
    with storage.open("portfolio-startseite.css", "rb") as asset:
        assert asset.read() == b"canonical:portfolio-startseite.css"


@pytest.mark.parametrize("ignore_pattern", ["projekt.css", "projekte"])
def test_prototype_finder_matches_ignore_patterns_per_path_component(
    tmp_path, ignore_pattern
):
    prototype_root = _prototype_root(tmp_path)
    for relative_path in PROTOTYPE_RUNTIME_ASSETS:
        asset = prototype_root / relative_path
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(f"canonical:{relative_path}".encode())

    with override_settings(ROOT_DIR=tmp_path):
        finder = PortfolioPrototypeFinder()
        listed_assets = {
            relative_path
            for relative_path, _storage in finder.list(ignore_patterns=[ignore_pattern])
        }

    assert "projekte/projekt.css" not in listed_assets
    assert listed_assets == set(PROTOTYPE_RUNTIME_ASSETS) - {"projekte/projekt.css"}


def test_production_manifest_collects_and_hashes_canonical_parity_assets(tmp_path):
    static_root = tmp_path / "collected"
    storages = production_staticfiles_storage(settings.STORAGES)

    with override_settings(STATIC_ROOT=static_root, STORAGES=storages):
        call_command("collectstatic", interactive=False, verbosity=0)

        for asset_name in (*WAGTAIL_PARITY_ADAPTERS, *PROTOTYPE_PARITY_ASSETS):
            collected_name = staticfiles_storage.stored_name(asset_name)

            assert collected_name != asset_name
            assert (static_root / collected_name).is_file()

        assert not (static_root / "portfolio/prototype/MEMORY.md").exists()
        assert not (
            static_root / "portfolio/prototype/portfolio-startseite.html"
        ).exists()
        assert not (static_root / "portfolio/prototype/fonts.css").exists()


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
    portfolio_assets = (
        "portfolio/fonts.css",
        "portfolio/fonts/saira-variable.woff2",
        "portfolio/fonts/astagina.woff2",
    )
    for portfolio_asset in portfolio_assets:
        source_path = finders.find(portfolio_asset)
        assert source_path is not None
        destination = source_root / portfolio_asset
        destination.parent.mkdir(parents=True, exist_ok=True)
        copyfile(source_path, destination)

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

        font_stylesheet_name = staticfiles_storage.stored_name("portfolio/fonts.css")
        saira_name = staticfiles_storage.stored_name(
            "portfolio/fonts/saira-variable.woff2"
        )
        astagina_name = staticfiles_storage.stored_name(
            "portfolio/fonts/astagina.woff2"
        )
        collected_font_stylesheet = (static_root / font_stylesheet_name).read_text()

        assert Path(saira_name).name in collected_font_stylesheet
        assert Path(astagina_name).name in collected_font_stylesheet
        assert (static_root / saira_name).read_bytes() == (
            source_root / "portfolio/fonts/saira-variable.woff2"
        ).read_bytes()
        assert (static_root / astagina_name).read_bytes() == (
            source_root / "portfolio/fonts/astagina.woff2"
        ).read_bytes()
