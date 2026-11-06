"""Synthetic process identities only: never signal a real process."""

import io
import json
import signal
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import dev_runner


@pytest.fixture
def state(tmp_path):
    return tmp_path / "dev.json"


@pytest.fixture
def owner(monkeypatch):
    process = Mock(pid=4321)
    process.create_time.return_value = 123.5
    process.cwd.return_value = str(dev_runner.ROOT)
    process.cmdline.return_value = ["python", str(Path(dev_runner.__file__).resolve())]
    monkeypatch.setattr(dev_runner.psutil, "Process", Mock(return_value=process))
    return process


def test_cleanup_only_signals_verified_owner(state, owner):
    state.write_text(json.dumps({"pid": 4321, "created": 123.5}))
    dev_runner.cleanup(state)
    owner.send_signal.assert_called_once_with(signal.SIGTERM)
    owner.wait.assert_called_once_with(timeout=15)


@pytest.mark.parametrize("mismatch", ["created", "cwd", "cmdline", "invalid", "missing", "legacy"])
def test_stale_reused_or_foreign_owner_never_signalled(state, owner, mismatch):
    state.write_text(json.dumps({"pid": 4321, "created": 123.5}))
    if mismatch == "created":
        owner.create_time.return_value = 999
    elif mismatch == "cwd":
        owner.cwd.return_value = "/synthetic/other-checkout"
    elif mismatch == "cmdline":
        owner.cmdline.return_value = ["python", "manage.py", "runserver"]
    elif mismatch == "invalid":
        state.write_text("not json")
    elif mismatch == "legacy":
        state.write_text("4321")
    else:
        state.write_text("{}")
    with pytest.raises(RuntimeError, match="Refusing cleanup"):
        dev_runner.cleanup(state)
    owner.send_signal.assert_not_called()


def test_no_state_does_nothing(state, owner):
    dev_runner.cleanup(state)
    owner.send_signal.assert_not_called()


@pytest.fixture
def fake_run(monkeypatch, owner):
    child = Mock(pid=5678, stdout=io.StringIO("\x1b[31msynthetic log\x1b[0m\n"))
    child.wait.return_value = 0
    popen = Mock(return_value=child)
    killpg = Mock()
    monkeypatch.setattr(dev_runner.subprocess, "Popen", popen)
    monkeypatch.setattr(dev_runner.os, "killpg", killpg)
    monkeypatch.setattr(dev_runner.fcntl, "flock", Mock())
    monkeypatch.setattr(dev_runner.signal, "signal", Mock())
    return SimpleNamespace(child=child, popen=popen, killpg=killpg)


