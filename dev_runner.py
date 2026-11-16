"""Own one checkout's local development supervisor and its process group."""

import argparse
import codecs
import contextlib
import fcntl
import json
import os
import re
import select
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "logs" / "dev.json"
TERM_GRACE = 1.0
KILL_GRACE = 2.0
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUPS = 2
READ_SIZE = 16384
ANSI_CARRY_LIMIT = 256
ANSI = re.compile(r"\x1b\[[0-9;]*m")
ANSI_PREFIX = re.compile(r"\x1b(?:\[[0-9;]*)?\Z")


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


def observe_exit(child):
    """Peek at the leader without releasing its PID/process-group identity."""
    return os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)


def group_alive(pgid):
    """Zombies cannot run or fork; the unreaped leader still reserves the PGID."""
    for pid in psutil.pids():
        try:
            if os.getpgid(pid) == pgid and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE:
                return True
        except (ProcessLookupError, psutil.NoSuchProcess):
            continue
    return False


def retire_group(child):
    """Finish every group signal before reaping the leader; fail with evidence."""
    scan_error = None
    for sig, grace in ((signal.SIGTERM, TERM_GRACE), (signal.SIGKILL, KILL_GRACE)):
        observe_exit(child)  # Refuse to signal if another waiter released our identity.
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + grace
        while True:
            try:
                alive = group_alive(child.pid)
            except (OSError, psutil.Error) as exc:
                scan_error = exc
                break  # Still attempt the final KILL, but never claim retirement.
            if not alive:
                if sig == signal.SIGKILL:
                    child.wait(timeout=KILL_GRACE)
                    return
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(0.02)
        # A final KILL also fences forks racing the last process-table snapshot.
    if scan_error is not None:
        raise RuntimeError("Cannot confirm owned group retirement; retaining ownership record") from scan_error
    raise RuntimeError("Owned process group did not retire; retaining ownership record")


class RotatingLog:
    """Keep only the active log and two backups, each bounded in actual bytes."""

    def __init__(self, path):
        self.path = path
        self.size = 0
        self.file = path.open("wb")

    def rotate(self):
        self.file.close()
        for index in range(LOG_BACKUPS, 1, -1):
            source = self.path.with_name(f"{self.path.name}.{index - 1}")
            if source.exists():
                source.replace(self.path.with_name(f"{self.path.name}.{index}"))
        self.path.replace(self.path.with_name(f"{self.path.name}.1"))
        self.file = self.path.open("wb")
        self.size = 0

    def write(self, text):
        data = text.encode("utf-8")
        while data:
            end = min(len(data), LOG_MAX_BYTES - self.size)
            # Each retained file is valid UTF-8, even at a rotation boundary.
            if end < len(data):
                while end and data[end] & 0xC0 == 0x80:
                    end -= 1
            if not end:
                self.rotate()
                continue
            self.file.write(data[:end])
            self.size += end
            data = data[end:]

    def flush(self):
        self.file.flush()

    def close(self):
        self.file.close()


class OutputLogger:
    """Decode fixed byte chunks and retain only a bounded possible colour suffix."""

    def __init__(self, log):
        self.log = log
        self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.pending = ""

    def write(self, chunk, final=False):
        text = self.decoder.decode(chunk, final=final)
        print(text, end="", flush=True)
        plain = ANSI.sub("", self.pending + text)
        self.pending = ""
        if not final:
            start = plain.rfind("\x1b")
            if start >= 0 and len(plain) - start <= ANSI_CARRY_LIMIT and ANSI_PREFIX.fullmatch(plain[start:]):
                self.pending = plain[start:]
                plain = plain[:start]
        self.log.write(plain)
        self.log.flush()


def stream_output(child, output):
    os.set_blocking(child.stdout.fileno(), False)
    eof = False
    while observe_exit(child) is None:
        if eof:
            time.sleep(0.02)
        elif select.select([child.stdout], [], [], 0.02)[0]:
            try:
                chunk = os.read(child.stdout.fileno(), READ_SIZE)
            except BlockingIOError:
                continue
            if chunk:
                output.write(chunk)
            else:
                eof = True


def drain_output(child, output):
    # Owned writers are retired. Do not wait on a pipe held by an escaped process.
    deadline = time.monotonic() + KILL_GRACE
    while time.monotonic() < deadline:
        try:
            chunk = os.read(child.stdout.fileno(), READ_SIZE)
        except BlockingIOError:
            break
        if not chunk:
            break
        output.write(chunk)
    output.write(b"", final=True)


@contextlib.contextmanager
def open_lock(path):
    """Hold one nontruncating, owned, single-link lock inode for the whole run."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_uid != os.geteuid() or opened.st_nlink != 1:
            raise RuntimeError("Refusing unsafe development lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Development services already owned by this checkout") from exc
        named = os.stat(path, follow_symlinks=False)
        held = os.fstat(fd)
        if (
            (named.st_dev, named.st_ino) != (held.st_dev, held.st_ino)
            or not stat.S_ISREG(named.st_mode)
            or held.st_uid != os.geteuid()
            or held.st_nlink != 1
        ):
            raise RuntimeError("Development lock identity changed while acquiring ownership")
        yield fd
    finally:
        os.close(fd)


def run(processes, state=STATE):
    state.parent.mkdir(parents=True, exist_ok=True)
    # The lock lives for the entire run; never unlink the lock file.
    with open_lock(state.parent / "dev.lock"):
        if state.exists():
            raise RuntimeError(f"Refusing to overwrite {state}; inspect/remove stale state first")
        child = None
        retired = False
        previous = {
            sig: signal.signal(sig, interrupted)
            for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT)
        }
        try:
            owner = psutil.Process()
            record = {"pid": owner.pid, "created": owner.create_time()}
            state.write_text(json.dumps(record))
            child = subprocess.Popen(
                ["uvx", "honcho", "start", *processes],
                cwd=ROOT,
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
            )
            record["pgid"] = child.pid
            state.write_text(json.dumps(record))
            with contextlib.closing(RotatingLog(state.parent / "dev.log")) as log:
                output = OutputLogger(log)
                try:
                    stream_output(child, output)
                finally:
                    # Keep logging open through signal-driven retirement and final decoding.
                    for sig in previous:
                        signal.signal(sig, signal.SIG_IGN)
                    retire_group(child)
                    retired = True
                    drain_output(child, output)
            result = child.returncode
            return result if result >= 0 else 128 - result
        finally:
            # Repeated interrupts must not interrupt teardown or its escalation.
            for sig in previous:
                signal.signal(sig, signal.SIG_IGN)
            try:
                if child is not None and not retired:
                    retire_group(child)
                state.unlink(missing_ok=True)
            finally:
                if child is not None:
                    child.stdout.close()
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
