"""Legacy Docker/media transfer helper; prefer commands.py production-db-to-local."""

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


def fetch_backup(host, username, backups_dir):
    import paramiko

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(host, username=username)
    _, stdout, _ = client.exec_command("cd site;python scripts/prod_backup.py")
    remote_path = None
    for line in stdout.read().decode("utf-8").splitlines():
        parts = shlex.split(line)
        if parts and parts[0] == "scp":
            remote_path = parts[1].split(":", 1)[1]
    if remote_path is None:
        raise ValueError("No backup announcement")
    backups_dir.mkdir(parents=True, exist_ok=True)
    path = backups_dir / Path(remote_path).name
    client.open_sftp().get(remote_path, str(path))
    return path


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
    path = fetch_backup(host, username, Path("backups").resolve())
    restore_download(path, replace_existing=args.replace_existing)


if __name__ == "__main__":
    main()
