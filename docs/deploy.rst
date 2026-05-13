Deploy
========

Staging and production deployments run through ops-control (SOPS-backed). The local ``deploy/``
directory is kept as a legacy reference.

Ops-control Prerequisites
-------------------------

* An ops-control clone (set ``OPS_CONTROL`` if not located at ``../ops-control``)
* An ops-library clone (set ``OPS_LIBRARY_PATH`` if not located at ``$PROJECTS_ROOT/ops-library``)
* SOPS age key configured (``SOPS_AGE_KEY_FILE`` defaults to ``~/.config/sops/age/keys.txt``)
* ``PROJECTS_ROOT`` pointing at the parent directory that contains this repo
* ``uv`` installed locally; the just recipes run ``uvx --from ansible-core ansible-playbook``

Deployment Commands
-------------------

From Justfile
~~~~~~~~~~~~~

Deploy to staging via ops-control::

    just deploy-staging

Deploy to production via ops-control::

    just deploy-production

The deploy recipes first install/update Ansible collections and the local ``ops-library``
collection via ``uvx ansible-galaxy``. They also install ``community.postgresql`` explicitly
because current ops-control roles require it. The recipes support overriding the launcher
commands when needed::

    ANSIBLE_PLAYBOOK_CMD="uvx --from ansible-core ansible-playbook" just deploy-staging

    ANSIBLE_GALAXY_CMD="uvx --from ansible-core ansible-galaxy" just deploy-staging

Database Backup
---------------

To backup the production database and restore it locally::

    uv run python commands.py production-db-to-local

**Important**: Make sure only PostgreSQL is running locally (not the full development stack)::

    just postgres

Transcript Worker
-----------------

Voxhelm transcript generation from Wagtail admin queues completion work on the
``cast_transcripts`` Django Tasks database backend. The ops-control
``deploy-homepage.yml`` playbook enables a managed systemd worker in addition
to Gunicorn::

    uv run python manage.py db_worker --backend cast_transcripts --worker-id homepage-transcripts

The worker service uses the ``cast_transcripts`` backend alias and the stable
``homepage-transcripts`` worker id. The worker requires the ``django_tasks_db``
migrations to have been applied before it starts processing jobs.

Legacy Deployment Process (Reference Only)
------------------------------------------

The legacy deployment uses Ansible and performs the following steps:

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

Legacy Deployment Directory Structure
-------------------------------------

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

Legacy Prerequisites
--------------------

* Ansible installed locally
* SSH access to the deployment servers
* Deployment secrets configured in ``deploy/secrets*.yml``
* PostgreSQL and Redis running on the production server
