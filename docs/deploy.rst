Deploy
========

The project uses Ansible for automated deployment to staging and production environments.

Deployment Commands
-------------------

From Commands.py
~~~~~~~~~~~~~~~~

Deploy to staging::

    uv run python commands.py deploy_staging

Deploy to production::

    uv run python commands.py deploy_production

From Justfile
~~~~~~~~~~~~~

Alternatively, you can use the just commands::

    just deploy-staging
    just deploy-production

Database Backup
---------------

To backup the production database and restore it locally::

    uv run python commands.py production_db_to_local

**Important**: Make sure only PostgreSQL is running locally (not the full development stack)::

    postgres -D databases/postgres

Deployment Process
------------------

The deployment uses Ansible and performs the following steps:

1. **Configuration Loading**

   * Loads shared secrets from ``deploy/secrets.yml``
   * Loads environment-specific secrets (``deploy/secrets_staging.yml`` or ``deploy/secrets_production.yml``)
   * Loads public variables from ``deploy/vars.yml``

2. **Server Setup**

   * Creates the deployment user with fish shell
   * Creates PostgreSQL database and user

3. **Code Deployment**

   * Syncs project files via rsync
   * Excludes: media files, backups, databases, .venv
   * Creates ``.env`` file from template

4. **Python Environment**

   * Creates virtual environment using uv
   * Installs production dependencies with ``uv sync --no-dev``

5. **Django Setup**

   * Runs database migrations
   * Collects static files
   * Updates Wagtail search index

6. **Service Configuration**

   * Creates Gunicorn start script
   * Configures systemd service
   * Sets up Traefik reverse proxy
   * Restarts the service

Deployment Directory Structure
------------------------------

The ``deploy/`` directory contains::

    deploy/
    ├── ansible.cfg          # Ansible configuration
    ├── deploy.yml           # Main deployment playbook
    ├── backup_database.yml  # Database backup playbook
    ├── restore_database.yml # Database restore playbook
    ├── vars.yml             # Public deployment variables
    ├── secrets*.yml         # Secret variables (git-ignored)
    ├── inventory/
    │   └── hosts.yml        # Server inventory
    ├── host_vars/
    │   ├── production.yml   # Production-specific vars
    │   └── staging.yml      # Staging-specific vars
    └── templates/
        ├── env.template.j2           # .env file template
        ├── gunicorn.sh.j2           # Gunicorn startup script
        ├── systemd.service.j2       # Systemd service definition
        ├── traefik.template.j2      # Traefik routing config
        └── user_config.fish.template.j2  # Fish shell config

Configuration
-------------

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

The deployment creates a ``.env`` file on the server with all necessary environment variables including:

* Database credentials
* Secret keys
* Email configuration
* External service API keys

These are stored in the ``secrets*.yml`` files which should never be committed to git.

Static Files
~~~~~~~~~~~~

Static files are served using WhiteNoise in production, eliminating the need for a separate web server for static content.

Prerequisites
-------------

* Ansible installed locally
* SSH access to the deployment servers
* Deployment secrets configured in ``deploy/secrets*.yml``
* PostgreSQL and Redis running on the production server
