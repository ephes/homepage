"""Quality commands report failures without running dependent coverage steps."""

from unittest.mock import Mock, call

import pytest
from typer.testing import CliRunner

import commands

runner = CliRunner()
FIRST_COMMAND = {
    "mypy": ["mypy", "."],
    "test": ["python", "-m", "pytest"],
    "coverage": ["coverage", "run", "-m", "pytest"],
}


@pytest.fixture
def tool(monkeypatch):
    tool = Mock(return_value=0)
    monkeypatch.setattr(commands.subprocess, "call", tool)
    monkeypatch.setattr(commands, "env_with_pythonpath", lambda: {"PYTHONPATH": "project:model"})
    monkeypatch.setattr(commands.platform, "system", lambda: "Darwin")
    return tool


@pytest.mark.parametrize("command", FIRST_COMMAND)
@pytest.mark.parametrize(("returncode", "expected_status"), [(1, 1), (2, 2), (-9, 137)])
def test_quality_failure_preserves_exit_status(tool, command, returncode, expected_status):
    tool.return_value = returncode

    result = runner.invoke(commands.cli, [command])

    assert result.exit_code == expected_status
    assert tool.call_count == 1
    assert tool.call_args.args == (FIRST_COMMAND[command],)


@pytest.mark.parametrize("command", FIRST_COMMAND)
def test_quality_startup_failure_is_reported(tool, command):
    tool.side_effect = OSError("cannot start tool")

    result = runner.invoke(commands.cli, [command])

    assert result.exit_code == 1
    assert "could not be started" in result.output
    assert "cannot start tool" in result.output
    assert tool.call_count == 1


@pytest.mark.parametrize("failure", [1, 2, OSError("cannot start tool")])
@pytest.mark.parametrize("step", [1, 2])
def test_coverage_stops_at_failed_report_or_opener(tool, step, failure):
    tool.side_effect = [0] * step + [failure]

    result = runner.invoke(commands.cli, ["coverage"])

    assert result.exit_code == (failure if isinstance(failure, int) else 1)
    if isinstance(failure, OSError):
        assert "could not be started" in result.output
    assert tool.call_count == step + 1
    assert tool.call_args.args == (["coverage", "html"] if step == 1 else ["open", "htmlcov/index.html"],)


@pytest.mark.parametrize("command", ["mypy", "test"])
def test_quality_success(tool, command):
    result = runner.invoke(commands.cli, [command])

    assert result.exit_code == 0
    expected_kwargs = {} if command == "mypy" else {"env": {"PYTHONPATH": "project:model"}}
    tool.assert_called_once_with(FIRST_COMMAND[command], **expected_kwargs)


@pytest.mark.parametrize(
    ("system", "release", "opener"),
    [
        ("Darwin", "", ["open", "htmlcov/index.html"]),
        ("Linux", "Microsoft WSL", ["explorer.exe", r"htmlcov\index.html"]),
        ("Linux", "ordinary Linux", None),
    ],
)
def test_coverage_success_preserves_platform_behavior(tool, monkeypatch, system, release, opener):
    monkeypatch.setattr(commands.platform, "system", lambda: system)
    monkeypatch.setattr(commands.platform, "release", lambda: release)

    result = runner.invoke(commands.cli, ["coverage"])

    assert result.exit_code == 0
    expected = [
        call(FIRST_COMMAND["coverage"], env={"PYTHONPATH": "project:model"}),
        call(["coverage", "html"]),
    ]
    if opener:
        expected.append(call(opener))
    assert tool.call_args_list == expected


@pytest.mark.parametrize("returncode", [0, 1, 2])
def test_wsl_explorer_return_status_is_best_effort(tool, monkeypatch, returncode):
    monkeypatch.setattr(commands.platform, "system", lambda: "Linux")
    monkeypatch.setattr(commands.platform, "release", lambda: "Microsoft WSL")
    tool.side_effect = [0, 0, returncode]

    result = runner.invoke(commands.cli, ["coverage"])

    assert result.exit_code == 0
    assert tool.call_count == 3
    assert tool.call_args.args == (["explorer.exe", r"htmlcov\index.html"],)


def test_wsl_explorer_startup_failure_is_reported(tool, monkeypatch):
    monkeypatch.setattr(commands.platform, "system", lambda: "Linux")
    monkeypatch.setattr(commands.platform, "release", lambda: "Microsoft WSL")
    tool.side_effect = [0, 0, OSError("cannot start Explorer")]

    result = runner.invoke(commands.cli, ["coverage"])

    assert result.exit_code == 1
    assert "explorer.exe could not be started" in result.output
    assert tool.call_count == 3
