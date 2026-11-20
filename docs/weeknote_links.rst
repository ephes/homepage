Weeknote Links Block
====================

Purpose
-------

``weeknote_links`` is a homepage-local Wagtail StreamField block for the
``overview`` section of weeknote posts. It replaces hand-authored rich-text
``h2`` + ``ul`` link sections with structured link data that can be validated,
rendered consistently across themes, and generated deterministically by daybook.

The logical author-facing value is a flat list of link items. Wagtail stores the
prepared ``ListBlock`` value with internal ``type: item`` wrappers and generated
item IDs, but clients should not construct that internal shape. Rendering groups
items by category in a fixed display order, so authors and automation do not
need to construct nested section objects.

Daybook author-facing JSON
--------------------------

django-cast supports configured custom ``CAST_POST_BODY_BLOCKS`` through the
editor API, so daybook emits the author-facing block shape below. The editor API
adapts this value through the configured Wagtail block's ``to_python()``,
``clean()``, and ``get_prep_value()`` path before storing it.

.. code-block:: json

   {
     "type": "weeknote_links",
     "value": [
       {
         "category": "articles",
         "kind": "article",
         "title": "Grid Security at Scale: How TenneT Built a 10x Faster Analysis Platform on PowSyBl",
         "url": "https://lfenergy.org/grid-security-at-scale-tennet-powsybl/",
         "source": "LF Energy",
         "source_url": "",
         "description": "<p>TenneT got a 10x speedup on grid security analysis by building ReFlow on top of the open-source PowSyBl framework.</p>"
       },
       {
         "category": "software",
         "kind": "link",
         "title": "p5.js",
         "url": "https://p5js.org/",
         "source": "",
         "source_url": "",
         "description": "<p>Friendly JavaScript library for creative coding.</p>"
       }
     ]
   }

Field mapping from daybook data:

* ``original_url`` -> ``url``
* ``title`` -> ``title``
* ``kind`` -> ``kind``
* ``source`` -> ``source``
* ``short_summary`` -> ``description`` as escaped rich-text HTML wrapped in a
  simple ``<p>...</p>`` paragraph when non-empty
* ``category`` -> ``category``; ``links`` is the valid fallback
* ``source_url`` -> ``source_url``; the key is required by automated Daybook
  output but its value may be ``""``

Validation constraints:

* ``weeknote_links`` requires at least one item.
* Every item must contain exactly ``category``, ``kind``, ``title``, ``url``,
  ``source``, ``source_url``, and ``description``. The four primary fields must
  be non-empty; ``source``, ``source_url``, and ``description`` may be empty
  strings subject to the constraint below.
* ``url`` and ``source_url`` must be valid URLs when present.
* ``source_url`` requires a non-empty ``source`` label.

Choices
-------

Category choices, in display order:

* ``articles`` — Articles
* ``software`` — Software
* ``videos`` — Videos
* ``podcasts`` — Podcasts
* ``social`` — Social
* ``weeknotes`` — Weeknotes
* ``books`` — Books
* ``papers`` — Papers
* ``links`` — Links

Rows already stored with retired category values appear together under
**Other links**, after the configured categories and in their original order.
New submissions must use a configured category.

Kind choices:

* ``article`` — Article
* ``video`` — Video
* ``podcast_episode`` — Podcast episode
* ``social_post`` — Social post
* ``link`` — Link

``kind`` is not used for grouping in the first version, but is rendered as a
CSS class hook and preserves machine-readable intent for future icons.

Legacy converter workflow
-------------------------

Use the ``convert_weeknote_links`` management command to convert existing
legacy weeknote rich-text sections. The command defaults to a safe dry run and
scopes to posts whose slug starts with ``weeknotes-``.

Dry run all candidate posts::

   uv run python manage.py convert_weeknote_links

Dry run one post::

   uv run python manage.py convert_weeknote_links --slug weeknotes-example

Write a JSON report while staying in dry-run mode::

   uv run python manage.py convert_weeknote_links --report /tmp/weeknote-links-report.json

Fail the command if any warnings are produced::

   uv run python manage.py convert_weeknote_links --fail-on-warnings

Create Wagtail draft revisions with converted bodies::

   uv run python manage.py convert_weeknote_links --write --report /tmp/weeknote-links-report.json

