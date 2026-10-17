Fediverse discovery
===================

The ``homepage.fedi`` app lets the site's domain act as the fediverse identity
domain while the actual server runs at ``https://fedi.wersdoerfer.de``.

``/@jochen`` and ``/@katharina``
   Redirect to the profile on the fedi host.

``/.well-known/webfinger``, ``/.well-known/host-meta``, ``/.well-known/nodeinfo``
   Fetched from the same path on the fedi host and returned to the client
   (``homepage.fedi.views._proxy_wellknown``). The proxy is deliberately
   narrow:

   * Only ``GET`` and ``HEAD`` are allowed; other methods get ``405``.
     Upstream is always fetched with ``GET``.
   * The only client header sent upstream is ``Accept``. Cookies (session,
     CSRF), ``Authorization`` and every other request header stay on this
     site.
   * The query string is forwarded once (webfinger and host-meta only;
     nodeinfo takes no query).
   * Only the upstream status, ``Content-Type``, ``Cache-Control``,
     ``Access-Control-Allow-Origin`` and ``Content-Encoding`` are returned.
     Upstream ``Set-Cookie`` and all other headers are dropped.
   * The body is not decoded: ``Accept-Encoding: identity`` is requested and
     any ``Content-Encoding`` the upstream still uses is passed on as is.
   * Upstream redirects are not followed; a ``3xx`` is returned to the client
     with its ``Location`` made absolute against the fedi host.
   * Timeouts: 3 s per TCP connect attempt, 10 s per socket read and a hard
     10 s overall deadline that also bounds DNS resolution (done in a helper
     thread), every connect attempt and the TLS handshake; when it passes, the
     upstream socket is shut down. Mastodon gives up on a lookup after about
     10 s without response headers, so a longer deadline would only hold a
     gunicorn worker. A timeout returns ``504``; any other
     connection or protocol error, a truncated body, a body larger than
     1 MiB, or an invalid upstream status, header or redirect location returns
     ``502``.
   * These ``502``/``504`` responses are expected when the fedi host is slow,
     for example while many servers resolve the account at once after a reply
     to a large account. Each is logged as a warning
     (``Timeout fetching ...`` / ``Failed to fetch ...``) but does not mail
     the admins: ``homepage.fedi.log_filters.SkipFediUpstreamFailures``,
     installed on the ``django.request`` logger in ``FediConfig.ready``, drops
     the request log record for them. Any ``500`` (an exception in the view or
     in a middleware) is still reported as usual.
   * The request is made with the standard library (``http.client``) and
     verified against the ``certifi`` CA bundle.

After deploying changes to this app, check that WebFinger still resolves, for
example ``curl 'https://wersdoerfer.de/.well-known/webfinger?resource=acct:jochen@wersdoerfer.de'``.
