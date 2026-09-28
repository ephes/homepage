"""Pre-render explicitly published editorial documents to A4 PDF artifacts.

Set RESUME_PDF_TOKEN in the environment, then run against a running site:
    uv run python manage.py render_resume_pdfs --base-url http://127.0.0.1:8003

RESUME_PUBLIC_RESOURCES assigns static PDF paths to their source resume slug.
Only intentionally public documents belong in that mapping.
"""

import os
import re
from pathlib import Path
from urllib.parse import parse_qsl, quote, quote_plus, urlencode, urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from homepage.resume_cover.resources import resources_for_slug

TOKEN_URL_PATTERN = re.compile(r"(?:https?://|/|\?)[^\s\"'<>]+")


def sanitized_playwright_error(error, token):
    """Keep Playwright's operational hint while removing resume credentials."""

    def redact_token_url(match):
        candidate = match.group(0)
        try:
            has_token = any(
                key.lower() == "token" for key, _value in parse_qsl(urlsplit(candidate).query, keep_blank_values=True)
            )
        except ValueError:
            has_token = "token=" in candidate.lower()
        return "[redacted resume URL]" if has_token else candidate

    sanitized = TOKEN_URL_PATTERN.sub(redact_token_url, str(error))
    encoded_tokens = {token, quote(token, safe=""), quote_plus(token, safe="")}
    for secret in sorted(encoded_tokens, key=len, reverse=True):
        if secret:
            sanitized = sanitized.replace(secret, "[redacted token]")
    return sanitized.strip() or "unknown Playwright error"


class Command(BaseCommand):
    help = "Render explicitly published editorial CV and cover-letter PDFs."

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default="http://127.0.0.1:8003")
        parser.add_argument("--slug", default="katharina")
        parser.add_argument(
            "--out",
            default=str(Path(settings.APPS_DIR) / "static"),
            help="Static root directory; paths come from RESUME_PUBLIC_RESOURCES.",
        )

    def handle(self, *args, **opts):
        token = os.environ.get("RESUME_PDF_TOKEN")
        if not token:
            raise CommandError("Set RESUME_PDF_TOKEN before rendering PDFs.")
        resources = resources_for_slug(opts["slug"])
        documents = []
        for key, route in (("cv_pdf", "cv"), ("cover_pdf", "detail")):
            if key not in resources:
                continue
            relative_path = Path(resources[key])
            if relative_path.is_absolute() or ".." in relative_path.parts or relative_path.suffix != ".pdf":
                raise CommandError("Published PDF paths must be relative .pdf paths inside the static root.")
            documents.append((route, relative_path))
        if not documents:
            raise CommandError("No published PDF resources configured for this resume slug.")

        out_dir = Path(opts["out"])
        base = opts["base_url"].rstrip("/")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    for route, relative_path in documents:
                        page = browser.new_page()
                        try:
                            page.emulate_media(media="print", reduced_motion="reduce")
                            path = reverse(f"django_resume:{route}", kwargs={"slug": opts["slug"]})
                            url = f"{base}{path}"
                            if route == "cv":
                                url += "?" + urlencode({"token": token})
                            response = page.goto(url, wait_until="networkidle")
                            if response is None or not response.ok:
                                status = response.status if response else "no response"
                                raise CommandError(
                                    f"Resume {route} returned {status}; check server availability and access."
                                )
                            if not page.query_selector(".editorial-sheet"):
                                raise CommandError(
                                    f"Resume {route} has no editorial sheet; check the source resume and access."
                                )
                            page.wait_for_timeout(500)
                            target = out_dir / relative_path
                            target.parent.mkdir(parents=True, exist_ok=True)
                            page.pdf(
                                path=str(target),
                                format="A4",
                                print_background=True,
                                prefer_css_page_size=True,
                            )
                            self.stdout.write(self.style.SUCCESS(f"wrote {target}"))
                        finally:
                            page.close()
                finally:
                    browser.close()
        except PlaywrightError as error:
            detail = sanitized_playwright_error(error, token)
            raise CommandError(f"PDF browser rendering failed: {detail}") from None
