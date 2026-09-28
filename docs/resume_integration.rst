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

Main reconciliation — 2026-09-28
--------------------------------

The combined branch incorporates ``origin/main`` at ``1f8e4a1``, including its
Django 6.1 and Wagtail 8.0 requirements, weeknote blocks and conversion command,
Micropub fixes, Sentry environment selection and documentation workflow. The
reviewed django-resume revision, portfolio static finder, Brotli compression,
editorial overrides and closed-registration policy remain in place. The lock
is regenerated from main's dependency baseline plus these explicit additions.

This is integration preparation, not a deployment or a merge into ``main``.
Validate the full homepage test suite, actual migrations, compressed manifest
assets, both portfolio browser profiles and real Wagtail admin light/dark/system
themes before accepting the branch. The old webmention list-count test is fixed
by main and must no longer be treated as an expected failure.

Verification on Python 3.14.4, Django 6.1.1 and Wagtail 8.0: the full homepage
suite passes (365 tests and four subtests); two container-only static tests are
skipped because no Docker daemon is available. The disposable database upgrades
successfully from the previous dependency baseline, portfolio migration checks
report no changes, and production collectstatic resolves hashed assets with
gzip/Brotli sidecars. Sphinx builds with warnings treated as errors.
The real-page smoke covers seven routes at 1440, 800 and 375 pixels, and four
admin appearance combinations: light, dark, system with a light OS preference,
and system with a dark OS preference. It also checks one-page CV/cover PDF
generation. Its only overflow findings are
the two existing heading cases below; it is not an unconditional reflow pass.

The disposable browser fixture uses synthetic content and images. It is not
visual acceptance of real editorial content. Two narrow-screen heading overflows
(``Buchgestaltung`` without a manual soft hyphen and ``Datenschutz``) reproduce
identically in the canonical prototype and Wagtail at 375 pixels: the document
does not scroll horizontally, but heading text overflows its box.
They are existing typography follow-ups, not changes
introduced by this integration; no unapproved global font-size or wrapping
redesign is included here.
