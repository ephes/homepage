"""Tests for the package source switch commands in commands.py. ``uv sync`` is always replaced."""

from __future__ import annotations

import subprocess

import pytest
import typer

import commands

DEV_PACKAGES = ("cast-vue", "cast-bootstrap5", "django-cast", "django-indieweb", "django-resume")
PYPROJECT = '[project]\nname = "example"\n\n[tool.uv.sources]\ncast-vue = { git = "https://example.invalid/x" }\n'
SUCCESS_MARKERS = ("activated", "editable mode", "Switched back", "installed from their git")


@pytest.fixture
def project(monkeypatch, tmp_path):
    root = tmp_path / "homepage"
    root.mkdir()
    for name in DEV_PACKAGES:
        (tmp_path / name).mkdir()
    (root / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    monkeypatch.setattr(commands, "get_project_root", lambda: root)
    return root


@pytest.fixture
def uv_sync(monkeypatch):
    calls = []

    def install(returncode=0, error=None):
        def run(cmd, **kwargs):
            calls.append((list(cmd), kwargs))
            if error is not None:
                raise error
            return subprocess.CompletedProcess(cmd, returncode)

        monkeypatch.setattr(commands.subprocess, "run", run)
        monkeypatch.setattr(commands.subprocess, "call", lambda cmd, **kwargs: run(cmd, **kwargs).returncode)
        return calls

    return install


COMMANDS = {
    "switch_to_dev_environment": (["uv", "sync"], 'django-cast = { path = "../django-cast", editable = true }'),
    "switch_to_git_sources": (
        ["uv", "sync", "--reinstall"],
        'django-cast = { git = "https://github.com/ephes/django-cast", branch = "develop" }',
    ),
}


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("returncode", [1, 2])
def test_failed_sync_fails_the_command_without_claiming_success(project, uv_sync, capsys, command, returncode):
    calls = uv_sync(returncode=returncode)
    expected_args, expected_source = COMMANDS[command]

    with pytest.raises(typer.Exit) as excinfo:
        getattr(commands, command)()

    assert excinfo.value.exit_code == 1
    assert [cmd for cmd, _ in calls] == [expected_args]
    output = " ".join(capsys.readouterr().out.split())
    assert not any(marker in output for marker in SUCCESS_MARKERS)
    assert f"exited with status {returncode}" in output
    assert "NOT updated" in output
    # The documented state after a failed sync: the new sources stay in pyproject.toml.
    assert "keeps the new source entries" in output
    assert expected_source in (project / "pyproject.toml").read_text(encoding="utf-8")


@pytest.mark.parametrize("command", COMMANDS)
def test_missing_uv_fails_the_command(project, uv_sync, capsys, command):
    uv_sync(error=FileNotFoundError(2, "No such file or directory", "uv"))

    with pytest.raises(typer.Exit) as excinfo:
        getattr(commands, command)()

    assert excinfo.value.exit_code == 1
    output = " ".join(capsys.readouterr().out.split())
    assert "could not be started" in output
    assert not any(marker in output for marker in SUCCESS_MARKERS)


@pytest.mark.parametrize("command", COMMANDS)
def test_successful_sync_keeps_source_edits_and_reports_success(project, uv_sync, capsys, command):
    calls = uv_sync()
    expected_args, expected_source = COMMANDS[command]

    getattr(commands, command)()

    assert [cmd for cmd, _ in calls] == [expected_args]
    assert all(not kwargs.get("shell") for _, kwargs in calls)
    text = (project / "pyproject.toml").read_text(encoding="utf-8")
    assert expected_source in text
    assert text.startswith('[project]\nname = "example"\n')
    output = capsys.readouterr().out
    assert ("Development environment activated!" in output) == (command == "switch_to_dev_environment")
    assert ("Switched back to git sources!" in output) == (command == "switch_to_git_sources")
