"""Owner decisions from the 2026-11-17 security audit (request #339, "wie empfohlen").

M2: IndieAuth ``me`` is bound to the logged-in account's profile URL.
L1: the unthrottled Wagtail admin password reset is off; allauth's rate-limited reset stays.
L2: the local dev server binds 127.0.0.1 and accepts only local host names by default.
L3: a Content-Security-Policy-Report-Only header with a bounded report endpoint.
"""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from cast.models import TemplateBaseDirectory
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from indieweb.models import Profile
from wagtail.models import Locale, Page, Site

REPO_ROOT = Path(__file__).resolve().parents[2]
ME = "https://wersdoerfer.de/jochen/"


@pytest.fixture
def themed_site(db):
    """allauth and IndieAuth pages extend the site's cast theme."""
    Locale.objects.get_or_create(language_code="en")
    root = Page.get_first_root_node() or Page.add_root(instance=Page(title="Root", slug="root"))
    Site.objects.all().delete()
    site = Site.objects.create(hostname="testserver", root_page=root, is_default_site=True)
    TemplateBaseDirectory.objects.create(site=site, name="bootstrap4")
    return site


# --- M2: IndieAuth me binding ---------------------------------------------------


def _auth_params(me=ME):
    return {
        "client_id": "https://client.example/",
        "redirect_uri": "https://client.example/callback",
        "state": "synthetic-state",
        "me": me,
        "response_type": "code",
        "scope": "create",
    }


def test_indieauth_me_binding_is_enabled():
    assert settings.INDIEWEB_BIND_ME_TO_USER is True


@pytest.mark.django_db
def test_other_account_cannot_claim_jochens_me(themed_site, client, django_user_model):
    other = django_user_model.objects.create_user("other", password="synthetic")
    client.force_login(other)
    response = client.get(reverse("indieweb:auth"), _auth_params())
    assert response.status_code == 400
    assert response.content == b"invalid me"


@pytest.mark.django_db
def test_account_with_other_profile_url_cannot_claim_jochens_me(themed_site, client, django_user_model):
    other = django_user_model.objects.create_user("other", password="synthetic")
    Profile.objects.create(user=other, url="https://wersdoerfer.de/katharina/")
    client.force_login(other)
    response = client.get(reverse("indieweb:auth"), _auth_params())
    assert response.status_code == 400
    assert response.content == b"invalid me"


@pytest.mark.django_db
def test_profile_owner_passes_the_me_binding(themed_site, client, django_user_model):
    owner = django_user_model.objects.create_user("owner", password="synthetic")
    Profile.objects.create(user=owner, url=ME)
    client.force_login(owner)
    response = client.get(reverse("indieweb:auth"), _auth_params())
    assert response.content != b"invalid me"


# --- L1: Wagtail admin password reset -------------------------------------------


@pytest.mark.django_db
def test_wagtail_admin_password_reset_is_disabled(client, django_user_model):
    django_user_model.objects.create_user("reset", email="reset@example.invalid", password="synthetic")
    url = f"/{settings.WAGTAILADMIN_BASE_URL.strip('/')}/password_reset/"
    assert client.get(url).status_code == 404
    assert client.post(url, {"email": "reset@example.invalid"}).status_code == 404
    assert mail.outbox == []


@pytest.mark.django_db
def test_wagtail_login_page_hides_reset_link(themed_site, client):
    response = client.get(f"/{settings.WAGTAILADMIN_BASE_URL.strip('/')}/login/")
    assert response.status_code == 200
    assert b"password_reset" not in response.content


@pytest.mark.django_db
def test_allauth_password_reset_stays_available(themed_site, client):
    assert client.get(reverse("account_reset_password")).status_code == 200


# --- L2: local dev server -------------------------------------------------------


