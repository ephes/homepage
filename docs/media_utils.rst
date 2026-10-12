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
of each blog; without it nothing is skipped.

A rendition is only regenerated when the storage backend reports that its file does
not exist. If the storage cannot answer (throttling, an outage, denied access), the
rendition is reported as ``unknown`` and neither deleted nor replaced. A missing
rendition keeps its database row: the new file is generated first and then attached
to that row, so a failed regeneration changes nothing.

The command exits with an error when a rendition could not be checked or regenerated.
Those renditions are listed on stderr and left unchanged, so it is safe to simply run
the command again.