@pytest.mark.parametrize("result,expected", [(0, 0), (23, 23), (-15, 143)])
def test_supervisor_result_logging_and_owned_group_cleanup(state, fake_run, result, expected):
    fake_run.child.wait.return_value = result
    assert dev_runner.run(["postgres", "django"], state) == expected
    assert not state.exists()
    assert state.with_name("dev.log").read_text() == "synthetic log\n"
    fake_run.popen.assert_called_once_with(
        ["uvx", "honcho", "start", "postgres", "django"],
        cwd=dev_runner.ROOT,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    fake_run.killpg.assert_called_once_with(5678, signal.SIGTERM)


def test_start_failure_removes_state(state, fake_run):
    fake_run.popen.side_effect = FileNotFoundError("synthetic missing honcho")
    with pytest.raises(FileNotFoundError):
        dev_runner.run([], state)
    assert not state.exists()
    fake_run.killpg.assert_not_called()


def test_stale_record_is_not_overwritten(state, fake_run):
    state.write_text("stale")
    with pytest.raises(RuntimeError, match="Refusing to overwrite"):
        dev_runner.run([], state)
    assert state.read_text() == "stale"
    fake_run.popen.assert_not_called()


def test_launchers_share_runner_without_name_kills():
    root = dev_runner.ROOT
    recipes = (root / "justfile").read_text()
    assert "pkill" not in recipes
    for recipe in ("dev: check-services", "dev-all: check-services", "cleanup:"):
        body = recipes.split(recipe + "\n", 1)[1].split("\n\n", 1)[0]
        assert "dev_runner.py" in body
        assert "|" not in body
    launcher = (root / "run_dev.sh").read_text()
    assert 'exec uv run --locked python "$PWD/dev_runner.py"' in launcher
    assert "pipefail" in launcher


@pytest.mark.parametrize("launcher", ["dev", "dev-all", "run_dev.sh"])
@pytest.mark.parametrize("result", [0, 23])
def test_launcher_preserves_fake_honcho_status(tmp_path, launcher, result):
    import os
    import shutil
    import sys

    root = dev_runner.ROOT
    shutil.copy(root / "dev_runner.py", tmp_path)
    shutil.copy(root / "run_dev.sh", tmp_path)
    tools = tmp_path / "tools"
    tools.mkdir()
    uv = tools / "uv"
    uv.write_text(f'#!/bin/bash\nshift 3\nexec "{sys.executable}" "$@"\n')
    uvx = tools / "uvx"
    uvx.write_text(f"#!/bin/bash\necho 'synthetic honcho'\nexit {result}\n")
    uv.chmod(0o755)
    uvx.chmod(0o755)
    if launcher == "run_dev.sh":
        command = ["bash", str(tmp_path / launcher)]
    else:
        recipes = (root / "justfile").read_text()
        body = recipes.split(f"{launcher}: check-services\n", 1)[1].split("\n\n", 1)[0].strip()
        body = body.removeprefix("@").replace("{{justfile_directory()}}", str(tmp_path))
        command = ["bash", "-c", body]
    completed = subprocess.run(
        command,
        cwd=tmp_path,
        env={**os.environ, "PATH": str(tools) + os.pathsep + os.environ["PATH"]},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert "synthetic honcho" in completed.stdout
    assert completed.returncode == result, completed.stderr
    assert not (tmp_path / "logs" / "dev.json").exists()


@pytest.mark.parametrize("stop_signal", [signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT])
def test_cleanup_stops_owned_tree_and_preserves_identically_named_unrelated_tree(tmp_path, monkeypatch, stop_signal):
    import os
    import shutil
    import sys
    import time

    import psutil

    script = tmp_path / "dev_runner.py"
    shutil.copy(dev_runner.ROOT / "dev_runner.py", script)
    tools = tmp_path / "tools"
    tools.mkdir()
    uvx = tools / "uvx"
    uvx.write_text(
        f"#!{sys.executable}\n"
        "import os, pathlib, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)', 'manage.py runserver'])\n"
        "pathlib.Path(os.environ['TREE_PID']).write_text(str(child.pid))\n"
        "time.sleep(60)\n"
    )
    uvx.chmod(0o755)
    env = {**os.environ, "PATH": str(tools) + os.pathsep + os.environ["PATH"]}
    unrelated_pid = tmp_path / "unrelated.pid"
    owned_pid = tmp_path / "owned.pid"
    unrelated = subprocess.Popen(
        [str(uvx), "honcho", "start"], env={**env, "TREE_PID": str(unrelated_pid)}, start_new_session=True
    )
    runner = subprocess.Popen([sys.executable, str(script)], cwd=tmp_path, env={**env, "TREE_PID": str(owned_pid)})
    try:
        deadline = time.monotonic() + 10
        while not (owned_pid.exists() and unrelated_pid.exists()):
            assert time.monotonic() < deadline, "Synthetic trees did not start"
            time.sleep(0.02)
        monkeypatch.setattr(dev_runner, "ROOT", tmp_path)
        monkeypatch.setattr(dev_runner, "__file__", str(script))
        state = tmp_path / "logs" / "dev.json"
        if stop_signal == signal.SIGTERM:
            dev_runner.cleanup(state)
        else:
            runner.send_signal(stop_signal)
        runner.wait(timeout=5)
        assert not state.exists()
        owned = psutil.Process(int(owned_pid.read_text())) if psutil.pid_exists(int(owned_pid.read_text())) else None
        deadline = time.monotonic() + 5
        while owned is not None and owned.is_running() and owned.status() != psutil.STATUS_ZOMBIE:
            assert time.monotonic() < deadline, "Owned descendant survived cleanup"
            time.sleep(0.02)
        assert unrelated.poll() is None
        assert psutil.Process(int(unrelated_pid.read_text())).is_running()
    finally:
        if runner.poll() is None:
            runner.terminate()
            runner.wait(timeout=5)
        os.killpg(unrelated.pid, signal.SIGTERM)
        unrelated.wait(timeout=5)


def test_repeated_interrupt_during_shutdown_cannot_skip_escalation(state, fake_run, monkeypatch):
    handlers = {}
    interrupted_wait = False

    def install(sig, handler):
        previous = handlers.get(sig, signal.SIG_DFL)
        handlers[sig] = handler
        return previous

    def wait(timeout=None):
        nonlocal interrupted_wait
        if timeout == 10:
            interrupted_wait = True
            handler = handlers[signal.SIGINT]
            if callable(handler):
                handler(signal.SIGINT, None)
            raise subprocess.TimeoutExpired("synthetic stubborn honcho", timeout)
        return 0

    monkeypatch.setattr(dev_runner.signal, "signal", install)
    fake_run.child.wait.side_effect = wait
    assert dev_runner.run([], state) == 0
    assert interrupted_wait
    assert not state.exists()
    assert fake_run.killpg.call_args_list == [((5678, signal.SIGTERM),), ((5678, signal.SIGKILL),)]


def test_shell_launcher_uses_physical_checkout_path(tmp_path):
    import os
    import shutil

    checkout = tmp_path / "checkout"
    checkout.mkdir()
    shutil.copy(dev_runner.ROOT / "run_dev.sh", checkout)
    linked = tmp_path / "linked"
    linked.symlink_to(checkout, target_is_directory=True)
    tools = tmp_path / "tools"
    tools.mkdir()
    uv = tools / "uv"
    uv.write_text('#!/bin/bash\nprintf "%s\\n" "$4"\n')
    uv.chmod(0o755)
    result = subprocess.run(
        ["bash", str(linked / "run_dev.sh")],
        env={**os.environ, "PATH": str(tools) + os.pathsep + os.environ["PATH"]},
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    assert result.stdout.strip() == str(checkout / "dev_runner.py")
