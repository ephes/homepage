"""The source-switch workflow must keep the reviewed resume integration pin."""

import re
import tomllib

import commands


def test_git_source_switch_restores_the_reviewed_resume_dependency(monkeypatch, tmp_path):
    source = (commands.get_project_root() / "pyproject.toml").read_text(encoding="utf-8")
    project = tomllib.loads(source)
    expected = project["tool"]["uv"]["sources"]["django-resume"]
    assert (
        "rev" in expected and "path" not in expected
    ), "pyproject still points at a local checkout or unpinned source"
    assert re.fullmatch(r"[0-9a-f]{40}", expected["rev"]), "django-resume must pin a full immutable commit"
    local_source, replacements = re.subn(
        r"(?m)^django-resume = .*$",
        'django-resume = { path = "../django-resume", editable = true }',
        source,
    )
    assert replacements == 1
    project_file = tmp_path / "pyproject.toml"
    project_file.write_text(local_source, encoding="utf-8")
    # Exercise the real root resolution and TOML writer against the temporary
    # project; only the external dependency installation is stubbed.
    monkeypatch.setattr(commands, "__file__", str(tmp_path / "commands.py"))
    monkeypatch.setattr(commands.subprocess, "call", lambda *args, **kwargs: 0)

    commands.switch_to_git_sources()

    result = tomllib.loads(project_file.read_text(encoding="utf-8"))
    assert result["tool"]["uv"]["sources"]["django-resume"] == expected
    assert result["project"] == project["project"]
