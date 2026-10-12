"""Tests for scripts/get_video_data.py. ffprobe is always replaced."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "get_video_data.py"
spec = importlib.util.spec_from_file_location("get_video_data", SCRIPT)
get_video_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(get_video_data)

LANDSCAPE = (
    b"Input #0, mov,mp4,m4a,3gp,3g2,mj2, from '%s':\n"
    b"  Duration: 00:00:05.00, start: 0.000000, bitrate: 1000 kb/s\n"
    b"  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(progressive), "
    b"1920x1080 [SAR 1:1 DAR 16:9], 900 kb/s, 30 fps, 30 tbr, 15360 tbn (default)\n"
)
PORTRAIT = LANDSCAPE.replace(b"1920x1080 [SAR 1:1 DAR 16:9]", b"1920x1080 [SAR 81:256 DAR 9:16]")
SIGNED_URL = "https://media.example/clip.mp4?X-Amz-Signature=s3cr3t-signature&X-Amz-Credential=AKIAEXAMPLE"
HOSTILE = "https://media.example/a b.mp4?x=\"$(touch pwned)`touch pwned`;touch pwned' && echo $HOME"


@pytest.fixture
def ffprobe(monkeypatch):
    calls = []

    def install(output=LANDSCAPE, returncode=0, error=None):
        def run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            if error is not None:
                raise error
            stdout = output.replace(b"%s", cmd[-1].encode()) if isinstance(output, bytes) else output
            return subprocess.CompletedProcess(cmd, returncode, stdout=stdout)

        def forbidden(*args, **kwargs):
            raise AssertionError("only subprocess.run with an argument list may be used")

        monkeypatch.setattr(get_video_data.subprocess, "run", run)
        for name in ("check_output", "call", "check_call", "Popen", "getoutput", "getstatusoutput"):
            monkeypatch.setattr(get_video_data.subprocess, name, forbidden)
        return calls

    return install


@pytest.mark.parametrize("source", [HOSTILE, SIGNED_URL, "-version", "--", "-i", "./clip one.mp4", "ünïcode $x.mp4"])
def test_input_is_one_unchanged_argument_without_a_shell(ffprobe, capsys, source):
    calls = ffprobe()

    assert get_video_data.main([source]) == 0

    ((cmd, kwargs),) = calls
    assert isinstance(cmd, list)
    assert cmd == ["ffprobe", "-hide_banner", "-i", source]
    assert not kwargs.get("shell", False)
    assert kwargs["timeout"] == get_video_data.FFPROBE_TIMEOUT_SECONDS
    assert 0 < kwargs["timeout"] <= 300
    assert kwargs["stdin"] is subprocess.DEVNULL
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

    assert recorded.read_text() == f"3\n-hide_banner\n-i\n{source}\n"
    assert not (tmp_path / "pwned").exists()
    captured = capsys.readouterr()
    assert "pwned" not in captured.out + captured.err


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"output": b"%s: Invalid data found when processing input\n", "returncode": 1},
        {"output": b"Input #0, from '%s':\n  Stream #0:0: Audio: aac\n"},
        {"error": subprocess.TimeoutExpired(["ffprobe", "-i", SIGNED_URL], 60, output=SIGNED_URL.encode())},
        {"error": FileNotFoundError(2, "No such file or directory", "ffprobe")},
    ],
    ids=["success", "ffprobe-error", "no-video", "timeout", "missing-ffprobe"],
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


def test_portrait_stream_is_reported_with_swapped_sides(ffprobe, capsys):
    ffprobe(output=PORTRAIT)

    assert get_video_data.main(["clip.mp4"]) == 0

    assert capsys.readouterr().out == "1080 1920\n"


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("  Stream #0:0: Video: h264 (High), yuv420p(tv, bt709), 1280x720 [SAR 1:1 DAR 16:9], 25 fps", (1280, 720)),
        (
            "  Stream #0:0: Video: h264, yuv420p(tv, bt709, progressive), 640x360 [SAR 1:1 DAR 16:9], 25 fps",
            (640, 360),
        ),
        ("  Stream #0:0: Video: mjpeg, yuvj420p(pc), 320x240, 90k tbr", (320, 240)),
        ("  Stream #0:1: Video: h264, yuv420p, 720x1280 [SAR 1:1 DAR 9:16], 30 fps", (1280, 720)),
        ("  Stream #0:0: Audio: aac (LC), 48000 Hz, stereo, fltp", None),
        ("Input #0, mov, from 'https://media.example/SAR/Stream #0:0, 1x2.mp4?sig=x':", None),
    ],
)
def test_stream_description_layouts(line, expected):
    assert get_video_data.parse_dimensions(f"ffprobe banner\n{line}\n") == expected


def test_legacy_encoded_output_is_decoded(ffprobe, capsys):
    ffprobe(output=b"Input #0, from 'caf\xe9.mp4':\n" + LANDSCAPE.split(b"\n", 1)[1])

    assert get_video_data.main(["clip.mp4"]) == 0

    assert capsys.readouterr().out == "1920 1080\n"


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
