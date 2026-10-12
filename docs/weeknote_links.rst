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
revision is saved the command locks the page row, reads the page again and
compares its latest revision, its live revision, its live state and its body
with what the conversion was computed from. If an editor saved a draft,
published, unpublished or deleted the page in between, nothing is created or
published for that post: the report records ``skipped:
"changed_since_read"``, the summary counts it as skipped and a note on stderr
names the number of such posts. The revision that is saved is built from the
page read under the lock, so the editor's other fields are never replaced by
older values. Running the command again is safe: it starts from the current
content and converts the post, or skips it as ``has_unpublished_changes`` when
the editor left a draft.

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
