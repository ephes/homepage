Admin login throttling
======================

The site has four password login forms:

* allauth's ``/accounts/login/``, limited by allauth's default
  ``ACCOUNT_RATE_LIMITS``.
* the Django admin login, ``<ADMIN_URL>login/``.
* the Wagtail admin login, ``<WAGTAILADMIN_BASE_URL>login/`` (``/cms/login/``).
* the Django REST Framework browsable-API login, ``/api-auth/login/``.

Before October 2026 the last three were plain Django ``LoginView``\ s with no
rate limit, so they accepted any number of password guesses.
``config/urls.py`` now routes all three through
``homepage.users.login_throttle.throttle_failed_logins``, which limits
**failed** login attempts. Portfolio hosts (``DJANGO_PORTFOLIO_HOSTS``) serve
the Wagtail admin login as well; ``config/urls_portfolio.py`` routes it
through the same wrapper, with the same counters. Every URL configuration
that mounts a password login must do so:

``admin_login_client``
    Failed attempts per client address. The default is ``20/hour``. Override
    it with ``DJANGO_ADMIN_LOGIN_CLIENT_RATE``. The client address is the last
    ``X-Forwarded-For`` entry, which Traefik appends; earlier entries are
    ignored. ``REST_FRAMEWORK["NUM_PROXIES"]`` (``DJANGO_NUM_PROXIES``,
    default ``1``) controls this.

``admin_login_username``
    Failed attempts per submitted username, from any address. The default is
    ``10/hour``. Override it with ``DJANGO_ADMIN_LOGIN_USERNAME_RATE``.
    Usernames are compared case-insensitively after the same NFKC
    normalization the login form applies, with surrounding whitespace ignored. This limit still holds when a client rotates addresses or sends a
    forged ``X-Forwarded-For`` header.

All three logins share the same counters. A POST counts as failed unless it
logs a user in, so a wrong password and an invalid form count. The Django
admin form refuses valid credentials of an account without staff status, so
those count as failed there. The Wagtail and browsable-API logins log such a
user in, so there they count as a successful login. Wagtail then admits only
users with the ``wagtailadmin.access_admin`` permission, independently of
staff status.
Successful logins do not count. GET requests are never throttled.

The client limit is checked first, and a refused request is not counted
against anything. Once either limit is reached, every POST is refused with
``429 Too Many Requests`` and a ``Retry-After`` header, even with the correct
password, until the oldest counted failure is older than the window.

The rates live in ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]``. The counters
use the ``api_token_auth_throttle`` cache when it is configured
(production: a shared file-based cache under ``DJANGO_CACHE_LOCATION``), and
the ``default`` cache otherwise. The legacy cache alias and directory are
retained so existing admin lockouts survive removal of the token endpoint.

Locked out?
-----------

Anyone who knows a username can use up its ``admin_login_username`` budget
and lock these three logins for that user for up to an hour. To get in anyway:

* log in at ``/accounts/login/`` instead. That session also opens the Django
  admin and the Wagtail admin, or
* clear the counters, for example with
  ``python manage.py shell -c "from django.core.cache import caches; caches['api_token_auth_throttle'].clear()"``
  on the server.

Token authentication
--------------------

``/api/api-token-auth/`` was removed on 2026-10-19 and returns 404. The
``improve_spamfilter`` and ``comments_api_endpoint_debug`` notebooks that
needed token issuance are no longer used. The endpoint-specific rate
settings ``DJANGO_API_TOKEN_AUTH_CLIENT_RATE`` and
``DJANGO_API_TOKEN_AUTH_USERNAME_RATE`` no longer apply.

Existing DRF tokens and ``TokenAuthentication`` remain available: django-cast
API views, including the comments API, inherit the site's
``REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]``. The cast-vue comments
UI uses session authentication and CSRF tokens and needs no token issuance
endpoint.

Change history
--------------

* 2026-10: the Django admin, Wagtail admin and browsable-API logins throttle
  failed attempts per client address and per username.
* 2026-10: the Wagtail admin login on portfolio hosts
  (``config/urls_portfolio.py``) is throttled too; it was served without the
  wrapper there.
* 2026-10-19: removed the unused token issuance endpoint; existing tokens
  and admin login throttling remain supported.
