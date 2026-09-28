from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import parse_qs, quote, quote_plus, urlsplit

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.template import Context, Template
from playwright.sync_api import Error as PlaywrightError

from homepage.resume_cover.management.commands import render_resume_pdfs
from homepage.resume_cover.resources import resources_for_slug


def test_published_resources_are_assigned_only_to_their_source_slug(settings):
    settings.RESUME_PUBLIC_RESOURCES = {
        "source": {"cv_pdf": "resume/source-cv.pdf", "portfolio_url": "/portfolio/"},
    }
    assert resources_for_slug("unrelated") == {}
    resources = resources_for_slug("source")
    assert resources["cv_pdf"] == "resume/source-cv.pdf"
    resources["cv_pdf"] = "changed.pdf"
    assert resources_for_slug("source")["cv_pdf"] == "resume/source-cv.pdf"
    template = Template("{% load resume_resources %}{% resume_resources resume as resources %}{{ resources.cv_pdf }}")
    assert template.render(Context({"resume": SimpleNamespace(slug="unrelated")})) == ""
    assert template.render(Context({"resume": SimpleNamespace(slug="source")})) == "resume/source-cv.pdf"


def test_pdf_render_requires_environment_token_before_browser_or_output(monkeypatch, tmp_path):
    monkeypatch.delenv("RESUME_PDF_TOKEN", raising=False)
    browser = MagicMock()
    monkeypatch.setattr(render_resume_pdfs, "sync_playwright", browser)
    target = tmp_path / "missing"
    with pytest.raises(CommandError, match="Set RESUME_PDF_TOKEN"):
        call_command("render_resume_pdfs", out=str(target))
    browser.assert_not_called()
    assert not target.exists()


@pytest.fixture
def pdf_browser(monkeypatch):
    manager = MagicMock()
    browser = manager.return_value.__enter__.return_value.chromium.launch.return_value
    page = browser.new_page.return_value
    page.goto.return_value = SimpleNamespace(ok=True, status=200)
    page.query_selector.return_value = object()
    monkeypatch.setattr(render_resume_pdfs, "sync_playwright", manager)
    return browser, page


def test_pdf_render_encodes_token_and_uses_shared_source_mapping(monkeypatch, settings, tmp_path, pdf_browser):
    token = "a+b&c=? /ü"
    monkeypatch.setenv("RESUME_PDF_TOKEN", token)
    settings.RESUME_PUBLIC_RESOURCES = {
        "another-source": {
            "cv_pdf": "resume/another-cv.pdf",
            "cover_pdf": "resume/another-letter.pdf",
        },
    }
    browser, page = pdf_browser
    output = StringIO()
    call_command("render_resume_pdfs", slug="another-source", out=str(tmp_path), stdout=output)
    cv_url, cover_url = [call.args[0] for call in page.goto.call_args_list]
    assert urlsplit(cv_url).path == "/resume/another-source/cv/"
    assert parse_qs(urlsplit(cv_url).query) == {"token": [token]}
    assert urlsplit(cover_url).path == "/resume/another-source/"
    assert not urlsplit(cover_url).query
    assert [call.kwargs["path"] for call in page.pdf.call_args_list] == [
        str(tmp_path / "resume/another-cv.pdf"),
        str(tmp_path / "resume/another-letter.pdf"),
    ]
    assert token not in output.getvalue()
    browser.close.assert_called_once()


@pytest.mark.parametrize("failure", ["navigation", "http", "sheet"])
def test_pdf_errors_do_not_expose_token(monkeypatch, tmp_path, pdf_browser, failure):
    token = "private-token-marker"
    monkeypatch.setenv("RESUME_PDF_TOKEN", token)
    browser, page = pdf_browser
    if failure == "navigation":
        page.goto.side_effect = PlaywrightError(f"navigation failed at ?token={token}")
    elif failure == "http":
        page.goto.return_value = SimpleNamespace(ok=False, status=403)
    else:
        page.query_selector.return_value = None
    output = StringIO()
    with pytest.raises(CommandError) as raised:
        call_command("render_resume_pdfs", out=str(tmp_path / "not-created"), stdout=output)
    assert token not in str(raised.value)
    if failure == "navigation":
        assert "navigation failed" in str(raised.value)
        assert "?token=" not in str(raised.value)
    assert token not in output.getvalue()
    assert not (tmp_path / "not-created").exists()
    page.pdf.assert_not_called()
    browser.close.assert_called_once()


def test_pdf_navigation_error_redacts_raw_and_urlencoded_token(monkeypatch, tmp_path, pdf_browser):
    token = "private +/ü?& marker"
    encoded_plus = quote_plus(token, safe="")
    encoded_percent = quote(token, safe="")
    monkeypatch.setenv("RESUME_PDF_TOKEN", token)
    _browser, page = pdf_browser
    token_url = f"http://127.0.0.1:8003/resume/katharina/cv/?token={encoded_plus}"
    page.goto.side_effect = PlaywrightError(
        f"Page.goto: net::ERR_CONNECTION_REFUSED at {token_url}\n"
        f'Call log: navigating to "{token_url}"; credential={token}; encoded={encoded_percent}'
    )

    with pytest.raises(CommandError) as raised:
        call_command("render_resume_pdfs", out=str(tmp_path / "not-created"))

    diagnostic = str(raised.value)
    assert "ERR_CONNECTION_REFUSED" in diagnostic
    assert "[redacted resume URL]" in diagnostic
    assert token_url not in diagnostic
    assert token not in diagnostic
    assert encoded_plus not in diagnostic
    assert encoded_percent not in diagnostic


def test_pdf_missing_browser_keeps_playwright_install_hint(monkeypatch, tmp_path):
    token = "missing-browser-private-token"
    monkeypatch.setenv("RESUME_PDF_TOKEN", token)
    manager = MagicMock()
    manager.return_value.__enter__.return_value.chromium.launch.side_effect = PlaywrightError(
        "BrowserType.launch: Executable doesn't exist at /playwright/chromium\n"
        "Please run: npx playwright install chromium"
    )
    monkeypatch.setattr(render_resume_pdfs, "sync_playwright", manager)

    with pytest.raises(CommandError) as raised:
        call_command("render_resume_pdfs", out=str(tmp_path / "not-created"))

    diagnostic = str(raised.value)
    assert "Executable doesn't exist" in diagnostic
    assert "npx playwright install chromium" in diagnostic
    assert token not in diagnostic


def test_pdf_unknown_source_is_rejected_before_browser(monkeypatch, tmp_path):
    monkeypatch.setenv("RESUME_PDF_TOKEN", "test-only")
    browser = MagicMock()
    monkeypatch.setattr(render_resume_pdfs, "sync_playwright", browser)
    with pytest.raises(CommandError, match="No published PDF resources"):
        call_command("render_resume_pdfs", slug="unrelated", out=str(tmp_path / "not-created"))
    browser.assert_not_called()
