"""Synthetic legacy-helper boundaries: never connect or run Docker/SQL."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def helper(monkeypatch):
    # Safe even against the old import-time script: fail before opening a client.
    client = Mock(side_effect=AssertionError("SSH client created during import"))
    monkeypatch.setitem(sys.modules, "paramiko", SimpleNamespace(SSHClient=client))
    dotenv = SimpleNamespace(
        find_dotenv=Mock(side_effect=AssertionError("dotenv lookup during import")), load_dotenv=Mock()
    )
    monkeypatch.setitem(sys.modules, "dotenv", dotenv)
    spec = importlib.util.spec_from_file_location("legacy_transfer", ROOT / "scripts/prod_to_local.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client.assert_not_called()
    dotenv.find_dotenv.assert_not_called()
    dotenv.load_dotenv.assert_not_called()
    return module


def test_import_is_inert(helper):
    assert callable(helper.main)


@pytest.mark.parametrize(
    "name", ["space name.sql.gz", "quote'\".sql.gz", "semi;colon.sql.gz", "$(touch marker).sql.gz"]
)
def test_local_commands_keep_paths_literal(helper, monkeypatch, tmp_path, name):
    path = tmp_path / name
    calls = []

    def run(argv, **kwargs):
        assert isinstance(argv, list)
        assert kwargs.get("shell", False) is False
        assert kwargs["check"] is True
        calls.append(argv)
        return SimpleNamespace(stdout="abcdef123456\n")

    monkeypatch.setattr(helper.subprocess, "run", run)
    restore = Mock()
    monkeypatch.setattr(helper, "restore_local_database", restore)
    helper.restore_download(path, replace_existing=True)
    assert ["docker", "cp", str(path.resolve()), "abcdef123456:/backups"] in calls
    assert ["docker-compose", "-f", "local.yml", "run", "postgres", "restore", name] in calls
    restore.assert_called_once_with(path, replace_existing=True)
    assert not (tmp_path / "marker").exists()
    assert all(argv[0] not in {"dropdb", "createdb", "gunzip", "psql", "bash"} for argv in calls)


def test_process_failure_stops_restore(helper, monkeypatch, tmp_path):
    run = Mock(side_effect=subprocess.CalledProcessError(17, ["docker"]))
    monkeypatch.setattr(helper.subprocess, "run", run)
    restore = Mock()
    monkeypatch.setattr(helper, "restore_local_database", restore)
    with pytest.raises(subprocess.CalledProcessError):
        helper.restore_download(tmp_path / "dump.sql.gz")
    assert run.call_count == 1
    restore.assert_not_called()


@pytest.mark.parametrize("output", ["", "abcdef123456\n123456abcdef\n", "$(touch marker)"])
def test_container_selection_requires_one_id(helper, monkeypatch, tmp_path, output):
    run = Mock(return_value=SimpleNamespace(stdout=output))
    monkeypatch.setattr(helper.subprocess, "run", run)
    with pytest.raises(ValueError):
        helper.restore_download(tmp_path / "dump.sql.gz")
    assert run.call_count == 1


def test_sql_publication_uses_maintained_restore(helper, monkeypatch, tmp_path):
    import commands

    restore = Mock()
    monkeypatch.setattr(commands, "_restore_dump_into_local_database", restore)
    path = tmp_path / "$(literal); quote'.sql.gz"
    helper.restore_local_database(path, replace_existing=False)
    restore.assert_called_once_with(path, "homepage", False)


@pytest.fixture
def transport(helper, monkeypatch, tmp_path):
    import gzip
    import os
    import stat

    payload = gzip.compress(
        b"-- synthetic SQL\nCREATE TABLE example (id integer);\n-- PostgreSQL database dump complete\n"
    )
    channel = Mock()
    channel.recv_ready.side_effect = lambda: bool(channel.output)
    channel.recv_stderr_ready.side_effect = lambda: bool(channel.errors)
    channel.output = b"scp homepage:site/backups/example.sql.gz backups\n"
    channel.errors = b""

    def recv(count):
        result, channel.output = channel.output[:count], channel.output[count:]
        return result

    def recv_error(count):
        result, channel.errors = channel.errors[:count], channel.errors[count:]
        return result

    channel.recv.side_effect = recv
    channel.recv_stderr.side_effect = recv_error
    channel.exit_status_ready.return_value = True
    channel.recv_exit_status.return_value = 0
    streams = [Mock(), Mock(channel=channel), Mock()]
    # Also exercise the old unbounded reader safely in the pre-fix check.
    streams[1].read.return_value = channel.output
    sftp = Mock()
    sftp.lstat.return_value = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_size=len(payload), st_mtime=10)

    def getfo(remote, target, *, callback, prefetch):
        assert prefetch is False
        assert remote.startswith("site/backups/")
        stages = list(tmp_path.rglob(".legacy-backup-*"))
        assert len(stages) == 1 and stages[0].stat().st_mode & 0o777 == 0o700
        assert os.fstat(target.fileno()).st_mode & 0o777 == 0o600
        target.write(payload)
        callback(len(payload), len(payload))
        return len(payload)

    sftp.getfo.side_effect = getfo
    client = Mock()
    client.exec_command.return_value = streams
    client.open_sftp.return_value = sftp
    monkeypatch.setitem(sys.modules, "paramiko", SimpleNamespace(SSHClient=Mock(return_value=client)))
    return SimpleNamespace(client=client, sftp=sftp, channel=channel, streams=streams, payload=payload)


def assert_closed(transport):
    transport.client.close.assert_called_once()
    transport.channel.close.assert_called_once()
    for stream in transport.streams:
        stream.close.assert_called_once()


def test_complete_private_download_and_deadlines(helper, transport, tmp_path):
    path = helper.fetch_backup("host.invalid", "synthetic", tmp_path)
    assert path.read_bytes() == transport.payload
    assert path.stat().st_mode & 0o777 == 0o600
    assert list(tmp_path.iterdir()) == [path]
    connect = transport.client.connect.call_args
    assert connect.kwargs["timeout"] > 0
    assert connect.kwargs["banner_timeout"] > 0
    assert connect.kwargs["auth_timeout"] > 0
    assert connect.kwargs["channel_timeout"] > 0
    assert transport.client.exec_command.call_args.kwargs["timeout"] > 0
    assert transport.sftp.get_channel.return_value.settimeout.call_args.args[0] > 0
    transport.sftp.close.assert_called_once()
    assert_closed(transport)


@pytest.mark.parametrize(
    "name", ["space name.sql.gz", "quote'\".sql.gz", "semi;colon.sql.gz", "$(touch marker).sql.gz"]
)
def test_announced_paths_are_literal(helper, transport, tmp_path, name):
    import shlex

    remote = "site/backups/" + name
    transport.channel.output = f"scp {shlex.quote('homepage:' + remote)} backups\n".encode()
    path = helper.fetch_backup("host.invalid", "synthetic", tmp_path)
    assert path.name == name
    assert transport.sftp.getfo.call_args.args[0] == remote
    assert not (tmp_path / "marker").exists()


@pytest.mark.parametrize(
    "announcement",
    [
        b"",
        b"not scp homepage:site/backups/example.sql.gz backups\n",
        b"scp homepage:site/backups/../example.sql.gz backups\n",
        b"scp homepage:/etc/example.sql.gz backups\n",
        b"scp homepage:site/backups/-example.sql.gz backups\n",
        b"scp other:site/backups/example.sql.gz backups\n",
        b"scp homepage:site/backups/example.sql.gz elsewhere\n",
        b"scp 'unterminated\n",
        b"scp homepage:site/backups/example.sql.gz backups extra\n",
        b"scp homepage:site/backups/example.sql.gz backups\n" * 2,
        b"scp homepage:site/backups/example.sql.gz backups\n\xff",
    ],
)
def test_refuse_ambiguous_or_malformed_announcements(helper, transport, tmp_path, announcement):
    transport.channel.output = announcement
    with pytest.raises(ValueError):
        helper.fetch_backup("host.invalid", "synthetic", tmp_path)
    transport.client.open_sftp.assert_not_called()
    assert list(tmp_path.iterdir()) == []
    assert_closed(transport)


@pytest.mark.parametrize("fault", ["status", "stdout_limit", "stderr_limit", "timeout"])
def test_failed_or_unbounded_remote_never_fetches(helper, transport, monkeypatch, tmp_path, fault):
    if fault == "status":
        transport.channel.recv_exit_status.return_value = 23
    elif fault == "stdout_limit":
        transport.channel.output = b"x" * (helper.MAX_COMMAND_BYTES + 1)
    elif fault == "stderr_limit":
        transport.channel.errors = b"x" * (helper.MAX_COMMAND_BYTES + 1)
    else:
        transport.channel.exit_status_ready.return_value = False
        clock = iter([0, 0, helper.COMMAND_TIMEOUT + 1])
        monkeypatch.setattr(helper.time, "monotonic", lambda: next(clock))
    with pytest.raises((ValueError, TimeoutError)):
        helper.fetch_backup("host.invalid", "synthetic", tmp_path)
    transport.client.open_sftp.assert_not_called()
    assert_closed(transport)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("fault", ["partial", "short", "corrupt", "empty", "oversized", "changed", "symlink", "fifo"])
def test_incomplete_download_never_publishes(helper, transport, tmp_path, fault):
    import stat

    import commands

    attr = transport.sftp.lstat.return_value
    if fault == "partial":

        def partial(remote, target, **kwargs):
            target.write(b"partial")
            raise OSError("synthetic interrupted transfer")

        transport.sftp.getfo.side_effect = partial
    elif fault in {"short", "corrupt"}:

        def broken(remote, target, **kwargs):
            content = b"bad" if fault == "corrupt" else transport.payload[:-4]
            target.write(content)
            return len(content)

        transport.sftp.getfo.side_effect = broken
        if fault == "corrupt":
            attr.st_size = 3
    elif fault == "empty":
        attr.st_size = 0
    elif fault == "oversized":
        attr.st_size = helper.MAX_BACKUP_BYTES + 1
    elif fault == "changed":
        transport.sftp.lstat.side_effect = [attr, SimpleNamespace(**{**vars(attr), "st_mtime": 11})]
    else:
        attr.st_mode = stat.S_IFLNK if fault == "symlink" else stat.S_IFIFO
    with pytest.raises((ValueError, OSError, commands.LocalRestoreError)):
        helper.fetch_backup("host.invalid", "synthetic", tmp_path)
    assert list(tmp_path.iterdir()) == []
    transport.sftp.close.assert_called_once()
    assert_closed(transport)


def test_existing_backup_bytes_are_never_overwritten(helper, transport, tmp_path):
    path = tmp_path / "example.sql.gz"
    path.write_bytes(b"existing synthetic backup")
    with pytest.raises(FileExistsError):
        helper.fetch_backup("host.invalid", "synthetic", tmp_path)
    assert path.read_bytes() == b"existing synthetic backup"
    assert list(tmp_path.iterdir()) == [path]
    assert_closed(transport)


@pytest.mark.parametrize("resource", ["client", "sftp", "channel", "stdin", "stdout", "stderr"])
def test_cleanup_failure_prevents_publication_and_local_steps(helper, transport, monkeypatch, tmp_path, resource):
    objects = dict(client=transport.client, sftp=transport.sftp, channel=transport.channel)
    objects.update(zip(["stdin", "stdout", "stderr"], transport.streams, strict=True))
    objects[resource].close.side_effect = OSError("synthetic close failure")
    restore = Mock()
    monkeypatch.setattr(helper, "restore_download", restore)
    with pytest.raises(OSError):
        helper.transfer_and_restore("host.invalid", "synthetic", tmp_path / "backups")
    restore.assert_not_called()
    assert list((tmp_path / "backups").iterdir()) == []
    transport.sftp.close.assert_called_once()
    assert_closed(transport)


@pytest.mark.parametrize("phase", ["connect", "exec", "open_sftp", "getfo"])
def test_acquisition_or_deadline_failure_closes_owned_resources(helper, transport, tmp_path, phase):
    target = {
        "connect": transport.client.connect,
        "exec": transport.client.exec_command,
        "open_sftp": transport.client.open_sftp,
        "getfo": transport.sftp.getfo,
    }[phase]
    target.side_effect = TimeoutError("synthetic timeout")
    with pytest.raises(TimeoutError):
        helper.fetch_backup("host.invalid", "synthetic", tmp_path)
    transport.client.close.assert_called_once()
    if phase in {"open_sftp", "getfo"}:
        assert_closed(transport)
    if phase == "getfo":
        transport.sftp.close.assert_called_once()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("phase", ["remote", "transfer"])
def test_hard_deadline_interrupts_stalled_negotiation(helper, transport, monkeypatch, tmp_path, phase):
    import signal

    def stalled(*args, **kwargs):
        signal.raise_signal(signal.SIGALRM)

    original_handler = signal.getsignal(signal.SIGALRM)
    target = transport.client.exec_command if phase == "remote" else transport.sftp.getfo
    target.side_effect = stalled
    restore = Mock()
    monkeypatch.setattr(helper, "restore_download", restore)
    with pytest.raises(TimeoutError):
        helper.transfer_and_restore("host.invalid", "synthetic", tmp_path)
    restore.assert_not_called()
    assert signal.getsignal(signal.SIGALRM) == original_handler
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    transport.client.close.assert_called_once()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("fault", ["status", "partial", "oversized", "invalid_gzip"])
def test_transfer_refusal_never_starts_local_steps(helper, transport, monkeypatch, tmp_path, fault):
    import commands

    if fault == "status":
        transport.channel.recv_exit_status.return_value = 5
    elif fault == "partial":
        transport.sftp.getfo.side_effect = OSError("synthetic interrupted download")
    elif fault == "oversized":
        transport.sftp.lstat.return_value.st_size = helper.MAX_BACKUP_BYTES + 1
    else:
        transport.sftp.getfo.side_effect = lambda remote, target, **kwargs: target.write(b"x" * len(transport.payload))
    restore = Mock()
    monkeypatch.setattr(helper, "restore_download", restore)
    with pytest.raises((ValueError, OSError, commands.LocalRestoreError)):
        helper.transfer_and_restore("host.invalid", "synthetic", tmp_path)
    restore.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_success_only_restores_published_artifact(helper, transport, monkeypatch, tmp_path):
    def restore(path, **kwargs):
        assert path.read_bytes() == transport.payload
        assert list(tmp_path.iterdir()) == [path]
        assert kwargs == {"replace_existing": True}
        transport.client.close.assert_called_once()
        transport.sftp.close.assert_called_once()

    local = Mock(side_effect=restore)
    monkeypatch.setattr(helper, "restore_download", local)
    helper.transfer_and_restore("host.invalid", "synthetic", tmp_path, replace_existing=True)
    local.assert_called_once()


def test_complete_gzip_without_dump_marker_is_not_published(helper, transport, tmp_path):
    import gzip

    import commands

    data = gzip.compress(b"-- synthetic unfinished SQL\n")
    transport.sftp.lstat.return_value.st_size = len(data)
    transport.sftp.getfo.side_effect = lambda remote, target, **kwargs: target.write(data)
    with pytest.raises(commands.LocalRestoreError):
        helper.fetch_backup("host.invalid", "synthetic", tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert_closed(transport)


def test_growing_transfer_stops_before_publication(helper, transport, tmp_path):
    def grow(remote, target, *, callback, **kwargs):
        target.write(transport.payload)
        callback(len(transport.payload) + 1, len(transport.payload))

    transport.sftp.getfo.side_effect = grow
    with pytest.raises(ValueError):
        helper.fetch_backup("host.invalid", "synthetic", tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert_closed(transport)


def test_owned_timer_is_refused_before_client_acquisition(helper, transport, tmp_path):
    import signal

    signal.setitimer(signal.ITIMER_REAL, 60)
    try:
        with pytest.raises(ValueError, match="unused real-time timer"):
            helper.fetch_backup("host.invalid", "synthetic", tmp_path)
        transport.client.connect.assert_not_called()
        transport.client.close.assert_not_called()
        assert signal.getitimer(signal.ITIMER_REAL)[0] > 0
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    assert list(tmp_path.iterdir()) == []


def test_existing_symlink_is_preserved(helper, transport, tmp_path):
    previous = tmp_path / "prior.sql.gz"
    previous.write_bytes(b"synthetic previous backup")
    final = tmp_path / "example.sql.gz"
    final.symlink_to(previous)
    with pytest.raises(FileExistsError):
        helper.fetch_backup("host.invalid", "synthetic", tmp_path)
    assert final.is_symlink()
    assert previous.read_bytes() == b"synthetic previous backup"
    assert sorted(tmp_path.iterdir()) == sorted([previous, final])
