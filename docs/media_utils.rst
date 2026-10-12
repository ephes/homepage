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
