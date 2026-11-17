from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Func, IntegerField, TextField
from django.db.models.functions import Cast

from homepage.core.weeknotes.converter import BodyConversion, convert_body


def _published_mode(target: Path) -> int:
    try:
        return target.stat().st_mode & 0o777
    except FileNotFoundError:
        umask = os.umask(0)
        os.umask(umask)
        return 0o666 & ~umask


# Report value for a page that changed between reading it and saving its conversion.
CHANGED_SINCE_READ = "changed_since_read"
# PostgreSQL's SQLSTATE for a row lock that NOWAIT could not get.
LOCK_NOT_AVAILABLE = "55P03"


class Command(BaseCommand):
    help = "Convert legacy weeknote h2+ul link sections into structured weeknote_links blocks."

    def add_arguments(self, parser):
        parser.add_argument("--after-pk", type=int, default=0, help="Continue after this processed page ID.")
        parser.add_argument("--through-pk", type=int, help="Keep the initial run's inclusive upper page ID.")
        parser.add_argument("--max-posts", type=int, default=100, help="Maximum processed posts (default: 100).")
        parser.add_argument(
            "--max-body-bytes",
            type=int,
            default=16 * 1024 * 1024,
            help="Total admitted stored body bytes (default: 16 MiB).",
        )
        parser.add_argument(
            "--max-report-bytes",
            type=int,
            default=4 * 1024 * 1024,
            help="Total admitted receipt bytes (default: 4 MiB).",
        )
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

        for name in ("max_posts", "max_body_bytes", "max_report_bytes"):
            if options[name] <= 0:
                raise CommandError(f"--{name.replace('_', '-')} must be positive.")
        if options["after_pk"] < 0 or (
            options["through_pk"] is not None and options["through_pk"] < options["after_pk"]
        ):
            raise CommandError("Require 0 <= --after-pk <= --through-pk.")
        queryset = (
            Post.objects.filter(slug__startswith="weeknotes-")
            .annotate(
                _body_bytes=Func(Cast("body", TextField()), function="OCTET_LENGTH", output_field=IntegerField())
            )
            .order_by("pk")
        )
        if options["slug"]:
            queryset = queryset.filter(slug=options["slug"])

        cursor = options["after_pk"]
        through_pk = options["through_pk"]
        if through_pk is None:
            through_pk = queryset.order_by("-pk").values_list("pk", flat=True).first() or cursor
        queryset = queryset.filter(pk__lte=through_pk)
        body_bytes = 0
        report_bytes = 3  # JSON list framing and trailing newline.
        boundary = ""
        report: list[dict[str, Any]] = []
        warning_count = 0
        changed_count = 0
        saved_count = 0
        published_count = 0
        skipped_count = 0
        conflict_count = 0

        publish_context = self._suppress_webmentions() if options["suppress_webmentions"] else nullcontext()
        with self._report_file(options["report"], report) as receipt, publish_context:
            while (next_pk := queryset.filter(pk__gt=cursor).values_list("pk", flat=True).first()) is not None:
                if len(report) >= options["max_posts"]:
                    boundary = "post budget"
                    break
                # Size admission happens in SQL, before a full Post/body is hydrated.
                # Repeat the size predicate on hydration to cover concurrent growth.
                post = queryset.filter(pk=next_pk, _body_bytes__lte=options["max_body_bytes"] - body_bytes).first()
                if post is None:
                    boundary = f"body budget (or removed page {next_pk})"
                    break
                body_bytes += post._body_bytes
                # What the conversion is computed from. It is compared with the page again
                # before anything is written.
                source = self._source_state(post)
                conversion = convert_body(post.body.raw_data)
                entry = self._report_entry(post, conversion)
                entry.update(page_id=post.pk, through_pk=through_pk)
                # Reserve room for the save result (64-bit revision ID, skip reason,
                # indentation and commas) before committing anything.
                entry_bytes = len(json.dumps(entry, indent=2, ensure_ascii=False).encode("utf-8")) + 256
                if report_bytes + entry_bytes > options["max_report_bytes"]:
                    boundary = "report budget"
                    break
                report_bytes += entry_bytes
                warning_count += len(conversion.warnings)
                if conversion.changed:
                    changed_count += 1
                if conversion.changed and options["write"]:
                    save_result = self._save_conversion(post, conversion, publish=options["publish"], source=source)
                    entry.update(save_result)
                    if save_result["published"]:
                        published_count += 1
                    if save_result["skipped"] == CHANGED_SINCE_READ:
                        conflict_count += 1
                    if save_result["skipped"]:
                        skipped_count += 1
                    else:
                        saved_count += 1
                report.append(entry)
                cursor = post.pk
                if receipt is not None:
                    self._checkpoint_report(receipt, report)

        action_count = saved_count if options["write"] else changed_count
        action = "converted" if options["write"] else "would convert"
        self.stdout.write(
            f"{action} {action_count} post(s), published {published_count}, "
            f"skipped {skipped_count}, warnings {warning_count}."
        )
        if boundary:
            continuation = f"--after-pk {cursor} --through-pk {through_pk}"
            self.stderr.write(f"Partial run: {boundary}; continue with the same flags and {continuation}.")
            raise CommandError(f"Partial run: {boundary}; {continuation}. Completed receipts were retained.")
        self.stdout.write(f"Complete through page ID {through_pk}.")
        if conflict_count:
            self.stderr.write(
                f"{conflict_count} post(s) changed or were being saved while they were being converted "
                "and were left untouched; "
                "run the command again to convert them from their current content."
            )
        if warning_count and options["fail_on_warnings"]:
            raise CommandError(f"Conversion produced {warning_count} warning(s).")

    @contextmanager
    def _report_file(self, path, report):
        if not path:
            yield None
            return
        target = Path(path)
        try:
            stream = tempfile.NamedTemporaryFile(
                mode="w+",
                encoding="utf-8",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".pending",
                delete=False,
            )
        except OSError as error:
            raise CommandError(f"Cannot stage conversion report before changes: {error}") from error
        try:
            with stream:
                # NamedTemporaryFile is always 0600; publish with the mode a plain
                # create would give (or the replaced report's mode) so readers keep access.
                os.chmod(stream.fileno(), _published_mode(target))
                # Write/flush before any revision; fail early on unavailable report storage.
                self._checkpoint_report(stream, report)
                yield stream
            os.replace(stream.name, target)
        except Exception as error:
            self.stderr.write(f"Conversion receipt retained at {stream.name!r} (may be incomplete).")
            for entry in report:
                if entry["revision_id"] is not None:
                    self.stderr.write(
                        f"Committed revision: {entry['slug']} revision_id={entry['revision_id']} "
                        f"published={entry['published']}"
                    )
            raise CommandError(
                f"Conversion/report failed: {error}. Any completed revisions remain committed; "
                "inspect the retained receipt and reported revision IDs before retrying."
            ) from error

    def _checkpoint_report(self, stream, report):
        stream.seek(0)
        payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if stream.write(payload) != len(payload):
            raise OSError("Short conversion report write")
        stream.truncate()
        stream.flush()
        os.fsync(stream.fileno())

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

    def _source_state(self, post) -> dict[str, Any]:
        """Identify the page state a conversion is computed from."""
        return {
            "latest_revision_id": post.latest_revision_id,
            "live_revision_id": post.live_revision_id,
            "live": post.live,
            # A copy: the conversion must not be able to alter what it is compared with.
            "body": json.loads(json.dumps(list(post.body.raw_data))),
        }

    def _save_conversion(
        self, post, conversion: BodyConversion, *, publish: bool, source: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Save ``conversion`` as a new revision of ``post`` unless the page moved on.

        ``source`` is the state the conversion was computed from (``_source_state``). The
        page is locked and read again here; the conversion is only written when that
        current page is still in the source state. Otherwise, or when the page is being
        saved by somebody else at this moment, nothing is created or published and the
        row is reported as ``changed_since_read``.
        """
        if source is None:
            source = self._source_state(post)
        with self._locked_current_post(post) as current:
            if current is None or self._source_state(current) != source:
                return {"revision_id": None, "published": False, "skipped": CHANGED_SINCE_READ}
            if current.has_unpublished_changes:
                return {
                    "revision_id": None,
                    "published": False,
                    "skipped": "has_unpublished_changes",
                }
            should_publish = publish and current.live
            # The revision is built from the page read under the lock, so no other
            # field of an older in-memory copy ends up in it.
            current.body = conversion.body
            revision = current.save_revision(changed=True)
            if should_publish:
                revision.publish()
            return {
                "revision_id": revision.id,
                "published": should_publish,
                "skipped": "",
            }

    @contextmanager
    def _locked_current_post(self, post):
        """Yield the current database state of ``post`` while holding its row locks.

        Saving a draft or publishing in the editor updates the page row and rows of
        the page's revisions. Holding their locks until the block ends makes those
        wait, and reading the page again under the locks sees every edit committed
        since the post list was loaded. Yields ``None`` when the page has been
        deleted or is being saved by somebody else right now.
        """
        from cast.models import Post
        from django.db import transaction

        with transaction.atomic():
            if not self._lock_rows(post):
                yield None
                return
            current = Post.objects.filter(pk=post.pk)
            if hasattr(post, "_body_bytes"):
                # Do not hydrate an unadmitted replacement body while checking conflicts.
                current = current.annotate(
                    _body_bytes=Func(Cast("body", TextField()), function="OCTET_LENGTH", output_field=IntegerField())
                ).filter(_body_bytes__lte=post._body_bytes)
            yield current.first()

    @staticmethod
    def _lock_rows(post) -> bool:
        """Lock the page's revisions and its page row without waiting; ``False`` when busy.

        Wagtail takes these locks in no single order: overwriting a draft updates the
        revision and then the page, saving and publishing in one request updates the
        page and then every revision. Waiting for either while holding the other can
        therefore deadlock with an editor, and PostgreSQL would resolve that by
        aborting one side, possibly the editor's save. So nothing is waited for: all
        rows are requested with NOWAIT, and a row that somebody else holds means the
        page is being saved right now. Once every row is held, this transaction only
        touches these rows and rows it inserts itself, so it cannot block on an
        editor later.

        ``no_key`` asks for the lock an UPDATE takes, so only real changes to the
        rows count as busy, not a foreign key check that merely references them.
        """
        from django.db import OperationalError, transaction
        from wagtail.models import Page

        try:
            # A refused lock fails the statement; the savepoint keeps the surrounding
            # transaction usable.
            with transaction.atomic():
                list(
                    post.revisions.select_for_update(nowait=True, no_key=True)
                    .order_by("pk")
                    .values_list("pk", flat=True)
                )
                list(
                    Page.objects.select_for_update(nowait=True, no_key=True)
                    .filter(pk=post.pk)
                    .values_list("pk", flat=True)
                )
        except OperationalError as exc:
            if getattr(exc.__cause__, "sqlstate", None) != LOCK_NOT_AVAILABLE:
                raise
            return False
        return True

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
