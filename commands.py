import contextlib
import datetime
import os
import platform
import shlex
import subprocess
import sys
from pathlib import Path


def get_project_root():
    return Path(__file__).parent.resolve()


def _toml_inline_table(value: dict) -> str:
    parts: list[str] = []
    for key, item in value.items():
        if isinstance(item, bool):
            rendered = "true" if item else "false"
        else:
            raw = str(item)
            escaped = raw.replace("\\", "\\\\").replace('"', '\\"')
            rendered = f'"{escaped}"'
        parts.append(f"{key} = {rendered}")
    return "{ " + ", ".join(parts) + " }"


def _replace_uv_sources(pyproject_path: Path, updates: dict[str, dict]) -> None:
    """
    Update (or create) entries in the [tool.uv.sources] section without needing external TOML libraries.

    This is intentionally minimal: it preserves the rest of the file as-is and only rewrites/creates the
    [tool.uv.sources] section and the keys we manage.
    """
    text = pyproject_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    section_header = "[tool.uv.sources]"
    header_index = next((i for i, line in enumerate(lines) if line.strip() == section_header), None)

    # If the section doesn't exist, append it at the end.
    if header_index is None:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.append(section_header + "\n")
        header_index = len(lines) - 1
        section_end = len(lines)
    else:
        # Find the end of the section (next TOML section header or EOF).
        section_end = next(
            (
                i
                for i in range(header_index + 1, len(lines))
                if lines[i].startswith("[") and lines[i].rstrip().endswith("]")
            ),
            len(lines),
        )

    # Parse existing entries (simple `name = { ... }` lines).
    existing: dict[str, int] = {}
    for i in range(header_index + 1, section_end):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, _rest = stripped.split("=", 1)
        existing[name.strip()] = i

    # Apply updates: replace existing lines or insert new ones before section end.
    insertion_point = section_end
    for name, mapping in updates.items():
        new_line = f"{name} = {_toml_inline_table(mapping)}\n"
        if name in existing:
            lines[existing[name]] = new_line
        else:
            lines.insert(insertion_point, new_line)
            insertion_point += 1
            section_end += 1

    pyproject_path.write_text("".join(lines), encoding="utf-8")


def bootstrap():
    """
    Called when first non-standard lib import fails.

    Given uv is installed, we need at least typer and rich to use this script.
    """
    if not (Path.cwd() / ".venv").exists():
        print("No .venv found, creating one using uv...")
        subprocess.run(["uv", "venv", ".venv"], check=True)
        print("Please activate the virtual environment and run the script again.")
        sys.exit(1)

    print("Sync requirements via uv...")
    subprocess.run(["uv", "sync"], check=True)


try:
    import typer
except ImportError:
    bootstrap()
    import typer

from rich import print  # noqa

cli = typer.Typer()


def get_pythonpath():
    """Add project root and model directory to string"""
    project_root = str(get_project_root())
    model_root = str(Path(__file__).parent / "model")
    return f"{project_root}:{model_root}"


def env_with_pythonpath():
    """Get en environment dict with includes PYTHONPATH"""
    env = os.environ.copy()
    env["PYTHONPATH"] = get_pythonpath()
    return env


@cli.command()
def mypy():
    """Run Mypy (configured in pyproject.toml)"""
    subprocess.call(["mypy", "."])


@cli.command()
def test():
    subprocess.call(["python", "-m", "pytest"], env=env_with_pythonpath())


@cli.command()
def coverage():
    """
    Run and show coverage.
    """
    subprocess.call(["coverage", "run", "-m", "pytest"], env=env_with_pythonpath())
    subprocess.call(["coverage", "html"])
    if platform.system() == "Darwin":
        subprocess.call(["open", "htmlcov/index.html"])
    elif platform.system() == "Linux" and "Microsoft" in platform.release():  # on WSL
        subprocess.call(["explorer.exe", r"htmlcov\index.html"])


@cli.command()
def jupyterlab():
    """
    Start a jupyterlab server.
    """
    project_root = get_project_root()
    notebook_dir = project_root / "notebooks"
    notebook_dir.mkdir(exist_ok=True)
    env = env_with_pythonpath()
    subprocess.call([sys.executable, "-m", "jupyterlab", "--notebook-dir", "notebooks/"], env=env)


@cli.command()
def update(upgrade: bool = typer.Option(True, "--upgrade/--no-upgrade")):
    """
    Update the requirements using uv.
    """
    print("Updating requirements via uv...")
    subprocess.call(["uv", "lock", "--upgrade"])


@cli.command()
def clean_build():
    commands = [
        ["rm", "-fr", "build/"],
        ["rm", "-fr", "dist/"],
        ["rm", "-fr", "*.egg-info"],
        ["rm", "-fr", "__pycache__"],
    ]
    for command in commands:
        subprocess.call(command)


@cli.command()
def clean_pyc():
    commands = [
        ["find", ".", "-name", "*.pyc", "-exec", "rm -f {} +"],
        ["find", ".", "-name", "*.pyo", "-exec", "rm -f {} +"],
        ["find", ".", "-name", "*~", "-exec", "rm -f {} +"],
    ]
    for command in commands:
        subprocess.call(command)


@cli.command()
def clean():
    clean_build()
    clean_pyc()


@contextlib.contextmanager
def working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd().absolute()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(prev_cwd)


