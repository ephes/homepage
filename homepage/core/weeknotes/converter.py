from __future__ import annotations

import html
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag
from django.core.exceptions import ValidationError

from .blocks import WeeknoteLinksBlock

HEADING_ALIASES = {
    "articles": "articles",
    "software": "software",
    "open source": "software",
    "videos": "videos",
    "youtube": "videos",
    "lectures": "videos",
    "podcasts": "podcasts",
    "mastodon": "social",
    "twitter": "social",
    "mastodon / twitter": "social",
    "weeknotes": "weeknotes",
    "weeklogs": "weeknotes",
    "books": "books",
    "papers": "papers",
    "links": "links",
}
AMBIGUOUS_HEADINGS = {"podcasts / videos", "videos / podcasts"}
ALLOWED_DESCRIPTION_TAGS = {"a", "b", "strong", "i", "em", "code"}
SEPARATOR_RE = re.compile(r"^(?:\s|&nbsp;)*(?:[|]|[-–—])(?:\s|&nbsp;)*")


@dataclass
class ConversionWarning:
    message: str
    heading: str = ""


@dataclass
class OverviewConversion:
    blocks: list[dict[str, Any]]
    changed: bool
    converted_sections: int = 0
    warnings: list[ConversionWarning] = field(default_factory=list)


@dataclass
class BodyConversion:
    body: list[dict[str, Any]]
    changed: bool
    converted_sections: int = 0
    warnings: list[ConversionWarning] = field(default_factory=list)


def convert_body(body: list[dict[str, Any]]) -> BodyConversion:
    """Convert legacy weeknote link sections in overview blocks."""
    changed = False
    converted_sections = 0
    warnings: list[ConversionWarning] = []
    converted_body: list[dict[str, Any]] = []

    for section in body:
        if section.get("type") != "overview" or not isinstance(section.get("value"), list):
            converted_body.append(section)
            continue
        conversion = convert_overview_blocks(section["value"])
        warnings.extend(conversion.warnings)
        converted_sections += conversion.converted_sections
        if conversion.changed:
            changed = True
            converted_section = dict(section)
            converted_section["value"] = conversion.blocks
            converted_body.append(converted_section)
        else:
            converted_body.append(section)

    return BodyConversion(
        body=converted_body,
        changed=changed,
        converted_sections=converted_sections,
        warnings=warnings,
    )


def convert_overview_blocks(blocks: list[dict[str, Any]]) -> OverviewConversion:
    converted: list[dict[str, Any]] = []
    changed = False
    converted_sections = 0
    warnings: list[ConversionWarning] = []

    for block in blocks:
        if block.get("type") != "paragraph" or not isinstance(block.get("value"), str):
            converted.append(block)
            continue
        paragraph_conversion = convert_paragraph_html(block["value"])
        warnings.extend(paragraph_conversion.warnings)
        converted_sections += paragraph_conversion.converted_sections
        if paragraph_conversion.changed:
            changed = True
            converted.extend(paragraph_conversion.blocks)
        else:
            converted.append(block)

    return OverviewConversion(
        blocks=converted,
        changed=changed,
        converted_sections=converted_sections,
        warnings=warnings,
    )


def convert_paragraph_html(source_html: str) -> OverviewConversion:
    soup = BeautifulSoup(source_html, "html.parser")
    nodes = list(soup.contents)
    output: list[dict[str, Any]] = []
    pending_html: list[str] = []
    pending_links: list[dict[str, Any]] = []
    warnings: list[ConversionWarning] = []
    changed = False
    converted_sections = 0
    index = 0

    def flush_html() -> None:
        html_fragment = "".join(pending_html).strip()
        pending_html.clear()
        if html_fragment:
            output.append(_block("paragraph", html_fragment))

    def flush_links() -> None:
        if not pending_links:
            return
        output.append(_block("weeknote_links", _prepared_weeknote_links(pending_links)))
        pending_links.clear()

    while index < len(nodes):
        node = nodes[index]
        if _is_blank_text(node):
            if pending_html:
                pending_html.append(str(node))
            index += 1
            continue

        next_index, next_node = _next_meaningful_node(nodes, index + 1)
        if _is_heading(node) and isinstance(next_node, Tag) and next_node.name == "ul":
            heading = _normalized_text(node)
            if heading.lower() in AMBIGUOUS_HEADINGS:
                flush_links()
                pending_html.append(str(node))
                pending_html.append(str(next_node))
                warnings.append(ConversionWarning("Ambiguous link heading preserved.", heading=heading))
                index = next_index + 1
                continue
            category = HEADING_ALIASES.get(heading.lower())
            if category is None:
                flush_links()
                pending_html.append(str(node))
                index += 1
                continue

            section = _convert_list(next_node, category=category, heading=heading)
            if section.warnings:
                flush_links()
                pending_html.append(str(node))
                pending_html.append(str(next_node))
                warnings.extend(section.warnings)
                index = next_index + 1
                continue
            validation_warning = _validation_warning(section.items, heading=heading)
            if validation_warning is not None:
                flush_links()
                pending_html.append(str(node))
                pending_html.append(str(next_node))
                warnings.append(validation_warning)
                index = next_index + 1
                continue

            flush_html()
            pending_links.extend(section.items)
            changed = True
            converted_sections += 1
            index = next_index + 1
            continue

        flush_links()
        pending_html.append(str(node))
        index += 1

    flush_html()
    flush_links()

    if not changed:
        return OverviewConversion(blocks=[], changed=False, warnings=warnings)
    return OverviewConversion(
        blocks=output,
        changed=True,
        converted_sections=converted_sections,
        warnings=warnings,
    )


@dataclass
class _ListConversion:
    items: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[ConversionWarning] = field(default_factory=list)


