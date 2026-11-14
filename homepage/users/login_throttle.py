"""Failed-login throttle for the password login views outside allauth.

allauth rate-limits ``/accounts/login/``, but the Django admin login
(``ADMIN_URL``), the Wagtail admin login (``WAGTAILADMIN_BASE_URL``) and the
browsable-API login (``api-auth/login/``) are plain Django ``LoginView``\\ s
with no limit of their own. Wrapping them with
:func:`throttle_failed_logins` limits failed attempts both per client address
and per submitted username, so the per-username limit still holds when an
attacker rotates addresses or spoofs ``X-Forwarded-For``.

Only failed attempts remain in the history. In-flight authentication temporarily
reserves capacity, and successful logins release it without using up the budget.
Once a limit is reached every attempt is refused with ``429``, including one
with the correct password.
"""

import hashlib
import math
import unicodedata
from contextlib import ExitStack, contextmanager
from functools import wraps
from pathlib import Path
from threading import RLock
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.cache import caches
from django.core.cache.backends.filebased import FileBasedCache
from django.core.cache.backends.locmem import LocMemCache
from django.core.exceptions import ImproperlyConfigured
from django.core.files import locks
from django.dispatch import receiver
from django.http import HttpResponse
from rest_framework.throttling import SimpleRateThrottle

# Keep the existing alias and directory so active admin lockouts survive
# removal of the token issuance endpoint.
THROTTLE_CACHE_ALIAS = "api_token_auth_throttle"

LOGGED_IN_ATTR = "_login_throttle_logged_in"
ADMISSION_SECONDS = 300
# A fixed set bounds lock files and memory even for arbitrary client input.
COUNTER_LOCKS = [RLock() for _ in range(64)]


@contextmanager
def counter_lock(throttle):
    """Serialize short cache transactions on our supported cache backends."""
    stripe = int(hashlib.sha256(throttle.key.encode()).hexdigest(), 16) % len(COUNTER_LOCKS)
    backend = throttle.cache
    if isinstance(backend, FileBasedCache):
        # Stable separate inodes: cache.set replaces its data file and clear/cull
        # removes entries. Neither operation may remove an active lock inode.
        directory = Path(settings.CACHES[throttle.cache_alias]["LOCATION"]) / "login-locks"
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        with (directory / f"{stripe}.lock").open("a+b") as lockfile:
            if not locks.lock(lockfile, locks.LOCK_EX):
                raise RuntimeError("Login counter locking unavailable")
            try:
                yield
            finally:
                locks.unlock(lockfile)
    elif isinstance(backend, LocMemCache):
        with COUNTER_LOCKS[stripe]:
            yield
    else:
        raise ImproperlyConfigured("Login throttling requires FileBasedCache or LocMemCache")


@receiver(user_logged_in, dispatch_uid="homepage.users.login_throttle")
def _mark_logged_in(sender, request, user, **kwargs):
    # The wrapped view logs a user in only through django.contrib.auth.login,
    # which sends this signal with the very request object the wrapper holds.
    if request is not None:
        setattr(request, LOGGED_IN_ATTR, True)


