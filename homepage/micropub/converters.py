"""
Content converters for micropub to django-cast StreamField.

This module provides utilities to convert various micropub content types
into appropriate Wagtail StreamField blocks.
"""

import re
from typing import Any

try:
    import bleach
except ImportError:
    bleach = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class ContentConverter:
    """Convert micropub content to StreamField blocks."""

    # Allowed HTML tags for rich text content
    ALLOWED_TAGS = [
        "p",
        "br",
        "strong",
        "em",
        "b",
        "i",
        "u",
        "a",
        "h2",
        "h3",
        "h4",
        "ul",
        "ol",
        "li",
        "blockquote",
        "pre",
        "code",
        "hr",
    ]

    ALLOWED_ATTRIBUTES = {
        "a": ["href", "title", "target", "rel"],
        "code": ["class"],
    }

    def __init__(self):
        self.code_pattern = re.compile(r"```(\w*)\n(.*?)\n```", re.DOTALL)

    def convert_content(self, content: str, properties: dict[str, list[Any]]) -> list[tuple[str, Any]]:
        """
        Convert micropub content to StreamField blocks.

        Args:
            content: The main content (HTML or plain text)
            properties: Full micropub properties for additional data

        Returns:
            List of (block_type, value) tuples for StreamField
        """
        blocks = []

        # Handle photos first if present
        photos = properties.get("photo", [])
        if photos and photos[0]:
            # Add photo as first block if it's a photo post
            blocks.extend(self._convert_photos(photos))

        # Process main content
        if content:
            blocks.extend(self._process_content(content))

        # Handle location if present
        location = properties.get("location", [])
        if location and location[0]:
            blocks.append(("paragraph", self._format_location(location[0])))

        return blocks

    def _process_content(self, content: str) -> list[tuple[str, Any]]:
        """Process content and convert to appropriate blocks."""
        blocks = []

        # Detect if content is HTML
        if self._is_html(content):
            blocks.extend(self._convert_html_to_blocks(content))
        else:
            # Handle plain text with potential markdown-style code blocks
            blocks.extend(self._convert_plain_text_to_blocks(content))

        return blocks

    def _is_html(self, content: str) -> bool:
        """Check if content appears to be HTML."""
        html_indicators = ["<p>", "<br", "<div", "<h", "<ul", "<ol", "<blockquote"]
        return any(indicator in content.lower() for indicator in html_indicators)

    def _convert_html_to_blocks(self, html: str) -> list[tuple[str, Any]]:
        """Convert HTML content to StreamField blocks."""
        blocks = []

        # Clean the HTML if bleach is available
        if bleach:
            clean_html = bleach.clean(html, tags=self.ALLOWED_TAGS, attributes=self.ALLOWED_ATTRIBUTES, strip=True)
        else:
            # If bleach is not available, use the HTML as-is (less secure)
            clean_html = html

        # Parse with BeautifulSoup if available
        if BeautifulSoup is None:
            # Fallback: treat as rich text block
            blocks.append(("paragraph", clean_html))
            return blocks

        soup = BeautifulSoup(clean_html, "html.parser")

        # Process top-level elements
        for element in soup.children:
            if hasattr(element, "name"):
                block = self._element_to_block(element)
                if block:
                    blocks.append(block)
            elif element.strip():
                # Plain text node
                blocks.append(("paragraph", f"<p>{element.strip()}</p>"))

        return blocks

    def _element_to_block(self, element) -> tuple[str, Any] | None:
        """Convert a BeautifulSoup element to a StreamField block."""
        if element.name in ["h2", "h3", "h4"]:
            return ("heading", element.get_text().strip())
        elif element.name == "pre":
            # Code block
            code_element = element.find("code")
            if code_element:
                language = ""
                if code_element.get("class"):
                    # Extract language from class like 'language-python'
                    classes = code_element.get("class", [])
                    for cls in classes:
                        if cls.startswith("language-"):
                            language = cls[9:]
                            break

                return ("code", {"language": language, "code": code_element.get_text().strip()})
            else:
                return ("code", {"language": "", "code": element.get_text().strip()})
        elif element.name == "blockquote":
            # Convert blockquote to rich text
            return ("paragraph", str(element))
        elif element.name in ["p", "ul", "ol"]:
            # Rich text blocks
            return ("paragraph", str(element))

        return None

    def _convert_plain_text_to_blocks(self, text: str) -> list[tuple[str, Any]]:
        """Convert plain text to StreamField blocks."""
        blocks = []

        # First, extract code blocks
        parts = []
        last_end = 0

        for match in self.code_pattern.finditer(text):
            # Add text before code block
            if match.start() > last_end:
                parts.append(("text", text[last_end : match.start()]))  # noqa: E203

            # Add code block
            language = match.group(1) or ""
            code = match.group(2).strip()
            parts.append(("code", {"language": language, "code": code}))

            last_end = match.end()

        # Add remaining text
        if last_end < len(text):
            parts.append(("text", text[last_end:]))

        # Process parts
        for part_type, content in parts:
            if part_type == "code":
                blocks.append(("code", content))
            else:
                # Split text into paragraphs
                paragraphs = content.strip().split("\n\n")
                for para in paragraphs:
                    if para.strip():
                        # Check if it's a heading (starts with #)
                        if para.startswith("#"):
                            heading_match = re.match(r"^(#{1,4})\s+(.+)$", para)
                            if heading_match:
                                heading_text = heading_match.group(2)
                                blocks.append(("heading", heading_text))
                                continue

                        # Regular paragraph
                        # Convert line breaks to <br>
                        formatted_para = para.strip().replace("\n", "<br>")
                        blocks.append(("paragraph", f"<p>{formatted_para}</p>"))

        return blocks

    def _convert_photos(self, photos: list[str]) -> list[tuple[str, Any]]:
        """Convert photo URLs to image blocks."""
        blocks = []

        for photo_url in photos:
            if isinstance(photo_url, str) and photo_url.strip():
                # For now, we'll add a paragraph with the image
                # In production, you'd want to download and create Image objects
                blocks.append(("paragraph", f'<p><img src="{photo_url}" alt="Photo from micropub"></p>'))

        return blocks

    def _format_location(self, location: Any) -> str:
        """Format location data for display."""
        if isinstance(location, dict):
            # h-geo or geo URI format
            if "latitude" in location and "longitude" in location:
                lat = location["latitude"]
                lon = location["longitude"]
                name = location.get("name", f"{lat}, {lon}")
                return (
                    f'<p>📍 <a href="https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=15/{lat}/{lon}">{name}'
                    f"</a></p>"
                )
            elif "properties" in location:
                # h-geo microformat
                props = location["properties"]
                lat = props.get("latitude", [None])[0]
                lon = props.get("longitude", [None])[0]
                name = props.get("name", [f"{lat}, {lon}"])[0]
                if lat and lon:
                    return (
                        f'<p>📍 <a href="https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=15/{lat}/{lon}">'
                        f"{name}</a></p>"
                    )
        elif isinstance(location, str):
            # Check if it's a geo URI
            if location.startswith("geo:"):
                parts = location[4:].split(",")
                if len(parts) >= 2:
                    lat, lon = parts[0], parts[1].split(";")[0]
                    return (
                        f'<p>📍 <a href="https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=15/{lat}/{lon}">'
                        "Location</a></p>"
                    )
            else:
                # Plain text location
                return f"<p>📍 {location}</p>"

        return f"<p>📍 {str(location)}</p>"
