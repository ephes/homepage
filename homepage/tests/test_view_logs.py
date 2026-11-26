import os
import signal
import subprocess
import sys
from contextlib import suppress
from pathlib import Path
from select import select
from unittest.mock import MagicMock, Mock

import pytest

import view_logs


@pytest.fixture
def log_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = Path("logs/dev.log")
    path.parent.mkdir()
    path.touch()
    return path


def test_zero_lines_prints_nothing(log_path, capsys):
    log_path.write_text("earlier\n", encoding="utf-8")

    view_logs.view_logs(lines=0)

    assert capsys.readouterr().out == ""


def test_negative_lines_are_a_usage_error(log_path):
    result = subprocess.run(
        [sys.executable, view_logs.__file__, "-n", "-1"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "non-negative" in result.stderr


@pytest.mark.parametrize("ending", ["", "\n"])
def test_tail_reads_only_requested_lines_and_decodes_across_blocks(log_path, monkeypatch, capsys, ending):
    block_size = 8192
    last_line = "prefix-é" + "x" * (block_size - 2) + ending
    with log_path.open("wb") as log:
        log.seek(5 * 1024 * 1024)
        log.write(b"\nEarlier [match]\n")
        log.write(last_line.encode("utf-8"))

    with log_path.open("rb") as log:
        counted_log = MagicMock(wraps=log)
        counted_log.__enter__.return_value = counted_log
        opener = Mock(return_value=counted_log)
        monkeypatch.setattr(Path, "open", opener)

        view_logs.view_logs(lines=1, grep="PREFIX-É")

    assert capsys.readouterr().out == last_line
    assert 0 < sum(call.args[0] for call in counted_log.read.call_args_list) <= 2 * block_size
    counted_log.readlines.assert_not_called()


def test_filter_is_literal_and_limited_to_selected_tail(log_path, capsys):
    log_path.write_text("[match] earlier\nmatch only\n[MATCH] selected\n", encoding="utf-8")

    view_logs.view_logs(lines=2, grep="[match]")

    assert capsys.readouterr().out == "[MATCH] selected\n"


@pytest.mark.parametrize("filtered", [False, True])
def test_follow_reopens_rotated_log_and_limits_initial_tail(log_path, filtered):
    log_path.write_text(
        "[match] tag outside backlog\nmatch tag without brackets\n[MATCH] TAG initial\n" if filtered else "initial\n",
        encoding="utf-8",
    )
    args = ["-n", "2", "-g", "[match] tag"] if filtered else ["-n", "1"]
    with subprocess.Popen(
        [sys.executable, view_logs.__file__, "-f", *args],
        stdout=subprocess.PIPE,
        bufsize=0,
        start_new_session=True,
    ) as viewer:
        try:
            assert select([viewer.stdout], [], [], 8)[0], "viewer did not print the initial tail"
            assert viewer.stdout.readline() == (b"[MATCH] TAG initial\n" if filtered else b"initial\n")

            log_path.rename(log_path.with_suffix(".log.1"))
            log_path.write_text(
                "match tag without brackets\n[MaTcH] tAg replacement\n" if filtered else "replacement\n",
                encoding="utf-8",
            )
            assert select([viewer.stdout], [], [], 8)[0], "viewer did not reopen the active path"
            assert viewer.stdout.readline() == (b"[MaTcH] tAg replacement\n" if filtered else b"replacement\n")

            # Signal only Python so the test requires the viewer to retire its own tail.
            viewer.send_signal(signal.SIGINT)
            assert viewer.wait(timeout=5) == 130
            assert select([viewer.stdout], [], [], 1)[0], "tail still holds the output pipe open"
            assert viewer.stdout.read(1) == b""
        finally:
            with suppress(ProcessLookupError):
                os.killpg(viewer.pid, signal.SIGKILL)
