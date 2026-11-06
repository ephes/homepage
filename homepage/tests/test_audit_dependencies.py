from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import audit_dependencies


@pytest.fixture
def exported():
    sources = [f"{name} @ git+https://github.com/ephes/{name}@{'a' * 40}" for name in audit_dependencies.GIT_SOURCES]
    return "\n".join(
        ["black==26.10.1", "tornado==6.6", "registry-transitive==1.0 ; sys_platform == 'win32'", *sources]
    )


def test_only_allowlisted_git_sources_are_excluded(exported, capsys):
    requirements = audit_dependencies.registry_requirements(exported)
    assert requirements.splitlines() == [
        "black==26.10.1",
        "tornado==6.6",
        "registry-transitive==1.0 ; sys_platform == 'win32'",
    ]
    assert capsys.readouterr().out.count("Not registry-audited:") == 5


@pytest.mark.parametrize(
    "unexpected",
    [
        "unknown @ git+https://github.com/ephes/unknown@" + "a" * 40,
        "black>=1",
        "-r other.txt",
        "thing @ file:///tmp/x",
    ],
)
def test_unexpected_sources_and_unpinned_requirements_fail_closed(exported, unexpected):
    with pytest.raises(ValueError):
        audit_dependencies.registry_requirements(exported + "\n" + unexpected)


@pytest.mark.parametrize("exported", ["", "black==26.10.1"])
def test_incomplete_export_fails_closed(exported):
    with pytest.raises(ValueError):
        audit_dependencies.registry_requirements(exported)


@pytest.mark.parametrize("result", [0, 1, 2])
def test_exact_audit_keeps_transitives_and_propagates_auditor_status(monkeypatch, exported, result):
    def fake_run(command, **kwargs):
        if command[0] == "uv":
            assert "--frozen" in command
            assert kwargs["check"]
            return SimpleNamespace(stdout=exported)
        assert command[:4] == ["uvx", "--from", "pip-audit==2.10.1", "pip-audit"]
        assert "--strict" in command and "--disable-pip" in command and "--no-deps" in command
        requirements = Path(command[-1]).read_text()
        assert "registry-transitive==1.0" in requirements
        assert "git+" not in requirements
        return SimpleNamespace(returncode=result)

    monkeypatch.setattr(audit_dependencies.subprocess, "run", fake_run)
    assert audit_dependencies.main() == result


def test_export_failure_never_launches_auditor(monkeypatch, capsys):
    run = Mock(
        side_effect=audit_dependencies.subprocess.CalledProcessError(23, ["uv"], stderr="synthetic export failure")
    )
    monkeypatch.setattr(audit_dependencies.subprocess, "run", run)
    assert audit_dependencies.main() == 23
    assert run.call_count == 1
    assert "synthetic export failure" in capsys.readouterr().err


def test_ci_uses_same_audit_command():
    workflow = (audit_dependencies.ROOT / ".github/workflows/ci.yml").read_text()
    assert "run: python audit_dependencies.py" in workflow
