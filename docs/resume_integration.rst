Editorial resume integration
============================

Release note — 2026-09-28
-------------------------

The editorial CV and cover letter now use the django-resume 0.3.0 page-registry
API together with the existing editorial theme. The dependency is an immutable
Git revision of the reviewed ``integration/editorial-030`` branch, with package
revision ``806a1b0570870bf0983a9cbf5b87f072c22c4d52`` and
version ``0.3.0+editorial``. It includes the exact upstream 0.3.0 release and the
editorial templates, assets and additional fields; the plain PyPI 0.3.0 package
does not contain those editorial additions.

``pyproject.toml`` and ``commands.py switch-to-git-sources`` must select the same
revision. ``uv.lock`` records the resulting build. Normal installation uses
``uv sync --locked`` and does not require a neighbouring checkout. Developers
may explicitly select a local django-resume checkout with the existing source
switch command. That checkout must contain the editorial integration and report
exactly ``0.3.0+editorial``; plain upstream ``0.3.0`` or a different development
version is not a supported integration environment. The upgrade test checks the
installed distribution version explicitly, because a uv source override must not
be assumed to enforce the dependency version specifier. Restore the pinned Git
sources before committing.

Retain the remote ``django-resume`` branch ``integration/editorial-030`` while
any consumer pins this revision: do not delete or rewrite its history during
homepage branch cleanup. The consumer continues to pin the commit, not a moving
branch tip. A separately coordinated release tag may replace this retention
arrangement later; this integration does not publish a package release or tag.

Existing URLs remain ``/resume/<slug>/`` for the cover letter and
``/resume/<slug>/cv/`` for the CV. The cover plugin override in
``homepage.resume_cover`` still supplies closing and signature fields and must
load after ``django_resume``. CV token checks and owner-only inline editing
remain active. The new page registry enables additional pages contributed by
installed apps through ``resume_pages.py``; this dependency upgrade does not
register a new portfolio route or relocate existing Wagtail pages.

As before, the CV token gate applies to anonymous visitors. Authenticated
homepage accounts are trusted readers and can read another owner's CV without a
token, but cannot edit it. Public and social self-registration remain disabled
through the homepage account adapters. Wagtail editor accounts belong to this
same trusted user base; do not open registration without revisiting this policy.

The committed CV and cover-letter PDFs remain separately generated static
artifacts. The dependency upgrade neither regenerates them nor changes their
existing public availability. See ``docs/dev/backlog.txt`` and
``manage.py render_resume_pdfs`` for that workflow.

The merge fixes resource ownership: only the ``katharina`` resume receives the
existing Katharina PDF links by default. Other slugs do not inherit these
documents. ``RESUME_PUBLIC_RESOURCES`` can explicitly map each slug to
``cv_pdf`` and ``cover_pdf`` static paths and an optional ``portfolio_url``.
Without a configured portfolio URL the former placeholder link is omitted.
The optional resource rail has an explicit component class, so omitting it does
not apply its label-position adjustment to the education rail.
This mapping publishes links to public static artifacts; it does not make PDFs
token-protected. Do not add confidential recipient-specific letters there.

PDF generation now requires ``RESUME_PDF_TOKEN`` in the environment with no
repository default or command-line token. ``render_resume_pdfs --slug katharina``
uses the same per-slug resource mapping; ``--out`` denotes a static-root directory,
with the mapping's relative paths below it. ``just render-pdfs`` shares the same
environment variable and probes server readiness without sending a token.
Failures omit token-bearing URLs. Generated artifacts still require a deliberate
content check before they are committed or published.

The old PDF implementation plan is archived and its historical preview-token
literal has been removed from the current tree. Git history may still contain
it: operators must revoke that previously used token in every database where it
is valid before exposing the database or deploying this workflow. No production
database or existing credentials were accessed or rotated by this integration.

The homepage intentionally shadows three dependency assets with its existing
editorial customizations: ``django_resume/css/editorial/screen.css``,
``django_resume/css/editorial/print.css`` and
``django_resume/js/editorial-lines.js`` under ``homepage/static``. These win
through ``FileSystemFinder``; a dependency upgrade does not automatically replace
them. The dependency-availability test separately uses ``AppDirectoriesFinder``
and verifies paths inside the installed django-resume package, so homepage
overrides cannot mask missing dependency assets. Compare upstream changes to
these overrides explicitly when upgrading.

Validation
----------

Run ``uv run pytest homepage/resume_cover/tests homepage/handwriting/tests homepage/tests/test_resume_dependency.py``
with isolated test database and local media storage. Browser handwriting tests
require the Chromium build matching the locked Playwright version. The upgrade
tests also check the registered routes, homepage override, the dependency's
editorial template/asset availability and the source-switch TOML round trip
from a local checkout back to the reviewed immutable Git revision.

Portfolio combination — 2026-09-28
----------------------------------

``integration/portfolio-resume`` combines the upgraded editorial branch with the
portfolio implementation, including the optional editable Hero, portrait and
imprint images. Both apps remain installed alongside django-cast. The Wagtail
page tree stays under ``/blogs/``; the existing homepage and resume routes are
not replaced. This merge does not introduce a django-resume portfolio adapter.

Run ``uv run pytest homepage/tests/test_resume_integration.py`` in addition to
the app suites. These integration contracts exercise the editorial cover
override, anonymous/token/owner access, persisted edits, dependency and homepage
static assets, and Cast/portfolio coexistence in one Wagtail site tree.

The following package brings this combined branch up to date with
``origin/main``. It requires its own dependency, migration, browser and
independent review checks before main-merge readiness is claimed.
