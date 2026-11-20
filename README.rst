Homepage
========

Just my own personal site


:License: MIT

Basic Commands
--------------

Running Tests
^^^^^^^^^^^^^

::

    $ pytest

Weeknote conversion
^^^^^^^^^^^^^^^^^^^

``convert_weeknote_links`` uses bounded invocations and explicit page-ID
continuation. See ``docs/weeknote_links.rst`` for budgets, partial runs and
receipt recovery before using ``--write`` or ``--publish``.

Developer quality commands
^^^^^^^^^^^^^^^^^^^^^^^^^^

Run ``uv run python commands.py test``, ``mypy``, or ``coverage`` (Mypy must be
installed separately). These commands exit zero on success, preserve nonzero
tool exit statuses (signals become 128 + signal number), and exit 1 with a diagnostic if a tool cannot start.
Coverage generates a report only after its tests pass, and opens it on macOS/WSL
only after report generation succeeds. Report failures and macOS opener failures
also fail the command. WSL Explorer return codes are best-effort because Explorer
can return nonzero after successfully opening; failure to start it still exits 1.
``just test`` and ``just coverage`` use these same commands. The committed coverage
configuration uses ``django-coverage-plugin``, included in the locked development
dependencies. ``uv sync --locked`` installs it (see ``docs/tests.rst``).
Template coverage remains unavailable with the current test settings; coverage
can warn and continue with Python coverage only (see ``docs/tests.rst``).

Lint
^^^^

::

    $ flake8

Continuous Integration
^^^^^^^^^^^^^^^^^^^^^^

GitHub Actions (``.github/workflows/ci.yml``) runs on every push and pull request:

* ``audit``: pinned pip-audit against the frozen runtime/development registry graph (see below)
* ``lint``: the pre-commit hooks via ``uv run prek run --all-files`` (Python 3.15.2)
* ``test``: ``pytest`` against a PostgreSQL 17 service container (Python 3.14
  and 3.15.2, uv 0.13.6, ``uv sync --locked``), with dummy AWS settings; test settings keep uploads in memory
* migration regressions: real executor reversals on fresh test databases
* portfolio browser gate: Chromium on synthetic rendered pages (Python 3.14 job; see ``docs/tests.rst``)

User pages
^^^^^^^^^^

User pages under ``/users/`` are not a public member directory. The list at
``/users/`` is for staff only: anonymous visitors are sent to the login page and
logged-in non-staff users get a 403. A profile at ``/users/<username>/`` is shown
to its owner and to staff. Anonymous visitors are sent to the login page; any
other logged-in user gets a 404, so the page does not reveal whether a username
exists.

Docs
^^^^

::

    $ cd docs
    $ make html

Local development services
^^^^^^^^^^^^^^^^^^^^^^^^^^

``just dev`` starts PostgreSQL and Django; ``just dev-all`` or ``./run_dev.sh``
starts the full Procfile. All use ``dev_runner.py`` to own one supervisor per
checkout, stream terminal output and save a colour-stripped ``logs/dev.log``.
Output drains in fixed 16 KiB byte chunks, including unterminated lines, with
incremental UTF-8 decoding (invalid bytes are replaced). Colour sequences split
across chunks are stripped with at most 256 characters of carry. Incomplete
escape suffixes exceeding that limit and unsupported sequences remain literal.
Terminal output stays live.

The active log rotates at 5 MiB into ``dev.log.1`` and ``dev.log.2``: at most
three files and 15 MiB of log content, with UTF-8 boundaries preserved. These
names belong to the runner. Startup resets the active log; backups remain until
rotation replaces them. ``just logs`` reads the active file; reopen or restart
``just logs-follow`` after rotation to follow the new active file.

``just cleanup`` signals only the runner recorded in ``logs/dev.json`` after
checking its PID, creation time, command and checkout. The runner stops its own
process group on exit, including INT, TERM, HUP and QUIT. ``just dev-force`` cleans up that checkout before starting
again; unrelated servers and notebooks are left alone. Individually started
services are not owned by this runner.

Cleanup refuses stale, legacy or mismatching records. Inspect the recorded
process first, then remove stale ``logs/dev.json`` (or the old ``logs/dev.pid``)
manually after inspecting/stopping any orphaned service PIDs individually; never
use a command-name kill to recover. Startup refuses to overwrite
an existing record. The stable ``dev.lock`` is opened without truncation or following
symlinks; only a regular file owned by the current user with one hard link is
admitted. The named inode must still match after the exclusive lock is acquired.
Never remove or replace ``dev.lock`` while a runner is active. The runner uses POSIX process groups and the locked ``psutil``
development dependency. Install dependencies with ``uv sync --locked`` first.
Supervisor failures produce a nonzero command status (including through logging),
signals become 128 + signal number. The leader stays unreaped until the owned
process group has received TERM (up to ten seconds grace) and a final KILL (two seconds
to confirm retirement), including descendants of an already-exited leader. Only
confirmed retirement removes the ownership record; failures retain its group ID
for manual inspection. Process-table access and POSIX ``waitid(WNOWAIT)`` are
required (on macOS: Python 3.13 or newer; older interpreters are refused before start).

Locked dependency audit
^^^^^^^^^^^^^^^^^^^^^^^