Publish converted live pages that do not already have unpublished changes::

   uv run python manage.py convert_weeknote_links --write --publish --report /tmp/weeknote-links-report.json

Publish converted pages without sending webmentions::

   uv run python manage.py convert_weeknote_links --write --publish --suppress-webmentions --report /tmp/weeknote-links-report.json

Pages that already have unpublished changes are skipped in write mode so the
command does not replace an editor's existing draft revision. The report records
these rows with ``skipped: "has_unpublished_changes"``.

The command also never writes over a page that changed while it was running.
The conversion of a post is computed from the page as it was read. Before the
revision is saved the command locks the page row and the rows of the page's
revisions, reads the page again and compares its latest revision, its live
revision, its live state and its body with what the conversion was computed
from. If an editor saved a draft, published, unpublished or deleted the page in
between, nothing is created or published for that post: the report records
``skipped: "changed_since_read"``, the summary counts it as skipped and a note
on stderr names the number of such posts. The revision that is saved is built
from the page read under the lock, so the editor's other fields are never
replaced by older values. Running the command again is safe: it starts from the
current content and converts the post, or skips it as
``has_unpublished_changes`` when the editor left a draft.

The command never waits for these locks. Wagtail locks the page row and its
revision rows in different orders depending on the action (overwriting a draft:
revision, then page; save and publish: page, then revisions), so a command that
waited for one while holding the other could deadlock with an editor and
PostgreSQL could abort the editor's save. The locks are requested with
``NOWAIT`` instead: a page that somebody is saving at that moment is reported
as ``changed_since_read`` too, and nothing is written for it. An editor save
that starts while the command holds the locks waits for the short moment in
which the revision is written and then completes. A new revision that another
database transaction has inserted but not committed yet cannot be seen; that
save completes afterwards and remains the latest revision.

Conversion limits
~~~~~~~~~~~~~~~~~

The converter never drops content it cannot represent. A heading and its list
are converted together or not at all; a refused section stays in the surrounding
rich-text paragraph exactly as written, in its original position, and the report
gets a warning with the section heading. A section is refused when:

* the heading is ambiguous (``Podcasts / Videos``) or the items fail block
  validation (for example a relative link);
* the heading holds anything but plain text, for example an image, a link,
  emphasis or an HTML comment (``<h2><img ...>Articles</h2>``). The block
  renders its category heading from a fixed label, so that markup could not be
  kept;
* the list holds anything but list items as direct children: text, another
  element such as a ``div`` or a link, or an HTML comment. Whitespace between
  items is fine;
* an item's primary link holds anything but plain text (an image, ``code``,
  emphasis, a comment): ``title`` is a plain-text field;
* an item has no primary link, rich markup before its primary link, or a
  description with markup other than ``a``, ``b``, ``strong``, ``i``, ``em`` and
  ``code``;
* the parenthesized source after the primary link is more than the ``source``
  and ``source_url`` fields can hold. Plain text (``(LF Energy)``) and exactly
  one link (``(<a href="...">Show</a>)``) are converted. Several links, text
  next to a link (``(via <a ...>Show</a>)``) or other markup inside the
  parentheses keep the section as HTML, so every source link stays clickable.

Fix the source HTML in the Wagtail editor (or leave the section as rich text)
and run the command again; it picks up the legacy sections that are left.

Recommended workflow:

1. Run a dry run and inspect the summary.
2. Run again with ``--report`` and review which posts changed, how many
   sections were converted, skipped posts, and any warnings.
3. Use ``--fail-on-warnings`` in scripted checks when a clean conversion is
   required.
4. Run ``--write`` only after the dry-run report is understood.
5. Add ``--publish`` only when converted live pages should be published
   immediately. Without ``--publish``, live pages receive draft revisions.
6. Add ``--suppress-webmentions`` for maintenance publishes of old posts where
   sending webmentions again would be noisy.

The command writes through Wagtail revisions. It records ``changed``,
``revision_id``, ``published``, and ``skipped`` per post in the JSON report.
``skipped`` is empty for a saved conversion, otherwise
``has_unpublished_changes`` or ``changed_since_read``.

Editor API round-trip
---------------------