@cli.command()
def production_db_to_local(
    production_host: str = typer.Option("wersdoerfer.de", help="SSH host for the production server."),
    production_ssh_user: str = typer.Option("root", help="SSH user for the production server."),
    production_db_name: str = typer.Option("homepage", help="Production PostgreSQL database name."),
    production_db_user: str = typer.Option("postgres", help="Remote system user allowed to dump PostgreSQL."),
    local_db_name: str = typer.Option("homepage", help="Local PostgreSQL database name to restore into."),
):
    """
    Fetch a production PostgreSQL dump over SSH and restore it locally.

    Make sure only the database is running using:
      just postgres
    """
    import psutil

    for proc in psutil.process_iter(["pid", "name", "username"]):
        try:
            cmdline = " ".join(proc.cmdline())
            if "honcho" in cmdline:
                print("please stop honcho first and start a single postgres db with just postgres")
                sys.exit(1)
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            # ignore processes that we cannot observe
            pass

    backups_dir = get_project_root() / "backups"
    backups_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    backup_path = backups_dir / f"{timestamp}_{production_db_name}.sql.gz"

    remote_dump_pipeline = (
        "set -o pipefail; "
        f"sudo -u {shlex.quote(production_db_user)} "
        f"pg_dump --no-owner --no-privileges {shlex.quote(production_db_name)} | gzip -c"
    )
    remote_dump_command = f"bash -lc {shlex.quote(remote_dump_pipeline)}"
    ssh_target = f"{production_ssh_user}@{production_host}"
    print(f"Creating production backup via SSH: {ssh_target}:{production_db_name}")
    try:
        with backup_path.open("wb") as backup_file:
            subprocess.run(["ssh", ssh_target, remote_dump_command], stdout=backup_file, check=True)
    except subprocess.CalledProcessError:
        backup_path.unlink(missing_ok=True)
        raise

    try:
        subprocess.run(["createuser", local_db_name], check=False)
        subprocess.run(["dropdb", "--if-exists", local_db_name], check=True)
        subprocess.run(["createdb", local_db_name], check=True)
        command = f"gunzip -c {shlex.quote(str(backup_path))} | psql {shlex.quote(local_db_name)}"
        print(command)
        subprocess.run(["bash", "-o", "pipefail", "-c", command], check=True)
    except subprocess.CalledProcessError:
        print(f"local restore failed; close open connections to {local_db_name} and rerun")
        print(f"production backup was saved at {backup_path}")
        raise
    print(backup_path)


def deploy(environment):
    """
    Use legacy ansible-playbook flow under deploy/ (kept for reference).
    """
    deploy_root = Path(__file__).parent / "deploy"
    with working_directory(deploy_root):
        subprocess.call(["ansible-playbook", "deploy.yml", "--limit", environment])


@cli.command()
def switch_to_dev_environment():
    """
    Switch to development mode using local editable packages.

    Modifies pyproject.toml to use local paths in tool.uv.sources.
    """
    project_root = get_project_root()
    projects_dir = project_root.parent
    pyproject_path = project_root / "pyproject.toml"

    # Define local package mappings
    packages = [
        ("cast-vue", projects_dir / "cast-vue"),
        ("cast-bootstrap5", projects_dir / "cast-bootstrap5"),
        ("django-cast", projects_dir / "django-cast"),
        ("django-indieweb", projects_dir / "django-indieweb"),
        ("django-resume", projects_dir / "django-resume"),
    ]

    print("Switching to local development sources in pyproject.toml...")

    updates: dict[str, dict] = {}
    for package_name, package_path in packages:
        if package_path.exists():
            print(f"✓ {package_name} -> {package_path}")
            updates[package_name] = {"path": f"../{package_path.name}", "editable": True}
        else:
            print(f"Warning: {package_path} does not exist, skipping")

    if updates:
        _replace_uv_sources(pyproject_path, updates)

        print("\nRunning uv sync to apply changes...")
        subprocess.call(["uv", "sync"])

        print("\nDevelopment environment activated!")
        print("Local packages are now installed in editable mode.")
        print("Changes to the source code will be reflected immediately.")
        print("\nIMPORTANT: Remember to run prek hooks before committing!")
        print("To switch back to git sources, run: uv run commands.py switch-to-git-sources")


@cli.command()
def switch_to_git_sources():
    """
    Switch back to git sources from local development mode.

    Restores original git sources in pyproject.toml.
    """
    project_root = get_project_root()
    pyproject_path = project_root / "pyproject.toml"

    # Define default git sources
    default_sources = {
        "cast-vue": {"git": "https://github.com/ephes/cast-vue"},
        "cast-bootstrap5": {"git": "https://github.com/ephes/cast-bootstrap5"},
        "django-cast": {"git": "https://github.com/ephes/django-cast", "branch": "develop"},
        "django-indieweb": {"git": "https://github.com/ephes/django-indieweb", "branch": "develop"},
        "django-resume": {"git": "https://github.com/ephes/django-resume", "branch": "editorial-theme"},
    }

    print("Restoring git sources in pyproject.toml...")
    _replace_uv_sources(pyproject_path, default_sources)
    for package_name, git_source in default_sources.items():
        print(f"✓ {package_name} -> {git_source}")

    print("\nRunning uv sync to apply changes...")
    subprocess.call(["uv", "sync", "--reinstall"])

    print("\nSwitched back to git sources!")
    print("All packages are now installed from their git repositories.")


@cli.command()
def recreate_resume_tables():
    """
    Drop and recreate the tables of the resume app.
    """
    subprocess.call(["python", "manage.py", "migrate", "resume", "zero"])
    subprocess.call(["rm", "-r", "homepage/resume/migrations/"])
    subprocess.call(["python", "manage.py", "makemigrations", "resume"])
    subprocess.call(["python", "manage.py", "migrate", "resume"])


if __name__ == "__main__":
    cli()
