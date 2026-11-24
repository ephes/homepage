"""Synthetic supervisors only: never signal an existing development service."""

import json
import os
import signal
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import dev_runner

# The runner refuses interpreters without waitid(WNOWAIT) (macOS before Python 3.13).
pytestmark = pytest.mark.skipif(
    not (hasattr(os, "waitid") and hasattr(os, "WNOWAIT")),
    reason="dev_runner needs os.waitid(WNOWAIT); on macOS use Python 3.13 or newer",
)


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
    read_fd, write_fd = os.pipe()
    os.write(write_fd, b"\x1b[31msynthetic log\x1b[0m\n")
    os.close(write_fd)
    stdout = os.fdopen(read_fd, "rb", buffering=0)
    child = Mock(pid=5678, stdout=stdout)
    child.wait.return_value = 0
    child.returncode = 0
    monkeypatch.setattr(dev_runner, "observe_exit", Mock(return_value=object()))
    monkeypatch.setattr(dev_runner, "group_alive", Mock(return_value=False))
    popen = Mock(return_value=child)
    killpg = Mock()
    monkeypatch.setattr(dev_runner.subprocess, "Popen", popen)
    monkeypatch.setattr(dev_runner.os, "killpg", killpg)
    monkeypatch.setattr(dev_runner.fcntl, "flock", Mock())
    monkeypatch.setattr(dev_runner.signal, "signal", Mock())
    yield SimpleNamespace(child=child, popen=popen, killpg=killpg)
    stdout.close()


@pytest.mark.parametrize("result,expected", [(0, 0), (23, 23), (-15, 143)])
def test_supervisor_result_logging_and_owned_group_cleanup(state, fake_run, result, expected):
    fake_run.child.wait.return_value = result
    fake_run.child.returncode = result
    assert dev_runner.run(["postgres", "django"], state) == expected
    assert not state.exists()
    assert state.with_name("dev.log").read_text() == "synthetic log\n"
    fake_run.popen.assert_called_once_with(
        ["uvx", "honcho", "start", "postgres", "django"],
        cwd=dev_runner.ROOT,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    assert fake_run.killpg.call_args_list == [((5678, signal.SIGTERM),), ((5678, signal.SIGKILL),)]


def test_start_failure_removes_state(state, fake_run):
    fake_run.popen.side_effect = FileNotFoundError("synthetic missing honcho")
    with pytest.raises(FileNotFoundError):
        dev_runner.run([], state)
    assert not state.exists()
    fake_run.killpg.assert_not_called()


@pytest.mark.parametrize("fail_replace", [False, True])
def test_ownership_record_is_published_atomically(state, fake_run, owner, monkeypatch, fail_replace):
    replace = Path.replace
    first = {"pid": 4321, "created": 123.5}
    second = {**first, "pgid": 5678}
    publications = []

    def inspect_before_replace(stage, destination):
        assert destination == state
        assert stage.parent == state.parent and stage != state
        assert stat.S_IMODE(stage.stat().st_mode) == 0o600
        publications.append(json.loads(stage.read_text()))
        if len(publications) == 1:
            assert not state.exists()
        else:
            assert json.loads(state.read_text()) == first
            dev_runner.cleanup(state)
            owner.send_signal.assert_called_once_with(signal.SIGTERM)
            if fail_replace:
                raise OSError("synthetic replace failure")
        return replace(stage, destination)

    def inspect_at_retirement(pgid, sig):
        assert json.loads(state.read_text()) == (first if fail_replace else second)

    monkeypatch.setattr(Path, "replace", inspect_before_replace)
    fake_run.killpg.side_effect = inspect_at_retirement
    if fail_replace:
        with pytest.raises(OSError, match="synthetic replace failure"):
            dev_runner.run([], state)
    else:
        assert dev_runner.run([], state) == 0
    assert publications == [first, second]
    assert not state.exists()
    assert {path.name for path in state.parent.iterdir()} <= {"dev.lock", "dev.log"}


@pytest.mark.parametrize("run_outcome", ["success", "nonzero", "interrupted"])
def test_pipe_close_failure_restores_signal_handlers(state, fake_run, monkeypatch, run_outcome):
    previous = {sig: Mock() for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT)}
    handlers = previous.copy()

    def install(sig, handler):
        old = handlers[sig]
        handlers[sig] = handler
        return old

    monkeypatch.setattr(dev_runner.signal, "signal", install)
    stdout = Mock(wraps=fake_run.child.stdout)
    stdout.close.side_effect = OSError("synthetic pipe close failure")
    fake_run.child.stdout = stdout

    if run_outcome == "nonzero":
        fake_run.child.returncode = 23
        assert dev_runner.run([], state) == 23
    elif run_outcome == "interrupted":
        interrupt = SystemExit(143)
        monkeypatch.setattr(dev_runner, "stream_output", Mock(side_effect=interrupt))
        with pytest.raises(SystemExit) as caught:
            dev_runner.run([], state)
        assert caught.value is interrupt
        assert any("synthetic pipe close failure" in note for note in caught.value.__notes__)
    else:
        with pytest.raises(OSError, match="synthetic pipe close failure"):
            dev_runner.run([], state)
    assert handlers == previous
    stdout.close.assert_called_once_with()
    assert not state.exists()


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

    def alive(pgid):
        nonlocal interrupted_wait
        interrupted_wait = True
        handler = handlers[signal.SIGINT]
        if callable(handler):
            handler(signal.SIGINT, None)
        return fake_run.killpg.call_count == 1

    monkeypatch.setattr(dev_runner.signal, "signal", install)
    monkeypatch.setattr(dev_runner, "group_alive", alive)
    monkeypatch.setattr(dev_runner, "TERM_GRACE", 0)
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


