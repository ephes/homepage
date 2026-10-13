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

2026-10-13 library refresh
--------------------------

``uv.lock`` moves django-indieweb ``develop`` from ``c7b8da62`` to ``4022366f``,
django-cast ``develop`` from ``8205bc48`` to ``5ac84fbd`` (0.2.68 development),
django-resume ``main`` from ``6f7ae123`` to ``195865ad``, cast-bootstrap5 ``main`` from ``d0ea6879`` to ``88134d96``.
No other locked package changed. None of the updates has a migration.

A follow-up on the same day moves django-indieweb ``develop`` from ``4022366f``
to ``9726be2d``; no other locked package changed and there is no migration or
settings change. The webmention rate limit now has a fixed window that no
longer extends while a client keeps sending (see :doc:`indieweb`, *Receiving
webmentions*). The counters use a new cache key namespace, so every client
starts with a fresh allowance after the deploy.

One setting is new: ``config.settings.production`` sets
``INDIEWEB_RATE_LIMIT_TRUSTED_PROXY_HOPS`` from ``DJANGO_NUM_PROXIES`` (default
``1``), so django-indieweb rate limits count the client address that Traefik
appends to ``X-Forwarded-For`` and not Traefik's own address. Local and test
settings keep the library default ``0`` (``REMOTE_ADDR``).

**Check before deploying:** django-cast now takes the Voxhelm API base and
token as a pair from one level: the Wagtail ``Voxhelm settings`` of the site
if either field is filled, otherwise the Django settings, otherwise the
environment. A site that has only one of the two Wagtail fields filled no
longer inherits the other from the environment, and transcript generation is
disabled for it. Before the deploy, open ``Settings -> Voxhelm settings`` for
every site and make sure that either both fields are blank (deployment
credentials are used) or both are filled. Changing the API base in Wagtail now
requires re-entering the token; saving with both fields blank removes the
stored token.

* django-indieweb analyses at most two received Webmention documents at a
  time per lock directory (``INDIEWEB_WEBMENTION_PARSE_MAX_CONCURRENT``). A
  further one waits up to 1 s for a slot; after that a synchronous receive
  answers ``503`` with ``Retry-After: 1``. An already verified mention keeps
  its state; a new submission is left as a ``pending`` row. Fetching a
  source or Vouch document has a total budget of 15 s
  (``INDIEWEB_WEBMENTION_FETCH_TOTAL_TIMEOUT_SECONDS``); a source that sends
  its body too slowly is marked ``failed``. Relative links in a source are
  resolved against the fetched source URL, so posts on this site can mention
  each other with relative links; documents containing ``<base`` still match
  on absolute links only. All new settings stay at their defaults.
  These apply to ``/indieweb/webmention/``. The lock directory stays at its
  default below the system temporary directory. The ``wagtail_deploy`` units
  use ``PrivateTmp``, so gunicorn and the transcript worker each have their own
  directory and their own two slots.
* django-indieweb keeps the complete ``next`` URL, including the
  authorization parameters, when IndieAuth or token management redirects to
  the login page.
* django-cast leaves view-restricted pages, and pages below them, out of the
  navigation links of blog, post and feed pages, for signed-in visitors too.
  Feed descriptions are rendered with the default theme of the blog or site
  and ignore a visitor's session, query or preview theme.
* django-cast answers HTMX theme-selector requests with the plain fragment
  when a theme has no ``select_theme.html``, and ``manage.py check`` reports
  missing optional theme templates as ``cast.W002`` warnings.
  ``Transcript.rewrite_speaker_labels`` also renames generic ``Speaker N:``
  cue prefixes.
* django-resume: the inline editor and the admin textarea now show stored text
  entity-escaped, so ampersands, angle brackets and nonbreaking spaces survive
  an unchanged save. Entities stored by earlier versions are not repaired and
  show up literally (for example ``&amp;``) until edited. Length limits apply
  to the stored text. ``manage.py remove_all_resumes`` only prints a count
  unless ``--delete-all-resumes`` is given; no deploy step or scheduled job
  here runs it. Inline edits of the token requirement switch no longer return
  an error. URL imports have a total budget of 15 s, JSON Resume imports reject
  more than 64 nesting levels and files over 2 MiB, and image uploads stop
  reading at 2 MiB. The admin loads HTMX 2.0.3 with a subresource integrity
  hash.