def _runserver_address(command_line, **env):
    """Expand a recipe's runserver address the way the recipe's shell does."""
    match = re.search(r"runserver (\S+)", command_line)
    assert match is not None, command_line
    result = subprocess.run(
        ["/bin/sh", "-c", f'printf %s "{match.group(1)}"'],
        env={"PATH": os.environ.get("PATH", ""), **env},
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return result.stdout


def _procfile_django():
    (line,) = (line for line in (REPO_ROOT / "Procfile").read_text().splitlines() if line.startswith("django:"))
    return line


def _justfile_django():
    lines = (REPO_ROOT / "justfile").read_text().splitlines()
    first, last = lines.index("django:") + 1, lines.index("django:") + 4
    (line,) = (line for line in lines[first:last] if "runserver" in line)
    return line


@pytest.mark.parametrize("command_line", [_procfile_django(), _justfile_django()], ids=["Procfile", "justfile"])
def test_dev_server_binds_loopback_by_default(command_line):
    assert _runserver_address(command_line) == "127.0.0.1:8000"
    assert _runserver_address(command_line, DJANGO_RUNSERVER_ADDR="0.0.0.0") == "0.0.0.0:8000"


LOCAL_PROBE = """
import json
from django.conf import settings
print(json.dumps(settings.ALLOWED_HOSTS))
"""


def _local_allowed_hosts(**overrides):
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "DJANGO_SETTINGS_MODULE": "config.settings.local",
        "DJANGO_READ_DOT_ENV_FILE": "False",
        "DATABASE_URL": "postgres:///unused",
        "DJANGO_AWS_ACCESS_KEY_ID": "test-only",
        "DJANGO_AWS_SECRET_ACCESS_KEY": "test-only",
        "DJANGO_AWS_STORAGE_BUCKET_NAME": "test-only",
        "CLOUDFRONT_DOMAIN": "cdn.example.invalid",
        **overrides,
    }
    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()\n" + LOCAL_PROBE],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_local_allowed_hosts_default_to_local_names():
    assert _local_allowed_hosts() == ["localhost", "127.0.0.1", "[::1]", ".localhost"]


def test_local_allowed_hosts_can_be_widened_explicitly():
    assert _local_allowed_hosts(DJANGO_ALLOWED_HOSTS="192.168.1.20,localhost") == ["192.168.1.20", "localhost"]


# --- L3: CSP report-only ----------------------------------------------------------


@pytest.mark.django_db
def test_responses_carry_report_only_csp(themed_site, client):
    response = client.get(reverse("account_login"))
    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
    policy = response.headers["Content-Security-Policy-Report-Only"]
    directives = dict(part.strip().split(" ", 1) for part in policy.split(";") if part.strip())
    assert directives["default-src"] == "'self'"
    assert directives["object-src"] == "'none'"
    assert directives["frame-ancestors"] == "'self'"
    assert directives["base-uri"] == "'self'"
    assert directives["report-uri"] == reverse("csp_report")


@pytest.mark.django_db
@override_settings(PORTFOLIO_HOSTS=["design.example.test"], ALLOWED_HOSTS=["design.example.test", "testserver"])
def test_portfolio_host_routes_csp_reports(client):
    response = client.post(
        "/csp-report/",
        data=b'{"csp-report": {}}',
        content_type="application/csp-report",
        HTTP_HOST="design.example.test",
    )
    assert response.status_code == 204


class _CspLog:
    def __init__(self, caplog):
        self._caplog = caplog

    @property
    def records(self):
        return [record for record in self._caplog.records if record.name == "homepage.csp"]


@pytest.fixture()
def csp_log(db, caplog):
    from homepage.core import csp

    cache.clear()
    csp._budget.reset()
    caplog.set_level(logging.WARNING, logger="homepage.csp")
    return _CspLog(caplog)


def _report(client, payload, content_type="application/csp-report"):
    return client.post(reverse("csp_report"), data=json.dumps(payload), content_type=content_type, secure=True)


def test_csp_report_is_logged_without_queries(client, csp_log):
    payload = {
        "csp-report": {
            "document-uri": "https://testserver/indieweb/auth/?code=SECRET-CODE&state=x",
            "violated-directive": "script-src-elem",
            "effective-directive": "script-src-elem",
            "blocked-uri": "https://evil.example/x.js?token=SECRET-TOKEN",
            "source-file": "https://testserver/static/app.js?v=SECRET-V",
            "line-number": 12,
        }
    }
    assert _report(client, payload).status_code == 204
    (record,) = csp_log.records
    message = record.getMessage()
    assert "script-src-elem" in message
    assert "https://evil.example" in message
    assert "document=testserver/indieweb/ " in message
    assert "source=testserver/static/:12" in message
    assert "SECRET" not in message


def test_reporting_api_format_is_accepted(client, csp_log):
    payload = [
        {
            "type": "csp-violation",
            "url": "https://testserver/blogs/?q=SECRET",
            "body": {
                "documentURL": "https://testserver/blogs/?q=SECRET",
                "effectiveDirective": "img-src",
                "blockedURL": "data",
            },
        },
        {"type": "deprecation", "body": {}},
    ]
    assert _report(client, payload, "application/reports+json").status_code == 204
    (record,) = csp_log.records
    assert "img-src" in record.getMessage()
    assert "document=testserver/blogs/ " in record.getMessage()
    assert "SECRET" not in record.getMessage()