@pytest.mark.parametrize("stop_signal", [None, signal.SIGTERM])
def test_exited_leader_retires_term_resistant_descendant(tmp_path, stop_signal):
    import os
    import sys
    import time

    import psutil

    script = tmp_path / "dev_runner.py"
    source = (dev_runner.ROOT / "dev_runner.py").read_text()
    assert source.count("\nTERM_GRACE = 10.0\n") == 1
    # Keep the resistant-descendant scenario fast; the escalation path is unchanged.
    script.write_text(source.replace("\nTERM_GRACE = 10.0\n", "\nTERM_GRACE = 0.5\n"))
    tools = tmp_path / "tools"
    tools.mkdir()
    pid_file = tmp_path / "descendant.pid"
    uvx = tools / "uvx"
    descendant = (
        "import os,pathlib,signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid())); time.sleep(60)"
    )
    uvx.write_text(
        f"#!{sys.executable}\n"
        "import pathlib, subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, '-c', {descendant!r}], "
        "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        f"while not pathlib.Path({str(pid_file)!r}).exists(): time.sleep(0.01)\n"
        + ("time.sleep(60)\n" if stop_signal else "sys.exit(23)\n")
    )
    uvx.chmod(0o755)
    runner = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env={**os.environ, "PATH": str(tools) + os.pathsep + os.environ["PATH"]},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    descendant_process = None
    try:
        deadline = time.monotonic() + 10
        while not pid_file.exists():
            assert time.monotonic() < deadline
            time.sleep(0.01)
        descendant_process = psutil.Process(int(pid_file.read_text()))
        if stop_signal:
            runner.send_signal(stop_signal)
        _, stderr = runner.communicate(timeout=10)
        assert runner.returncode == (128 + stop_signal if stop_signal else 23), stderr
        assert not descendant_process.is_running() or descendant_process.status() == psutil.STATUS_ZOMBIE
        assert not (tmp_path / "logs" / "dev.json").exists()
    finally:
        if runner.poll() is None:
            runner.kill()
            runner.wait(timeout=5)
        if descendant_process and descendant_process.is_running():
            descendant_process.kill()


def test_uncertain_group_cleanup_retains_ownership_record(state, fake_run, monkeypatch):
    # A running leader cannot explain EPERM: the group may hold processes we cannot signal.
    monkeypatch.setattr(dev_runner, "observe_exit", Mock(return_value=None))
    monkeypatch.setattr(dev_runner, "stream_output", Mock())
    fake_run.killpg.side_effect = PermissionError("synthetic denied group signal")
    with pytest.raises(PermissionError):
        dev_runner.run([], state)
    assert state.exists()
    fake_run.child.wait.assert_not_called()


def test_denied_signal_after_leader_exit_still_requires_confirmed_retirement(state, fake_run, monkeypatch):
    fake_run.killpg.side_effect = PermissionError("synthetic denied group signal")
    monkeypatch.setattr(dev_runner, "group_alive", lambda pid: True)
    monkeypatch.setattr(dev_runner, "TERM_GRACE", 0)
    monkeypatch.setattr(dev_runner, "KILL_GRACE", 0)
    with pytest.raises(RuntimeError, match="did not retire"):
        dev_runner.run([], state)
    assert state.exists()
    fake_run.child.wait.assert_not_called()