class LoginFailureThrottle(SimpleRateThrottle):
    """Sliding-window counter of failed logins for one key.

    DRF's ``allow_request`` records every request it allows. Here checking
    and recording are separate, so only failures are recorded.
    """

    @property
    def cache_alias(self):
        return THROTTLE_CACHE_ALIAS if THROTTLE_CACHE_ALIAS in settings.CACHES else "default"

    @property
    def cache(self):
        return caches[self.cache_alias]

    def __init__(self, ident):
        super().__init__()
        self.key = self.cache_format % {"scope": self.scope, "ident": ident}

    def _load(self):
        self.now = self.timer()
        self.history = [t for t in self.cache.get(self.key, []) if t > self.now - self.duration]

    def is_blocked(self):
        if self.rate is None:
            return False
        self._load()
        return len(self.history) >= self.num_requests

    def record_failure(self):
        if self.rate is None:
            return
        with counter_lock(self):
            self._record_failure()

    def _record_failure(self):
        self._load()
        self.history.insert(0, self.now)
        # Keep only what is needed to decide, so junk cannot grow an entry.
        while len(self.history) > self.num_requests:
            self.history.pop()
        self.cache.set(self.key, self.history, self.duration)

    def _admissions(self):
        return {key: expiry for key, expiry in self.cache.get(self.key + "_inflight", {}).items() if expiry > self.now}

    def reserve(self):
        """Count pending authentication against the same failure budget."""
        self.reservation = None
        if self.rate is None:
            return True
        with counter_lock(self):
            self._load()
            pending = self._admissions()
            if len(self.history) + len(pending) >= self.num_requests:
                expiries = [t + self.duration for t in self.history] + list(pending.values())
                self.retry_after = max(min(expiries) - self.now, 1)
                return False
            self.reservation = uuid4().hex
            pending[self.reservation] = self.now + ADMISSION_SECONDS
            self.cache.set(self.key + "_inflight", pending, ADMISSION_SECONDS)
            return True

    def finish(self, *, failed=False):
        if self.reservation is None:
            return
        with counter_lock(self):
            self._load()
            pending = self._admissions()
            pending.pop(self.reservation, None)
            # Removing the reservation and recording failure share the lock, so
            # there is no admission gap between the two states.
            if failed:
                self._record_failure()
            if pending:
                self.cache.set(self.key + "_inflight", pending, ADMISSION_SECONDS)
            else:
                self.cache.delete(self.key + "_inflight")
            self.reservation = None

    def wait(self):
        if hasattr(self, "retry_after"):
            return self.retry_after
        # Seconds until the oldest failure that still counts expires.
        oldest = self.history[self.num_requests - 1]
        return max(oldest + self.duration - self.now, 1)


class AdminLoginClientThrottle(LoginFailureThrottle):
    """Failed logins per client address.

    ``get_ident`` honours ``REST_FRAMEWORK["NUM_PROXIES"]``, so only the
    address appended by the trusted reverse proxy counts.
    """

    scope = "admin_login_client"

    def __init__(self, request):
        super().__init__(self.get_ident(request))


class AdminLoginUsernameThrottle(LoginFailureThrottle):
    """Failed logins per submitted username, whatever the client address."""

    scope = "admin_login_username"

    def __init__(self, username):
        # Hash the username so arbitrary input always yields a safe cache key.
        super().__init__(hashlib.sha256(normalize_username(username).encode()).hexdigest())


def normalize_username(username):
    """Map every spelling the login form accepts for one account to one key.

    Django's ``AuthenticationForm`` applies NFKC before authenticating, so
    compatibility spellings such as full-width letters reach the same user.
    Case-folding errs towards sharing counters between usernames.
    """
    folded = unicodedata.normalize("NFKC", username).strip().casefold()
    return unicodedata.normalize("NFKC", folded)


def submitted_username(request):
    username = request.POST.get("username")
    if not isinstance(username, str) or not username.strip():
        # A blank username fails form validation before authentication.
        return None
    return username


def too_many_attempts(throttle):
    response = HttpResponse(
        "Too many login attempts. Try again later.",
        status=429,
        content_type="text/plain; charset=utf-8",
    )
    response["Retry-After"] = str(math.ceil(throttle.wait()))
    return response


def throttle_failed_logins(view):
    """Limit failed and in-flight login POSTs per client and per username."""

    @wraps(view)
    def throttled_view(request, *args, **kwargs):
        if request.method != "POST":
            return view(request, *args, **kwargs)
        # Check the client limit first: a refused client neither reaches the
        # view nor creates a counter for the username it sent.
        throttles = [AdminLoginClientThrottle(request)]
        username = submitted_username(request)
        if username is not None:
            throttles.append(AdminLoginUsernameThrottle(username))
        entered = False
        with ExitStack() as cleanup:
            for throttle in throttles:
                if not throttle.reserve():
                    return too_many_attempts(throttle)
                cleanup.callback(
                    lambda throttle=throttle: throttle.finish(
                        failed=entered and not getattr(request, LOGGED_IN_ATTR, False)
                    )
                )
            entered = True
            return view(request, *args, **kwargs)

    throttled_view.login_throttled = True
    return throttled_view
