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

Source queries
   ``q=source&url=...`` resolves the URL through the Wagtail page tree (using
   Wagtail's hostname/port site selection and the percent-decoded path) and
   returns the post only when the token owner has Wagtail edit permission on it.

Webmention targets
------------------

``homepage.webmention_config.CastURLResolver`` accepts targets on the current
site's domain (``localhost:8000`` when the Django site domain is ``localhost``):

* ``/jochen/`` – the personal page.
* ``/blogs/{blog}/`` – the blog, if it is a live, public child of the Wagtail
  site root.
* ``/blogs/{blog}/{post}/`` (and sub-routes such as ``.../transcript/``) – the
  live, public post with that slug *below that blog*.

Drafts, pages with view restrictions (or below restricted pages), and posts
with the same slug in another blog are not valid targets.