def test_missing_waitid_is_refused_before_record_or_child(state, fake_run, monkeypatch):
    monkeypatch.delattr(dev_runner.os, "WNOWAIT", raising=False)
    with pytest.raises(RuntimeError, match="waitid"):
        dev_runner.run([], state)
    fake_run.popen.assert_not_called()
    assert not state.exists()


def test_leader_exiting_during_group_signal_is_rechecked(state, fake_run, monkeypatch):
    # The leader is still running at the pre-signal check and exits before killpg.
    states = iter([None])
    monkeypatch.setattr(dev_runner, "observe_exit", lambda child: next(states, object()))
    fake_run.killpg.side_effect = PermissionError("synthetic Darwin zombie-only group")
    dev_runner.retire_group(fake_run.child)
    fake_run.child.wait.assert_called_once()


def test_exited_leader_alone_in_group_retires_without_signal_error():
    """Darwin refuses killpg with EPERM when only the unreaped (zombie) leader remains."""
    import sys
    import time

    leader = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    try:
        deadline = time.monotonic() + 5
        while dev_runner.observe_exit(leader) is None:
            assert time.monotonic() < deadline
            time.sleep(0.01)
        dev_runner.retire_group(leader)
        assert leader.returncode == 0
    finally:
        if leader.poll() is None:
            leader.kill()
            leader.wait(timeout=5)


def test_leader_is_reserved_until_all_group_signals_complete(state, fake_run, monkeypatch):
    events = []
    fake_run.killpg.side_effect = lambda pid, sig: events.append(sig)

    def reap(timeout):
        assert events == [signal.SIGTERM, signal.SIGKILL]
        events.append("reap")
        return 0

    fake_run.child.wait.side_effect = reap
    assert dev_runner.run([], state) == 0
    assert events == [signal.SIGTERM, signal.SIGKILL, "reap"]


def test_unconfirmed_retirement_retains_group_evidence(state, fake_run, monkeypatch):
    monkeypatch.setattr(dev_runner, "group_alive", lambda pid: True)
    monkeypatch.setattr(dev_runner, "TERM_GRACE", 0)
    monkeypatch.setattr(dev_runner, "KILL_GRACE", 0)
    with pytest.raises(RuntimeError, match="did not retire"):
        dev_runner.run([], state)
    assert json.loads(state.read_text())["pgid"] == 5678
    fake_run.child.wait.assert_not_called()


def test_failed_retirement_is_attempted_once_and_still_drains_output(state, fake_run, monkeypatch):
    attempts = []

    def retire(child):
        attempts.append(child)
        if len(attempts) == 1:
            raise RuntimeError("Cannot confirm owned group retirement; retaining ownership record")

    monkeypatch.setattr(dev_runner, "retire_group", retire)
    with pytest.raises(RuntimeError, match="Cannot confirm"):
        dev_runner.run([], state)
    # A silent second cycle could unlink dev.json while the error says it is retained.
    assert attempts == [fake_run.child]
    assert state.exists()
    assert state.with_name("dev.log").read_text() == "synthetic log\n"


def test_output_pipe_is_nonblocking_before_streaming_starts(state, fake_run, monkeypatch):
    """An early signal must not leave teardown in a blocking read held open by an escaped writer."""
    import threading

    read_fd, write_fd = os.pipe()
    os.write(write_fd, b"early output\n")
    stdout = os.fdopen(read_fd, "rb", buffering=0)
    fake_run.child.stdout = stdout

    def interrupt(child, output):
        raise SystemExit(143)

    monkeypatch.setattr(dev_runner, "stream_output", interrupt)
    monkeypatch.setattr(dev_runner, "KILL_GRACE", 0.2)
    outcome = []

    def target():
        try:
            dev_runner.run([], state)
        except SystemExit as exc:
            outcome.append(exc.code)

    worker = threading.Thread(target=target)
    worker.start()
    worker.join(timeout=5)
    hung = worker.is_alive()
    os.close(write_fd)  # Unblock a hung read so the test always finishes.
    worker.join(timeout=5)
    stdout.close()
    assert not hung
    assert outcome == [143]
    assert state.with_name("dev.log").read_text() == "early output\n"


