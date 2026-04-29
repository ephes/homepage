# Justfile for homepage project development

# ========= Deploy Config (override via .envrc or environment) =========
# Path to your local ops-control clone
OPS_CONTROL := env_var_or_default("OPS_CONTROL", "/Users/jochen/projects/ops-control")
PROJECTS_ROOT := env_var_or_default("PROJECTS_ROOT", "/Users/jochen/projects")
OPS_LIBRARY_PATH := env_var_or_default("OPS_LIBRARY_PATH", PROJECTS_ROOT + "/ops-library")
SOPS_AGE_KEY_FILE := env_var_or_default("SOPS_AGE_KEY_FILE", "~/.config/sops/age/keys.txt")
ANSIBLE_PLAYBOOK_CMD := env_var_or_default("ANSIBLE_PLAYBOOK_CMD", "uvx --from ansible-core ansible-playbook")
ANSIBLE_GALAXY_CMD := env_var_or_default("ANSIBLE_GALAXY_CMD", "uvx --from ansible-core ansible-galaxy")
export BLOG_COVER_URL := env_var_or_default("BLOG_COVER_URL", "https://wersdoerfer.de/blogs/ephes_blog/")
export BLOG_COVER_OUTPUT := env_var_or_default("BLOG_COVER_OUTPUT", "tmp/wersdoerfer-de-blogs-ephes_blog.jpg")
export BLOG_COVER_REMOTE := env_var_or_default("BLOG_COVER_REMOTE", "root@wersdoerfer.de")
export BLOG_COVER_REMOTE_APP := env_var_or_default("BLOG_COVER_REMOTE_APP", "/home/homepage/site")
export BLOG_COVER_REMOTE_UPLOAD := env_var_or_default("BLOG_COVER_REMOTE_UPLOAD", "/tmp/wersdoerfer-de-blogs-ephes_blog.jpg")
export BLOG_COVER_SLUG := env_var_or_default("BLOG_COVER_SLUG", "ephes_blog")
export BLOG_COVER_TITLE := env_var_or_default("BLOG_COVER_TITLE", "wersdoerfer-de-blogs-ephes_blog")
export BLOG_COVER_ALT_TEXT := env_var_or_default("BLOG_COVER_ALT_TEXT", "Just a screenshot of the blog overview page.")
export BLOG_COVER_USER := env_var_or_default("BLOG_COVER_USER", "jochen")

# Default recipe - show available commands
default:
    @just --list

# Check if services are already running
check-services:
    @echo "Checking for running services..."
    @if lsof -i :8000 > /dev/null 2>&1; then \
        echo "❌ Port 8000 already in use (Django)"; \
        echo "   PID: $(lsof -ti :8000)"; \
        exit 1; \
    fi
    @if lsof -i :5432 > /dev/null 2>&1; then \
        echo "⚠️  Port 5432 already in use (PostgreSQL)"; \
        echo "   This might be your system PostgreSQL - checking..."; \
        if pgrep -f "postgres -D databases/postgres" > /dev/null; then \
            echo "   ❌ Local dev PostgreSQL already running"; \
            echo "   PID: $(pgrep -f 'postgres -D databases/postgres')"; \
            exit 1; \
        else \
            echo "   ✓ System PostgreSQL detected, will use different port"; \
        fi; \
    fi
    @echo "✓ All clear to start services"

# Kill any leftover processes from previous runs
cleanup:
    @echo "Cleaning up any leftover processes..."
    @-pkill -f "postgres -D databases/postgres" 2>/dev/null || true
    @-pkill -f "manage.py runserver" 2>/dev/null || true
    @-pkill -f "jupyterlab" 2>/dev/null || true
    @if [ -f logs/dev.pid ]; then \
        kill $(cat logs/dev.pid) 2>/dev/null || true; \
        rm logs/dev.pid; \
    fi
    @echo "✓ Cleanup complete"

