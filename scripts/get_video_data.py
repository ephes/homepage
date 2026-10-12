"""Print the width and height of a video as ffprobe reports them.

Usage::

    uv run python scripts/get_video_data.py <local path or URL>

The argument is handed to ffprobe as the value of ``-i`` in an argument list,
never through a shell: quotes, spaces, ``$(...)`` or backticks in it are plain
text, and a value that starts with ``-`` is still the input, not an option
(ffprobe has no ``--`` separator, the ``-i`` option is its boundary).

Only the first video stream's width, height and display aspect ratio are
requested, as JSON, so nothing is guessed from text that could contain the
file name. The input itself is never printed and ffprobe's messages, which
repeat it, are discarded: a signed URL (query string with credentials) does
not end up in terminal scrollback or logs. ffprobe gets 60 seconds; a hanging
remote source ends with an error.
"""

import json
import subprocess
import sys

FFPROBE_TIMEOUT_SECONDS = 60


class VideoProbeError(Exception):
    """ffprobe could not be run or reported no video stream with a size."""


def ffprobe_command(source: str) -> list[str]:
    """Return the ffprobe argument list; ``source`` is one unchanged argument after ``-i``."""
    return [
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
        source,
    ]


def parse_dimensions(output: bytes | str) -> tuple[int, int] | None:
    """Return (width, height) of the first video stream in ffprobe's JSON report, or None.

    As before, a stream whose display aspect ratio is portrait is reported with
    its sides swapped.
    """
    try:
        streams = json.loads(output)["streams"]
        stream = streams[0]
        width, height = stream["width"], stream["height"]
    except (ValueError, LookupError, TypeError):
        return None
    if not all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in (width, height)):
        return None
    try:
        aspect_width, aspect_height = map(int, stream.get("display_aspect_ratio", "").split(":"))
    except (ValueError, AttributeError):
        aspect_width = aspect_height = 0
    if 0 < aspect_width < aspect_height:
        width, height = height, width
    return width, height


def probe(source: str, timeout: float = FFPROBE_TIMEOUT_SECONDS) -> tuple[int, int]:
    if not source or "\x00" in source:
        raise VideoProbeError("the input must be a non-empty path or URL")
    try:
        result = subprocess.run(
            ffprobe_command(source),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise VideoProbeError(f"ffprobe did not finish within {timeout:g} seconds") from None
    except OSError as error:
        raise VideoProbeError(f"ffprobe could not be started ({error.strerror or type(error).__name__})") from None
    # ffprobe's messages repeat the input, so they are discarded and never shown.
    if result.returncode != 0:
        raise VideoProbeError(f"ffprobe failed with exit status {result.returncode}")
    dimensions = parse_dimensions(result.stdout)
    if dimensions is None:
        raise VideoProbeError("ffprobe reported no video stream with a size for the input")
    return dimensions


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: get_video_data.py <local path or URL>", file=sys.stderr)
        return 2
    try:
        width, height = probe(args[0])
    except VideoProbeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(width, height)
    return 0


if __name__ == "__main__":
    sys.exit(main())