@pytest.mark.parametrize("kind", ["symlink", "hardlink"])
def test_lock_admission_never_modifies_special_or_linked_file(state, fake_run, kind):
    import os

    victim = state.with_name("victim")
    victim.write_text("synthetic sentinel")
    lock = state.with_name("dev.lock")
    if kind == "symlink":
        lock.symlink_to(victim)
    elif kind == "hardlink":
        os.link(victim, lock)
    with pytest.raises((OSError, RuntimeError)):
        dev_runner.run([], state)
    assert victim.read_text() == "synthetic sentinel"
    fake_run.popen.assert_not_called()
    assert not state.exists()


def test_replaced_lock_path_is_refused_after_flock(state, fake_run):
    lock = state.with_name("dev.lock")
    lock.write_text("original")

    def replace(fd, operation):
        lock.unlink()
        lock.write_text("replacement")

    dev_runner.fcntl.flock.side_effect = replace
    with pytest.raises(RuntimeError, match="lock"):
        dev_runner.run([], state)
    fake_run.popen.assert_not_called()
    assert lock.read_text() == "replacement"


def test_second_runner_cannot_truncate_or_replace_held_lock(state):
    lock = state.with_name("dev.lock")
    lock.write_text("stable sentinel")
    before = lock.stat()
    with lock.open("r+") as held:
        dev_runner.fcntl.flock(held, dev_runner.fcntl.LOCK_EX | dev_runner.fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="already owned"):
            dev_runner.run([], state)
    assert lock.read_text() == "stable sentinel"
    assert lock.stat().st_ino == before.st_ino


def test_unterminated_output_is_read_in_fixed_chunks(state, fake_run, monkeypatch):
    import hashlib
    import os

    payload = (b"x" * (16384 - 1) + "€".encode() + b"\x1b[31mred\x1b[0m") * 512
    source = state.with_name("output.bin")
    source.write_bytes(payload)
    monkeypatch.setattr(dev_runner, "LOG_MAX_BYTES", 16 * 1024 * 1024)
    terminal = hashlib.sha256()
    writes = []

    class Terminal:
        def write(self, text):
            terminal.update(text.encode())
            writes.append(len(text))

        def flush(self):
            pass

    with source.open("rb", buffering=0) as stream:

        class ChunkOnly:
            def fileno(self):
                return stream.fileno()

            def readline(self):
                raise AssertionError("Unbounded line read")

            def __iter__(self):
                raise AssertionError("Unbounded line iteration")

            def close(self):
                pass

        fake_run.child.stdout = ChunkOnly()
        monkeypatch.setattr(dev_runner.sys, "stdout", Terminal())
        monkeypatch.setattr(
            dev_runner,
            "observe_exit",
            lambda child: object() if stream.tell() == len(payload) else None,
        )
        original_read = os.read
        reads = []

        def read(fd, size):
            assert 0 < size <= 16384
            reads.append(size)
            return original_read(fd, size)

        monkeypatch.setattr(dev_runner.os, "read", read)
        assert dev_runner.run([], state) == 0
    expected_terminal = payload.decode()
    expected_log = dev_runner.ANSI.sub("", expected_terminal)
    assert terminal.hexdigest() == hashlib.sha256(expected_terminal.encode()).hexdigest()
    assert state.with_name("dev.log").read_text() == expected_log
    assert len(reads) > 500
    assert max(writes) <= 16384


@pytest.mark.parametrize(
    "parts",
    [
        [b"\xe2", b"\x82", b"\xac\x1b", b"[3", b"1mred\x1b[", b"0m\n"],
        [b"\x1b[" + b"1" * 128] * 1000,
        [b"partial \xe2"],
    ],
)
def test_incremental_output_decoder_and_ansi_carry_are_bounded(parts, capsys):
    import io

    log = io.StringIO()
    output = dev_runner.OutputLogger(log)
    for part in parts:
        output.write(part)
        assert len(output.pending) <= dev_runner.ANSI_CARRY_LIMIT
        assert len(output.decoder.getstate()[0]) <= 3
    output.write(b"", final=True)
    terminal = capsys.readouterr().out
    assert terminal == b"".join(parts).decode("utf-8", errors="replace")
    if len(parts) < 10:
        assert log.getvalue() == dev_runner.ANSI.sub("", terminal)
    else:
        assert len(log.getvalue()) + dev_runner.ANSI_CARRY_LIMIT >= len(terminal)
    assert not output.pending


