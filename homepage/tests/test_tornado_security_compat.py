"""Check notebook tooling's redirect fix without opening a listening socket."""

from unittest.mock import Mock

import pytest
from tornado.httputil import HTTPHeaders, HTTPServerRequest, RequestStartLine
from tornado.web import Application, HTTPError, RedirectHandler


def redirect_handler():
    request = HTTPServerRequest(
        start_line=RequestStartLine("GET", "/old", "HTTP/1.1"),
        headers=HTTPHeaders({"Host": "notebook.invalid"}),
        connection=Mock(),
    )
    handler = RedirectHandler(Application(), request, url="/{0}/target")
    handler.redirect = Mock()
    return handler


def test_substituted_triple_slash_redirect_is_rejected():
    # CVE-2026-126347: browsers treat ///host as a different authority.
    handler = redirect_handler()
    with pytest.raises(HTTPError) as error:
        handler.get("//attacker.invalid")
    assert error.value.status_code == 400
    handler.redirect.assert_not_called()


def test_local_redirect_substitution_still_works():
    handler = redirect_handler()
    handler.get("local")
    handler.redirect.assert_called_once_with("/local/target", permanent=True)