@pytest.mark.parametrize(
    ("media_type", "legacy_shape", "status"),
    [
        ("application/csp-report; charset=UTF-8", True, 204),
        ("application/reports+json; charset=UTF-8", False, 204),
        ("application/csp-report", False, 400),
        ("application/reports+json", True, 400),
        ("application/json", True, 415),
    ],
)
def test_csp_report_shape_matches_media_type(client, csp_log, media_type, legacy_shape, status):
    payload = (
        {"csp-report": {"effective-directive": "script-src"}}
        if legacy_shape
        else [{"type": "csp-violation", "body": {"effectiveDirective": "script-src"}}]
    )
    assert _report(client, payload, media_type).status_code == status
    assert len(csp_log.records) == (1 if status == 204 else 0)


def test_empty_reporting_api_batch_is_accepted(client, csp_log):
    assert _report(client, [], "application/reports+json").status_code == 204
    assert csp_log.records == []


def test_reporting_api_stops_reading_after_five_supported_reports(client, csp_log, monkeypatch):
    from homepage.core import csp

    class CountingBatch(list):
        reads = 0

        def __iter__(self):
            for item in super().__iter__():
                self.reads += 1
                yield item

    def violation(line):
        return {"type": "csp-violation", "body": {"lineNumber": line}}

    batch = CountingBatch(
        [
            None,
            violation(1),
            {"type": "deprecation", "body": {}},
            violation(2),
            {"type": "csp-violation", "body": []},
            violation(3),
            violation(4),
            violation(5),
            violation(6),
        ]
    )
    monkeypatch.setattr(csp, "json", SimpleNamespace(loads=lambda body: batch))

    assert _report(client, [], "application/reports+json").status_code == 204
    assert [record.getMessage().rsplit(":", 1)[1] for record in csp_log.records] == ["1", "2", "3", "4", "5"]
    assert batch.reads == 8


@pytest.mark.parametrize("reporting_api", [False, True], ids=["legacy", "reporting-api"])
def test_csp_reports_omit_opaque_document_and_external_source_paths(client, csp_log, reporting_api):
    document = "https://testserver/opaque-document-id/private"
    source = "https://assets.example.test/static/opaque-source-id/app.js"
    if reporting_api:
        payload = [{"type": "csp-violation", "body": {"documentURL": document, "sourceFile": source}}]
        response = _report(client, payload, "application/reports+json")
    else:
        response = _report(client, {"csp-report": {"document-uri": document, "source-file": source}})

    assert response.status_code == 204
    (record,) = csp_log.records
    assert "document=https://testserver source=https://assets.example.test:-" in record.getMessage()
    assert "opaque-" not in record.getMessage()


@pytest.mark.parametrize("value", ["inline", "eval", "data", "", "wasm-eval"])
def test_keyword_blocked_uris_are_kept(client, csp_log, value):
    payload = {
        "csp-report": {"document-uri": "https://wersdoerfer.de/", "effective-directive": "x", "blocked-uri": value}
    }
    assert _report(client, payload).status_code == 204
    assert f"blocked={value or '-'}" in csp_log.records[0].getMessage()


def test_csp_report_endpoint_rejects_other_methods(client, csp_log):
    assert client.get(reverse("csp_report")).status_code == 405
    assert csp_log.records == []


@pytest.mark.parametrize("body", [b"not json", b"[1, 2]", b'"x"', b"{" * 5000], ids=["text", "list", "string", "deep"])
def test_invalid_reports_are_rejected(client, csp_log, body):
    response = client.post(reverse("csp_report"), data=body, content_type="application/csp-report")
    assert response.status_code == 400
    assert csp_log.records == []


def test_oversized_reports_are_refused_without_logging(client, csp_log):
    body = json.dumps({"csp-report": {"document-uri": "https://wersdoerfer.de/", "x": "a" * 20_000}})
    response = client.post(reverse("csp_report"), data=body, content_type="application/csp-report")
    assert response.status_code == 413
    assert csp_log.records == []


def test_report_logging_is_rate_limited(client, csp_log, settings):
    settings.CSP_REPORT_LOG_LIMIT_PER_MINUTE = 3
    payload = {"csp-report": {"document-uri": "https://wersdoerfer.de/", "effective-directive": "img-src"}}
    for _ in range(10):
        assert _report(client, payload).status_code == 204
    messages = [record.getMessage() for record in csp_log.records]
    assert len([m for m in messages if m.startswith("CSP report-only violation")]) == 3
    assert len([m for m in messages if "suppressed" in m]) == 1


def test_report_fields_are_truncated(client, csp_log):
    payload = {
        "csp-report": {
            "document-uri": "https://wersdoerfer.de/" + "p" * 2000,
            "effective-directive": "d" * 500,
            "blocked-uri": "https://" + "h" * 300 + ".example/",
        }
    }
    assert _report(client, payload).status_code == 204
    assert len(csp_log.records[0].getMessage()) < 900