@pytest.mark.parametrize("payload", ["synthetic line\n" * 1000, "€" * 10000 + "latest\n"], ids=["lines", "unicode"])
def test_log_retention_bounds_bytes_and_keeps_latest_output(state, fake_run, monkeypatch, capsys, payload):
    source = state.with_name("output.bin")
    source.write_bytes(payload.encode())
    monkeypatch.setattr(dev_runner, "LOG_MAX_BYTES", 128, raising=False)
    monkeypatch.setattr(dev_runner, "LOG_BACKUPS", 2, raising=False)
    with source.open("rb", buffering=0) as stdout:
        fake_run.child.stdout = stdout
        assert dev_runner.run([], state) == 0
    assert capsys.readouterr().out == payload
    logs = sorted(state.parent.glob("dev.log*"))
    assert {path.name for path in logs} == {"dev.log", "dev.log.1", "dev.log.2"}
    assert all(0 < path.stat().st_size <= 128 for path in logs)
    retained = "".join(state.with_name(name).read_text() for name in ("dev.log.2", "dev.log.1", "dev.log"))
    assert payload.endswith(retained)
    assert retained.endswith("line\n" if payload.startswith("synthetic") else "latest\n")


def test_process_table_failure_still_attempts_final_group_kill(state, fake_run, monkeypatch):
    monkeypatch.setattr(dev_runner, "group_alive", Mock(side_effect=PermissionError("synthetic process table denied")))
    with pytest.raises(RuntimeError, match="confirm"):
        dev_runner.run([], state)
    assert signal.SIGKILL in [call.args[1] for call in fake_run.killpg.call_args_list]
    fake_run.child.wait.assert_not_called()
    assert state.exists()


def test_reserved_leader_and_stubborn_child_retire_with_known_inventory(tmp_path, monkeypatch):
    """Use a complete synthetic inventory, without querying unrelated OS processes."""
    import sys
    import time

    import psutil

    pid_file = tmp_path / "child.pid"
    descendant_code = (
        "import os,pathlib,signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid())); time.sleep(60)"
    )
    leader_code = (
        "import pathlib,subprocess,sys,time; "
        f"subprocess.Popen([sys.executable, '-c', {descendant_code!r}]); "
        f"p=pathlib.Path({str(pid_file)!r})\n"
        "while not p.exists(): time.sleep(0.01)\n"
        "sys.exit(23)\n"
    )
    leader = subprocess.Popen([sys.executable, "-c", leader_code], start_new_session=True)
    descendant = None
    try:
        deadline = time.monotonic() + 5
        while dev_runner.observe_exit(leader) is None:
            assert time.monotonic() < deadline
            time.sleep(0.01)
        descendant = psutil.Process(int(pid_file.read_text()))
        monkeypatch.setattr(dev_runner.psutil, "pids", lambda: [leader.pid, descendant.pid])
        monkeypatch.setattr(dev_runner, "TERM_GRACE", 0.5)
        killpg = os.killpg
        signals = []

        def signal_reserved_group(pgid, sig):
            assert leader.returncode is None
            assert dev_runner.observe_exit(leader) is not None
            signals.append(sig)
            killpg(pgid, sig)

        monkeypatch.setattr(dev_runner.os, "killpg", signal_reserved_group)
        dev_runner.retire_group(leader)
        assert leader.returncode == 23
        assert signals == [signal.SIGTERM, signal.SIGKILL]
        assert not descendant.is_running() or descendant.status() == psutil.STATUS_ZOMBIE
    finally:
        if descendant and descendant.is_running():
            descendant.kill()
        if leader.poll() is None:
            leader.kill()
        leader.wait(timeout=5)


@pytest.mark.parametrize("chunk", [b"end \xe2", b"end\x1b[31"], ids=["utf8", "ansi"])
def test_signal_shutdown_finalizes_pending_output(state, fake_run, monkeypatch, chunk):
    source = state.with_name("output.bin")
    source.touch()

    def interrupt(child, output):
        output.write(chunk)
        raise SystemExit(143)

    monkeypatch.setattr(dev_runner, "stream_output", interrupt)
    with source.open("rb", buffering=0) as stdout:
        fake_run.child.stdout = stdout
        with pytest.raises(SystemExit, match="143"):
            dev_runner.run([], state)
    assert state.with_name("dev.log").read_text() == chunk.decode("utf-8", errors="replace")
    assert not state.exists()
