"""Print the width and height of a video as ffprobe reports them.

Usage::

    uv run python scripts/get_video_data.py <local path or URL>

The argument is handed to ffprobe as the value of ``-i`` in an argument list,
never through a shell: quotes, spaces, ``$(...)`` or backticks in it are plain
text, and a value that starts with ``-`` is still the input, not an option
(ffprobe has no ``--`` separator, the ``-i`` option is its boundary).

The input itself is never printed. A signed URL (query string with
credentials) therefore does not end up in terminal scrollback or logs, and
ffprobe's own output, which repeats the input, is parsed but not shown.
ffprobe gets 60 seconds; a hanging remote source ends with an error.
"""

import re
import subprocess
import sys

FFPROBE_TIMEOUT_SECONDS = 60
# "1920x1080" or "1920x1080 [SAR 1:1 DAR 16:9]" as one comma separated field.
_SIZE = re.compile(r", (\d+)x(\d+)(?: \[SAR \d+:\d+ DAR (\d+):(\d+)\])?(?=,|\s|$)")


class VideoProbeError(Exception):
    """ffprobe could not be run or its output held no video size."""


def ffprobe_command(source: str) -> list[str]:
    """Return the ffprobe argument list; ``source`` is one unchanged argument after ``-i``."""
    return ["ffprobe", "-hide_banner", "-i", source]


def decode_output(output: bytes) -> str:
    for encoding in ("utf-8", "utf-16"):
        try:
            return output.decode(encoding)
        except UnicodeDecodeError:
            continue
    return output.decode("latin-1")


def parse_dimensions(output: str) -> tuple[int, int] | None:
    """Return (width, height) from ffprobe's stream description, or None.

    As before, a stream whose display aspect ratio (DAR) is portrait is reported
    with its sides swapped, and the last matching line wins. The size is found
    by its ``<width>x<height>`` shape, wherever it is in the line.
    """
    dimensions = None
    for line in output.split("\n"):
        if "SAR" not in line and "Stream #0:0" not in line:
            continue
        size = _SIZE.search(line)
        if size is None:
            # Not a video stream description (the line may also be ffprobe
            # repeating the input); it carries no size.
            continue
        width, height = int(size.group(1)), int(size.group(2))
        if size.group(3) is not None and int(size.group(3)) < int(size.group(4)):
            width, height = height, width
        dimensions = (width, height)
    return dimensions


def probe(source: str, timeout: float = FFPROBE_TIMEOUT_SECONDS) -> tuple[int, int]:
    if not source or "\x00" in source:
        raise VideoProbeError("the input must be a non-empty path or URL")
    try:
        result = subprocess.run(
            ffprobe_command(source),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise VideoProbeError(f"ffprobe did not finish within {timeout:g} seconds") from None
    except OSError as error:
        raise VideoProbeError(f"ffprobe could not be started ({error.strerror or type(error).__name__})") from None
    # ffprobe's output repeats the input, so it is never shown in an error.
    if result.returncode != 0:
        raise VideoProbeError(f"ffprobe failed with exit status {result.returncode}")
    dimensions = parse_dimensions(decode_output(result.stdout))
    if dimensions is None:
        raise VideoProbeError("ffprobe reported no video size for the input")
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
