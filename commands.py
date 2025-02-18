import contextlib
import os
import platform
import subprocess
import sys
import webbrowser
from pathlib import Path


def get_project_root():
    return Path(__file__).parent.resolve()


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
        subprocess.call(*command)


@cli.command()
def clean_pyc():
    commands = [
        ["find", ".", "-name", "*.pyc", "-exec", "rm -f {} +"],
        ["find", ".", "-name", "*.pyo", "-exec", "rm -f {} +"],
        ["find", ".", "-name", "*~", "-exec", "rm -f {} +"],
    ]
    for command in commands:
        subprocess.call(*command)


@cli.command()
def clean():
    clean_build()
    clean_pyc()


@cli.command()
def docs():
    autogenerated = [
        "cast.api.rst",
        "cast.migrations.rst",
        "cast.rst",
        "cast.templatetags.rst",
        "modules.rst",
    ]
    for rst_name in autogenerated:
        (Path("docs") / rst_name).unlink(missing_ok=True)
    commands = [
        ["sphinx-apidoc", "-o", "docs/", "cast"],
        ["make", "-C", "docs", "clean"],
        ["make", "-C", "docs", "html"],
    ]
    for command in commands:
        subprocess.call(*command)
    file_url = "file://" + str(Path("docs/_build/html/index.html").resolve())
    webbrowser.open_new_tab(file_url)


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
def production_db_to_local():
    """
    Use ansible to create and fetch a backup.

    Make sure only the database is running using:
      postgres -D databases/postgres
    """
    import psutil

    for proc in psutil.process_iter(["pid", "name", "username"]):
        if proc.info["name"] is None or "python" not in proc.info["name"]:
            continue
        try:
            cmdline = " ".join(proc.cmdline())
            if "honcho" in cmdline:
                print("please stop honcho first and start a single postgres db with postgres -D databases/postgres")
                sys.exit(1)
        except psutil.AccessDenied:
            # ignore processes that we cannot observe
            pass

    deploy_root = Path(__file__).parent / "deploy"
    with working_directory(deploy_root):
        output = subprocess.check_output(
            ["ansible-playbook", "backup_database.yml", "--limit", "production"], text=True
        )
    [line] = [line for line in output.split("\n") if "sql.gz" in line]
    backup_file_name = line.split('"')[-2]
    backup_path = get_project_root() / "backups" / backup_file_name
    db_name = "homepage"
    subprocess.call(["dropdb", db_name])
    subprocess.call(["createdb", db_name])
    subprocess.call(["createuser", db_name])
    command = f"gunzip -c {backup_path} | psql {db_name}"
    print(command)
    subprocess.call(command, shell=True)
    print(backup_path)


def deploy(environment):
    """
    Use ansible-playbook to deploy the site to the staging server.
    """
    deploy_root = Path(__file__).parent / "deploy"
    with working_directory(deploy_root):
        subprocess.call(["ansible-playbook", "deploy.yml", "--limit", environment])


@cli.command()
def deploy_staging():
    deploy("staging")


@cli.command()
def deploy_production():
    deploy("production")


@cli.command()
def switch_to_dev_environment():
    """
    Switch to the development environment installing a list of
    packages in development mode using flit.
    """
    from contextlib import chdir

    projects_dir = get_project_root().parent

    uv_install_dev = ["uv", "pip", "install", "-e"]
    for project in ["django-cast"]:
        uv_args = uv_install_dev.copy()
        uv_args.append(projects_dir / project)
        subprocess.call(uv_args)

    flit_install_dev = [sys.executable, "-m", "flit", "install", "-s"]
    for project in ["cast-vue", "cast-bootstrap5"]:
        with chdir(projects_dir / project):
            subprocess.call(flit_install_dev)


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
