Content Security Policy (report-only)
=====================================

Every HTML response carries a ``Content-Security-Policy-Report-Only`` header
built by Django's ``ContentSecurityPolicyMiddleware`` from
``SECURE_CSP_REPORT_ONLY`` in ``config/settings/base.py``. It applies to the
main site and to the portfolio host. For this site-wide policy browsers **block
nothing**; they report what it would block. The site sets no enforcing policy of
its own (``SECURE_CSP`` stays empty). Views that already send their own
enforcing ``Content-Security-Policy`` header keep it, for example
django-indieweb's IndieAuth consent and token management pages and
django-resume's JSON Resume theme pages. The middleware does not
overwrite a header a view has set. Static files served by WhiteNoise get no CSP
header.

The first policy:

* ``default-src 'self'``, ``object-src 'none'``, ``base-uri 'self'``,
  ``form-action 'self'``;
* ``frame-ancestors 'self'`` (the Wagtail page preview frames the site from its
  own origin; ``X-Frame-Options: DENY`` still applies elsewhere);
* scripts from the site, ``https://plausible.io`` and ``https://cdn.jsdelivr.net``
  (no inline scripts, so inline ``<script>`` blocks are reported);
* styles from the site and jsDelivr, inline styles allowed;
* images from the site, ``data:`` and any ``https:`` source (webmention avatars);
* media from the site, the CloudFront domain and ``https://s3.amazonaws.com``;
* fonts from the site, ``data:`` and jsDelivr; connections to the site and Plausible.

Reports
-------

``report-uri`` points to ``/csp-report/`` (``homepage.core.csp.csp_report``), on
both the main and the portfolio host. The endpoint accepts POSTs only, is
CSRF-exempt, refuses bodies over 16 KiB with ``413`` and invalid JSON with
``400``, and handles at most five reports per request. It understands the
classic ``application/csp-report`` body and the Reporting API list format.

Each report becomes one WARNING line on the ``homepage.csp`` logger (the
gunicorn journal in production)::

    CSP report-only violation directive=script-src-elem blocked=https://cdn.example document=wersdoerfer.de/blogs/ source=wersdoerfer.de/static/:12

The line holds the directive, the blocked origin (or a keyword such as
``inline``, ``eval`` or ``data``), and where the violation happened. URLs can
carry secrets (IndieAuth codes in query strings, allauth confirmation and reset
keys in paths, possibly percent-encoded), so a document or script location is
only the host plus the first path segment, and only when that segment is a plain
word of ``a-z``, digits, ``_`` and ``-`` (otherwise ``?``):
``wersdoerfer.de/accounts/`` for any allauth page, ``wersdoerfer.de/blogs/`` for
any blog page, ``wersdoerfer.de/static/`` for any static script. User info, query strings and fragments are never logged; the blocked
resource is logged as its origin only. Every logged field is restricted to a
fixed character set and length. Each worker process logs at most ``CSP_REPORT_LOG_LIMIT_PER_MINUTE``
reports per minute (default 30; production runs four gunicorn workers, so at
most 120 violation lines plus four suppression notices a minute); one notice
marks the rest of that worker's minute as suppressed. The budget is counted in memory under a lock, so the endpoint never
writes to the cache.

Reading the reports on production::

    journalctl -u homepage --since today | grep 'CSP report-only'

Next steps
----------

Collect reports for a while, move inline scripts to static files or nonces
(``{{ csp_nonce }}``, which needs ``CSP.NONCE`` in the directive and pages that are
not cached with a fixed nonce), then copy the directives that produce no
legitimate reports into ``SECURE_CSP`` to enforce them.