# Start development server with logging (postgres + django only)
dev: check-services
    @mkdir -p logs
    @echo "Starting development services (postgres + django)..."
    @# Save process group ID for cleanup
    @echo $$ > logs/dev.pid
    @# Use honcho with specific processes
    @bash -c 'uvx honcho start postgres django 2>&1 | tee >(sed "s/\x1b\[[0-9;]*m//g" > logs/dev.log)' || (rm -f logs/dev.pid; exit 1)
    @rm -f logs/dev.pid

# Start all services from Procfile
dev-all: check-services
    @mkdir -p logs
    @echo "Starting all development services..."
    @echo $$ > logs/dev.pid
    @# Run all services defined in Procfile
    @bash -c 'uvx honcho start 2>&1 | tee >(sed "s/\x1b\[[0-9;]*m//g" > logs/dev.log)' || (rm -f logs/dev.pid; exit 1)
    @rm -f logs/dev.pid

# Start dev server without checks (force start)
dev-force: cleanup
    @just dev

# Start individual services
postgres:
    @echo "Starting PostgreSQL..."
    postgres -D databases/postgres

django:
    @echo "Starting Django development server..."
    PYTHONUNBUFFERED=true uv run python manage.py runserver 0.0.0.0:8000

jupyter:
    @echo "Starting JupyterLab..."
    uv run python commands.py jupyterlab

# View logs
logs *ARGS:
    @if [ -f logs/dev.log ]; then \
        python view_logs.py {{ARGS}}; \
    else \
        echo "No log file found. Run 'just dev' first."; \
    fi

# Follow logs in real-time
logs-follow:
    @just logs -f

# Filter logs
logs-grep PATTERN:
    @just logs -g "{{PATTERN}}"

# Run Django management commands
manage *ARGS:
    uv run python manage.py {{ARGS}}

# Run tests
test *ARGS:
    uv run python commands.py test {{ARGS}}

# Run coverage
coverage:
    uv run python commands.py coverage

# Database operations
db-migrate:
    @just manage makemigrations
    @just manage migrate

db-shell:
    @just manage dbshell

production-db-to-local:
    uv run python commands.py production-db-to-local

# Shell access
shell:
    @just manage shell_plus

# Install dependencies
install:
    uv sync

# Update prek hook revisions
update-hooks:
    env -u VIRTUAL_ENV uv run prek auto-update

# Build documentation
docs:
    uv run python commands.py docs

# Install ops-control Ansible dependencies via uvx
deploy-bootstrap:
    #!/usr/bin/env bash
    set -euo pipefail
    test -d "{{OPS_CONTROL}}" || (echo "ops-control not found at {{OPS_CONTROL}}"; exit 1)
    test -d "{{OPS_LIBRARY_PATH}}" || (echo "ops-library not found at {{OPS_LIBRARY_PATH}}"; exit 1)
    cd "{{OPS_CONTROL}}"
    {{ANSIBLE_GALAXY_CMD}} collection install -r collections/requirements.yml -p ./collections
    # ops-control roles also use community.postgresql, but it is not currently listed in collections/requirements.yml.
    {{ANSIBLE_GALAXY_CMD}} collection install community.postgresql -p ./collections
    build_dir="$(mktemp -d "${TMPDIR:-/tmp}/homepage-ops-library.XXXXXX")"
    trap 'rm -rf "${build_dir}"' EXIT
    {{ANSIBLE_GALAXY_CMD}} collection build "{{OPS_LIBRARY_PATH}}" --output-path "${build_dir}" --force
    shopt -s nullglob
    tarballs=("${build_dir}"/local-ops_library-*.tar.gz)
    if [[ "${#tarballs[@]}" -ne 1 ]]; then
        echo "Expected exactly one local-ops_library tarball in ${build_dir}, found ${#tarballs[@]}"
        exit 1
    fi
    {{ANSIBLE_GALAXY_CMD}} collection install "${tarballs[0]}" -p ./collections --force

