IndieWeb: Micropub and Webmention
=================================

Micropub publishing
-------------------

Posts created through the Micropub endpoint (``/indieweb/micropub/``, IndieAuth
token) and the local form (``/indieweb/micropub-form/``) both go through
``homepage.micropub.handler.CastPostMicropubHandler``.

Target blog
   Clients choose the blog with the ``mp-channel`` property, using the blog slug.
   ``q=channel`` / ``q=config`` list the blogs the token owner may publish into.
   Without ``mp-channel`` the blog named by ``MICROPUB_DEFAULT_BLOG_SLUG``
   (environment variable, default ``ephes_blog``) is used. There is no fallback
   to another blog; an unknown, non-live or ambiguous slug rejects the request.
   The local form offers a blog selector limited to publishable blogs (blogs
   whose slug is shared by another live blog are never offered).

Permissions
   The posting user needs Wagtail page permission to add *and* publish pages
   below the target blog (grant ``Add`` and ``Publish`` on the blog via a group
   in the Wagtail admin, or be a superuser). Inactive users never qualify.
   Rejected requests create nothing; the endpoint answers ``400
   invalid_request`` and the form shows a generic error without exception text.

Publication
   A Micropub post is published the way the Wagtail admin publishes a page:
   body and categories are applied first, **one** revision is saved, and that
   revision goes live through Wagtail's revision API (``revision.publish()``).
   The live revision therefore contains the tags, so restoring or republishing
   it keeps them, and the usual publication effects run exactly once: the
   ``wagtail.publish`` log entry, the ``page_published`` signal and with it
   django-cast's media preparation and the outgoing webmentions of
   ``homepage.core.webmention_integration`` (see `Outgoing webmentions`_).
   Everything except the webmention delivery runs in one transaction. If a
   category is not text, tags cannot be applied or the publication is refused,
   nothing is created, no webmention is sent and the endpoint answers ``400
   invalid_request`` (or ``500`` for an unexpected error).

Logging
   The endpoint is authenticated and receives private text, so property
   **values** never reach the logs: no content, title, slug, category, photo URL
   or channel value, and no exception text or traceback that could quote them.
   The handler logs the names of the known properties it received (unknown
   names only as a count), the number of categories and photos, the ids of the
   created post and its blog, and for a failure the exception class
   (``Micropub create failed: MicropubTargetError``). django-indieweb logs the
   message of a rejected request and the traceback of an unexpected error, so
   the handler lets only its own errors (fixed messages) through and replaces
   every other exception with one that names the original class and carries no
   message, cause or context: ``MicropubContentError`` for a ``ValueError``
   (``400``), ``MicropubInternalError`` otherwise (``500``). There is no
   setting that turns payload logging on. The webmention diagnostics name the
   published page by id and each target reduced to scheme, host and path,
   without query string, fragment, credentials or error text. Wagtail's own
   ``INFO`` lines for a created or published page contain the page title, as
   they do for pages handled in the admin; production logs from ``WARNING`` up.

Photos
   ``photo`` values are URL strings. django-indieweb rejects anything else
   (including ``{"value": ..., "alt": ...}`` objects) with ``400
   invalid_request`` before the handler runs, so a photo is never dropped
   silently.

Content sanitization
   The content converter sanitizes every paragraph block with ``nh3`` (a
   runtime dependency) against its tag allow-list before storing it; there is
   no fallback that stores unsanitized HTML.

Source queries
   ``q=source&url=...`` resolves the URL through the Wagtail page tree (using
   Wagtail's hostname/port site selection and the percent-decoded path) and
   returns the post only when the token owner has Wagtail edit permission on it.

Unsupported actions
   Only creating posts and ``q=source`` lookups are supported. The Micropub
   ``update``, ``delete`` and ``undelete`` actions are rejected with ``400
   invalid_request`` and change nothing, so clients such as Quill no longer
   report a deletion that did not happen. Edit or unpublish posts in the
   Wagtail admin instead.

Outgoing webmentions
--------------------

Publishing a django-cast ``Post`` or ``Episode`` sends webmentions to the
external URLs its content links to
(``homepage.core.webmention_integration``, on Wagtail's ``page_published``
signal). A webmention tells a third-party endpoint the URL of the page and that
the page links to it, so two rules apply:

Only public pages
   A page with a Wagtail view restriction (login, password or group) is never
   announced. The restriction can sit on the page itself or on any ancestor,
   for example a private blog. Such a page is not rendered for link discovery
   and no request leaves the server. Publishing it again after the restriction
   has been removed sends its webmentions; removing the restriction alone does
   not.

Only committed publications
   The ``page_published`` receiver does not render or send anything itself. It
   registers the delivery with ``transaction.on_commit``, and the delivery runs
   in the same process when the outermost database transaction that is open at
   that moment commits; no queue is involved. For a publication inside a
   transaction this means that nothing is rendered or sent before the commit.
   Which transaction that is depends on the caller, not on this module:

   * a Micropub post is published inside the handler's own transaction, so its
     webmentions leave after that transaction has committed;
   * with ``ATOMIC_REQUESTS`` (the default in ``config/settings/base.py``, used
     for local development and tests) it is the request;
   * ``config/settings/production.py`` replaces the database setting and does
     not set ``ATOMIC_REQUESTS``, so in production it is the transaction the
     publishing code itself opened, and the delivery can run before the admin
     request has finished;
   * when no transaction is open at all (autocommit), ``on_commit`` calls the
     delivery at once, so it runs inside the signal receiver, after Wagtail has
     saved the page as live. There is nothing left to roll back in that case.

   A publication that is rolled back announces nothing. At delivery time the
   page is read again from the database and is skipped when it was deleted,
   unpublished, restricted or replaced by a newer live revision in the
   meantime (the newer publication has its own delivery).

Delivery is best effort. A failure while rendering or sending does not fail or
undo the publication: it is logged as
``Webmention delivery failed for page <id>: <exception class>`` at ``WARNING``
and there is no automatic retry. Publish the page again to resend.

Webmention targets
------------------

``homepage.webmention_config.CastURLResolver`` accepts targets on the current
site's domain (``localhost:8000`` when the Django site domain is ``localhost``):

* ``/jochen/`` – the personal page (the view returns 404 while no ``jochen``
  user exists).
* ``/blogs/{blog}/`` – the blog, if it is a live, public child of the Wagtail
  site root.
* ``/blogs/{blog}/{post}/`` (and sub-routes such as ``.../transcript/``) – the
  live, public post with that slug *below that blog*.

Drafts, pages with view restrictions (or below restricted pages), and posts
with the same slug in another blog are not valid targets.

Displaying webmentions
----------------------

The templates in ``homepage/templates/indieweb/webmention_types/`` override
django-indieweb's per-type templates (like, reply, repost, mention). Like the
upstream templates, they must keep this policy for remote content:

* Every link to a remote author or source URL carries
  ``rel="nofollow noopener ugc"`` and ``referrerpolicy="no-referrer"``, so
  visitors' post URLs are not sent to the remote site.
* Every remote avatar ``<img>`` carries ``referrerpolicy="no-referrer"`` and
  ``loading="lazy"``, so the avatar host does not learn which post is viewed.

``homepage/tests/test_webmentions.py`` renders each override and fails if a
remote link or avatar lacks these attributes.
