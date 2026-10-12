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

If the local ``homepage`` database already exists, the command refuses to run. Confirm
replacing it with ``just production-db-to-local homepage --replace-existing``, or pass
another name to restore into a separate database instead, e.g.
``just production-db-to-local homepage_prod``. The existing database is only replaced
after the complete dump loaded without errors; see :doc:`install` for the details and
for recovering from an interrupted restore.

**Important**: Make sure only PostgreSQL is running locally (not the full development stack)::

    just postgres

2026-10-12 cast-bootstrap5 refresh
----------------------------------

``uv.lock`` moves cast-bootstrap5 ``main`` from ``bcd0b513`` to ``4ed370aa``. No
other locked package changed. The source conflict that kept it at ``bcd0b513``
(see the refresh note below) is resolved: cast-bootstrap5 ``main`` now takes
django-cast from the ``develop`` branch, as this project does.

The update brings the search suggestion input fixes (text composition and
modified clicks are respected) with a rebuilt search modal bundle, so
``collectstatic`` picks up a new hashed asset. It has no migrations and needs no
settings change.

2026-10-12 library refresh
--------------------------

``uv.lock`` moves django-cast ``develop`` from ``0e55a47b`` to ``95965b91``,
django-indieweb ``develop`` from ``5187311d`` to ``289ea25a`` and django-resume
``main`` from ``bcdeb44b`` to ``c9d5172f``. No other locked package changed.
cast-bootstrap5 stays at ``bcd0b513``: its ``main`` now pins django-cast to a
fixed commit in ``tool.uv.sources``, which conflicts with tracking ``develop``
here.

* django-indieweb migration ``0029_reconcile_no_scope_grants`` deletes duplicate
  no-scope tokens and auth codes before ``0030_scope_not_null`` makes the scope
  column non-null. Take a database backup before deploying.
  The ops-control deploy migrates while the previous release is still serving
  and restarts the service afterwards. The previous pin stores a no-scope grant
  as ``NULL``, so an IndieAuth authorization issued without a scope during that
  window can recreate a duplicate and make ``0030`` fail, or fail itself once
  ``0030`` has run. Do not authorize IndieAuth clients while deploying. If
  ``0030`` fails, ``0029`` is already recorded and a plain rerun skips it:
  run ``migrate indieweb 0028`` (reversing ``0029`` is a no-op), then deploy
  again so ``0029`` reconciles the new rows before ``0030``.
  A failed run can drop the pending restart, and the rerun may then see no
  source or dependency change: confirm that ``homepage.service`` and the
  transcript worker were restarted after the successful rerun, and restart them
  if they still run the previous release.
* django-cast strips EXIF GPS from new image uploads. Existing originals are not
  rewritten; ``python manage.py report_image_gps`` lists them read-only.
* django-cast restricts the Wagtail images API to staff unless
  ``CAST_PUBLIC_IMAGES_API`` is ``True``. The setting stays unset here.
* django-resume no longer lets a resume owner install JSON Resume catalog themes
  from the browser. ``DJANGO_RESUME_JSON_RESUME_ALLOW_CATALOG_THEME_INSTALL``
  stays at its default ``False`` and the deploy does not run
  ``install_json_resume_catalog_themes``: production has no theme cache, so no
  installed theme is lost, and **Preview render** / **Use render theme** answer
  403 until an operator installs themes with that command. The pinned
  ``resumed`` 7 renderer needs Node.js 24 or newer.

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

.. _sentry-privacy:

Sentry Privacy
~~~~~~~~~~~~~~

Error reports sent to Sentry do not identify visitors or users:
``config.settings.production`` calls ``sentry_sdk.init`` with
``send_default_pii=False`` and ``max_request_body_size="never"``. Events keep
the stack trace (including local variables) and the request URL, method and
non-sensitive headers, but not client IP addresses, the logged-in user,
cookies or request bodies (form posts, JSON payloads, uploads).

These are fixed defaults, not ``.env`` settings; change them in the settings
module only after an owner decision. ``homepage/tests/test_production_sentry.py``
guards them.

.. _hsts:

HSTS
~~~~

Two layers send ``Strict-Transport-Security``:

* Traefik, through the ``wagtail_deploy`` headers middleware in ops-library:
  ``stsSeconds: 15552000`` (180 days), ``stsIncludeSubdomains`` and
  ``stsPreload``. This is the header visitors see while that middleware is in
  place.
* Django's ``SecurityMiddleware`` (``config.settings.production``), as the
  fallback when the site is served without that middleware.

Django defaults to the same 180 days with ``includeSubDomains`` and **without**
``preload``. The old cookiecutter value (``max-age=60`` plus ``preload``) is
gone. ``preload`` asks browsers to hard-code the domain and its subdomains as
HTTPS-only; removal from the preload list takes months, and hstspreload.org
requires ``max-age`` of at least one year anyway, so the token does nothing
useful at 180 days. ``manage.py check --deploy`` reports ``security.W021``
for this on purpose.

The settings can be overridden from ``.env``:

* ``DJANGO_SECURE_HSTS_SECONDS`` (default ``15552000``)
* ``DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`` (default ``True``)
* ``DJANGO_SECURE_HSTS_PRELOAD`` (default ``False``)

Upgrade path to preload (owner decision): confirm every subdomain of the domain
serves HTTPS, set ``DJANGO_SECURE_HSTS_SECONDS=31536000`` and
``DJANGO_SECURE_HSTS_PRELOAD=True``, raise ``stsSeconds`` in the Traefik
middleware to match, then submit the domain at https://hstspreload.org/.
Until then the ``stsPreload`` flag in the Traefik middleware should be dropped
in ops-library so both layers agree.

Static Files
~~~~~~~~~~~~

Static files are served using WhiteNoise in production, eliminating the need for a separate web server for static content.
