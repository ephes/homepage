Deploy
========

Staging and production deployments run through ops-control (SOPS-backed).

Ops-control Prerequisites
-------------------------

* An ops-control clone (set ``OPS_CONTROL`` if not located at ``../ops-control``)
* An ops-library clone (set ``OPS_LIBRARY_PATH`` if not located at ``$PROJECTS_ROOT/ops-library``)
* SOPS age key configured (``SOPS_AGE_KEY_FILE`` defaults to ``~/.config/sops/age/keys.txt``)
* ``PROJECTS_ROOT`` pointing at the parent directory that contains this repo
* ``just`` and ``uv`` installed locally; ops-control selects the deployment engine
  from its current service metadata for the requested host.

Deployment Commands
-------------------

From Justfile
~~~~~~~~~~~~~

Deploy to staging via ops-control::

    just deploy-staging

Deploy to production via ops-control::

    just deploy-production

The recipes call ``just deploy-one homepage staging`` or
``just deploy-one homepage production`` inside ``OPS_CONTROL``. This respects
ops-control's current per-host Ansible/pyinfra routing and safety guards; do not
bypass those guards with a direct Ansible invocation. Update ops-control before
deploying so its metadata reflects the intended engine.

``PROJECTS_ROOT`` defaults to this checkout's parent. The dispatcher always deploys
``$PROJECTS_ROOT/homepage``: name this checkout ``homepage`` when using that
default. A checkout named differently would select a sibling ``homepage`` instead;
set ``PROJECTS_ROOT`` explicitly to the parent of the intended ``homepage`` source
and verify it before deployment.
``SOPS_AGE_KEY_FILE`` and ``OPS_LIBRARY_PATH`` are forwarded to the dispatcher.
The legacy Ansible Homepage branch in ops-control currently selects its default
SOPS key internally; a custom forwarded key is effective on the pyinfra path.
These commands deploy the selected local source, including uncommitted changes;
inspect its status and diff before deployment.

For an Ansible target, prepare collections when needed with ``just deploy-bootstrap``.
It installs the required collections and the local ``ops-library`` collection.
Pyinfra deployments do not need that bootstrap. Its launcher remains configurable::

    ANSIBLE_GALAXY_CMD="uvx --python 3.14 --from ansible-core ansible-galaxy" just deploy-bootstrap

Ansible bootstrap runs on Python 3.14 because ansible-core 2.21 does not start on
Python 3.15. Deployment launcher selection belongs to ops-control.

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

JSON Resume render themes
-------------------------

django-resume renders a resume with JSON Resume themes from a pinned catalog
(``/resume/<slug>/json-resume/themes/``). A theme is an npm package that the
``resumed`` renderer executes with Node.js; ``resumed`` 7 needs Node.js 24.

* ``DJANGO_RESUME_JSON_RESUME_THEME_DIR`` is the theme cache. It defaults to
  ``.django-resume-jsonresume-themes`` in the project root and can be set
  through the environment variable of the same name.
* Resume owners cannot make the server run ``npm install``
  (``DJANGO_RESUME_JSON_RESUME_ALLOW_CATALOG_THEME_INSTALL`` stays ``False``).
  **Preview render** and **Use render theme** work for themes in the cache and
  answer 403 with "... is not installed on this site ..." otherwise.
* Production: the ops-control playbook installs Node.js 24 (NodeSource, role
  ``nodejs_install``) and runs
  ``python manage.py install_json_resume_catalog_themes`` on every deploy,
  where ``homepage_resume_themes_enabled`` is set for the host. The cache
  directory is excluded from the rsync, so it survives deploys. Staging has
  the switch off: themes answer 403 there.
* Locally, with Node.js 24 and npm on ``PATH``::

    uv run python manage.py install_json_resume_catalog_themes

2026-11-27 cast-react v0.0.7
----------------------------

``uv.lock`` moves cast-react from ``v0.0.6`` (``e9beabd0``) to ``v0.0.7``
(``78ecc24a``, from its Git tag). Nothing else in the lock changed. No
migration and no settings change. Dropdowns draw their own arrow with room
to the right edge; the footer Site theme menu aligns with the header, stacks
on phones and also appears on Django-rendered pages (feed, transcript, plain
pages), except on the full theme chooser. Static assets and templates only.

Rollback: as under "2026-11-27 React theme (cast-react v0.0.3)" below, with the
commit before this change; a reader who chose React then sees the 0.0.6
controls again.

2026-11-27 cast-react v0.0.6
----------------------------

``uv.lock`` moves cast-react from ``v0.0.5`` (``b82b43cb``) to ``v0.0.6``
(``e9beabd0``, from its Git tag). Nothing else in the lock changed. No
migration and no settings change. List rows show only the post's overview
with a "Read more" link to the post page; the post page shows overview and
detail. Static assets only.

Rollback: as under "2026-11-27 React theme (cast-react v0.0.3)" below, with the
commit before this change; a reader who chose React then sees the 0.0.5 list
again.

Deployed ``0f137f6`` on 2026-11-27 at 17:16 with ``just pyinfra-check homepage
production`` first, from an isolated clean ``PROJECTS_ROOT``. Verified after
it: the host's ``uv.lock`` names cast-react ``v0.0.6``; the units are active
with ``NRestarts=0`` and their journal since the deploy holds no warning or
error. In a browser with React chosen (phone and desktop): the blog post lists (first page, page 2, tag, month and search filters, the second blog) and a post
show only the overview with a Read more link, no detail part; the post page
shows overview and detail. The other themes answer 200 unchanged.

2026-11-27 cast-react v0.0.5
----------------------------

``uv.lock`` moves cast-react from ``v0.0.4`` (``8030bdad``) to ``v0.0.5``
(``b82b43cb``, from its Git tag). Nothing else in the lock changed. No
migration and no settings change. Tags and categories show the ten most-used
choices as pills; the rest open as a compact alphabetical index with counts
and a filter field. The custom date range folds below the month menu, list
rows show a cover only once, the phone header keeps navigation on one
scrolling line, and server pages use a centered column. Static assets only.

Rollback: as under "2026-11-27 React theme (cast-react v0.0.3)" below, with the
commit before this change; a reader who chose React then sees the 0.0.4 look
again.

Deployed ``bb0375f`` on 2026-11-27 at 13:58 with ``just pyinfra-check homepage
production`` first. Verified after it: the host's ``uv.lock`` names cast-react
``v0.0.5``; the units are active with ``NRestarts=0`` and their journal since
the deploy holds no warning or error. In a browser with React chosen (phone
and desktop, light and dark): the blog post list with the tag filter (top tags, searchable index, choosing a tag filters the list), a post, the feed page and the theme chooser render in the theme's look. The other
themes answer 200 unchanged.

2026-11-27 cast-react v0.0.4
----------------------------

``uv.lock`` moves cast-react from ``v0.0.3`` (``6a949de5``) to ``v0.0.4``
(``8030bdad``, from its Git tag). Nothing else in the lock changed. No
migration and no settings change. The release orders the tag and category
filters by post count (12 shown, the rest behind "Show all"), shows months as
one select grouped by year, and renders the feed page, transcript pages, the
theme chooser and pages without a blog (imprint, account pages) with the
theme's header and styles. These pages load a small ``page`` entry from the
same Vite manifest instead of the React app; ``collectstatic`` picks it up.
``test_cast_react_theme.py`` checks for the new page layout instead of the old
plain page.

Rollback: as under "2026-11-27 React theme (cast-react v0.0.3)" below, with the commit before this change; a
reader who chose React then sees the 0.0.3 look again.

Deployed ``5a0be16`` on 2026-11-27 at 13:12 with ``just pyinfra-check homepage
production`` first. Verified after it in a browser with React chosen: the blog's
post list with the filter panel (top tags and month menu), a post, and the
theme chooser render in the theme's look.

2026-11-27 React theme (cast-react v0.0.3)
------------------------------------------

``uv.lock`` adds cast-react ``v0.0.3`` (``6a949de5``, from its Git tag; it is
not on PyPI). Nothing else in the lock changed. ``cast_react`` joins
``INSTALLED_APPS``, ``CAST_CUSTOM_THEMES`` offers it as "React" and the
production ``DJANGO_VITE`` reads its manifest from
``staticfiles/cast_react/manifest.json``. The package ships its built bundle,
so ``collectstatic`` picks it up and no Node.js build runs on the host. No
migration. No blog changes its theme: React is only used where a reader picks
it in the theme chooser (stored in the session) or an editor sets it.

Deployed ``9c70913`` over ``ebc7f51`` on 2026-11-27 at 11:44. No task result
was ``READY`` or ``RUNNING`` before it; ``just pyinfra-check homepage
production`` showed the source sync and its dependent steps; ops-control ran at
``9c555d76``. Verified after it: the host's ``uv.lock`` names cast-react
``v0.0.3`` (``6a949de5``) and ``staticfiles/cast_react/`` holds the bundle;
both units are active with ``NRestarts=0``; ``/``, the blog, its RSS feed and
``robots.txt`` answered 200. In a browser the theme chooser offers React;
choosing it shows the blog's post list and a post in the React theme, the
chooser page itself and the account pages still render, and choosing Bootstrap
5 again restores the previous look. The other themes answer 200 unchanged
(``?theme=`` for bootstrap5, vue, bootstrap4 and plain). The journal since the
deploy holds only the known CSP report-only notices on ``/blogs/``.