PRODUCTION_PROBE = """
import json
import django
django.setup()
from django.conf import settings
print(json.dumps({
    "bind": settings.INDIEWEB_BIND_ME_TO_USER,
    "wagtail_reset": settings.WAGTAIL_PASSWORD_RESET_ENABLED,
    "csp_middleware": "django.middleware.csp.ContentSecurityPolicyMiddleware" in settings.MIDDLEWARE,
    "enforced": settings.SECURE_CSP,
    "media_src": [str(v) for v in settings.SECURE_CSP_REPORT_ONLY["media-src"]],
    "report_uri": settings.SECURE_CSP_REPORT_ONLY["report-uri"],
}))
"""


def test_production_settings_carry_the_owner_decisions(tmp_path):
    from homepage.tests.test_production_indieweb_proxy import DUMMY_PRODUCTION_ENV

    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")}
    env.update(DUMMY_PRODUCTION_ENV)
    env["DJANGO_CACHE_LOCATION"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", PRODUCTION_PROBE],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout.strip().splitlines()[-1])
    assert values == {
        "bind": True,
        "wagtail_reset": False,
        "csp_middleware": True,
        "enforced": {},
        "media_src": ["'self'", "https://cdn.example.invalid", "https://s3.amazonaws.com"],
        "report_uri": ["/csp-report/"],
    }


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ("https://testserver/accounts/confirm-email/SECRET-CONFIRMATION-KEY/", "testserver/accounts/"),
        ("https://testserver/accounts/password/reset/key/SECRET-uid-SECRET-key/", "testserver/accounts/"),
        ("https://testserver/accounts%2Fconfirm-email%2FSECRET-KEY/", "https://testserver"),
        ("https://testserver/SECRET-FIRST/", "https://testserver"),
        ("https://testserver/static/js/app.js", "testserver/static/"),
        ("https://cdn.example/static/SECRET-TOKEN/lib.js", "https://cdn.example"),
        ("https://testserver/static/../accounts/SECRET/", "testserver/static/"),
        ("https://testserver/static/%2e%2e/SECRET", "testserver/static/"),
        ("https://foreign.example/private/SECRET-PATH/", "https://foreign.example"),
        ("https://user:SECRET-PW@testserver/blogs/", "testserver/blogs/"),
        ("http://[::1]:8000/blogs/a-post/", "http://[::1]:8000"),
        ("http://testserver/blogs/a-post/", "http://testserver"),
        ("https://testserver:444/blogs/a-post/", "https://testserver:444"),
        ("https://testserver:443/blogs/a-post/", "testserver:443/blogs/"),
        ("https://testserver/", "https://testserver"),
        ("https://testserver:99999/", "invalid"),
    ],
)
def test_locations_keep_only_known_same_origin_prefixes(client, csp_log, document, expected):
    payload = {"csp-report": {"document-uri": document, "effective-directive": "script-src"}}
    assert _report(client, payload).status_code == 204
    message = csp_log.records[0].getMessage()
    assert f"document={expected} " in message
    assert "SECRET" not in message


def test_concurrent_admissions_respect_the_budget(settings):
    import threading

    from homepage.core import csp

    settings.CSP_REPORT_LOG_LIMIT_PER_MINUTE = 5
    csp._budget.reset()
    results = []
    lock = threading.Lock()

    def worker():
        for _ in range(50):
            outcome = csp._budget.admit()
            with lock:
                results.append(outcome)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
    assert sum(1 for log_it, _ in results if log_it) == 5
    assert sum(1 for _, notice in results if notice) == 1


def test_reports_never_write_the_cache(client, csp_log, monkeypatch):
    writes = []
    for name in ("set", "add", "incr", "set_many"):
        monkeypatch.setattr(cache, name, lambda *args, _name=name, **kwargs: writes.append(_name))
    payload = {"csp-report": {"document-uri": "https://testserver/", "effective-directive": "img-src"}}
    for _ in range(5):
        assert _report(client, payload).status_code == 204
    assert writes == []


def test_budget_rollover_is_monotonic(settings, monkeypatch):
    from homepage.core import csp

    settings.CSP_REPORT_LOG_LIMIT_PER_MINUTE = 1
    budget = csp._MinuteBudget()
    now = {"t": 120.0}
    monkeypatch.setattr(csp.time, "monotonic", lambda: now["t"])
    assert budget.admit() == (True, False)
    assert budget.admit() == (False, True)
    now["t"] = 180.0  # next minute
    assert budget.admit() == (True, False)
    assert budget.admit() == (False, True)
    now["t"] = 179.0  # a late reader of the previous minute must not reopen it
    assert budget.admit() == (False, False)
    now["t"] = 180.5
    assert budget.admit() == (False, False)