# Production deployment
deploy-staging: deploy-bootstrap
    @test -d "{{OPS_CONTROL}}" || (echo "ops-control not found at {{OPS_CONTROL}}"; exit 1)
    @test -f "{{OPS_CONTROL}}/inventories/prod/hosts.yml" || (echo "Missing ops-control inventory at {{OPS_CONTROL}}/inventories/prod/hosts.yml"; exit 1)
    @test -f "{{OPS_CONTROL}}/playbooks/deploy-homepage.yml" || (echo "Missing ops-control playbook at {{OPS_CONTROL}}/playbooks/deploy-homepage.yml"; exit 1)
    cd "{{OPS_CONTROL}}" && \
    PROJECTS_ROOT={{PROJECTS_ROOT}} \
    SOPS_AGE_KEY_FILE={{SOPS_AGE_KEY_FILE}} \
    {{ANSIBLE_PLAYBOOK_CMD}} -i inventories/prod/hosts.yml playbooks/deploy-homepage.yml -l staging -e target_host=staging -e service_secrets_env=staging

deploy-production: deploy-bootstrap
    @test -d "{{OPS_CONTROL}}" || (echo "ops-control not found at {{OPS_CONTROL}}"; exit 1)
    @test -f "{{OPS_CONTROL}}/inventories/prod/hosts.yml" || (echo "Missing ops-control inventory at {{OPS_CONTROL}}/inventories/prod/hosts.yml"; exit 1)
    @test -f "{{OPS_CONTROL}}/playbooks/deploy-homepage.yml" || (echo "Missing ops-control playbook at {{OPS_CONTROL}}/playbooks/deploy-homepage.yml"; exit 1)
    cd "{{OPS_CONTROL}}" && \
    PROJECTS_ROOT={{PROJECTS_ROOT}} \
    SOPS_AGE_KEY_FILE={{SOPS_AGE_KEY_FILE}} \
    {{ANSIBLE_PLAYBOOK_CMD}} -i inventories/prod/hosts.yml playbooks/deploy-homepage.yml

# Generate the default blog cover image from the production blog overview.
blog-cover-screenshot:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p "$(dirname "$BLOG_COVER_OUTPUT")"
    uvx shot-scraper shot "$BLOG_COVER_URL" -o "$BLOG_COVER_OUTPUT" --width 1600 --height 800 --quality 90 --wait 1000

# Generate and install the default blog cover image on production.
blog-cover-update-production: blog-cover-screenshot
    #!/usr/bin/env bash
    set -euo pipefail
    {
        printf 'set -euo pipefail\n'
        printf 'blog_cover_remote_upload=%q\n' "$BLOG_COVER_REMOTE_UPLOAD"
        printf 'trap '\''rm -f "$blog_cover_remote_upload"'\'' EXIT\n'
        printf "base64 --decode > %q <<'BLOG_COVER_IMAGE'\n" "$BLOG_COVER_REMOTE_UPLOAD"
        base64 < "$BLOG_COVER_OUTPUT"
        printf '\nBLOG_COVER_IMAGE\n'
        printf 'cd %q\n' "$BLOG_COVER_REMOTE_APP"
        printf 'sudo -u homepage .venv/bin/python manage.py update_blog_cover_image %q --blog-slug %q --title %q --alt-text %q --user %q\n' \
            "$BLOG_COVER_REMOTE_UPLOAD" \
            "$BLOG_COVER_SLUG" \
            "$BLOG_COVER_TITLE" \
            "$BLOG_COVER_ALT_TEXT" \
            "$BLOG_COVER_USER"
    } | ssh "$BLOG_COVER_REMOTE" 'bash -s'

# Help for common issues
troubleshoot:
    @echo "Common issues and solutions:"
    @echo ""
    @echo "1. Port already in use:"
    @echo "   just cleanup  # Kill leftover processes"
    @echo "   just dev      # Try again"
    @echo ""
    @echo "2. Force restart everything:"
    @echo "   just dev-force"
    @echo ""
    @echo "3. Check what's using a port:"
    @echo "   lsof -i :8000  # Django"
    @echo "   lsof -i :5432  # PostgreSQL"
    @echo ""
    @echo "4. View logs:"
    @echo "   just logs          # Last 50 lines"
    @echo "   just logs-follow   # Real-time"
    @echo "   just logs-grep ERROR"