Rollback: the sequence under "2026-11-27 django-cast 766c225f" below, with
the commit before this change, including the emptied ``staticfiles``. No
database step is needed, unless an editor has since saved React as a theme:
first check ``manage.py shell`` for ``Blog.objects.filter(template_base_dir="react")``
and ``TemplateBaseDirectory.objects.filter(name="react")`` (both in
``cast.models``) and set any match back to its previous theme in the Wagtail
admin and publish it (a draft leaves the live theme on React), then rerun the
queries; django-cast keeps using a stored ``react`` after the package is
gone. A reader whose session still names ``react`` falls back to the site's
theme on its own.

2026-11-27 django-cast 766c225f, cast-bootstrap5 44aece3, django-indieweb 47a983a
---------------------------------------------------------------------------------

``uv.lock`` moves django-cast ``develop`` from ``d4f29f33`` to ``766c225f``
(still 0.2.70 development state), cast-bootstrap5 from ``8a11f2b`` to
``44aece3`` and django-indieweb ``develop`` from ``3faf52a`` to ``47a983a``.
Nothing else in the lock changed. No package adds a migration in these
ranges; django-cast and cast-bootstrap5 ship new Vite bundles and manifests.
The upgrade actions in django-cast 0.2.70 concern the editor API, Voxhelm
settings clients and primary/replica routers; this site uses none of them (no
``DATABASE_ROUTERS``).

Local gates on PostgreSQL 17: dependency audit, prek, npm test (25 passed),
pytest on Python 3.15.2 and 3.14 (1454 passed each), the migration tests (8
passed), 49 browser tests and the docs build with ``-W``.

Deployed ``4c732aa`` over ``7ed91ed`` on 2026-11-27 at 08:44 (owner approval
in chat the same day; the only other change since ``7ed91ed`` is the deploy
history). No task result was ``READY`` or ``RUNNING`` before it; ``just
pyinfra-check homepage production`` showed only the source sync; ops-control
ran at ``49b3ab74``. Verified after it: the host's ``uv.lock`` names the three
new revisions; both units are active with new PIDs and ``NRestarts=0``; the
front page, the blog, a post, the blog RSS feed, the Claas und Nora blog, one
of its posts and its RSS feed, ``/cms/login/`` and ``robots.txt`` answered
200 and the static CSS/JS of a post and the front page answered 200; the
journal of both units held no error for the first ten minutes and no warning
that was not already logged before the deploy (CSP report-only notices on
``/blogs/`` and 404s for unknown URLs). The Claas und Nora RSS feed still takes about
3.2 s uncached; its cost is not the storage size lookup.

Rollback to ``7ed91ed``, under the shared production deploy lock:

1. As root stop ``homepage.service`` and ``homepage-db-worker.service``.
2. As the ``homepage`` user empty ``/home/homepage/site/staticfiles`` (what
   ``collectstatic --clear`` does), for the reason given in step 3 of the
   2026-11-25 relock rollback below.
3. In ops-control run ``just pyinfra-check homepage production`` and
   ``just deploy-one homepage production`` with ``PROJECTS_ROOT`` pointing at
   the parent of a clean checkout of the previous commit.

No database step is needed.

2026-11-26 Weeknote link sections keep order and visible spaces
---------------------------------------------------------------

Deployed ``7ed91ed`` (last recorded deploy ``9e32eac``) on 2026-11-26 at 17:53
as a routine code-only deploy. The change sits in the manually run
``convert_weeknote_links`` command: every converted link section becomes its
own ``weeknote_links`` block, so adjacent sections keep their order and a
repeated heading, and a list with a nonbreaking or other visible space between
its items stays rich text. No service code path changes. No migration,
settings, static file, dependency or unit change; ``just pyinfra-check homepage
production`` showed only the source sync; ops-control ran at ``67d841c7``.

Verified after the deploy: ``converter.py``, ``CHANGELOG.md``,
``docs/weeknote_links.rst`` and ``uv.lock`` on the host equal ``7ed91ed``; both
units are active with new PIDs and ``NRestarts=0``; the journal of both units
since the deploy holds no warning or error; the front page, the blog, its RSS
feed and ``robots.txt`` answered 200. A read-only in-memory probe of
``convert_paragraph_html`` on the host returned three blocks for a Software,
Articles, Software sequence and kept a list with ``&nbsp;`` between its items
unconverted. The command itself was not run.

Rollback, only after the owner authorizes it: revert ``5a301a3`` and
``25996b8`` on main, then run ``just pyinfra-check homepage production`` and
``just deploy-one homepage production`` with ``PROJECTS_ROOT`` pointing at the
parent of a clean checkout of the reverted commit. No database step and no
static rebuild are needed.

2026-11-26 robots.txt for the blog filter URLs
----------------------------------------------

