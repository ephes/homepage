#!/usr/bin/env python3
"""
Simple log viewer for development.
Shows the last N lines from dev.log and can filter by patterns.
"""

import argparse
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


def view_logs(lines=50, grep=None, follow=False):
    if lines < 0:
        raise ValueError("line count must be non-negative")
    log_file = Path("logs/dev.log")

    if not log_file.exists():
        print(f"No log file found at {log_file}")
        print("Run ./run_dev.sh first to start logging")
        return

    if follow:
        # For following, we'll use tail
        import subprocess

        cmd = ["tail", "-f", str(log_file)]
        if grep:
            # Add grep to filter
            cmd = ["tail", "-f", str(log_file), "|", "grep", "--line-buffered", grep]
            cmd = " ".join(cmd)
            subprocess.run(cmd, shell=True)
        else:
            subprocess.run(cmd)
    else:
        tail = read_tail(log_file, lines)
        if grep:
            needle = grep.lower()
            tail = "".join(line for line in StringIO(tail) if needle in line.lower())
        print(tail, end="")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View development logs")
    parser.add_argument("-n", "--lines", type=int, default=50, help="Number of lines to show")
    parser.add_argument("-g", "--grep", help="Filter lines containing this pattern")
    parser.add_argument("-f", "--follow", action="store_true", help="Follow log file (like tail -f)")

    args = parser.parse_args()
    if args.lines < 0:
        parser.error("line count must be non-negative")
    view_logs(args.lines, args.grep, args.follow)
