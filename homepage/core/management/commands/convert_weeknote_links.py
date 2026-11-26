from __future__ import annotations

import json
import os
import stat
import tempfile
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections, router, transaction
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


def _sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _receipt_generation(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


# Report value for a page that changed between reading it and saving its conversion.
CHANGED_SINCE_READ = "changed_since_read"
# PostgreSQL's SQLSTATE for a row lock that NOWAIT could not get.
LOCK_NOT_AVAILABLE = "55P03"
RECEIPT_FORMAT = "homepage-weeknote-receipt-v1"
# Header/outcome frames are not part of the per-page receipt budget a run admits.
RECEIPT_FRAME_ALLOWANCE = 64 * 1024


class Command(BaseCommand):
    help = "Convert legacy weeknote h2+ul link sections into structured weeknote_links blocks."

    def add_arguments(self, parser):
        parser.add_argument("--recover-receipt", help="Publish a retained journal as JSON without converting posts.")
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
        if options["suppress_webmentions"] and not options["publish"]:
            raise CommandError("--suppress-webmentions requires --publish.")

        for name in ("max_posts", "max_body_bytes", "max_report_bytes"):
            if options[name] <= 0:
                raise CommandError(f"--{name.replace('_', '-')} must be positive.")
        if options["after_pk"] < 0 or (
            options["through_pk"] is not None and options["through_pk"] < options["after_pk"]
        ):
            raise CommandError("Require 0 <= --after-pk <= --through-pk.")
        if options["recover_receipt"]:
            self._recover_receipt(options)
            return

        from cast.models import Post

        alias = self._writer_alias(Post, write=options["write"])
        queryset = (
            Post.objects.using(alias)
            .filter(slug__startswith="weeknotes-")
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
            last_pk = queryset.order_by("-pk").values_list("pk", flat=True).first()
            # Never start with an upper bound below the continuation cursor.
            through_pk = max(last_pk or 0, cursor)
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
        run = {"after_pk": cursor, "through_pk": through_pk, "status": "partial"}
        scope = {name: options[name] for name in ("slug", "write", "publish", "suppress_webmentions")}
        with self._report_file(options["report"], report, run, scope) as receipt, publish_context:
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
                # Admit the largest save result and exact outer-list indentation,
                # including warning-heavy entries, before committing anything.
                reserved = {
                    **entry,
                    "revision_id": 9223372036854775807,
                    "published": False,
                    "skipped": "has_unpublished_changes",
                }
                payload = json.dumps(reserved, indent=2, ensure_ascii=False)
                entry_bytes = len(payload.encode("utf-8")) + 2 * (payload.count("\n") + 1) + 2
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
                    self._checkpoint_report(receipt, entry)
                run["after_pk"] = cursor
                del post, source, conversion, entry
            run["status"] = "partial" if boundary else "complete"

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
    def _report_file(self, path, report, run, scope):
        if not path:
            yield None
            return
        target = Path(path)
        try:
            stream = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".journal",
                delete=False,
            )
        except OSError as error:
            raise CommandError(f"Cannot stage conversion receipt before changes: {error}") from error
        try:
            with stream:
                # Private append-only JSONL frames: header, completed pages, outcome.
                self._append_frame(stream, {"format": RECEIPT_FORMAT, **run, "scope": scope})
                _sync_directory(target.parent)
                yield stream
                self._append_frame(stream, {"outcome": dict(run)})
            self._publish_report(target, report)
        except (Exception, KeyboardInterrupt) as error:
            self.stderr.write(f"Conversion receipt retained at {stream.name!r} (may be incomplete).")
            for entry in report:
                if entry["revision_id"] is not None:
                    self.stderr.write(
                        f"Committed revision: {entry['slug']} revision_id={entry['revision_id']} "
                        f"published={entry['published']}"
                    )
            if isinstance(error, KeyboardInterrupt):
                raise
            raise CommandError(
                f"Conversion/report failed: {error}. Any completed revisions remain committed; "
                "inspect the retained receipt and reported revision IDs before retrying."
            ) from error
        try:
            os.unlink(stream.name)
        except OSError:
            self.stderr.write(f"Report published; redundant journal retained at {stream.name!r}.")

    def _checkpoint_report(self, stream, entry):
        self._append_frame(stream, {"entry": entry})

    @staticmethod
    def _append_frame(stream, frame):
        payload = json.dumps(frame, ensure_ascii=False) + "\n"
        if stream.write(payload) != len(payload):
            raise OSError("Short conversion receipt write")
        stream.flush()
        os.fsync(stream.fileno())

    def _publish_report(self, target, report):
        stream = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".pending",
            delete=False,
        )
        try:
            with stream:
                os.chmod(stream.fileno(), _published_mode(target))
                payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
                if stream.write(payload) != len(payload):
                    raise OSError("Short conversion report write")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(stream.name, target)
        except (Exception, KeyboardInterrupt):
            self.stderr.write(f"Staged JSON report retained at {stream.name!r} (may be incomplete).")
            raise
        try:
            _sync_directory(target.parent)
        except OSError:
            self.stderr.write(f"Report replaced at {str(target)!r}; durability uncertain.")
            raise

    def _recover_receipt(self, options):
        if not options["report"] or any(
            options[name] for name in ("write", "publish", "suppress_webmentions", "slug", "after_pk", "through_pk")
        ):
            raise CommandError("--recover-receipt requires --report and no conversion/scope flags.")
        source = Path(options["recover_receipt"])
        target = Path(options["report"])
        if source.resolve() == target.resolve():
            raise CommandError("Recovery report must differ from its journal.")
        try:
            report, run, scope = self._read_receipt(source, options["max_posts"], options["max_report_bytes"])
            self._publish_report(target, report)
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise CommandError(
                f"Cannot recover receipt: {error}. Original journal preserved; no posts changed."
            ) from error
        self.stdout.write(f"Recovered {len(report)} completed page receipt(s); status={run['status']}; scope={scope}.")
        self.stdout.write(f"Continuation: --after-pk {run['after_pk']} --through-pk {run['through_pk']}.")
        self.stderr.write(
            "Check stderr/revisions from the failed run for a commit after its last complete frame. "
            "Recovery never retries or publishes database revisions."
        )

    @staticmethod
    def _read_receipt(path, max_posts, max_bytes):
        report = []
        consumed = 0
        entry_bytes = 0
        limit = max_bytes + RECEIPT_FRAME_ALLOWANCE
        header = None
        finished = False

        def open_journal(name: str, flags: int) -> int:
            return os.open(name, flags | os.O_NONBLOCK | os.O_NOFOLLOW)

        # Admit the opened descriptor before reading; binary reads bound raw bytes.
        with open(path, "rb", opener=open_journal) as stream:
            fd = stream.fileno()
            admitted = os.fstat(fd)
            if not stat.S_ISREG(admitted.st_mode):
                raise ValueError("Receipt must be a regular file")
            if admitted.st_size > limit:
                raise ValueError("Receipt exceeds budget")
            generation = _receipt_generation(admitted)
            while line := stream.readline(limit - consumed + 1):
                consumed += len(line)
                if consumed > limit:
                    raise ValueError("Receipt exceeds budget")
                if not line.endswith(b"\n"):
                    if finished:
                        raise ValueError("Unexpected bytes after outcome")
                    break  # Stable EOF is checked below before publishing the validated prefix.
                frame = json.loads(line)
                if not isinstance(frame, dict):
                    raise ValueError("Receipt frame must be an object")
                if header is None:
                    if frame["format"] != RECEIPT_FORMAT:
                        raise ValueError("Unknown receipt format")
                    header = frame
                    cursor, through = frame["after_pk"], frame["through_pk"]
                    if type(cursor) is not int or type(through) is not int or not 0 <= cursor <= through:
                        raise ValueError("Invalid receipt boundary")
                elif finished:
                    raise ValueError("Unexpected frame after outcome")
                elif "entry" in frame:
                    # Compact entry frames are never larger than the indented
                    # receipt bytes the run charged against --max-report-bytes.
                    entry_bytes += len(line)
                    if entry_bytes > max_bytes:
                        raise ValueError("Receipt exceeds budget")
                    entry = frame["entry"]
                    pk = entry["page_id"]
                    if (
                        type(pk) is not int
                        or not cursor < pk <= through
                        or entry["through_pk"] != through
                        or len(report) >= max_posts
                    ):
                        raise ValueError("Invalid page order/boundary or receipt post budget exceeded")
                    # Require the fields needed to inspect committed progress.
                    for field in (
                        "slug",
                        "revision_id",
                        "published",
                        "changed",
                        "warnings",
                        "skipped",
                        "converted_sections",
                    ):
                        entry[field]
                    report.append(entry)
                    cursor = pk
                else:
                    outcome = frame["outcome"]
                    if (
                        outcome["after_pk"] != cursor
                        or outcome["through_pk"] != through
                        or outcome["status"] not in {"partial", "complete"}
                    ):
                        raise ValueError("Invalid receipt outcome")
                    finished = True
            if header is None:
                raise ValueError("Missing receipt header")
            if (
                consumed != admitted.st_size
                or _receipt_generation(os.fstat(fd)) != generation
                or _receipt_generation(path.stat(follow_symlinks=False)) != generation
            ):
                raise ValueError("Receipt changed while reading")
        run = {"after_pk": cursor, "through_pk": through, "status": outcome["status"] if finished else "partial"}
        return report, run, header["scope"]

    @staticmethod
    def _writer_alias(post_model, *, write):
        alias = router.db_for_write(post_model)
        if alias not in connections:
            raise CommandError(f"Unknown weeknote writer database alias: {alias!r}")
        if not write:
            return alias

        # Wagtail's public revision API takes no using= and Page.save() and
        # save_revision() open atomic blocks on default. Its implicit ORM
        # operations must agree with our explicit scan, locks and reload.
        if alias != DEFAULT_DB_ALIAS:
            raise CommandError(f"Weeknote revision saves require the default database; writer is {alias!r}.")

        from django.contrib.contenttypes.models import ContentType
        from wagtail.models import (
            Comment,
            Page,
            PageLogEntry,
            ReferenceIndex,
            Revision,
            Site,
            TaskState,
            WorkflowState,
        )

        models = dict.fromkeys(
            (
                post_model,
                Page,
                Revision,
                ContentType,
                Site,
                Comment,
                ReferenceIndex,
                PageLogEntry,
                WorkflowState,
                TaskState,
                post_model.tags.through,
                *(
                    field.related_model
                    for field in (*post_model._meta.fields, *post_model._meta.many_to_many)
                    if field.is_relation
                ),
            )
        )
        for model in models:
            for operation, route in (("read", router.db_for_read), ("write", router.db_for_write)):
                routed_alias = route(model)
                if routed_alias != alias:
                    raise CommandError(
                        f"Weeknote revision saves require {model._meta.label} on database {alias!r}; "
                        f"The {operation} router selects {routed_alias!r}."
                    )
        return alias

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

        alias = post._state.db
        with transaction.atomic(using=alias):
            if not self._lock_rows(post, alias):
                yield None
                return
            current = Post.objects.using(alias).filter(pk=post.pk)
            if hasattr(post, "_body_bytes"):
                # Do not hydrate an unadmitted replacement body while checking conflicts.
                current = current.annotate(
                    _body_bytes=Func(Cast("body", TextField()), function="OCTET_LENGTH", output_field=IntegerField())
                ).filter(_body_bytes__lte=post._body_bytes)
            current = current.first()
            if current is not None:
                writer = router.db_for_write(Post, instance=current)
                if writer != alias:
                    raise CommandError(f"Weeknote page {current.pk} is routed to {writer!r}, expected {alias!r}.")
            yield current

    @staticmethod
    def _lock_rows(post, alias) -> bool:
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
        from django.db import OperationalError
        from wagtail.models import Page

        try:
            # A refused lock fails the statement; the savepoint keeps the surrounding
            # transaction usable.
            with transaction.atomic(using=alias):
                list(
                    post.revisions.using(alias)
                    .select_for_update(nowait=True, no_key=True)
                    .order_by("pk")
                    .values_list("pk", flat=True)
                )
                list(
                    Page.objects.using(alias)
                    .select_for_update(nowait=True, no_key=True)
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