Homepage's django-cast dependency includes editor API support for custom blocks
configured through ``CAST_POST_BODY_BLOCKS``. Daybook can send the author-facing
JSON shape above; the editor API validates and prepares it through the Wagtail
block API and returns the same logical value without exposing internal
``ListBlock`` item wrappers.

Bounded runs and continuation
-----------------------------

Each invocation processes at most 100 posts, 16 MiB of stored JSON body bytes and
4 MiB of receipt data (including reserved save-result space). Override these
positive limits with ``--max-posts``, ``--max-body-bytes`` and
``--max-report-bytes``. Bodies are size-checked by PostgreSQL before hydration;
only one eligible Post is hydrated at a time, without an ORM result cache. The
same size guard applies to the locked conflict recheck. Conversion copies and
warnings are bounded by the admitted body work; retained receipts by both the
post and receipt budgets.

Traversal uses increasing page IDs, with the initial maximum eligible ID as a
fixed inclusive boundary (never below ``--after-pk``). It no longer uses
publication dates. On a budget
boundary the command publishes the completed per-invocation report, prints
``Partial run`` with ``--after-pk N --through-pk M``, and exits nonzero. Repeat the
same scope/write/publish/suppression flags with that continuation, keeping each
report under a separate name. Every processed receipt includes ``page_id`` and
``through_pk``; no receipt is emitted for an unprocessed page. A completed run
explicitly says ``Complete through page ID M``. Concurrent inserts above M belong
to a later run; this ID boundary is not a content snapshot.

If the next body or receipt cannot fit even in a fresh invocation, increase the
relevant budget explicitly or inspect that post separately with ``--slug``.
Never advance past an unprocessed page to make a run appear complete. Existing
conflict/draft skips remain in the report: revisit those separately, since
continuation moves past every processed page, including skips and warnings.

Report publication and interrupted runs
---------------------------------------

With ``--report``, the command creates a unique private sibling ``.journal``
(0600), writes a versioned header and flushes/fsyncs it before database changes.
Each completed page appends one newline-framed JSON record, then flushes/fsyncs
its revision ID and publication result. Header, page and outcome records are
command-specific UTF-8 JSONL; embedded newlines are JSON-escaped. Work is linear
in completed receipt bytes, without rewriting the growing prefix. The bounded
report list is serialized once at completion to a separate sibling ``.pending``
file, fsynced, closed and atomically replaced over the target. Published reports
remain JSON arrays and retain the previous report's mode or the umask-derived
creation mode. Successful publication removes the redundant journal.

On a handled conversion, write, flush, close or replace failure, the existing
report survives. The command exits nonzero, retains the journal (and any staged
JSON), and prints every committed revision ID, slug and publication flag on
stderr, including a commit whose checkpoint failed. Database changes already
committed are not undone. Preserve stderr together with the journal. A hard kill
between database commit and journal fsync can leave an unacknowledged revision;
inspect the page's revisions before retrying that boundary. There is no atomic
transaction spanning PostgreSQL and a local file.

Recover completed receipts without querying, saving or publishing posts::

   uv run python manage.py convert_weeknote_links --recover-receipt /tmp/.report.json.UNIQUE.journal --report /tmp/recovered.json

Recovery validates the format, increasing page IDs, fixed upper bound, outcome
and invocation post/receipt budgets (page frames against ``--max-report-bytes``;
header and outcome frames get a fixed 64 KiB allowance), then atomically
publishes the same JSON array.
Increase ``--max-posts``/``--max-report-bytes`` explicitly if the original run used
larger budgets. The original journal remains untouched. Recovery prints the
original scope/write/publish flags, status and exact continuation IDs. A missing
outcome is explicitly partial; recovery never replays conversions. A complete
outcome means traversal finished, not that every conflict/draft/warning was fixed.

An incomplete final frame, invalid sequence or oversized journal is refused
before replacing the report. Keep the original, inspect complete newline frames
and stderr/revisions, and if needed make a separate verified copy containing only
complete frames before recovery. Do not silently discard a tail or infer that an
unacknowledged revision was never committed. Continuation skips processed page
IDs, so revisit conflicts and drafts separately and inspect the first unprocessed
page after an interrupted run before using ``--write --publish`` again.
