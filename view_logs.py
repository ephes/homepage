#!/usr/bin/env python3
"""
Simple log viewer for development.
Shows the last N lines from dev.log and can filter by patterns.
"""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Iterable
from io import StringIO
from os import SEEK_END
from pathlib import Path

TAIL_BLOCK_SIZE = 8192


def read_tail(log_file: Path, lines: int) -> str:
    if lines == 0:
        return ""

    chunks = []
    with log_file.open("rb") as log:
        end = log.seek(0, SEEK_END)
        position = end
        while position:
            size = min(position, TAIL_BLOCK_SIZE)
            position -= size
            log.seek(position)
            chunk = log.read(size)
            # The final newline terminates the last line instead of starting an empty one.
            if position + size == end and chunk.endswith(b"\n"):
                lines += 1
            newline_count = chunk.count(b"\n")
            if newline_count >= lines:
                offset = len(chunk.rsplit(b"\n", lines)[0]) + 1
                chunks.append(chunk[offset:])
                break
            lines -= newline_count
            chunks.append(chunk)
    # Decode only after rejoining bytes so multibyte characters may span chunks.
    return b"".join(reversed(chunks)).decode("utf-8")


def print_matches(lines: Iterable[str], pattern: str, *, flush: bool = False) -> None:
    needle = pattern.lower()
    for line in lines:
        if needle in line.lower():
            print(line, end="", flush=flush)


def follow_log(log_file: Path, lines: int, grep: str | None) -> int:
    cmd = ["tail", "-n", str(lines), "-F", str(log_file)]
    with subprocess.Popen(cmd, stdout=subprocess.PIPE if grep else None, encoding="utf-8", errors="replace") as tail:
        try:
            if grep and tail.stdout is not None:
                print_matches(tail.stdout, grep, flush=True)
            return tail.wait()
        finally:
            if tail.poll() is None:
                tail.terminate()
                tail.wait()


def view_logs(lines: int = 50, grep: str | None = None, follow: bool = False) -> int:
    if lines < 0:
        raise ValueError("line count must be non-negative")
    log_file = Path("logs/dev.log")

    if not log_file.exists():
        print(f"No log file found at {log_file}")
        print("Run ./run_dev.sh first to start logging")
        return 0

    if follow:
        return follow_log(log_file, lines, grep)

    tail = read_tail(log_file, lines)
    if grep:
        print_matches(StringIO(tail), grep)
    else:
        print(tail, end="")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View development logs")
    parser.add_argument("-n", "--lines", type=int, default=50, help="Number of lines to show")
    parser.add_argument("-g", "--grep", help="Filter lines containing this pattern")
    parser.add_argument("-f", "--follow", action="store_true", help="Follow the active log through rotation")

    args = parser.parse_args()
    if args.lines < 0:
        parser.error("line count must be non-negative")
    try:
        raise SystemExit(view_logs(args.lines, args.grep, args.follow))
    except KeyboardInterrupt:
        raise SystemExit(130) from None