Deployed ``9e32eac`` (last recorded deploy ``3d35925``) on 2026-11-26 at 16:42
as a routine code-only deploy. ``robots.txt`` now disallows the blog index
filter parameters ``date_facets``, ``tag_facets`` and ``category_facets``, as
first (``/*?tag_facets=``) or later (``/*?*&tag_facets=``) query parameter;
crawlers walked every filter combination (about 40% of all requests). The only
other change since ``3d35925`` is documentation. No migration, settings, static
file, dependency or unit change; ``just pyinfra-check homepage production``
showed only the source sync; ops-control ran at ``8ff629a4``.

Verified after the deploy: ``https://wersdoerfer.de/robots.txt`` serves the new
rules; the front page, the blog, its second page and its RSS feed answered 200;
both units are active with new PIDs and ``NRestarts=0``; the journal of both
units since the deploy holds no warning or error.

Rollback, only after the owner authorizes it: revert ``9e32eac`` on main, then
run ``just pyinfra-check homepage production`` and
``just deploy-one homepage production`` with ``PROJECTS_ROOT`` pointing at the
parent of a clean checkout of the reverted commit. No database step and no
static rebuild are needed.

2026-11-26 Lossless weeknote prose and attributed sections
----------------------------------------------------------

Deployed ``3d35925`` (last recorded deploy ``7b5d19e``) on 2026-11-26 at 13:08
as a routine code-only deploy. The change sits in the manually run
``convert_weeknote_links`` command: top-level prose next to a converted section
keeps escaped text, HTML comments and nonbreaking spaces; a refused section
keeps the blank text between its heading and list; sections whose heading,
list, items, primary or source links carry attributes the structured block
cannot keep stay rich text. No service code path changes. No migration,
settings, static file, dependency or unit change; ops-control ran at
``8bb3ca0d``.

Verified after the deploy: ``converter.py``, ``CHANGELOG.md``,
``docs/weeknote_links.rst`` and ``uv.lock`` on the host equal ``3d35925``; both
units are active with new PIDs and ``NRestarts=0``; the journal of both units
since the deploy holds no warning or error; the front page, the blog and its
RSS feed answered 200. The command was not run.

Rollback, only after the owner authorizes it: revert the commits from
``81ce3c7`` to ``3d35925`` on main, then run
``just pyinfra-check homepage production`` and
``just deploy-one homepage production`` with ``PROJECTS_ROOT`` pointing at the
parent of a clean export of the reverted commit. No database step and no
static rebuild are needed.

2026-11-26 Cover image staging checks
-------------------------------------

Deployed ``7b5d19e`` over ``7cdbd2b`` on 2026-11-26 at 04:01 as a routine
code-only deploy. The change sits in the manually run
``update_blog_cover_image`` command: every staging write must accept the full
chunk and the staged file must match the source byte count before the image is
handed to Wagtail, and both temporary ``pre_save`` upload receivers are
disconnected even if registering the second one fails. No service code path
changes. No migration, settings, static file, dependency or unit change;
ops-control ran at ``204ad6b6``, and the pyinfra-check table was byte-equal to
the one of the previous deploy.

Verified after the deploy: ``update_blog_cover_image.py``, ``CHANGELOG.md``,
``docs/development.rst`` and ``uv.lock`` on the host equal ``7b5d19e``; both
units got new PIDs with ``NRestarts=0``; ``manage.py check`` under production
settings reports no issue; a read-only import probe
(``default_transaction_read_only=on``) shows the deployed command carries the
short-write and staged-size checks and connects the receivers inside the
``try`` block; the front page, the blog, its RSS feed, a post and the portfolio
host answered 200; the journal of both units since the deploy holds no warning
or error. The command was not run.

Rollback, only after the owner authorizes it: revert ``7b5d19e`` on main, then
run ``just pyinfra-check homepage production`` and
``just deploy-one homepage production`` with ``PROJECTS_ROOT`` pointing at the
parent of a clean export of the reverted commit. No database step and no
static rebuild are needed.

2026-11-26 Weeknote link conversion fidelity
--------------------------------------------

Deployed ``cfc01db`` over ``e394eba`` on 2026-11-26 at 00:14 as a routine
code-only deploy. The change sits in the legacy weeknote link converter, which
only the manually run ``convert_weeknote_links`` command calls: escaped text in
source labels and descriptions stays text (``1dd1480``), sections whose
heading, list, items or links carry a fragment target stay legacy rich text with
a warning (``80633bf``, ``cfc01db``), and the heading lookahead no longer copies
the remaining nodes (``8838294``). No service code path changes. No migration,
settings, static file, dependency or unit change; ops-control ran at
``204ad6b6``, and the pyinfra-check table was byte-equal to the steady one of
the previous deploy (only ``Sync homepage source`` changes content).

Verified after the deploy: ``converter.py``, ``CHANGELOG.md``,
``docs/weeknote_links.rst`` and ``uv.lock`` on the host equal ``cfc01db``; both
units got new PIDs with ``NRestarts=0``; ``manage.py check`` under production
settings reports no issue; a read-only shell probe
(``default_transaction_read_only=on``) converts two synthetic in-memory
paragraphs with the deployed converter and shows an item ``id`` keeping its
section as rich text with the fragment-anchor warning; the front page, the blog,
its RSS feed, a post, the facet API and the portfolio host answered 200; the
journal of both units since the deploy holds no warning or error. No weeknote
was converted.

Rollback, only after the owner authorizes it: revert ``1dd1480``..``cfc01db``
on main, then run ``just pyinfra-check homepage production`` and
``just deploy-one homepage production`` with ``PROJECTS_ROOT`` pointing at the
parent of a clean export of the reverted commit. No database step and no
static rebuild are needed.

2026-11-25 Webmention site paths on the publishing database, seeding site recheck
---------------------------------------------------------------------------------

Deployed ``e394eba`` over ``22df569`` on 2026-11-25 at 22:54 as a routine
code-only deploy. Runtime change: an outgoing Webmention resolves its source
URL before and after rendering from site root paths read on the publishing
database (``b5112c1``, building on ``896fcb7``, which this deploy ships too).
Also shipped, without a service caller: ``seed_portfolio`` rechecks the default
site after locking its parent page (``e394eba``). No migration, settings,
static file, dependency or unit change; ops-control ran at ``204ad6b6``. Before
the deploy no task result was queued or running, and the pyinfra-check table
was the steady one (only ``Sync homepage source`` changes content).

Verified after the deploy: the changed files and ``uv.lock`` on the host equal
``e394eba``; both units got new PIDs with ``NRestarts=0``; ``manage.py check``
under production settings reports no issue; a read-only shell probe
(``default_transaction_read_only=on``) shows the new
``_uncached_site_root_paths(database)`` signature and returns the two live site
roots; the front page, the blog, its RSS feed, a post, the portfolio host and
``/cms/login/`` answered 200, as did the CSS and JS the blog references; the
journal of both units since the deploy holds no warning or error. The
publishing-alias resolution itself runs only when a post is published and is
covered by tests only.

Rollback, only after the owner authorizes it: revert ``b5112c1`` and
``e394eba`` on main, then run ``just pyinfra-check homepage production`` and
``just deploy-one homepage production`` with ``PROJECTS_ROOT`` pointing at the
parent of a clean export of the reverted commit. No database step and no
static rebuild are needed.

2026-11-25 django-cast d4f29f33, cast-bootstrap5 8a11f2b, django-indieweb 3faf52a
---------------------------------------------------------------------------------

Deployed ``22df569`` over ``c356620`` on 2026-11-25 at 17:31 (owner approval in
chat the same day). Also shipped from main: the Webmention source URL recheck
after rendering (``fbd36a4``, ``7ea3e90``) and the operator command changes
``5cd2fe6`` and ``34e075f``. The pyinfra-check table was the steady one (no unit
change). Before the deploy no task result was queued. Verified after the
deploy: the host's ``uv.lock`` names the three new revisions; ``showmigrations``
lists ``indieweb.0032`` and ``indieweb.0033`` as applied; ``manage.py check``
under production settings reports no issue; both units got new PIDs with
``NRestarts=0``; the front page, the blog, the RSS feed, a post, the portfolio
host and ``/cms/login/`` answered 200 and the static CSS/JS they reference
answered 200; the journal of both units held no warning or error for the
first ten minutes.

``uv.lock`` moves django-cast ``develop`` from ``e0c632ad`` to ``d4f29f33``
(0.2.70 development state), cast-bootstrap5 from ``b7f16729`` to ``8a11f2b``
(gallery opening fixes) and django-indieweb ``develop`` from ``7ab7a8ef``
(before 0.7.0) to ``3faf52a`` (0.7.1 plus the unreleased 0.7.2 changes).
Nothing else in the lock changed. django-cast adds no migration in this range.
django-indieweb adds ``indieweb.0032`` (two nullable columns) and
``indieweb.0033`` (``failure_attempts``, a non-null JSON column without a
database default) on ``WebmentionOutboundTarget``; the deploy's ``migrate``
applies them. One homepage test changed: the Micropub source query budget
counts the token recheck on the write database (9 → 10 queries).

Migration window: between ``migrate`` and the unit restarts the old code
still serves. If a post is published in that window, its outbound Webmention
targets cannot be stored, the delivery failure is logged and swallowed, and
the publication itself succeeds. Precondition for the deploy: nobody publishes
while it runs, and no ``READY`` or ``RUNNING`` task result is queued.

Local gates on PostgreSQL 17: audit, prek, npm test, pytest on Python 3.15.2
and 3.14 (1367 passed each), the migration tests, 49 browser tests and the
docs build; ``manage.py check`` reports no ``indieweb`` issue.

Rollback to the live commit (``c356620``), under the shared production deploy
lock:

1. As root stop ``homepage.service`` and ``homepage-db-worker.service``.
2. If ``indieweb.0033`` was applied: the old code does not know
   ``failure_attempts`` (a non-null column without a database default), so
   reverse it with the new code that is still installed, as the ``homepage``
   user with the site ``.env``: ``manage.py migrate indieweb 0032``. This
   drops the per-attempt failure history and keeps the aggregate failure
   count, so the old code can insert outbound targets again and a later
   upgrade does not count stale attempts.
3. As the ``homepage`` user empty ``/home/homepage/site/staticfiles`` (what
   ``collectstatic --clear`` does). The deploy's plain ``collectstatic`` skips
   source files that are not newer than the collected copy, and the older
   packages come from the uv cache with older timestamps, so without this the
   newer Vite manifests of django-cast and cast-bootstrap5 would stay next to a
   ``staticfiles.json`` for the old lock and pages could fail with HTTP 500.
4. In ops-control run ``just deploy-one homepage production`` with
   ``PROJECTS_ROOT`` pointing at the parent of a clean checkout of
   ``c356620``. Its ``collectstatic`` fills the empty directory from the old
   packages, and the deploy starts both units again.

2026-11-25 Portfolio settings per site database and parity-checked deploy
-------------------------------------------------------------------------

Deployed ``c356620`` over ``75ee1e3``. The only runtime change is in the
portfolio (``7e0e198``): per-site shell and legal settings are read from the
database alias of the request's Wagtail site, and a draft project preview with
exactly one public sibling now recommends it. On production the site comes from
the default database and nine projects are public, so public pages render as
before. Also shipped, without a runtime caller: the ``CastURLResolver`` changes
(``e42c22c``; django-indieweb does not call it), the manually run
``regenerate_broken_renditions`` command (``9e2bbc5``), the contributor scripts
``scripts/subset_saira_fonts.py`` and ``scripts/get_video_data.py``
(``e446404``, ``5a9a421``), tests (``70395f2``) and a changelog wording fix
(``c356620``). No migration, settings, static file, dependency or ops-control
change; ops-control ran at ``bc906814``.

Gated under the shared production deploy lock, held from the first check to the
end of verification. Before the lock, a local preflight rebuilt both manifests
from the git objects and compared them byte for byte with the staged ones.
Under the lock, before deploy-one: all 437 tracked files of ``75ee1e3`` matched
on the host; the pyinfra-check table equalled the reviewed one row for row (only
``Install ca-certificates`` may vary with the apt cache); a file-level rsync dry
run with the deploy's arguments transferred exactly the 16 changed files; and a
read-only probe of the portfolio pages on the gunicorn origin
(``127.0.0.1:10013``, ``Host: design.wersdoerfer.de``) recorded a baseline:
status, body digest and length of the index, the eleven pages it links to and
one missing path, with every listener owned by ``homepage.service``. Verified
after the deploy: all 437 tracked files on the host equal ``c356620``; both
units got new PIDs and kept them for 120 seconds; the front page, the blog RSS
feed and the portfolio host answered 200; the same origin probe returned
records identical to the baseline; the journal of both units since the deploy
holds no traceback or error; and the Fediverse proxy on the origin still
answered like the fedi host. The draft-preview recommendation and a routed site
database are covered by tests only.

Rollback, only after the owner authorizes it: back to ``75ee1e3`` through the
reviewed wrapper of this deploy (``deploy.sh rollback``), not through a bare
``just deploy-one``. Under the shared production deploy lock the wrapper checks
that every tracked host file equals ``75ee1e3`` or is one of the 16 changed
files at its ``c356620`` content, that the pyinfra-check table lists the
reviewed operations by name in the same order, and that a file-level rsync dry
run transfers only those files. In that table, operations that already showed
a change in the reviewed forward table may differ; an operation that showed
none must still show none, except ``Install ca-certificates`` (varies with the
apt cache) and ``Start homepage.service`` / ``Start homepage-db-worker.service``
(a failed forward run can leave a unit stopped). It then runs deploy-one with
``PROJECTS_ROOT`` pointing at the parent of a clean checkout of ``75ee1e3`` and
repeats the post-deploy verification against ``75ee1e3``, including the
portfolio probe against the forward run's baseline. The wrapper belongs to
this deploy's bundle; if that bundle is no longer available, a rollback needs a
newly reviewed plan with the same gates. No database step and no static
rebuild are needed.

2026-11-25 Webmention recheck after rendering and bounded target diagnostics
----------------------------------------------------------------------------

Deployed ``75ee1e3``: an outgoing Webmention checks again after rendering that
the same revision is still live and publicly accessible on the publishing
database, so a restriction or a newer publication arriving while the post is
rendered suppresses the delivery (``ac24c90``); target diagnostics escape
non-printable characters and stop at 256 characters (``4037fc1``);
``5172904`` and ``75ee1e3`` only reword the rollback note of the previous
entry. No migration, settings, static file, dependency or ops-control change.

Gated under the shared production deploy lock, held from the first check to the
end of verification. Before the lock, a local preflight rebuilt both manifests
from the git objects of ``5385441`` and ``75ee1e3`` and compared them byte for
byte with the staged ones. Under the lock, before deploy-one: all 437 tracked
files of ``5385441`` matched on the host; the pyinfra-check table equalled the
reviewed one row for row (only ``Install ca-certificates`` may vary with the
apt cache); and a file-level rsync dry run with the deploy's arguments
transferred exactly the six changed files. Verified after the deploy: all 437
tracked files on the host equal ``75ee1e3``; both units got new PIDs and kept
them for 120 seconds; the front page, the blog RSS feed and the portfolio host
answered 200; the journal of both units since the deploy holds no traceback or
error; and the Fediverse proxy on the gunicorn origin still answered like the
fedi host. The changed code runs only when a post is published, so production
did not exercise it; the new behaviour is covered by the tests only.

Rollback, only after the owner authorizes it: back to ``5385441`` through the
reviewed wrapper of this deploy (``deploy.sh rollback``), not through a bare
``just deploy-one``. Under the shared production deploy lock the wrapper checks
that every tracked host file equals ``5385441`` or is one of the six changed
files at its ``75ee1e3`` content, that the pyinfra-check table lists the
reviewed operations by name in the same order, and that a file-level rsync dry
run transfers only those six files. In that table, operations that already
showed a change in the reviewed forward table may differ; an operation that
showed none must still show none, except ``Install ca-certificates`` (varies
with the apt cache) and ``Start homepage.service`` /
``Start homepage-db-worker.service`` (a failed forward run can leave a unit
stopped, and starting it again is part of the recovery). It then runs
deploy-one from a fresh ops-control worktree with ``PROJECTS_ROOT`` pointing
at the parent of a clean checkout of ``5385441`` and repeats the post-deploy
verification against ``5385441``. The wrapper belongs to this deploy's bundle;
if that bundle is no longer available, a rollback needs a newly reviewed plan
with the same gates. No database step and no static rebuild are needed.

2026-11-25 Fediverse proxy late deadline and resolver failures
--------------------------------------------------------------

Deployed ``5385441``: the Fediverse ``.well-known`` proxy rejects a response
that completes after the 10 s deadline with ``504``, even when the shutdown
timer runs late, by checking the elapsed time after the upstream headers and
after reading and closing the response stream (``2a6dfe5``); an unexpected
exception in the DNS resolver thread now returns ``502`` and releases the
resolver slot instead of failing the request with a server error
(``7f7cd5e``); ``5385441`` corrects the wording in the docs and changelog. No
migration, settings, static file, dependency or ops-control change. On
production Traefik sends the public ``.well-known`` paths straight to Mastodon,
so public requests do not reach this proxy; it is the fallback when that route
is switched off.

Gated under the shared production deploy lock, held from the first check to the
end of verification: before deploy-one, all 437 tracked files of ``2a2d4d4``
matched on the host; the pyinfra-check table equalled the reviewed one row for
row (only ``Install ca-certificates`` may vary with the apt cache); and a
file-level rsync dry run with the deploy's arguments transferred exactly the
six changed files. Verified after the deploy: all 437 tracked files on the host
equal ``5385441``; both units got new PIDs and kept them for 120 seconds; the
front page, the blog RSS feed and the portfolio host answered 200; the journal
of both units since the deploy holds no traceback or error; and a GET of
``/.well-known/nodeinfo`` on the gunicorn origin (``127.0.0.1:10013``, every
listener in ``homepage.service``) answered 200 from the Django proxy
(``Vary: Accept``) with the upstream's ``Cache-Control`` and the same body as a
direct request to the fedi host. This is a regression check of the changed
fetch path; the late-deadline ``504`` and the resolver ``502`` need fault
injection and are covered by the tests only.

Rollback, only after the owner authorizes it: back to ``2a2d4d4`` through the
reviewed wrapper of this deploy (``deploy.sh rollback``), not through a bare
``just deploy-one``. Under the shared production deploy lock the wrapper checks
that every tracked host file equals ``2a2d4d4`` or is one of the six changed
files at its ``5385441`` content, that the pyinfra-check table lists the
reviewed operations by name in the same order, and that a file-level rsync dry
run transfers only those six files. In that table, operations that already
showed a change in the reviewed forward table may differ; an operation that
showed none must still show none, except ``Install ca-certificates`` (varies
with the apt cache) and ``Start homepage.service`` /
``Start homepage-db-worker.service`` (a failed forward run can leave a unit
stopped, and starting it again is part of the recovery). It then runs
deploy-one from a fresh ops-control worktree with ``PROJECTS_ROOT`` pointing
at the parent of a clean checkout of
``2a2d4d4`` and repeats the post-deploy verification against ``2a2d4d4``. The
wrapper belongs to this deploy's bundle; if that bundle is no longer available,
a rollback needs a newly reviewed plan with the same gates. No database step
and no static rebuild are needed.

2026-11-25 Fediverse proxy cache directives and response close
--------------------------------------------------------------

Deployed ``2a2d4d4``: the Fediverse ``.well-known`` proxy passes every upstream
``Cache-Control`` field on, joined in upstream order (``2f22f39``), and closes
the upstream response once the bounded body read finishes or fails
(``2a2d4d4``). No migration, settings, static file, dependency or ops-control
change. On production Traefik sends the public ``.well-known`` paths straight
to Mastodon, so public requests do not reach this proxy; it is the fallback
when that route is switched off.

Gated under the shared production deploy lock, held from the first check to the
end of verification: before deploy-one, all 437 tracked files of ``3151d42``
matched on the host; the pyinfra-check table equalled the reviewed one row for
row (only ``Install ca-certificates`` may vary with the apt cache); and a
file-level rsync dry run with the deploy's arguments transferred exactly the
five changed files. Verified after the deploy: all 437 tracked files on the host
equal ``2a2d4d4``; both units got new PIDs and kept them for 120 seconds; the
front page, the blog RSS feed and the portfolio host answered 200; the journal
of both units since the deploy holds no traceback or error; and a GET of
``/.well-known/nodeinfo`` on the gunicorn origin (``127.0.0.1:10013``, every
listener in ``homepage.service``) answered 200 from the Django proxy
(``Vary: Accept``) with the upstream's ``Cache-Control`` and the same body as a
direct request to the fedi host. The upstream sends a single ``Cache-Control``
field, so the multi-field join is covered by the tests, not by this check.

Rollback: ``just deploy-one homepage production`` from a fresh ops-control
worktree, with ``PROJECTS_ROOT`` pointing at the parent of a clean checkout of
``3151d42``. No database step and no static rebuild are needed.

2026-11-25 Rendition repair transaction guard and blog deduplication
--------------------------------------------------------------------

Deployed ``3151d42``: ``regenerate_broken_renditions`` refuses an enclosing
transaction before it touches rendition storage and saves each repaired row in
its own durable transaction (``711d73b``), and it scans each requested blog
once even when its slug is passed more than once (``3151d42``). No migration,
settings, static file, dependency or ops-control change; only the command, its
tests and docs changed.

Gated under the shared production deploy lock, held from the first check to the
end of verification: before deploy-one, all 437 tracked files of ``6d129c0``
matched on the host; the pyinfra-check table equalled the reviewed one row for
row (only ``Install ca-certificates`` may vary with the apt cache); and a
file-level rsync dry run with the deploy's arguments transferred exactly the six
changed files. Verified after the deploy: all 437 tracked files on the host
equal ``3151d42``; both units got new PIDs and kept them for 120 seconds; the
front page, the blog RSS feed and the portfolio host answered 200; the journal
of both units since the deploy holds no traceback or error; and
``manage.py regenerate_broken_renditions --help`` loads with the site ``.env``
(no repair was run).

Rollback: ``just deploy-one homepage production`` from a fresh ops-control
worktree, with ``PROJECTS_ROOT`` pointing at the parent of a clean checkout of
``cc4a88c`` (code identical to ``6d129c0``). No database step and no static
rebuild are needed.

2026-11-25 Portfolio redirects, project shortcut and command receipts
---------------------------------------------------------------------

Deployed ``6d129c0``: slashless non-GET requests on the portfolio host get a
307 redirect that keeps method and body (``da1e03e``), the ``Projekte`` menu
offers ``Neues Projekt`` to editors with add permission on a portfolio
homepage they cannot edit (``fffc7e7``), ``seed_portfolio`` prints its creation
receipt after the commit (``0630e90``), and ``update_blog_cover_image`` tracks
only its own cover and rendition uploads for rollback (``8a692f2``). No
migration, settings, static file, dependency or ops-control change. The
pyinfra-check table was the steady one, with ``Install ca-certificates``
unchanged because the host's apt cache was less than an hour old.

Verified after the deploy: sha256 of the 259 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``6d129c0``; right before deploy-one, the synced checkout held exactly the 437
files of ``6d129c0`` byte for byte; the deploy log shows the source sync,
collectstatic and both unit restarts in that order; both units got new PIDs and
stayed on them for 120 seconds; the front page, the blog RSS feed and the
portfolio host answered 200; the journal since the deploy holds no traceback.
A POST with a valid CSRF token to the slashless ``/cms/login`` on the portfolio
host answered 301 before the deploy and 307 to ``/cms/login/`` after it, while
the slashless GET ``/impressum`` stayed 301; neither request logged in.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``df1c1ab``). No database step and no static rebuild are
needed.

2026-11-25 Portfolio bootstrap lock and blog cover source staging
-----------------------------------------------------------------

Deployed ``df1c1ab``: ``seed_portfolio`` locks the Wagtail parent page before it
checks for an existing portfolio and reports a site conflict without leaving a
draft page (``39a3858``), and ``update_blog_cover_image`` stages the source once
from a bounded regular file before the publication transaction (``df1c1ab``).
Both are operator commands; the services do not call them. No migration,
settings, static file, dependency or ops-control change; the pyinfra-check table
was the steady one.

Verified after the deploy: sha256 of the 259 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``df1c1ab``; right before deploy-one, the synced checkout held exactly the 437
files of ``df1c1ab`` byte for byte; the deploy log shows the source sync,
collectstatic and both unit restarts in that order; both units got new PIDs and
stayed on them for 120 seconds; the front page, the blog RSS feed and the
portfolio host answered 200; the journal since the deploy holds no traceback.
A read-only ``manage.py shell`` probe (read-only database session with lock and
statement timeouts, caches and network blocked, writes refused, no file
written) showed the deployed cover staging accepting a regular file up to the
exact limit and refusing oversized, empty, special, directory and missing
sources, and the deployed ``seed_portfolio`` reaching its page lock by id after
reading only the categories and the default site (the lock statement itself was
not sent).

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``d9fb890``). No database step and no static rebuild are
needed.

2026-11-24 Micropub category limits and title draft
---------------------------------------------------

Deployed ``d9fb890``: the local Micropub form and the Micropub handler reject a
category batch over 50 entries or 4,096 characters before validating single
names, and the form template keeps the article title draft when switching to
Note and back. The deploy also includes the development runner changes of
``2671144`` and ``3810ef7`` (not used by the services). No migration, settings,
static file or dependency change.

The same deploy applied two infrastructure changes from ops-control main
``3181d809``: uv 0.13.9 on the host (was 0.13.6), and ``homepage.service``
with ``RuntimeDirectory=django-site/homepage`` and
``XDG_RUNTIME_DIR=/run/django-site/homepage``, so Gunicorn 26 puts its control
socket at ``/run/django-site/homepage/gunicorn.ctl`` instead of
``~/.gunicorn/``.

Verified after the deploy: sha256 of the 259 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``d9fb890``; the deploy log shows the source sync, collectstatic and both unit
restarts in that order; both units got new PIDs and stayed on them for 120
seconds; the front page, the blog RSS feed and the portfolio host answered
200; the journal since the deploy holds no traceback. A read-only
``manage.py shell`` probe (read-only database session, caches and network
blocked, writes refused) showed the deployed form and handler rejecting 51
entries and 4,097 characters without validating any name, still accepting the
exact limits, and the template engine loading the new form template. A
read-only host check showed uv 0.13.9, the runtime directory owned by
``homepage`` and the Gunicorn master listening on the new control socket.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``8e49e38``). No database step and no static rebuild are
needed. The uv and unit changes belong to ops-control and stay.

2026-11-21 Portfolio theme sync across tabs and live reduced motion
-------------------------------------------------------------------

Deployed ``8e49e38``: the theme menu script of the portfolio site
(``homepage/portfolio/static/portfolio/prototype/theme-switch.js``) follows a
theme choice made in another open tab, including the reset to System, and reads
the reduced-motion preference at every menu close. The runtime change is this
one static file; collectstatic writes the new hashed name
``theme-switch.49648f0d94ae.js`` next to the old ``theme-switch.19e947e72adf.js``,
which stays in the static directory. No Python, template, migration, settings
or environment change.

Verified after the deploy: sha256 of the 259 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``8e49e38``; the deploy log shows the source sync, collectstatic and both unit
restarts in that order; both units got new PIDs and stayed on them for 120
seconds; the front page, the blog RSS feed and the portfolio host answered
200; the journal since the deploy holds no traceback. Two read-only HTTP
checks against ``https://design.wersdoerfer.de``: the index, the legal pages
and the 9 project pages each reference exactly the new hashed script, which is
served byte-identical to the committed file plain and gzip with the immutable
cache header; headless Chromium (off-origin requests, CSP reports and any
non-GET aborted) showed a second tab following dark, system, light (before the
deploy it stayed on system) and an immediate menu close under reduced motion
(before: delayed).

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``b410c92``). No database step is needed; the deploy's
collectstatic points the pages back to the old hashed file.

2026-11-21 Profile name save and staff account directory pages
--------------------------------------------------------------

Deployed ``a8bf1c8``: the profile form at ``/users/~update/`` saves only the
display name with one update of that column for the signed-in account (404 if
the account was deleted meanwhile), so concurrent changes to other account
fields are kept; the staff directory at ``/users/`` lists 50 accounts per page
in username order and answers invalid or out-of-range page values with 404
(``README.rst``, user pages). Production has three accounts, so the directory
stays one page without navigation. No migration, no new static files and no
settings or environment change.

Verified after the deploy: sha256 of the 259 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``a8bf1c8``; both units restarted after the source sync, got new PIDs and stayed
on them for 120 seconds; the front page, the blog RSS feed and the portfolio
host answered 200; the journal since the deploy holds no traceback. A read-only
``manage.py shell`` probe (same isolation as the previous deploy, now in one
repeatable-read snapshot) called the deployed views directly: the directory
lists exactly all accounts on page 1 of 1 with a page size of 50, a page beyond
the last gives 404 and non-staff users still get 403; a profile POST, with the
update stubbed and every model save refused, ran one name-only update for the
requesting account and no model save (before the deploy the same POST reached
a full model save).

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``8d5093f``). No database step and no static rebuild are needed.

2026-11-21 Webmention section ordering
--------------------------------------

Deployed ``8d5093f``: the webmention section of post pages shows each legacy
mention type as one section after likes, reposts, replies and mentions, and
places mentions without any date last in input order instead of sorting them by
the current time (``docs/indieweb.rst``, "Displaying webmentions"). The deploy
also ships the earlier merged changes to the manually run
``regenerate_broken_renditions`` and ``convert_weeknote_links`` commands (not
run by the deploy). Production has only the four preferred mention types and no
undated verified mention, so no rendered webmention section changed. No
migration, no new static files and no settings or environment change.

Verified after the deploy: sha256 of the 259 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``8d5093f``; both units restarted after the source sync, got new PIDs and stayed
on them for 120 seconds; the front page, the blog RSS feed and the portfolio
host answered 200; the journal since the deploy holds no traceback. A read-only
``manage.py shell`` probe (same isolation as the previous deploy) rendered the
webmention section of all 18 targets with verified webmentions: same counts and
same digest before and after, and the order equals the new rule already before
the deploy. Unsaved synthetic mentions showed the old ordering before and the
new grouping and stable undated placement afterwards.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``e8d6b6d``). No database step and no static rebuild are needed.

2026-11-21 Micropub source lookup races and image database
----------------------------------------------------------

Deployed ``e8d6b6d``: a Micropub ``q=source`` lookup whose post or content type
disappears between the route lookup and the concrete page fetch gets the ordinary
missing-target response (``400 invalid_request``) instead of a server error, and
the source export fetches unresolved image IDs from the post's own database
(``homepage/micropub/README.md``; production has a single page database, so its
exported source is identical). No
migration, no new static files and no settings or environment change.

Verified after the deploy: sha256 of the 259 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``e8d6b6d``; both units restarted after the source sync, got new PIDs and stayed
on them for 120 seconds; the front page, the blog RSS feed and the portfolio
host answered 200; the journal since the deploy holds no traceback. A read-only
``manage.py shell`` probe (``PGOPTIONS`` with ``default_transaction_read_only=on``,
``python -B``, inside a rolled-back transaction, all cache aliases replaced by
process-local memory caches, file-cache and socket access refused and
self-tested) resolved the live post ``/blogs/ephes_blog/out-of-yaml/``: the
normal lookup returned the post before and after; with the content type lookup or
the concrete post fetch made to raise ``DoesNotExist`` in-process, the lookup
raised before the deploy and returned ``None`` afterwards; the source export
produced HTML with the same image count and hash before and after and read its
images through the post's database alias (``default``) afterwards.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``e81ca07``). No database step and no static rebuild are needed.

2026-11-21 favicon HEAD and single-query homepage profiles
----------------------------------------------------------

Deployed ``234da06``: ``/favicon.ico`` accepts ``HEAD`` on the main and
portfolio hosts and answers it with the same media type, length, disposition
and one-day public cache policy as ``GET`` and an empty body (before: 405 with
``Allow: GET``). The homepage at ``/`` loads both featured user records with
one query; the rendered page is unchanged. No migration, no new static files
and no settings or environment change.

Verified after the deploy: sha256 of the 259 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``234da06``; both units restarted after the source sync, got new PIDs and stayed
on them for 120 seconds; the front page, the blog RSS feed and the portfolio
host answered 200; the journal since the deploy holds no traceback. A public
probe with a unique query string per request showed ``HEAD /favicon.ico`` on
both hosts change from 405 to 200 with the ``GET`` headers, ``GET`` serving the
same 477 bytes, and the anonymous front page rendering byte-identically after
blanking the CSRF tokens and nonces, with a freshly issued CSRF token.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``313a0c0``). No database step and no static rebuild are needed.

2026-11-21 webmention publish lookup and nonfatal delivery log
--------------------------------------------------------------

Deployed ``7752b77``: the ``page_published`` webmention receiver resolves a
base page to its Post or Episode explicitly on the publishing database instead
of through ``page.specific``, and the post-commit delivery callback keeps
running later commit callbacks if both delivery and its warning log fail. On
production only the ``default`` alias holds pages, so publishing behaves as
before. No migration, no new static files and no settings or environment
change.

Verified after the deploy: sha256 of the 258 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``7752b77``; both units restarted after the source sync, got new PIDs and stayed
on them for 120 seconds; the front page, the blog RSS feed and the portfolio
host answered 200; the journal since the deploy holds no traceback. A read-only
``manage.py shell`` probe (``PGOPTIONS`` with ``default_transaction_read_only=on``,
``python -B``, inside a rolled-back transaction, sending stubbed) gave the
receiver the base ``Page`` of the live public post 801: it queued exactly one
delivery callback (removed again, never run) before and after the deploy, and
afterwards through the new resolver on ``default``. The real committed lookup
returned post 801 for its live revision and nothing for a stale one. A direct
call of the delivery callback with a failing lookup and a failing warning log
raised ``OSError`` before the deploy and returned afterwards.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``9e658f8``). No database step and no static rebuild are needed.

2026-11-20 POST-only Micropub preview and best-effort success log
-----------------------------------------------------------------

Deployed ``266b1d3``: the logged-in local Micropub preview
(``/indieweb/micropub-form/preview/``) accepts only POST; other methods get
``405`` with ``Allow: POST`` before any content conversion, anonymous requests
still redirect to login. The local Micropub form keeps its success message and
redirect if writing the success log line fails. The legacy
``scripts/prod_to_local.py`` helper (bounded SFTP prefetch, directory syncs)
runs only on a developer machine. No migration, no new static files and no
settings or environment change.

Verified after the deploy: sha256 of the 258 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``266b1d3``; both units restarted after the source sync, got new PIDs and stayed
on them for 120 seconds; the front page, the blog RSS feed and the portfolio
host answered 200. A read-only ``manage.py shell`` probe (``PGOPTIONS`` with
``default_transaction_read_only=on``, ``python -B``, inside a rolled-back
transaction, no table access) called the preview view in-process with a
``RequestFactory`` request, an in-memory logged-in stand-in user and template
rendering stubbed: a GET returned 200 with an empty conversion before the deploy
and 405 with ``Allow: POST`` and no conversion afterwards; a POST rendered the
same escaped preview before and after.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``e22de29``). No database step and no static rebuild are needed.

2026-11-20 rendition purge after commit and narrow route lookup
---------------------------------------------------------------

Deployed ``e22de29``: the Micropub route lookup (``find_page_for_url``) probes
the Wagtail page tree with only the page ID and content type and then loads the
specific page once on the site's database. ``regenerate_broken_renditions``
purges the cache of a repaired rendition only after the write transaction
commits (:doc:`media_utils`). Public page rendering, Webmention resolution and
the portfolio are unchanged. No migration, no new static files and no settings
or environment change.

Verified after the deploy: sha256 of the 258 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``e22de29``; both units restarted after the source sync, got new PIDs and stayed
on them for 120 seconds; the front page, the blog RSS feed and the portfolio
host answered 200. A read-only ``manage.py shell`` probe (``PGOPTIONS`` with
``default_transaction_read_only=on``, ``python -B``, inside a rolled-back
transaction) resolved the live blog URL and a missing path through
``find_page_for_url``: the same results before and after (the specific ``Blog``,
fully loaded, and ``None``), with the route probe query reading 29 page columns
before the deploy and 2 afterwards.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``55c7f97``). No database step and no static rebuild are needed.

2026-11-20 portfolio detail context, seed scope and rendition retry fixes
-------------------------------------------------------------------------

Deployed ``1046691``: portfolio project detail pages reuse the already loaded
menu list for the two recommendations and the project counter and check each
content block once (:doc:`portfolio_wagtail`). The operator commands changed
too: ``regenerate_broken_renditions --retry-cache-purge`` skips rendition rows
that no longer exist and lists only renewed purge failures, an ambiguous blog
slug is refused before any repair (:doc:`media_utils`), and ``seed_portfolio``
works on the requested hostname and port or default-site path. No migration, no
new static files and no settings or environment change.

Verified after the deploy: sha256 of the 258 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``1046691``; both units restarted after the source sync, got new PIDs and stayed
on them for 120 seconds; the front page, the blog RSS feed and the portfolio
host answered 200. A read-only ``manage.py shell`` probe (``PGOPTIONS`` with
``default_transaction_read_only=on``, ``python -B``, inside a rolled-back
transaction, cache purge patched out) ran a purge retry for a rendition ID that
does not exist: before the deploy it failed and asked for the same retry again,
afterwards it reported the row as skipped and completed. The portfolio index,
the two legal pages and all nine linked project pages were fetched before and
after the deploy, directly from the gunicorn origin (checked to be the restarted
``homepage.service``) and through public HTTPS: all answered 200 with identical
HTML.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``de18414``). No database step and no static rebuild are needed.

2026-11-20 weeknote links with retired categories and webmention alias guards
-----------------------------------------------------------------------------

Deployed ``af821a6``: stored weeknote links whose category is no longer a
configured choice render in a final **Other links** group instead of
disappearing, and grouping runs in one pass (:doc:`weeknote_links`). Publishing
a post whose page or ancestor has a cyclic alias chain, or an alias source that
no longer exists, now proceeds without scheduling webmention delivery instead
of failing in the ``page_published`` receiver (:doc:`indieweb`). No migration,
no new static files and no settings or environment change.

Verified after the deploy: sha256 of the 258 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``af821a6``; both units got new PIDs and stayed on them for 120 seconds; the
front page, the blog RSS feed and the portfolio host answered 200. A read-only
``manage.py shell`` probe (``PGOPTIONS`` with
``default_transaction_read_only=on``, ``python -B``, inside a rolled-back
transaction) rendered an in-memory weeknote block with one retired and one
current category: before the deploy the retired link was missing, afterwards it
appeared under **Other links**. The same probe gave an unsaved copy of the main
blog page an alias to a non-existent page ID: before the deploy the visibility
check raised ``Page.DoesNotExist``, afterwards it returned ``False``; the blog
page itself stayed public both times.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``f665dee``). No database step and no static rebuild are needed.

2026-11-20 page lookup by target host and rendition repair fences
-----------------------------------------------------------------

Deployed ``34744f6``: Micropub source queries resolve a page URL with the
URL routes of its target host, so portfolio-host URLs such as
``https://design.wersdoerfer.de/<project>/`` now find their page (:doc:`indieweb`).
``regenerate_broken_renditions`` batches post image and gallery lookups, keeps
the original rendition when its file reappears or storage cannot confirm it is
missing, and ``--retry-cache-purge`` requires the reported ``--database``
alias (:doc:`media_utils`). No migration, no new static files and no settings
or environment change.

Verified after the deploy: sha256 of the 258 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``34744f6``; both units got new PIDs and stayed on them for 120 seconds; the
front page, the blog RSS feed and the portfolio host answered 200. A read-only
``manage.py shell`` probe (inside a rolled-back transaction) of the page lookup
returned ``None`` for ``https://design.wersdoerfer.de/`` and
``https://design.wersdoerfer.de/eine-schule-wird-sichtbar/`` before the deploy,
and afterwards exactly the portfolio index page and that project page read
from the portfolio site; the main blog URL resolved to the same blog both
times. ``manage.py help regenerate_broken_renditions`` lists ``--database``.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``31c6b39``). No database step and no static rebuild are needed.

2026-11-20 CSP report shapes and portfolio copy checks
------------------------------------------------------

Deployed ``31c6b39``, which also brings ``5e23ecb`` live: ``/csp-report/``
answers 415 for other media types and 400 for a JSON root that does not match
the media type, and logs directive names, violation keywords and non-HTTP(S)
schemes only from fixed allowlists (:doc:`csp`). Webmentions are scheduled and
reloaded on the publishing database (:doc:`indieweb`). Optional portfolio copy
counts as empty when its displayed text is only whitespace or a starter
placeholder, project detail pages load teaser images only for the two
recommended projects, and the legal settings editor accepts ``<BR>`` in any
letter case (:doc:`portfolio_wagtail`). No migration, no new static files and
no settings or environment change.

Verified after the deploy: sha256 of the 258 tracked ``homepage/`` and
``config/`` sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals
``31c6b39``; both units got new PIDs and stayed on them for 120 seconds; the
front page, the blog RSS feed and the portfolio host answered 200. A report
sent as ``application/json`` got 415, and a synthetic report with an unknown
directive and scheme was logged as ``directive=other blocked=other``. The
landing page, the legal pages and all nine project pages of the portfolio host
rendered byte-identical to before the deploy (after removing nonces).

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``91850a6``). No database step and no static rebuild are needed.

2026-11-19 CSP report log scope
-------------------------------

Deployed ``17c83d1``: the ``/csp-report/`` endpoint keeps a first path segment
only for reviewed route prefixes on the request's own origin and logs every
other location as its origin (:doc:`csp`), and it stops reading a Reporting API
batch after five accepted reports. No migration, no new static files and no
settings or environment change.

Verified after the deploy: sha256 of the tracked ``homepage/`` and ``config/``
sources plus ``pyproject.toml`` and ``uv.lock`` on the host equals ``17c83d1``;
both units stayed on the same PID for 120 seconds; the front page, the blog RSS
feed and the portfolio host answered 200. A synthetic report with an unlisted
same-origin document and a ``/static/`` source was logged as
``document=https://wersdoerfer.de source=wersdoerfer.de/static/:<line>``, which
also shows that Django sees these requests as HTTPS behind Traefik.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``f201a37``). No database step and no static rebuild are needed.

2026-11-18 owner security decisions
-----------------------------------

From the 2026-11-17 audit, as recommended: ``INDIEWEB_BIND_ME_TO_USER`` is on
(:doc:`indieweb`), Wagtail's admin password reset is off
(:doc:`admin_login_throttle`), the development server binds ``127.0.0.1``
(:doc:`development`), and a report-only Content-Security-Policy with the
``/csp-report/`` endpoint is added (:doc:`csp`). No migration, no new static
files and no new required environment variable (``INDIEWEB_BIND_ME_TO_USER``
and ``CSP_REPORT_LOG_LIMIT_PER_MINUTE`` are optional overrides).

Before the deploy, a read-only check on production and staging found the
``jochen`` account's django-indieweb profile URL exactly
``https://wersdoerfer.de/jochen/``; the other accounts have no profile, and the
only IndieAuth token on each host belongs to ``jochen``. Existing tokens are not
affected by the binding.

Rollback: ``just deploy-one homepage production`` from a clean checkout of the
previous commit (``251d723``). No database step and no static rebuild are needed.

2026-11-17 allauth rate limits per client
-----------------------------------------

``config.settings.base`` sets ``ALLAUTH_TRUSTED_PROXY_COUNT`` from
``DJANGO_NUM_PROXIES`` (default ``1``). allauth's per-IP rate limits for
``/accounts/login/``, failed logins, password resets and sign-ups now count the
client address that Traefik appends to ``X-Forwarded-For``, not Traefik's own
address, which all visitors used to share. No migration, no new environment
variable; see :doc:`admin_login_throttle`. Local requests without
``X-Forwarded-For`` keep using ``REMOTE_ADDR``.

2026-11-18 Wagtail 8.1 and django-cast e0c632ad
------------------------------------------------

``uv.lock`` moves Wagtail from 8.0.1 to 8.1 (``pyproject.toml`` now allows
``>=8.1,<8.2``), django-cast ``develop`` from ``93ac6cb4`` to ``e0c632ad``
(release 0.2.68 plus the 0.2.69 version bump) and draftjs-exporter from 7.1.0
to 7.3.1, which Wagtail 8.1 requires. No other locked package changed. Neither
package adds migrations in this range: the 196 numbered migration files of the Wagtail
apps this site installs are byte-identical between the 8.0.1 and 8.1 wheels
(only Wagtail's own bundled test app, which the site does not install,
squashed its migrations), and django-cast stays
at ``cast.0094``. Deploying
the previous lock again therefore needs no database step.

Wagtail 8.1 upgrade considerations, checked for this site:

* Python 3.10 support is dropped; the site runs on Python 3.15.2.
* The internal admin API ``/cms/api/main/`` and the ``construct_admin_api``
  hook are replaced by ``/cms/api/explorer/<id>/``. This site does not use
  either; its only ``wagtail_hooks.py`` (portfolio) does not touch them.
* Pages with an ``ajax_template`` now send ``Vary: X-Requested-With``. No page
  model of this site or django-cast defines one.
* Sitemaps include all locales when ``WAGTAIL_I18N_ENABLED`` is on. It is off
  here, and the site serves no Wagtail sitemap.
* Redirects are only auto-created when live pages move or are renamed, not
  drafts (``WAGTAILREDIRECTS_AUTO_CREATE = "always"`` restores the old
  behaviour). The default is kept.
* On Django 6.1 Wagtail now sends admin mail through ``mailers.default``.
  Without ``MAILERS``, Django builds that mailer from the existing
  ``EMAIL_BACKEND`` settings, so production keeps the Mailgun backend. Moving
  to ``MAILERS`` (deprecation of the ``EMAIL_*`` settings in Django 2028) is
  separate work.

django-cast 0.2.68 upgrade actions, checked for this site: no
``cast/audio``, ``cast/video`` or ``cast/transcript`` ``confirm_delete.html``
overrides exist, so the new delete confirmation field needs no template
change. New transcript uploads need ``.json`` or ``.vtt`` extensions; existing
files are unchanged.

Local gates on Python 3.15.2 with PostgreSQL 17: the full suite ran 1178
passed and 1 failed; the failure was a timing assertion in
``homepage/tests/test_dev_runner.py`` ("Synthetic trees did not start", one
parameter case), and the whole file (50 tests, all three parameter cases of
that test included) passed in each of three consecutive runs on its own. The migration (8) and
browser (49) regressions, ``makemigrations --check``, prek and the dependency
audit passed. A database migrated and seeded with synthetic blog, podcast,
image and gallery content under the old lock migrated with "No migrations to
apply" under the new one, with an identical ``showmigrations`` and the same
responses for pages, feeds and the admin. In a browser, the admin page explorer
loaded its pages from the new ``/cms/api/explorer/<id>/`` endpoint without
JavaScript errors or missing static files.

Rollback: redeploy the previous commit with a clean static rebuild; no
database step is needed. Hold the shared deploy lock on the host for the whole
sequence (``python -m pyinfra_support.deploy_lock acquire production`` in
ops-control, export ``OPS_CONTROL_DEPLOY_LOCK=production=<token>`` so the
nested ``just deploy-one`` accepts it, release afterwards):

1. As root stop ``homepage.service`` and ``homepage-db-worker.service``.
2. As the ``homepage`` user empty ``/home/homepage/site/staticfiles`` (what
   ``collectstatic --clear`` does; it only holds collected files).
3. In ops-control run ``just deploy-one homepage production`` with
   ``PROJECTS_ROOT`` set to a directory whose ``homepage`` subdirectory is a
   clean checkout of the previous commit. Its ``collectstatic`` fills the
   empty directory from the old packages, and the deploy starts both units
   again. Check each unit with its own ``systemctl is-active``.

The deploy's plain ``collectstatic`` skips a source file that is not newer
than the collected copy. The site's virtualenv hardlinks files from the uv
cache, so the older packages carry the cache's older timestamps. Without the
clean rebuild a rollback would keep the Wagtail 8.1 and django-cast static
files, including ``cast/vite/manifest.json``, next to a ``staticfiles.json``
for the old lock. The units stay stopped until the deploy starts them, because
WhiteNoise indexes the static files at startup and fails on a file removed
under it.

The first forward deploy is not affected: Wagtail 8.1 and django-cast
``e0c632ad`` were never installed for this user, so they are unpacked into
the cache freshly and are newer than the collected files. A forward deploy
after a rollback is affected the same way (the cached 8.1 files are older
than the rebuilt 8.0.1 copies), so it needs the same sequence.

2026-11-17 django-cast develop 93ac6cb4
---------------------------------------

``uv.lock`` moves django-cast ``develop`` from ``c290ec1a`` to ``93ac6cb4``.
No other locked package changed; django-cast no longer depends on
``python-dateutil`` directly, but the package stays locked through other
dependencies. django-cast adds no migrations in this range (the schema stays at
``cast.0094``), so deploying the previous lock again needs no database step.

Upgrade actions from the django-cast release notes, checked for this site:

* Theme discovery only looks at ``<template-root>/cast/<theme>/``. The local
  themes live in ``homepage/templates/cast/<theme>/``, and cast-bootstrap5 and
  cast-vue ship theirs as ``templates/cast/<theme>/`` in their apps, so nothing
  moves. The offered theme list (bootstrap4, plain, vue, bootstrap5) is
  unchanged.
* Configured ``cast_private_media``, ``cast_public_transcripts`` and
  ``cast_voice_references`` storages now fail loudly instead of falling back.
  This site configures none of them, so the fallbacks still apply.
* Comment posting only accepts Wagtail page targets unless
  ``CAST_COMMENTS_ALLOWED_TARGET_MODELS`` opts in others. Comments here are on
  blog posts, so the setting stays unset.
* The modal facet counts view opts out of ``ATOMIC_REQUESTS`` and reads all
  groups in one snapshot. With PostgreSQL and Wagtail's default database
  search backend it keeps answering, also with a search term; other backends
  would get HTTP 503.
* Galleries are limited to 500 images. The largest gallery here has 38.
* ``cast.runner`` is removed. This site's test settings use Django's
  ``DiscoverRunner``.

Navigation without view-restricted pages, the non-zero exit codes of
``media_replace`` and ``recalc_video_posters`` and the Voxhelm credential pair
were already part of ``c290ec1a``; the release notes only list them under
upgrade actions now.

Local gates: the PostgreSQL test suite on Python 3.15.2 and 3.14.8, the
migration and browser regressions, ``makemigrations --check``, prek and the
dependency audit all passed.

2026-10-29 Python 3.15.2
------------------------

ops-control now deploys this site on Python 3.15.2 (previously 3.15.1) with uv
0.13.6, the first uv release that can install 3.15.2. The lock and application
code are unchanged, and CI tests 3.15.2 instead of 3.15.1. The interpreter is
installed by ops-control's runtime step before the normal deploy. The deploy
restarts the web and worker processes only when it syncs changed files or
dependencies; the new interpreter alone does not trigger a restart, so check
afterwards that both processes run 3.15.2 and restart them if not. Django and
Wagtail upstream support for Python 3.15 is unchanged from the 2026-10-24 note.

2026-10-24 image and JSON parser security patches
-------------------------------------------------

The follow-up lock upgrades Pillow 12.3.0 to 13.0.0 and Django REST framework
3.18.1 to 3.18.3. See :doc:`development` for the advisory links and compatibility
scope. Use the committed lock and the normal static rebuild and service restart
workflow. This application change does not provision Python or establish that
any live service has been updated; host qualification remains separate.

2026-10-24 Django and Wagtail security patches
------------------------------------------------

Django 6.1.2 and Wagtail 8.0.1 replace 6.1.1 and 8.0 in the committed lock.
No application model, settings or deployment-recipe behavior changes; all
package migration files were compared unchanged. Inspect the installed
migration plan before deployment as usual; this is an operator step, not an
automated guard added to the app. See :doc:`development` for the one-off checks
and the Python 3.15.1 upstream-support caveat.

Rebuild static files and restart the web and worker processes through the
normal ops-control workflow: Wagtail's packaged admin assets can change between
patch releases. The isolated compressed-static check passed all seven required
application manifests with no Brotli output. Shared media and existing database
data were not used by that check.

The controller's Python 3.15.1 provisioning and live rollout are separately
reviewed. An application merge alone does not mean a server was updated.
Deploying the previous lock reinstalls the older framework versions and their
security issues; do not silently undo these patches during recovery.

2026-10-21 main site fonts without layout shifts
------------------------------------------------

* The main site (blog, start page, profile pages) loads its own Saira subsets from
  ``static/fonts/`` instead of the portfolio's full variable fonts: about 39 KB upright
  and 44 KB italic per page instead of 172 KB and 202 KB. See *Main Site Fonts* in
  :doc:`development`.
* ``font-display: optional``: text no longer jumps when Saira arrives after the first
  paint (PageSpeed CLS was about 0.3 on the blog list and on post pages). On a slow first
  visit, that page view may show the system font; later pages use the cached Saira.
* No migration and no settings change; ``collectstatic`` picks up the new font files.
  Rollback: deploy the previous commit.
* Follow-up: the contour lines in the blog list's hero compute the noise field once
  per grid point instead of once per contour level. The drawing is pixel-identical,
  but takes about 6 ms instead of 50 ms on a desktop-wide hero, which removes the
  blocking time PageSpeed reported for the blog list (230 ms on its desktop run).
* Follow-up: on the blog list, post images from the second post on carry
  ``loading="lazy"`` (override of django-cast's ``cast/image/image.html``, switched on in
  ``post_body.html``). They no longer load before the first paint on phones, where they
  sat far below the screen but still counted toward PageSpeed's simulated LCP. Detail
  pages and the first post on the list load their images as before.
* Follow-up: inline code in the light theme uses ``--cast-link-on-white`` (#004c99)
  instead of the theme's ``--cast-accent`` (#0066cc). On the ``--cast-bg-alt`` code
  background the old blue reached only 4.2:1, which PageSpeed flagged as too little
  contrast; the new one reaches 6.4:1. Dark theme, code blocks and code inside links are
  unchanged.

2026-10-15 portfolio layout and typography
------------------------------------------

* Hero: the middle grid row grows with ``Moin`` on wide screens; the lead follows below,
  the hero may become taller than the screen.
* Project tiles: four columns, a two-column 1-2 pattern, or the hero projects stacked
  with the other projects in a reel — chosen by container queries on the projects area.
* Project pages: hyphenated, smaller project titles on phones, calmer wrapping of lead
  and case texts (no ``text-wrap: pretty``, limited hyphenation), optical left
  alignment of headline lines, no visible frame around the mobile back-to-top link.
* Empty texts and unchanged ``[…]`` starter placeholders in statement, challenge,
  solution, stats and testimonial are no longer rendered. This removes the placeholder
  testimonials currently visible on the live project pages.
* Migrations ``portfolio.0004_hero_tile_help_text`` and
  ``portfolio.0005_optional_case_texts`` only change help texts and block definitions;
  they run no SQL.

2026-10-15 portfolio content out of the code
--------------------------------------------

The portfolio's editorial content now lives only in the database.

* Personal data and editorial copy are removed from the portfolio's field defaults
  (``PortfolioSiteSettings``, ``PortfolioIndexPage``, ``ErrorPageSettings``) and from the
  template fallbacks; the defaults are neutral placeholders such as ``[Name]`` or empty
  values. Migration ``portfolio.0003_neutral_defaults`` only records the new defaults; it
  runs no SQL.
* ``seed_portfolio`` no longer fills services, about items and clients; it creates the
  categories and, with ``--create``, an empty portfolio page.
* Before deploying, every portfolio site must have saved ``Portfolio-Site``,
  ``Portfolio-Rechtsseiten`` and ``501-Seite`` settings. A site without saved settings
  shows the placeholders after the deploy. Saved pages and settings are unchanged.

2026-10-15 portfolio legal settings form
----------------------------------------

The Wagtail form for the portfolio's legal pages (Einstellungen → Portfolio-Rechtsseiten)
answered with a server error: its address block held ``<br>``, but Wagtail's rich-text
editor only reads the self-closing ``<br/>``. Opening a settings form creates the settings
row from the defaults, so a site whose editor tried the form already stores ``<br>``.

* The default address placeholders use ``<br/>``.
* Paragraph and address blocks of the legal copy hand stored ``<br>`` to the editor as
  ``<br/>``, so existing rows open without a data change. Saving the form stores ``<br/>``.
* Migration ``portfolio.0002_legal_copy_line_breaks`` only records the new block class;
  it runs no SQL.
* The default Datenschutz section "Cookies & Tracking" no longer claims that nothing is
  stored on the visitor's device; it now says that no third-party cookies or tracking
  services are used and only technically required data is stored (§ 25 Abs. 2 TDDDG).
  Sites that already saved their legal settings keep their own text.

2026-10-15 Python 3.15
----------------------

Production moves from Python 3.14.8 to 3.15.0. The interpreter is set in
ops-control (``wagtail_python_version`` in ``playbooks/deploy-homepage.yml``);
the ops-library ``wagtail_deploy`` role installs it with uv, rebuilds the
virtualenv when the version differs and runs ``uv sync --frozen``. Expect a
short outage while the virtualenv is rebuilt.

* ``pyproject.toml`` drops the ``brotli`` extra of ``whitenoise``. ``brotli``
  has no Python 3.15 wheel, so it would be compiled on the host. WhiteNoise
  keeps writing ``.gz`` files and serves gzip; no setting needs brotli. The
  ops-control playbook deletes the ``.br`` files left in ``staticfiles/``
  before ``collectstatic``, because WhiteNoise serves an existing ``.br``
  file without checking that it still matches the original.
* ``uv.lock`` moves pydantic to 2.14.1, pydantic-core to 2.50.1 and
  markupsafe to 3.0.4, which ship Python 3.15 wheels, and django-indieweb
  ``develop`` from ``dc6365af`` to ``c1918dc6``. No migration.
* django-indieweb answers ``413`` on the IndieAuth authorization and token
  endpoints (``/indieweb/auth/``, ``/indieweb/token/``) for bodies above
  64 KiB (``INDIEWEB_INDIEAUTH_MAX_BODY_BYTES``), for a malformed
  ``Content-Length`` and for any ``Transfer-Encoding``. Normal IndieAuth
  form posts are far below the limit. No middleware of this site reads the
  request body before those views.
* PyYAML (a development dependency through Jupyter) has no 3.15 wheel yet and
  is built from source during ``uv sync`` on the host; the host has a C
  compiler.
* CI tests on Python 3.14 and 3.15 with uv 0.13.1 (3.15.0 needs uv 0.13.0 or
  later); lint runs on 3.15.
* Django 6.1 and Wagtail 8.0 do not list Python 3.15 as supported yet. The
  699 tests pass on 3.14.8 and 3.15.0 against PostgreSQL 17.

Rollback: set ``wagtail_python_version`` back to ``"3.14.8"`` in ops-control
and deploy again; the role rebuilds the virtualenv on 3.14. The lock works on
both versions.

2026-10-14 library refresh
--------------------------

``uv.lock`` moves django-cast ``develop`` from ``5ac84fbd`` to ``704a60aa``,
django-indieweb ``develop`` from ``9726be2d`` to ``dc6365af``, cast-bootstrap5
``main`` from ``88134d96`` to ``9fba4b2d`` and django-resume ``main`` from
``195865ad`` to ``7e2fb3e8``. No other locked package changed. None of the
updates has a migration or needs a settings change.

* django-cast writes internal page links in feed item descriptions as absolute
  URLs, keeps polling a Voxhelm job through lost connections, and names a guest
  without a voice reference from the leftover diarization label.
  ``media_stale`` now skips files younger than 7 days
  (``CAST_MEDIA_STALE_MIN_AGE_DAYS``) or of unknown age and re-checks age and
  references before each deletion. Nothing here runs it on a schedule.
* django-indieweb falls back to ``GET`` when outbound Webmention discovery gets
  an error answer to ``HEAD``. Behaviour changes: a ``multipart/form-data``
  Micropub POST needs the ``create`` (or ``post``) scope and gets ``403``
  otherwise; rejected WebSub callback ``GET`` requests answer ``404``; an
  unknown ``INDIEWEB_LOG_REDACTION`` value fails closed to ``redact`` and
  passthrough logs keep 4 instead of 8 token characters. None of this affects
  this site: the Micropub handler supports only creates (``update``,
  ``delete`` and ``undelete`` are already rejected), the local Micropub form
  calls the handler directly, no WebSub subscription is configured and
  ``INDIEWEB_LOG_REDACTION`` is not set.
* cast-bootstrap5 ships a compiled German catalog and sets ``<html lang>`` from
  the active language. This site's ``cast/bootstrap5/base.html`` extends the
  theme's template, so its pages now declare the active language (``en-us``
  with the default ``LANGUAGE_CODE``) instead of ``en``.
* django-resume keeps the stored avatar on admin saves of simple plugins and
  treats an empty timeline or project item position as ``0``.

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
