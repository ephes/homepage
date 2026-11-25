Replace
=======

Replace a file on s3 with a local version. Useful for compressed videos etc.:
 * uv run python manage.py s3_replace blogs_videos/cwdW8U8bQ16ahPa6h2mgSg.MOV

Regenerate missing renditions
=============================

When rendition files were deleted from s3, regenerate them for one or more blogs:
 * uv run python manage.py regenerate_broken_renditions ephes_blog other_blog

The command checks every post of each blog, including gallery images, and prints a
summary per post and per blog. Use ``--limit N`` to check only the newest ``N`` posts
of each blog; without it nothing is skipped. Before accessing storage, the command
checks that every requested slug identifies exactly one blog. After validation,
it scans each distinct blog once in first-argument order. If a slug is shared
across page trees, use the reported Wagtail page IDs and tree paths to identify
the intended blog in the admin. Repair by slug requires a unique blog slug.

The scan fetches direct images, galleries and gallery images in post batches of
up to 100. An image shared by direct slots, galleries, posts or requested blogs
is checked once per invocation, using its database alias and primary key.
Rendition queries and storage checks scale with unique images and their
renditions. The final ``checked images`` count
reports unique images attempted. Repair/error/cache-pending counts belong to the
first post/blog that encounters the image; later references add no duplicate
outcomes. Unknown and failed images are not retried within the same run. A new
invocation checks them again. Calling ``regenerate_renditions_for_post(post)``
directly still works and deduplicates that post's direct/gallery overlap; callers
may pass a shared ``seen_images`` set to extend that scope across posts.

A rendition is only regenerated when the storage backend reports that its file does
not exist. If the storage cannot answer (throttling, an outage, denied access), the
rendition is reported as ``unknown`` and neither deleted nor replaced. A missing
rendition keeps its database row: the new file is generated first and then attached
to that row. Before attachment the storage backend must confirm the saved
name exists and, when it exposes sizes, that the byte count matches the
generated file. A failed check leaves the row unchanged. Repairs use a distinct ``repair-<random-id>`` filename, preserving
existing storage objects. The row save runs inside a top-level database transaction,
so even a save hook that writes and then raises leaves the old row intact.

If verification or attachment fails, the command deletes the newly allocated file
only after establishing ownership and checking that no rendition row references it. A storage backend that returns a different name makes ownership
uncertain: that object is retained and its name is reported for recovery. Failed
reference checks or deletion also retain the primary error and report the cleanup
name/error. Inspect those named objects before removing them manually. An interrupted
process or a storage write that raises before returning a name can still leave an
object behind; this is compensation for reported save failures, not a crash-atomic
storage/database transaction. At attachment the rendition row is locked and its
observed file, image, filter, focal point and dimensions are compared with current
values. A concurrent replacement wins; the losing repair reports a conflict and
compensates its own unreferenced output. After the row comparison, the command
checks the original storage key again under the row lock. If the original file
has returned or storage cannot confirm absence, the row stays unchanged and the
same cleanup rules apply. External storage writers can still change an object
after that final check.

The command exits with an error when a rendition could not be checked or regenerated.
Those renditions are listed on stderr and left unchanged, so it is safe to simply run
the command again.

Cache invalidation runs after commit on the rendition’s database alias. If a
purge fails, the usable replacement stays committed and counts as regenerated.
Independent repairs continue.
The command exits nonzero and reports the database alias and ID for each
``cache purge pending`` rendition. The retry purges cache keys without allocating
files::

    uv run python manage.py regenerate_broken_renditions --retry-cache-purge 123 456 --database=default

Use the explicit ``--database`` alias reported by repair. The retry reads the
current rows on that alias and purges their cache keys. Group IDs by alias and
retry each alias separately. Deleted rows are reported and skipped. The retry
exits nonzero only for renewed purge failures and lists those IDs with the alias
for the next attempt. Retry accepts no blog slugs or limit.

Run the repair command and its helpers with autocommit enabled on the rendition
database. An open transaction causes repair to raise ``CommandError`` before
accessing rendition storage. Call the helper outside the transaction so each
replacement commits before its cache is purged.

Video width and height
======================

Print the width and height of a video, as ffprobe reports them, for a local file or a URL:
 * uv run python scripts/get_video_data.py path/to/video.mp4
 * uv run python scripts/get_video_data.py "https://media.example/video.mp4?signature=..."

The output is one line, ``<width> <height>``. A stream with a portrait display aspect
ratio is printed with its sides swapped.

The path or URL is passed to ``ffprobe`` as the value of ``-i`` in an argument list and
never through a shell. Quotes, spaces, ``$(...)`` and backticks are therefore plain text,
and a value starting with ``-`` is still the input. Use a path or URL you trust anyway:
ffprobe opens whatever it names.

Only the first video stream's width, height and display aspect ratio are requested from
ffprobe, as JSON. A file without a video stream has no size, whatever its name looks
like.

The input is never printed and ffprobe's own messages (which repeat it) are discarded, so
a signed URL does not end up in the terminal scrollback or in logs. Errors go to stderr
without the input and the exit status is 1: ffprobe missing, ffprobe failing, no video
stream with a size, or no answer within 60 seconds. Exactly one argument is expected
(exit status 2 otherwise).
