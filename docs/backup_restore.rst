Backup
======

How to backup the production database:
 * Use pg_dump or your preferred PostgreSQL backup tool
 * Store backups in a secure location

How to backup the s3 contents (copy to local media directory):
 * uv run python manage.py s3_backup

How to restore the local contents to s3 (copy local media directory to s3):
 * uv run python manage.py s3_restore

Restore
=======

How to restore the production backup to the local database:
 * just production-db-to-local (see :doc:`install`; an existing local database is only
   replaced with ``--replace-existing`` and only after the complete dump loaded)

Repair and conversion recovery evidence
---------------------------------------

Portfolio conclusion migration 0011 now streams pages and handles each live/latest
record independently. Replaying that historical migration does not repair an
already-applied database; see ``portfolio_wagtail.rst`` before planning a repair.

For missing rendition repair, preserve stderr and distinguish unchanged failures
from committed replacements with cache purge pending. Retry only those cache IDs
with ``regenerate_broken_renditions --retry-cache-purge``; see ``media_utils.rst``.
Cover import failures can retain uncertain storage names (including S3); inspect
references and object ownership before manual cleanup, as described in
``development.rst``. Never infer ownership solely from a prior exists check.

Weeknote conversion reports are atomically replaced from a unique sibling receipt.
If reporting fails after committed revisions, preserve the retained ``.pending``
file and stderr revision IDs before retrying. The old report describes the prior
run, not the partial new one; see ``weeknote_links.rst`` for recovery details.