def _convert_list(ul: Tag, *, category: str, heading: str) -> _ListConversion:
    items: list[dict[str, Any]] = []
    warnings: list[ConversionWarning] = []
    list_items = [li for li in ul.find_all("li", recursive=False)]
    if not list_items:
        return _ListConversion(warnings=[ConversionWarning("List section has no direct list items.", heading=heading)])

    for li in list_items:
        item = _convert_list_item(li, category=category, heading=heading)
        if isinstance(item, ConversionWarning):
            warnings.append(item)
            continue
        items.append(item)
    return _ListConversion(items=items, warnings=warnings)


def _convert_list_item(li: Tag, *, category: str, heading: str) -> dict[str, Any] | ConversionWarning:
    primary_link = li.find("a")
    if primary_link is None or not primary_link.get("href"):
        return ConversionWarning("List item has no primary link.", heading=heading)

    prefix_html, after_html = _split_around_primary_link(li, primary_link)
    prefix_text = BeautifulSoup(prefix_html, "html.parser").get_text(" ", strip=True)
    title = primary_link.get_text(" ", strip=True)
    if prefix_text:
        if "<" in prefix_html:
            return ConversionWarning("List item has rich prefix before primary link.", heading=heading)
        title = f"{prefix_text} {title}".strip()

    source, source_url, rest_html = _extract_source(after_html)
    description = _extract_description(rest_html)
    if description is None:
        return ConversionWarning("List item description uses unsupported rich markup.", heading=heading)

    return {
        "category": category,
        "kind": _kind_for_category(category),
        "title": title,
        "url": primary_link["href"],
        "source": source,
        "source_url": source_url,
        "description": description,
    }


def _split_around_primary_link(li: Tag, primary_link: Tag) -> tuple[str, str]:
    before: list[str] = []
    after: list[str] = []
    seen_primary = False
    for child in li.contents:
        if child is primary_link:
            seen_primary = True
            continue
        if seen_primary:
            after.append(str(child))
        else:
            before.append(str(child))
    return "".join(before), "".join(after)


def _extract_source(after_html: str) -> tuple[str, str, str]:
    soup = BeautifulSoup(after_html, "html.parser")
    contents = list(soup.contents)
    first_index = _first_nonblank_index(contents)
    if first_index is None:
        return "", "", after_html

    first = contents[first_index]
    if not isinstance(first, NavigableString) or "(" not in str(first):
        return "", "", after_html

    before_open, source_text = str(first).split("(", 1)
    if before_open.strip():
        return "", "", after_html

    source_parts: list[str] = []
    rest_parts: list[str] = [str(node) for node in contents[:first_index]]
    source_end_search_start = first_index + 1
    if ")" in source_text:
        source_before_close, rest_after_close = source_text.split(")", 1)
        source_parts.append(source_before_close)
        rest_parts.append(rest_after_close)
        rest_parts.extend(str(node) for node in contents[source_end_search_start:])
    else:
        source_parts.append(source_text)
        closed = False
        for node in contents[source_end_search_start:]:
            if not closed and isinstance(node, NavigableString) and ")" in str(node):
                source_before_close, rest_after_close = str(node).split(")", 1)
                source_parts.append(source_before_close)
                rest_parts.append(rest_after_close)
                closed = True
                continue
            if closed:
                rest_parts.append(str(node))
            else:
                source_parts.append(str(node))
        if not closed:
            return "", "", after_html

    source_html = "".join(source_parts)
    rest_html = "".join(rest_parts)
    source_soup = BeautifulSoup(source_html, "html.parser")
    links = source_soup.find_all("a")
    if len(links) == 1 and source_soup.get_text(" ", strip=True) == links[0].get_text(" ", strip=True):
        return links[0].get_text(" ", strip=True), links[0].get("href", ""), rest_html
    return source_soup.get_text(" ", strip=True), "", rest_html


def _extract_description(rest_html: str) -> str | None:
    rest_html = SEPARATOR_RE.sub("", rest_html).strip()
    if not rest_html:
        return ""
    description_soup = BeautifulSoup(rest_html, "html.parser")
    if any(tag.name not in ALLOWED_DESCRIPTION_TAGS for tag in description_soup.find_all()):
        return None
    return f"<p>{description_soup.decode_contents().strip()}</p>"


def _prepared_weeknote_links(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    block = WeeknoteLinksBlock()
    value = block.clean(block.to_python(items))
    return block.get_prep_value(value)


def _validation_warning(items: list[dict[str, Any]], *, heading: str) -> ConversionWarning | None:
    try:
        _prepared_weeknote_links(items)
    except ValidationError:
        return ConversionWarning("List section failed structured block validation.", heading=heading)
    return None


def _block(block_type: str, value: Any) -> dict[str, Any]:
    return {"type": block_type, "value": value, "id": str(uuid.uuid4())}


def _is_heading(node: Any) -> bool:
    return isinstance(node, Tag) and node.name in {"h2", "h3"}


def _is_blank_text(node: Any) -> bool:
    return isinstance(node, NavigableString) and not str(node).strip()


def _next_meaningful_node(nodes: list[Any], start: int) -> tuple[int, Any | None]:
    for index, node in enumerate(nodes[start:], start=start):
        if not _is_blank_text(node):
            return index, node
    return -1, None


def _first_nonblank_index(nodes: list[Any]) -> int | None:
    for index, node in enumerate(nodes):
        if not _is_blank_text(node):
            return index
    return None


def _normalized_text(node: Tag) -> str:
    return html.unescape(node.get_text(" ", strip=True)).strip()


def _kind_for_category(category: str) -> str:
    return {
        "articles": "article",
        "videos": "video",
        "podcasts": "podcast_episode",
        "social": "social_post",
    }.get(category, "link")
