"""Audit the frozen registry graph, explicitly inventorying first-party Git sources."""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GIT_SOURCES = frozenset({"cast-bootstrap5", "cast-vue", "django-cast", "django-indieweb", "django-resume"})


def registry_requirements(export):
    registry = []
    skipped = {}
    for line in export.splitlines():
        if not line.strip():
            continue
        source = re.fullmatch(r"([a-z0-9-]+) @ git\+https://github.com/ephes/([a-z0-9-]+)@([0-9a-f]{40})", line)
        if source and source[1] in GIT_SOURCES and source[1] == source[2] and source[1] not in skipped:
            skipped[source[1]] = source[3]
        elif re.fullmatch(r"[a-z0-9][a-z0-9.-]*==[A-Za-z0-9_.+!-]+(?: ; .+)?", line):
            registry.append(line)
        else:
            raise ValueError("Unexpected requirement in frozen export; refusing an incomplete audit")
    if set(skipped) != GIT_SOURCES or not registry:
        raise ValueError("Frozen export must contain registry dependencies and all five expected Git sources")
    for name, commit in sorted(skipped.items()):
        print(f"Not registry-audited: {name} @ {commit}", flush=True)
    return "\n".join(registry) + "\n"


def audit():
    exported = subprocess.run(
        ["uv", "export", "--frozen", "--no-hashes", "--no-emit-project", "--no-header", "--no-annotate"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    requirements = registry_requirements(exported.stdout)
    with tempfile.TemporaryDirectory(prefix="homepage-audit-") as directory:
        path = Path(directory) / "requirements.txt"
        path.write_text(requirements)
        return subprocess.run(
            [
                "uvx",
                "--from",
                "pip-audit==2.10.1",
                "pip-audit",
                "--strict",
                "--disable-pip",
                "--no-deps",
                "--cache-dir",
                os.environ.get("PIP_AUDIT_CACHE_DIR", str(ROOT / ".cache" / "pip-audit")),
                "-r",
                str(path),
            ],
            cwd=ROOT,
        ).returncode


def main():
    try:
        return audit()
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or str(exc), file=sys.stderr)
        return exc.returncode
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
