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
    spec = importlib.util.spec_from_file_location("legacy_transfer", ROOT / "scripts/prod_to_local.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client.assert_not_called()
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