* cast-bootstrap5 ships rebuilt bundles, so ``collectstatic`` picks up new
  hashed assets. A Podlove player that fails to load shows a message and a
  ``Retry loading player`` button instead of loading forever. The color mode
  choice applies for the rest of the page session when the browser refuses to
  store it. Search suggestions give up after 5 s and say so; submitting the
  search still works. Consecutive plain blockquotes merge only when nothing
  but whitespace separates them and they carry no attributes such as ``cite``
  or ``id``.

2026-10-12 security library refresh
-----------------------------------

``uv.lock`` moves django-indieweb ``develop`` from ``289ea25a`` to ``c7b8da62``,
django-cast ``develop`` from ``95965b91`` to ``8205bc48`` (0.2.68 development),
django-resume ``main`` from ``c9d5172f`` to ``6f7ae123``, cast-bootstrap5 ``main``
from ``4ed370aa`` to ``d0ea6879`` and cast-vue ``main`` from ``a0db14fb`` to
``0e1d408b``. No other locked package changed. None of the
updates has a migration, and no settings change is needed.

* django-indieweb parses fetched Webmention source and Vouch documents in a
  short-lived child process, ``python -m indieweb.webmention_parse_worker``,
  one per fetched document. The child limits itself to 512 MiB of address
  space and 20 s of CPU time; the receiving process ends it after 30 s. Over a
  limit the Webmention is marked ``failed`` and nothing from the document is
  stored. The ``INDIEWEB_WEBMENTION_PARSE_*`` settings stay at these defaults.
  The Webmention endpoint (``/indieweb/webmention/``) processes in the request,
  so the child is started by a gunicorn worker with the interpreter of the
  same virtualenv (``sys.executable``); the gunicorn timeout of 600 s is well
  above the 30 s limit. The ``wagtail_deploy`` units (``NoNewPrivileges``,
  ``PrivateTmp``, ``ProtectSystem=strict``) have no system call filter, memory
  limit or task limit that would stop the child or its ``setrlimit`` calls,
  and the child's temporary result files go to the private ``/tmp``. Each
  concurrent receive can start one child of up to 512 MiB. On Linux the kernel
  enforces the memory limit; the local macOS check is only a backstop, so
  after deploying to staging send one Webmention and confirm that it is
  verified and that the log has no ``source too expensive to process``
  warning.
* django-cast limits comment posting to ``CAST_COMMENTS_POST_RATE_LIMIT`` posts
  (default 20) per ``CAST_COMMENTS_POST_RATE_WINDOW`` seconds (default 600) per
  logged-in user or anonymous client address and answers further posts with
  ``429`` and ``Retry-After``. Both settings stay at their defaults. The
  client address comes from ``REST_FRAMEWORK["NUM_PROXIES"]``
  (``DJANGO_NUM_PROXIES``, default ``1``), which matches Traefik as the only
  reverse proxy; see :doc:`admin_login_throttle`. The counters live in the
  ``default`` cache, not in ``api_token_auth_throttle``.
* django-cast ``media_replace --yes`` and ``recalc_video_posters`` now exit
  non-zero when at least one item failed, and ``media_backup`` has a new
  ``--refresh-changed`` option. No deploy step or scheduled job here runs these
  commands.
* django-resume renders ``company_url``, project ``url`` and ``school_url`` only
  as ``http``, ``https`` or ``mailto`` links, removes plugin data in one
  transaction with row locks, and writes ``export_json_resume`` output
  atomically with owner-only permissions (``0600``).
* cast-bootstrap5 and cast-vue ship rebuilt bundles (gallery metadata and modal
  focus fixes; comment drafts and list state fixes), so ``collectstatic`` picks
  up new hashed assets.

The 588 tests passed on Python 3.14.8 against PostgreSQL. ``makemigrations
--check`` reported no changes.

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

The same worker processes received webmentions, one task at a time; see
*Receiving webmentions* in :doc:`indieweb`. Since 2026-10-13 the Webmention
endpoint answers ``202`` and leaves the fetch to this worker, so a stopped
worker means that received webmentions stay ``pending``. Deploy the web process
and the worker from the same commit: a worker running older code fails the
queued task because it cannot import it.

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
