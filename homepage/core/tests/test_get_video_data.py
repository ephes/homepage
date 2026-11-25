"""Tests for scripts/get_video_data.py. ffprobe is always replaced."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "get_video_data.py"
spec = importlib.util.spec_from_file_location("get_video_data", SCRIPT)
get_video_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(get_video_data)


def report(width=1920, height=1080, aspect="16:9"):
    stream = {"width": width, "height": height}
    if aspect is not None:
        stream["display_aspect_ratio"] = aspect
    return json.dumps({"programs": [], "streams": [stream]}).encode()


LANDSCAPE = report()
NO_VIDEO = json.dumps({"programs": [], "streams": []}).encode()
EXPECTED_OPTIONS = [
    "ffprobe",
    "-v",
    "error",
    "-select_streams",
    "v:0",
    "-show_entries",
    "stream=width,height,display_aspect_ratio",
    "-of",
    "json",
    "-i",
]
SIGNED_URL = "https://media.example/clip.mp4?X-Amz-Signature=s3cr3t-signature&X-Amz-Credential=AKIAEXAMPLE"
HOSTILE = "https://media.example/a b.mp4?x=\"$(touch pwned)`touch pwned`;touch pwned' && echo $HOME"


@pytest.fixture
def ffprobe(monkeypatch):
    calls = []

    def install(output=LANDSCAPE, returncode=0, error=None):
        def popen(cmd, **kwargs):
            calls.append((cmd, kwargs))
            if isinstance(error, FileNotFoundError):
                raise error
            process = MagicMock(returncode=returncode)
            process.__enter__.return_value = process
            process.wait.return_value = returncode
            return process

        def read_report(fd, deadline):
            if isinstance(error, subprocess.TimeoutExpired):
                raise error
            return output

        def forbidden(*args, **kwargs):
            raise AssertionError("the probe must use Popen with an argument list")

        monkeypatch.setattr(get_video_data.subprocess, "Popen", popen)
        monkeypatch.setattr(get_video_data, "read_probe_report", read_report)
        for name in ("run", "check_output", "call", "check_call", "getoutput", "getstatusoutput"):
            monkeypatch.setattr(get_video_data.subprocess, name, forbidden)
        return calls

    return install


@pytest.mark.parametrize("source", [HOSTILE, SIGNED_URL, "-version", "--", "-i", "./clip one.mp4", "ünïcode $x.mp4"])
def test_input_is_one_unchanged_argument_without_a_shell(ffprobe, capsys, source):
    calls = ffprobe()

    assert get_video_data.main([source]) == 0

    ((cmd, kwargs),) = calls
    assert isinstance(cmd, list)
    assert cmd == [*EXPECTED_OPTIONS, source]
    assert not kwargs.get("shell", False)
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["stdout"] is subprocess.PIPE
    assert kwargs["stderr"] is subprocess.DEVNULL  # ffprobe's messages repeat the input
    assert capsys.readouterr().out == "1920 1080\n"


def test_hostile_input_does_not_run_commands_with_the_real_subprocess(tmp_path, monkeypatch, capsys):
    """With a real process: a stand-in ffprobe records its arguments, nothing else runs."""
    recorded = tmp_path / "argv.txt"
    fake = tmp_path / "bin" / "ffprobe"
    fake.parent.mkdir()
    fake.write_text(f'#!/bin/sh\nprintf \'%s\\n\' "$#" "$@" > "{recorded}"\n')
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake.parent}:/usr/bin:/bin")
    monkeypatch.chdir(tmp_path)
    source = 'clip.mp4"; touch pwned; $(touch pwned) `touch pwned`'

    assert get_video_data.main([source]) == 1  # the stand-in prints no stream description

    assert recorded.read_text() == "\n".join([str(len(EXPECTED_OPTIONS)), *EXPECTED_OPTIONS[1:], source, ""])
    assert not (tmp_path / "pwned").exists()
    captured = capsys.readouterr()
    assert "pwned" not in captured.out + captured.err


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"output": SIGNED_URL.encode() + b": Invalid data found when processing input\n", "returncode": 1},
        {"output": NO_VIDEO},
        {"output": b"Input #0, from '" + SIGNED_URL.encode() + b"':\n  Stream #0:0: Video: h264, 12x34\n"},
        {"error": subprocess.TimeoutExpired(["ffprobe", "-i", SIGNED_URL], 60, output=SIGNED_URL.encode())},
        {"error": FileNotFoundError(2, "No such file or directory", "ffprobe")},
    ],
    ids=["success", "ffprobe-error", "no-video", "not-json", "timeout", "missing-ffprobe"],
)
def test_signed_url_is_never_printed(ffprobe, capsys, kwargs):
    ffprobe(**kwargs)

    status = get_video_data.main([SIGNED_URL])

    captured = capsys.readouterr()
    for secret in ("s3cr3t-signature", "AKIAEXAMPLE", "X-Amz", "media.example"):
        assert secret not in captured.out + captured.err
    if kwargs:
        assert status == 1
        assert captured.out == ""
        assert captured.err.startswith("error: ")
        assert "Traceback" not in captured.err
    else:
        assert status == 0


def test_timeout_and_missing_binary_are_reported(ffprobe, capsys):
    ffprobe(error=subprocess.TimeoutExpired(["ffprobe"], 60))
    assert get_video_data.main(["clip.mp4"]) == 1
    assert "did not finish within 60 seconds" in capsys.readouterr().err

    ffprobe(error=FileNotFoundError(2, "No such file or directory", "ffprobe"))
    assert get_video_data.main(["clip.mp4"]) == 1
    assert "could not be started" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("output_size", "close_stdout", "timeout", "message"),
    [
        # The size limit is hit without waiting, so a generous deadline keeps a
        # slow interpreter start from turning this case into a timeout.
        (65537, False, 30, "ffprobe JSON report exceeded 65536 bytes"),
        (32, False, 0.75, "ffprobe did not finish within"),
        (32, True, 0.75, "ffprobe did not finish within"),
    ],
    ids=["oversized", "stalled-reading", "stalled-after-eof"],
)
def test_probe_bounds_output_and_reaps_child(monkeypatch, output_size, close_stdout, timeout, message):
    child = (
        "import os, sys, time; "
        "os.write(2, sys.argv[1].encode()); "
        f"os.write(1, b'x' * {output_size}); " + ("os.close(1); " if close_stdout else "") + "time.sleep(60)"
    )
    monkeypatch.setattr(get_video_data, "ffprobe_command", lambda source: [sys.executable, "-c", child, source])
    started = []
    real_popen = subprocess.Popen

    def recording_popen(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        started.append(process)
        return process

    monkeypatch.setattr(get_video_data.subprocess, "Popen", recording_popen)

    with pytest.raises(get_video_data.VideoProbeError, match=message) as caught:
        get_video_data.probe(SIGNED_URL, timeout=timeout)

    assert SIGNED_URL not in str(caught.value)
    [process] = started
    assert process.returncode is not None
    with pytest.raises(ChildProcessError):
        os.waitpid(process.pid, os.WNOHANG)


def test_probe_accepts_a_valid_report_at_the_limit(monkeypatch):
    child = f"import sys; sys.stdout.buffer.write({LANDSCAPE!r}.ljust(65536))"
    monkeypatch.setattr(get_video_data, "ffprobe_command", lambda source: [sys.executable, "-c", child])

    assert get_video_data.probe("clip.mp4") == (1920, 1080)


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (report(1280, 720, "16:9"), (1280, 720)),
        (report(320, 240, None), (320, 240)),
        (report(320, 240, "N/A"), (320, 240)),
        (report(320, 240, "0:1"), (320, 240)),
        (report(1920, 1080, "9:16"), (1080, 1920)),
        (report(720, 1280, "9:16"), (1280, 720)),
        (NO_VIDEO, None),
        (b"{}", None),
        (b"[]", None),
        (b"", None),
        (b"\xff\xfe not json", None),
        (report(0, 1080), None),
        (report("1920", "1080"), None),
        (report(True, 1080), None),
        (json.dumps({"streams": [{"width": 1920, "height": 1080, "display_aspect_ratio": 3}]}).encode(), (1920, 1080)),
    ],
)
def test_report_layouts(ffprobe, capsys, output, expected):
    ffprobe(output=output)

    status = get_video_data.main(["clip.mp4"])

    captured = capsys.readouterr()
    if expected is None:
        assert status == 1
        assert captured.out == ""
        assert "no video stream with a size" in captured.err
    else:
        assert status == 0
        assert captured.out == f"{expected[0]} {expected[1]}\n"


def test_size_is_not_guessed_from_a_file_name(tmp_path, monkeypatch, capsys):
    """An audio file whose name looks like a stream description has no video size.

    The stand-in ffprobe behaves like the real one for an audio-only file: it
    reports no video stream as JSON and repeats the file name on stderr.
    """
    fake = tmp_path / "bin" / "ffprobe"
    fake.parent.mkdir()
    fake.write_text(
        "#!/bin/sh\n"
        "for last; do :; done\n"
        "printf 'Input #0, wav, from %s:\\n  Stream #0:0: Video: x, 12x34 [SAR 1:1 DAR 1:2]\\n' \"$last\" >&2\n"
        """printf '{"programs": [], "streams": []}\\n'\n"""
    )
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake.parent}:/usr/bin:/bin")

    assert get_video_data.main(["SAR, 12x34 audio.wav"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: ffprobe reported no video stream with a size for the input\n"


@pytest.mark.parametrize("argv", [[], ["a.mp4", "b.mp4"], [""], ["a\x00b.mp4"]])
def test_wrong_usage_runs_nothing(ffprobe, capsys, argv):
    calls = ffprobe()

    assert get_video_data.main(argv) in (1, 2)

    assert calls == []
    assert capsys.readouterr().out == ""


def test_importing_the_script_runs_nothing():
    source = SCRIPT.read_text()
    assert "shell=True" not in source
    assert 'if __name__ == "__main__":' in source
