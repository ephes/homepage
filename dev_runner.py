"""Own one checkout's local development supervisor and its process group."""

import argparse
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
    for sig, grace in ((signal.SIGTERM, TERM_GRACE), (signal.SIGKILL, KILL_GRACE)):
        observe_exit(child)  # Refuse to signal if another waiter released our identity.
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + grace
        while group_alive(child.pid):
            if time.monotonic() >= deadline:
                break
            time.sleep(0.02)
        else:
            if sig == signal.SIGKILL:
                child.wait(timeout=KILL_GRACE)
                return
        # A final KILL also fences forks racing the last process-table snapshot.
    raise RuntimeError("Owned process group did not retire; retaining ownership record")


def stream_output(child, log):
    def write(line):
        text = line.decode("utf-8", errors="replace")
        print(text, end="", flush=True)
        log.write(ANSI.sub("", text))
        log.flush()

    eof = False
    while observe_exit(child) is None:
        if eof:
            time.sleep(0.02)
        elif select.select([child.stdout], [], [], 0.02)[0]:
            line = child.stdout.readline()
            if line:
                write(line)
            else:
                eof = True
    # No descendant may keep the pipe open after the leader has completed.
    return


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
            with (state.parent / "dev.log").open("w") as log:
                stream_output(child, log)
                # Repeated interrupts cannot release identity before the final signal.
                for sig in previous:
                    signal.signal(sig, signal.SIG_IGN)
                retire_group(child)
                retired = True
                for line in child.stdout:
                    text = line.decode("utf-8", errors="replace")
                    print(text, end="", flush=True)
                    log.write(ANSI.sub("", text))
                log.flush()
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
