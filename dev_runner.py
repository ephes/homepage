"""Own one checkout's local development supervisor and its process group."""

import argparse
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "logs" / "dev.json"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def cleanup(state=STATE):
    """Signal only the recorded runner, checking its identity before sending."""
    if not state.exists():
        return
    try:
        record = json.loads(state.read_text())
        process = psutil.Process(record["pid"])
        if (
            process.create_time() != record["created"]
            or process.cwd() != str(ROOT)
            or process.cmdline()[1:2] != [str(Path(__file__).resolve())]
        ):
            raise ValueError("process identity does not match")
        # psutil rechecks PID reuse when sending the signal.
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=15)
    except (KeyError, TypeError, ValueError, OSError, psutil.Error) as exc:
        raise RuntimeError(f"Refusing cleanup of stale/mismatching {state}: {exc}") from exc


def interrupted(signum, frame):
    raise SystemExit(128 + signum)


def run(processes, state=STATE):
    state.parent.mkdir(parents=True, exist_ok=True)
    # The lock lives for the entire run; never unlink the lock file.
    with (state.parent / "dev.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Development services already owned by this checkout") from exc
        if state.exists():
            raise RuntimeError(f"Refusing to overwrite {state}; inspect/remove stale state first")
        child = None
        previous = {
            sig: signal.signal(sig, interrupted)
            for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT)
        }
        try:
            owner = psutil.Process()
            state.write_text(json.dumps({"pid": owner.pid, "created": owner.create_time()}))
            child = subprocess.Popen(
                ["uvx", "honcho", "start", *processes],
                cwd=ROOT,
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
            )
            with (state.parent / "dev.log").open("w") as log:
                for line in child.stdout:
                    print(line, end="", flush=True)
                    log.write(ANSI.sub("", line))
                    log.flush()
            result = child.wait()
            return result if result >= 0 else 128 - result
        finally:
            # Repeated interrupts must not interrupt teardown or its escalation.
            for sig in previous:
                signal.signal(sig, signal.SIG_IGN)
            try:
                if child is not None:
                    # This group was created by this run, never discovered by name.
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
            finally:
                state.unlink(missing_ok=True)
                for sig, handler in previous.items():
                    signal.signal(sig, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("processes", nargs="*")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    try:
        if args.cleanup:
            cleanup()
            return 0
        return run(args.processes)
    except (OSError, RuntimeError) as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
