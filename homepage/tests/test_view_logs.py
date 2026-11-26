import subprocess
import sys
from pathlib import Path
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
