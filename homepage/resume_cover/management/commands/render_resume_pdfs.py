"""Pre-render the editorial CV and cover letter to A4 PDF files via headless Chromium.

Approach B from the design spec: the PDFs are build/deploy artifacts, not generated
in the live request path. Run against a running site (dev :8003, or the deployed URL):

    uv run python manage.py render_resume_pdfs --base-url http://127.0.0.1:8003

Output goes to homepage/static/resume/ so WhiteNoise serves it (re-run collectstatic
after rendering in production).
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from playwright.sync_api import sync_playwright

DOCUMENTS = [
    ("/resume/katharina/cv/", "katharina-lebenslauf.pdf"),
    ("/resume/katharina/", "katharina-anschreiben.pdf"),
]


class Command(BaseCommand):
    help = "Render the editorial CV and cover letter to A4 PDF files."

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default="http://127.0.0.1:8003")
        parser.add_argument("--token", default="localpreview2026")
        parser.add_argument(
            "--out",
            default=str(Path(settings.APPS_DIR) / "static" / "resume"),
            help="Output directory for the PDF files.",
        )

    def handle(self, *args, **opts):
        out_dir = Path(opts["out"])
        out_dir.mkdir(parents=True, exist_ok=True)
        base, token = opts["base_url"].rstrip("/"), opts["token"]

        with sync_playwright() as p:
            browser = p.chromium.launch()
            for path, filename in DOCUMENTS:
                page = browser.new_page()
                # print media + reduced-motion => print CSS applies and the handwriting
                # + drawn structural lines jump to their final state (editorial-lines.js
                # adds cv-line-drawn immediately under reduced-motion).
                page.emulate_media(media="print", reduced_motion="reduce")
                url = f"{base}{path}?token={token}"
                page.goto(url, wait_until="networkidle")
                page.wait_for_timeout(500)
                target = out_dir / filename
                page.pdf(
                    path=str(target),
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                )
                page.close()
                self.stdout.write(self.style.SUCCESS(f"wrote {target}"))
            browser.close()
