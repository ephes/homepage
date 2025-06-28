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
```

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
python manage.py test_micropub --title "My Post" --content "Post content"
```

## Handler Details

The `CastPostMicropubHandler` class:
- Creates posts in the "ephes_blog" by default
- Converts micropub properties to Post model fields
- Handles categories/tags
- Creates proper Wagtail revisions and log entries
- Publishes posts immediately

## Content Conversion

Supports:
- HTML content with allowed tags
- Plain text with automatic paragraph breaks
- Markdown-style code blocks (```language)
- Headings (# syntax in plain text)
- Photo URLs (converted to image HTML)
- Location data (formatted with OpenStreetMap links)
