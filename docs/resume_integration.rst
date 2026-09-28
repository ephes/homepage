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

The committed CV and cover-letter PDFs remain separately generated static
artifacts. The dependency upgrade neither regenerates them nor changes their
existing public availability. See ``docs/dev/backlog.txt`` and
``manage.py render_resume_pdfs`` for that workflow.

Validation
----------

Run ``uv run pytest homepage/resume_cover/tests homepage/handwriting/tests homepage/tests/test_resume_dependency.py``
with isolated test database and local media storage. Browser handwriting tests
require the Chromium build matching the locked Playwright version. The upgrade
tests also check the registered routes, homepage override, the dependency's
editorial template/asset availability and the source-switch TOML round trip
from a local checkout back to the reviewed immutable Git revision.

The next integration packages combine this upgraded branch with the portfolio
branch and then bring the combined branch up to date with ``origin/main``.
They require their own tests and independent reviews before merge readiness is
claimed.
