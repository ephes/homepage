#!/bin/bash
# Shared ownership, logging and exit-status handling with just dev/dev-all.
set -euo pipefail
cd -P "$(dirname "$0")"
exec uv run --locked python "$PWD/dev_runner.py" "$@"
