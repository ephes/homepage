#!/usr/bin/env python3
"""
Pre-commit hook to ensure tool.uv.sources doesn't contain local editable paths.
Automatically switches back to git sources if local paths are detected.
"""
import subprocess
import sys
from pathlib import Path

import toml


def main():
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return 0

    # Read pyproject.toml
    with open(pyproject_path) as f:
        data = toml.load(f)

    # Check if tool.uv.sources exists
    if "tool" not in data or "uv" not in data["tool"] or "sources" not in data["tool"]["uv"]:
        return 0

    sources = data["tool"]["uv"]["sources"]
    has_local_paths = False

    # Check for local paths
    for package, source in sources.items():
        if isinstance(source, dict) and "path" in source and source.get("editable"):
            print(f"Found local editable path for {package}: {source['path']}")
            has_local_paths = True

    if has_local_paths:
        print("\n⚠️  Local editable paths detected in tool.uv.sources!")
        print("Automatically switching back to git sources...")

        # Run the switch-to-git-sources command
        result = subprocess.run(["uv", "run", "commands.py", "switch-to-git-sources"], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error switching to git sources: {result.stderr}")
            return 1

        print("✅ Switched back to git sources. Please stage the updated pyproject.toml")
        print("Run 'git add pyproject.toml' to include the changes")
        return 1  # Exit with error to stop the commit

    return 0


if __name__ == "__main__":
    sys.exit(main())
