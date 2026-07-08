from __future__ import annotations

import json
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from homepage.core.weeknotes.converter import BodyConversion, convert_body


class Command(BaseCommand):
    help = "Convert legacy weeknote h2+ul link sections into structured weeknote_links blocks."

    def add_arguments(self, parser):
        parser.add_argument("--slug", help="Convert only one weeknote post slug.")
        parser.add_argument("--write", action="store_true", help="Create Wagtail revisions with converted bodies.")
        parser.add_argument(
            "--publish", action="store_true", help="Publish converted live pages without draft changes."
        )
        parser.add_argument(
            "--suppress-webmentions",
            action="store_true",
            help="Temporarily disconnect the homepage webmention sender while publishing converted pages.",
        )
        parser.add_argument("--report", help="Write a JSON conversion report to this path.")
        parser.add_argument("--fail-on-warnings", action="store_true", help="Exit non-zero when warnings are found.")

    def handle(self, *args, **options):
        from cast.models import Post

        if options["suppress_webmentions"] and not options["publish"]:
            raise CommandError("--suppress-webmentions requires --publish.")

        queryset = Post.objects.filter(slug__startswith="weeknotes-").order_by("visible_date")
        if options["slug"]:
            queryset = queryset.filter(slug=options["slug"])

        report: list[dict[str, Any]] = []
        warning_count = 0
        changed_count = 0
        saved_count = 0
        published_count = 0
        skipped_count = 0

        publish_context = self._suppress_webmentions() if options["suppress_webmentions"] else nullcontext()
        with publish_context:
            for post in queryset:
                conversion = convert_body(post.body.raw_data)
                warning_count += len(conversion.warnings)
                if conversion.changed:
                    changed_count += 1
                entry = self._report_entry(post, conversion)
                if conversion.changed and options["write"]:
                    save_result = self._save_conversion(post, conversion, publish=options["publish"])
                    entry.update(save_result)
                    if save_result["published"]:
                        published_count += 1
                    if save_result["skipped"]:
                        skipped_count += 1
                    else:
                        saved_count += 1
                report.append(entry)

        if options["report"]:
            Path(options["report"]).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

        action_count = saved_count if options["write"] else changed_count
        action = "converted" if options["write"] else "would convert"
        self.stdout.write(
            f"{action} {action_count} post(s), published {published_count}, "
            f"skipped {skipped_count}, warnings {warning_count}."
        )
        if warning_count and options["fail_on_warnings"]:
            raise CommandError(f"Conversion produced {warning_count} warning(s).")

    def _report_entry(self, post, conversion: BodyConversion) -> dict[str, Any]:
        return {
            "slug": post.slug,
            "changed": conversion.changed,
            "converted_sections": conversion.converted_sections,
            "warnings": [{"heading": warning.heading, "message": warning.message} for warning in conversion.warnings],
            "revision_id": None,
            "published": False,
            "skipped": "",
        }

    def _save_conversion(self, post, conversion: BodyConversion, *, publish: bool) -> dict[str, Any]:
        if post.has_unpublished_changes:
            return {
                "revision_id": None,
                "published": False,
                "skipped": "has_unpublished_changes",
            }
        should_publish = publish and post.live and not post.has_unpublished_changes
        post.body = conversion.body
        revision = post.save_revision(changed=True)
        if should_publish:
            revision.publish()
        return {
            "revision_id": revision.id,
            "published": should_publish,
            "skipped": "",
        }

    @contextmanager
    def _suppress_webmentions(self):
        from wagtail.signals import page_published

        from homepage.core.webmention_integration import send_webmentions_on_publish

        disconnected = page_published.disconnect(send_webmentions_on_publish)
        try:
            yield
        finally:
            if disconnected:
                page_published.connect(send_webmentions_on_publish)
