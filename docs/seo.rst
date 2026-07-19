Search and Social Metadata
==========================

Blog posts
----------

Homepage uses django-cast's Bootstrap 5 post template contract. Post metadata is
owned by the Wagtail page and rendered as follows:

* ``seo_title`` supplies the HTML title, Open Graph title, Twitter title, and
  ``BlogPosting`` headline; the page title is the fallback.
* ``search_description`` supplies the standard, Open Graph, Twitter, and
  ``BlogPosting`` descriptions; the page title is the fallback.
* ``cover_image`` supplies a focal-point-aware 1200x630 JPEG. The parent blog
  cover is the fallback when a post has no cover.
* Post pages emit a canonical URL, ``og:site_name``, article publication and
  modification times, and ``BlogPosting`` JSON-LD.
* The ephes blog adds ``twitter:creator=@ephes`` locally. Generic django-cast
  themes do not hard-code a site account.

The deployed django-cast 0.2.64 lock accepts ``seo_title`` and
``search_description`` on post and episode create/update and returns them on
reads. Homepage's matching cast-bootstrap5 templates expose that contract in
production, and Daybook's validated metadata sidecar delivers the owned
weeknote fields with the draft overview.

Authoring guidance
------------------

Use the visible post title as ``seo_title`` unless a long themed title needs a
faithful shorter form. Write ``search_description`` as one or two plain-text
sentences describing the main theme; roughly 140–170 characters is a useful
target. Do not paste the whole opening section into the description.

Covers are optional. Prefer a representative image already used by the post;
otherwise use an intentional rendered-preview capture or the blog-level
fallback. Always provide useful alt text for a post-specific cover.

Verification
------------

After deployment, inspect the rendered ``<head>`` on staging and verify that:

* title and description tags are non-empty;
* there is exactly one canonical URL;
* image tags use absolute URLs and report 1200x630 dimensions;
* no empty ``og:image`` or ``twitter:image`` tag is emitted;
* ``article:published_time`` and ``article:modified_time`` are ISO 8601 values;
* the ``application/ld+json`` block parses as JSON and identifies a
  ``BlogPosting``; and
* unlisted family posts retain their inherited ``noindex`` directive.
