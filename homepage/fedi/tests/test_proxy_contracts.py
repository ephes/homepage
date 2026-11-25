"""Offline cache and diagnostic contracts, independent of database setup."""

import http.client

import pytest
from django.core.cache import cache
from django.test import RequestFactory
from django.utils.cache import has_vary_header
from django.views.decorators.cache import cache_page

from homepage.fedi import views


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.mark.parametrize("view", [views.wellknown_webfinger, views.wellknown_hostmeta, views.wellknown_nodeinfo])
@pytest.mark.parametrize("first_accept", ["application/json", "text/html", "application/xml"])
def test_cached_proxy_separates_accept_representations(monkeypatch, request_factory, view, first_accept):
    calls = []

    def fetch(url, accept):
        calls.append(accept)
        return 200, {"Content-Type": accept, "Cache-Control": "public, max-age=60"}, accept.encode()

    monkeypatch.setattr(views, "_fetch", fetch)
    cache.clear()
    cached_view = cache_page(60)(view)
    accepts = [first_accept, "text/html" if first_accept != "text/html" else "application/xml"]
    try:
        for accept in accepts * 2:
            response = cached_view(request_factory.get("/.well-known/nodeinfo", HTTP_ACCEPT=accept))
            assert response.content == accept.encode()
            assert response["Content-Type"] == accept
        assert calls == accepts
    finally:
        cache.clear()


@pytest.mark.parametrize("method", ["get", "head"])
@pytest.mark.parametrize("status", [200, 302, 404])
@pytest.mark.parametrize("upstream_vary", [None, "accept, ACCEPT-Encoding, Cookie, Origin", "*"])
def test_proxy_variation_allowlist(monkeypatch, request_factory, method, status, upstream_vary):
    headers = {"Cache-Control": "max-age=60", "Location": "/discovery", "Set-Cookie": "private=value"}
    if upstream_vary is not None:
        headers["Vary"] = upstream_vary
    monkeypatch.setattr(views, "_fetch", lambda *args: (status, headers, b"document"))

    response = views.wellknown_nodeinfo(getattr(request_factory, method)("/.well-known/nodeinfo"))

    assert response.status_code == status
    assert response["Cache-Control"] == "max-age=60"
    assert response["Vary"] == ("*" if upstream_vary == "*" else "Accept")
    assert response.content == (b"" if method == "head" else b"document")
    assert not response.has_header("Set-Cookie")
    if status == 302:
        assert response["Location"] == views.FEDI_BASE_URL + "/discovery"


def test_proxy_preserves_repeated_cache_control_in_order(monkeypatch, request_factory):
    headers = http.client.HTTPMessage()
    headers["Cache-Control"] = "max-age=60"
    headers["cache-control"] = "private"
    monkeypatch.setattr(views, "_fetch", lambda *args: (200, headers, b"document"))

    response = views.wellknown_nodeinfo(request_factory.get("/.well-known/nodeinfo"))

    assert response["Cache-Control"] == "max-age=60, private"


def test_upstream_vary_star_prevents_cache_reuse(monkeypatch, request_factory):
    calls = []

    def fetch(*args):
        calls.append(args)
        return 200, {"Vary": "Accept, *", "Cache-Control": "max-age=60"}, b"document"

    monkeypatch.setattr(views, "_fetch", fetch)
    cache.clear()
    cached_view = cache_page(60)(views.wellknown_nodeinfo)
    try:
        for _ in range(2):
            response = cached_view(request_factory.get("/.well-known/nodeinfo"))
            assert has_vary_header(response, "*")
        assert len(calls) == 2
    finally:
        cache.clear()


def test_wildcard_in_repeated_vary_headers_is_preserved(monkeypatch, request_factory):
    headers = http.client.HTTPMessage()
    headers["Vary"] = "Accept"
    headers["Vary"] = "*"
    monkeypatch.setattr(views, "_fetch", lambda *args: (200, headers, b"document"))

    response = views.wellknown_nodeinfo(request_factory.get("/.well-known/nodeinfo"))

    assert response["Vary"] == "*"


SECRET = "invented-private-token-96"


@pytest.mark.parametrize(
    "failure, category, status",
    [
        (views.UpstreamError(SECRET), "Failed to fetch", 502),
        (views.UpstreamTimeout(SECRET), "Timeout fetching", 504),
        ((99, {"Content-Type": f"synthetic-{SECRET}"}, b""), "Invalid upstream response", 502),
        ((200, {"Content-Type": f"application/json\r\n {SECRET}"}, b""), "Invalid upstream response", 502),
        ((302, {"Location": f"http://[{SECRET}]"}, b""), "Invalid upstream response", 502),
    ],
)
def test_gateway_diagnostics_are_private(monkeypatch, request_factory, caplog, failure, category, status):
    def fetch(*args):
        if isinstance(failure, Exception):
            raise failure
        return failure

    monkeypatch.setattr(views, "_fetch", fetch)
    request = request_factory.get(f"/.well-known/nodeinfo?private={SECRET}")

    response = views.wellknown_nodeinfo(request)

    assert response.status_code == status
    assert response.content == (b"Upstream timeout" if status == 504 else b"Bad gateway")
    assert request.fedi_upstream_failure is True
    assert category in caplog.text
    assert "/.well-known/nodeinfo" in caplog.text
    assert SECRET not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.parametrize(
    "error_type", [http.client.BadStatusLine, http.client.HTTPException, OSError, ValueError, TimeoutError]
)
def test_fetch_transport_errors_have_safe_messages_and_no_displayed_chain(monkeypatch, error_type):
    class Connection:
        sock = None

        def __init__(self, *args):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            raise error_type(SECRET)

        def close(self):
            pass

    monkeypatch.setattr(views.http.client, "HTTPConnection", Connection)
    monkeypatch.setattr(views, "_connect", lambda *args: None)

    expected = views.UpstreamTimeout if error_type is TimeoutError else views.UpstreamError
    with pytest.raises(expected) as caught:
        views._fetch("http://upstream.invalid/discovery", "application/json")

    assert SECRET not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def test_dns_error_message_is_private(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError(SECRET)

    monkeypatch.setattr(views.socket, "getaddrinfo", fail)
    with pytest.raises(views.UpstreamError, match="^cannot resolve upstream$"):
        views._resolve("upstream.invalid", 443, 1)