Run ``python audit_dependencies.py`` locally, exactly as CI does. It exports the
frozen default runtime and development graph without resolving or changing the
lock, then runs ``pip-audit==2.10.1 --strict --disable-pip --no-deps``. Export,
extraction, dependency collection and auditor failures fail the command. Registry
requirements retain their interpreter/platform markers, so the audit covers the
current environment (CI uses Linux/Python 3.15.2). Optional groups and separately
resolved prek hook environments are outside this export.

The five first-party Git requirements (cast-bootstrap5, cast-vue, django-cast,
django-indieweb and django-resume) are printed with their locked commits and
excluded from registry matching; their registry transitives remain audited.
Unexpected sources fail closed. This is not an advisory audit of the Git source
code. ``PIP_AUDIT_CACHE_DIR`` can override the default ``.cache/pip-audit`` cache.

The development lock refresh raises Black to at least 26.10.1 and Tornado to at
least 6.6 for the reported formatter/notebook advisories. Application dependencies
and all five source commits remain pinned. The independent Black prek hook uses
the same fixed formatter release; no application deployment is needed.

Selector and notebook security updates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The lock uses Soup Sieve 4.1 with Beautiful Soup 4.15.0. Soup Sieve requires
Python 3.11.5 or later, below this project's Python 3.12 minimum. Its 4.x
selectors skip inert HTML ``template`` contents unless called on the template
itself; ``iframe`` children no longer count as a separate document. See the
`Soup Sieve changelog <https://facelessuser.github.io/soupsieve/about/changelog/>`_
and `CVE-2026-126190 advisory <https://github.com/facelessuser/soupsieve/security/advisories/GHSA-mmhr-3c5m-f64f>`_.

Tornado 6.6.1 enters only through ``dj-notebook``'s Jupyter development stack
(ipykernel, jupyter-client/server/lab, notebook and terminado), not the runtime
graph. No application code imports Tornado. The
`6.6.1 release notes <https://www.tornadoweb.org/en/stable/releases/v6.6.1.html>`_
list security fixes and restore compatible RedirectHandler substitutions;
no API migration is needed from the previously locked 6.6. LF-only HTTP header
endings are scheduled for removal in 6.7. Regression tests check the
`CVE-2026-126347 triple-slash redirect fix <https://github.com/tornadoweb/tornado/security/advisories/GHSA-5cjw-f85j-cv6r>`_
and ordinary local substitutions without opening a server socket.

Legacy transfer helper
^^^^^^^^^^^^^^^^^^^^^^

Prefer ``just production-db-to-local`` for a local SQL restore. The independent
``scripts/prod_to_local.py`` remains a legacy Docker/media workflow and requires
Paramiko separately (``uv run --with paramiko python scripts/prod_to_local.py``).
Only explicit invocation loads dotenv, reads ``PRODUCTION_HOST`` and
``PRODUCTION_USERNAME`` and starts transfer/local operations; importing it is inert.
Docker commands receive literal argument lists, including backup names containing
spaces, quotes or shell punctuation. A failed command stops subsequent steps.

Local SQL publication delegates to ``commands.py``'s maintained staging,
verification and cutover implementation; it never drops the live database first.
Replacing an existing local ``homepage`` database requires ``--replace-existing``.
The maintained restore preconditions (this consent and no leftover staging or
recovery database from an interrupted restore) are checked before the production
backup is requested and before any Docker/media step. The maintained restore checks
them again at the end, so a database created meanwhile still stops the SQL step
after the legacy Docker/media steps ran. This helper is not a deployment tool.

The legacy fetch accepts exactly one ``scp homepage:site/backups/<name>.sql.gz
backups`` announcement (shell quoting is accepted as data), only after a zero
remote exit status. Combined stdout/stderr is limited to 64 KiB. SSH connection,
banner and authentication timeouts are ten seconds; the complete remote backup
command has 30 minutes, SFTP setup has 300 seconds, and the prefetched download
has 300 seconds plus one second per MiB of the announced size (about three hours
for the 10 GiB maximum). Channel I/O and each transport close have ten seconds. Hard negotiation deadlines require POSIX,
the main thread and an unused real-time signal timer. Existing signal handlers
are restored. Unknown SSH host keys remain refused.

The helper caps SFTP prefetch at 64 concurrent requests with Paramiko 3.3 and
later. With Paramiko 2.8 through 3.2, it disables prefetch and reads
sequentially. See the
`Paramiko SFTP documentation <https://docs.paramiko.org/en/3.3/api/sftp.html#paramiko.sftp_client.SFTPClient.getfo>`_.

Downloads must be nonempty regular remote files of at most 10 GiB, retain their
size/mtime during transfer, and match the received byte count. A unique private
stage (directory 0700, file 0600) holds the download. The maintained dump verifier
requires a complete gzip stream and pg_dump completion marker. All transports
must close successfully before an atomic, non-overwriting publication under
``backups/``. The helper syncs the backup directory after linking the final
name and again after removing the private stage. It also syncs the parents of
newly created backup directories. If a sync fails after publication, the
helper reports the path with uncertain durability, preserves the named backup,
and stops before starting local restore steps.
Existing files, including symlinks, are refused and preserved;
remove or move an old backup deliberately before retrying the same name. Failed
or interrupted downloads remove their owned stage and never start local steps.
A forced process kill may leave a private ``.legacy-backup-*`` stage; inspect and
remove it manually. Backup validation establishes transfer completeness, not
trust in arbitrary SQL; use only the configured trusted backup producer.
