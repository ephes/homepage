"""Receive Content-Security-Policy violation reports (report-only policy).

Browsers POST reports here for ``SECURE_CSP_REPORT_ONLY`` (config/settings/base.py).
Each report becomes one compact WARNING line on the ``homepage.csp`` logger:
directive, blocked origin (or keyword such as ``inline``), and where it happened.
URLs can carry secrets, so locations are reduced to origins. Only reviewed
same-origin route prefixes can appear for documents and source files. Bodies are
capped, fields truncated, and each worker process logs at most
``CSP_REPORT_LOG_LIMIT_PER_MINUTE`` reports per minute. See docs/csp.rst.
"""

import json
import logging
import re
import threading
import time
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger("homepage.csp")

MAX_BODY_BYTES = 16 * 1024
MAX_REPORTS_PER_REQUEST = 5
_FIELD_MAX = 200
_KEYWORD = re.compile(r"[a-z][a-z-]{0,29}")
_DIRECTIVE = re.compile(r"[a-z][a-z-]{0,39}")
_HOST = re.compile(r"[a-z0-9.-]{1,253}|[0-9a-f:.]{2,45}")
# Fixed route families from the site URLconfs, plus locally served static assets.
_ROUTE_PREFIXES = frozenset(
    {
        "accounts",
        "api-auth",
        "blogs",
        "cms",
        "datenschutz",
        "documents",
        "impressum",
        "indieweb",
        "portfolio",
        "resume",
        "static",
        "users",
    }
)


def _netloc(parts) -> str | None:
    """``host[:port]`` without user info, IPv6 in brackets; ``None`` if malformed."""
    try:
        hostname = parts.hostname or ""
        port = parts.port
    except ValueError:
        return None
    if not _HOST.fullmatch(hostname):
        return None
    host = f"[{hostname}]" if ":" in hostname else hostname
    return f"{host}:{port}" if port is not None else host


def _origin_key(scheme: str, netloc: str) -> tuple[str, str]:
    default_port = ":443" if scheme == "https" else ":80"
    return scheme, netloc.removesuffix(default_port)


def _location(value: object, *, request_origin: tuple[str, str] | None = None) -> str:
    """Keep CSP keywords, URL origins and reviewed same-origin route prefixes."""
    if not isinstance(value, str) or not value.strip():
        return "-"
    value = value.strip()
    if _KEYWORD.fullmatch(value):
        return value  # inline, eval, data, wasm-eval, blob, ...
    try:
        parts = urlsplit(value)
    except ValueError:
        return "invalid"
    if parts.scheme not in {"http", "https"}:
        return parts.scheme if _KEYWORD.fullmatch(parts.scheme) else "other"
    netloc = _netloc(parts)
    if netloc is None:
        return "invalid"
    if request_origin == _origin_key(parts.scheme, netloc):
        first = parts.path.removeprefix("/").partition("/")[0]
        if first in _ROUTE_PREFIXES:
            return f"{netloc}/{first}/"
    return f"{parts.scheme}://{netloc}"


def _directive(value: object) -> str:
    if isinstance(value, str) and _DIRECTIVE.fullmatch(value.strip()):
        return value.strip()
    return "-"


def _line(value: object) -> str:
    return str(value) if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 10**9 else "-"


def _reports(payload: object) -> list[dict[str, object]]:
    """Normalize ``application/csp-report`` and Reporting API (``reports+json``) bodies."""
    if isinstance(payload, dict) and isinstance(payload.get("csp-report"), dict):
        report = payload["csp-report"]
        return [
            {
                "directive": report.get("effective-directive") or report.get("violated-directive"),
                "blocked": report.get("blocked-uri"),
                "document": report.get("document-uri"),
                "source": report.get("source-file"),
                "line": report.get("line-number"),
            }
        ]
    if isinstance(payload, list):
        reports = []
        for item in payload:
            if not isinstance(item, dict) or item.get("type") != "csp-violation":
                continue
            body = item.get("body")
            if not isinstance(body, dict):
                continue
            reports.append(
                {
                    "directive": body.get("effectiveDirective"),
                    "blocked": body.get("blockedURL"),
                    "document": body.get("documentURL"),
                    "source": body.get("sourceFile"),
                    "line": body.get("lineNumber"),
                }
            )
        return reports
    return []


class _MinuteBudget:
    """Per-process log budget; the lock makes admission atomic across threads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._minute = -1
        self._count = 0

    def admit(self) -> tuple[bool, bool]:
        """Return (log this report, log the suppression notice)."""
        limit = int(getattr(settings, "CSP_REPORT_LOG_LIMIT_PER_MINUTE", 30))
        with self._lock:
            # Monotonic and read under the lock: windows advance in order and survive
            # wall-clock corrections.
            minute = int(time.monotonic() // 60)
            if minute > self._minute:
                self._minute, self._count = minute, 0
            if self._count > limit:
                return False, False
            self._count += 1
            return self._count <= limit, self._count == limit + 1

    def reset(self) -> None:
        with self._lock:
            self._minute, self._count = -1, 0


_budget = _MinuteBudget()


@csrf_exempt
@require_POST
def csp_report(request: HttpRequest) -> HttpResponse:
    try:
        declared = int(request.headers.get("content-length") or 0)
    except ValueError:
        return HttpResponse(status=400)
    if declared > MAX_BODY_BYTES:
        return HttpResponse(status=413)
    body = request.read(MAX_BODY_BYTES + 1)
    if len(body) > MAX_BODY_BYTES:
        return HttpResponse(status=413)
    try:
        payload = json.loads(body)
    except (ValueError, RecursionError):
        return HttpResponse(status=400)
    request_origin = _origin_key(request.scheme, request.get_host().lower())
    for report in _reports(payload)[:MAX_REPORTS_PER_REQUEST]:
        log_it, notice = _budget.admit()
        if log_it:
            logger.warning(
                "CSP report-only violation directive=%s blocked=%s document=%s source=%s:%s",
                _directive(report["directive"]),
                _location(report["blocked"]),
                _location(report["document"], request_origin=request_origin),
                _location(report["source"], request_origin=request_origin),
                _line(report["line"]),
            )
        elif notice:
            logger.warning("CSP report logging suppressed for the rest of this minute")
    return HttpResponse(status=204)
