Deploy
========

Staging and production deployments run through ops-control (SOPS-backed).

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

    just production-db-to-local

This replaces the local ``homepage`` database. Pass another name to restore into a
separate database instead, e.g. ``just production-db-to-local homepage_prod``.

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

Configuration
-------------

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

The deployment creates a ``.env`` file on the server with all necessary environment variables including:

* Database credentials
* Secret keys
* Email configuration
* External service API keys

The values come from ops-control's SOPS-encrypted secrets.

.. _sentry-environment:

Sentry Environment
~~~~~~~~~~~~~~~~~~

Staging and production both run ``config.settings.production``. The Sentry SDK
tags events ``production`` whenever no environment is supplied, so staging errors
would otherwise be indistinguishable from production ones.

``DJANGO_SENTRY_ENVIRONMENT`` sets the tag explicitly and defaults to
``production`` when unset. The ops-control playbook derives it from the target
host and renders it into ``.env`` via the ``wagtail_deploy`` role
(``wagtail_django_sentry_environment``), so staging deploys report
``environment=staging``.

Static Files
~~~~~~~~~~~~

Static files are served using WhiteNoise in production, eliminating the need for a separate web server for static content.

