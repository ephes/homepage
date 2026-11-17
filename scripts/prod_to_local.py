"""Legacy Docker/media transfer helper; prefer commands.py production-db-to-local."""

import argparse
import os
import re
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path, PurePosixPath

# The legacy producer announces: scp homepage:site/backups/<name>.sql.gz backups
CONNECT_TIMEOUT = 10
COMMAND_TIMEOUT = 60
TRANSFER_TIMEOUT = 300
MAX_COMMAND_BYTES = 64 * 1024  # stdout and stderr together
MAX_BACKUP_BYTES = 10 * 1024**3


@contextmanager
def deadline(seconds):
    """Bound even Paramiko's subsystem/exec negotiation; standalone POSIX use only."""
    if signal.getitimer(signal.ITIMER_REAL)[0]:
        raise ValueError("Legacy transfer requires an unused real-time timer")
    previous = signal.getsignal(signal.SIGALRM)

    def expired(signum, frame):
        raise TimeoutError("Legacy transfer deadline exceeded")

    signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def close_resource(resource):
    with deadline(CONNECT_TIMEOUT):
        resource.close()


def backup_announcement(output):
    announcements = []
    for line in output.decode("utf-8").splitlines():
        if line.lstrip().startswith("scp"):
            parts = shlex.split(line)
            if len(parts) != 3 or parts[0] != "scp" or parts[2] != "backups":
                raise ValueError("Malformed backup announcement")
            prefix = "homepage:"
            if not parts[1].startswith(prefix):
                raise ValueError("Unexpected backup source")
            remote = parts[1].removeprefix(prefix)
            path = PurePosixPath(remote)
            if (
                str(path) != remote
                or path.parent != PurePosixPath("site/backups")
                or path.name.startswith("-")
                or not path.name.endswith(".sql.gz")
                or len(path.name.encode("utf-8")) > 255
                or any(ord(char) < 32 or ord(char) == 127 for char in remote)
            ):
                raise ValueError("Unexpected backup path")
            announcements.append(remote)
    if len(announcements) != 1:
        raise ValueError("Expected one backup announcement")
    return announcements[0]


def read_remote_result(channel):
    output = bytearray()
    count = 0
    until = time.monotonic() + COMMAND_TIMEOUT
    while True:
        if time.monotonic() >= until:
            raise TimeoutError("Remote backup deadline exceeded")
        received = False
        for ready, recv, keep in (
            (channel.recv_ready, channel.recv, True),
            (channel.recv_stderr_ready, channel.recv_stderr, False),
        ):
            if ready():
                chunk = recv(min(16384, MAX_COMMAND_BYTES - count + 1))
                count += len(chunk)
                if count > MAX_COMMAND_BYTES:
                    raise ValueError("Remote backup output exceeds allowance")
                if keep:
                    output.extend(chunk)
                received = True
        if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
            if channel.recv_exit_status() != 0:
                raise ValueError("Remote backup command failed")
            return bytes(output)
        if not received:
            time.sleep(0.01)


def verify_backup(path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from commands import _verify_dump_file

    _verify_dump_file(path)


def fetch_backup(host, username, backups_dir):
    import paramiko

    backups_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    # The only reusable name is published after validation AND transport cleanup.
    with tempfile.TemporaryDirectory(prefix=".legacy-backup-", dir=backups_dir) as staging:
        stage = Path(staging) / "download.sql.gz"
        with ExitStack() as resources:
            with deadline(CONNECT_TIMEOUT):
                client = paramiko.SSHClient()
                resources.callback(close_resource, client)
                client.load_system_host_keys()  # Retain Paramiko's reject-unknown-host policy.
                client.connect(
                    host,
                    username=username,
                    timeout=CONNECT_TIMEOUT,
                    banner_timeout=CONNECT_TIMEOUT,
                    auth_timeout=CONNECT_TIMEOUT,
                    channel_timeout=CONNECT_TIMEOUT,
                )
            with deadline(COMMAND_TIMEOUT):
                streams = client.exec_command("cd site && python scripts/prod_backup.py", timeout=COMMAND_TIMEOUT)
                for stream in streams:
                    resources.callback(close_resource, stream)
                channel = streams[1].channel
                resources.callback(close_resource, channel)
                channel.settimeout(CONNECT_TIMEOUT)
                remote = backup_announcement(read_remote_result(channel))
            with deadline(TRANSFER_TIMEOUT):
                sftp = client.open_sftp()
                resources.callback(close_resource, sftp)
                sftp.get_channel().settimeout(CONNECT_TIMEOUT)
                before = sftp.lstat(remote)
                if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_BACKUP_BYTES:
                    raise ValueError("Backup must be a nonempty regular file within the size allowance")

                def progress(transferred, total):
                    if total != before.st_size or transferred > before.st_size:
                        raise ValueError("Backup size changed during transfer")

                fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as target:
                    copied = sftp.getfo(remote, target, callback=progress, prefetch=False)
                    target.flush()
                    os.fsync(target.fileno())
                after = sftp.lstat(remote)
                if (
                    not stat.S_ISREG(after.st_mode)
                    or (after.st_size, after.st_mtime) != (before.st_size, before.st_mtime)
                    or copied != before.st_size
                    or stage.stat().st_size != before.st_size
                ):
                    raise ValueError("Incomplete or changed backup transfer")
        verify_backup(stage)
        final = backups_dir / PurePosixPath(remote).name
        # Atomic no-clobber publication: an existing file/symlink is never replaced.
        os.link(stage, final)
        return final


def transfer_and_restore(host, username, backups_dir, *, replace_existing=False):
    path = fetch_backup(host, username, backups_dir)
    restore_download(path, replace_existing=replace_existing)


def restore_local_database(path, *, replace_existing=False):
    # Also support direct invocation from scripts/, without installing the project.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from commands import _restore_dump_into_local_database

    _restore_dump_into_local_database(path, "homepage", replace_existing)


def restore_download(path, *, replace_existing=False):
    """Keep legacy Docker/media steps; delegate SQL staging and cutover."""
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=homepage_production_postgres", "--format", "{{.ID}}"],
        check=True,
        capture_output=True,
        text=True,
    )
    container = result.stdout.strip()
    if not re.fullmatch(r"[a-f0-9]{12,64}", container):
        raise ValueError("Expected exactly one PostgreSQL container")
    commands = [
        ["docker", "cp", str(path.resolve()), f"{container}:/backups"],
        ["docker-compose", "-f", "local.yml", "down"],
        ["docker-compose", "-f", "local.yml", "run", "django", "./manage.py"],
        ["docker-compose", "-f", "local.yml", "run", "postgres", "restore", path.name],
        ["docker-compose", "-f", "local.yml", "run", "django", "./manage.py", "s3_backup"],
    ]
    for command in commands:
        subprocess.run(command, check=True)
    restore_local_database(path, replace_existing=replace_existing)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace-existing", action="store_true", help="Confirm replacement of local homepage database"
    )
    args = parser.parse_args(argv)
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv())
    host = os.environ.get("PRODUCTION_HOST")
    username = os.environ.get("PRODUCTION_USERNAME")
    if not host or not username:
        parser.error("PRODUCTION_HOST and PRODUCTION_USERNAME are required")
    transfer_and_restore(host, username, Path("backups").resolve(), replace_existing=args.replace_existing)


if __name__ == "__main__":
    main()
