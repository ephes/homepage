# Micropub Integration for Django-Cast

This Django app provides a Micropub handler for creating blog posts in django-cast via the IndieWeb Micropub protocol.

## Features

- **Micropub Handler**: Converts Micropub requests to django-cast Post objects
- **Content Conversion**: Handles various content types (HTML, plain text, markdown-style code blocks)
- **StreamField Integration**: Creates proper Wagtail StreamField blocks
- **Local Form Interface**: Web form for testing Micropub posting without external clients
- **Management Command**: Create posts from the command line

## URL Structure

The app integrates with both django-indieweb and provides its own local interface:

- `/indieweb/micropub/` - The Micropub API endpoint (provided by django-indieweb)
- `/indieweb/micropub-form/` - Local form interface for creating posts
- `/indieweb/micropub-form/preview/` - Preview endpoint for content conversion

## Configuration

Add to your Django settings:

```python
# Micropub handler configuration
INDIEWEB_MICROPUB_HANDLER = "homepage.micropub.handler.CastPostMicropubHandler"

# Your site URL (for local development)
INDIEWEB_ME_URL = env("INDIEWEB_ME_URL", default="http://localhost:8000")

# Blog (slug) used when a client does not select one via mp-channel
MICROPUB_DEFAULT_BLOG_SLUG = env("MICROPUB_DEFAULT_BLOG_SLUG", default="ephes_blog")
```

## Target Blog and Permissions

Every post goes into an explicitly determined blog:

- Clients select a blog with the `mp-channel` property (Micropub channels
  extension), using a blog slug. `GET /indieweb/micropub/?q=channel` (and
  `q=config`) lists the blogs the token owner may publish into.
- Without `mp-channel`, the blog named by `MICROPUB_DEFAULT_BLOG_SLUG` is used.
  There is no fallback to some other blog: an unknown, non-live or ambiguous
  slug rejects the request.
- The local form shows a blog selector limited to the same publishable blogs.

The posting user (the token owner for IndieAuth requests) needs the Wagtail
page permissions to **add and publish** pages below the target blog
(`can_add_subpage` and `can_publish_subpage`, granted via group page
permissions in the Wagtail admin, or as a superuser). Inactive users never
qualify. Rejected requests create nothing; the Micropub endpoint answers them
with `400 invalid_request` (django-indieweb maps handler `ValueError`s to that
response), and the form shows a generic error message.

`q=source` lookups resolve the URL through the Wagtail page tree and require
Wagtail **edit** permission on the post (not mere ownership).

Only creating posts and `q=source` lookups are supported. The Micropub
`update`, `delete` and `undelete` actions are rejected with
`400 invalid_request` and change nothing (the handler raises `ValueError`, so
clients do not report a success that did not happen). Edit or unpublish posts
in the Wagtail admin instead.

## Usage

### Via Micropub Clients

Use any Micropub client (like Quill, Indigenous, etc.) with:
- Endpoint: `https://yoursite.com/indieweb/micropub/`
- Authentication: IndieAuth

### Via Local Form

1. Navigate to `/indieweb/micropub-form/`
2. Choose post type (note or article)
3. Fill in content and optional fields
4. Click "Publish"

### Via Management Command

```bash
python manage.py test_micropub --title "My Post" --content "Post content" [--blog ephes_blog]
```

## Handler Details

The `CastPostMicropubHandler` class:
- Creates posts in the blog selected via `mp-channel`, or `MICROPUB_DEFAULT_BLOG_SLUG`
- Enforces Wagtail add + publish page permissions on the target blog
- Converts micropub properties to Post model fields
- Handles categories/tags
- Creates proper Wagtail revisions and log entries
- Publishes posts immediately
- Rejects `update`, `delete` and `undelete` with `ValueError` (not supported)

## Content Conversion

Supports:
- HTML content with allowed tags
- Plain text with automatic paragraph breaks
- Markdown-style code blocks (```language)
- Headings (# syntax in plain text)
- Photo URLs (converted to image HTML)
- Location data (formatted with OpenStreetMap links)

All paragraph HTML (from HTML input, plain text, photos and locations) is
sanitized with `nh3`, a runtime dependency, against the converter's tag
allow-list before it is stored; scripts, event handlers and `javascript:` URLs
are removed. There is no unsanitized fallback.

The preview page (`/indieweb/micropub-form/preview/`) escapes code blocks and
sanitizes paragraph HTML against the converter's tag allow-list before
rendering; form messages are rendered with autoescaping.
