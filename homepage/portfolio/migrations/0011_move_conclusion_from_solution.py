"""Move the closing, fully bold paragraph of each solution into the new Fazit field.

Every project ended its solution with one bold paragraph that worked as a conclusion. The
page now shows it in bold at the end of the solution, so it becomes its own field.
The live page and its latest revision are both updated, so drafts keep the same split.
"""

import json

from bs4 import BeautifulSoup, NavigableString
from django.db import migrations

BOLD_TAGS = {"b", "strong"}
EMPTY_WRAPPERS = {"p", "div", "span", "br", "b", "strong"}


def meaningful(node):
    if isinstance(node, NavigableString):
        return bool(node.strip())
    return node.name not in EMPTY_WRAPPERS or any(meaningful(child) for child in node.contents)


def split_conclusion(html):
    """Return (solution without its closing bold paragraph, that paragraph) or (html, "")."""

    soup = BeautifulSoup(html or "", "html.parser")
    blocks = list(soup.contents)
    filled = [node for node in blocks if meaningful(node)]
    if not filled or getattr(filled[-1], "name", None) != "p":
        return html, ""
    last = filled[-1]
    children = [child for child in last.contents if not (isinstance(child, NavigableString) and not child.strip())]
    if not children or any(getattr(child, "name", None) not in BOLD_TAGS for child in children):
        return html, ""
    conclusion = str(last)
    last.extract()
    remaining = list(soup.contents)
    while remaining and not meaningful(remaining[-1]):
        remaining.pop().extract()
    return str(soup).strip(), conclusion


def move_out(stream):
    conclusion = ""
    for block in stream:
        if block.get("type") != "challenge_solution":
            continue
        solution, found = split_conclusion(block.get("value", {}).get("solution", ""))
        if found and not conclusion:
            block["value"]["solution"] = solution
            conclusion = found
    return stream, conclusion


def move_back(stream, conclusion):
    for block in stream:
        if block.get("type") == "challenge_solution" and conclusion:
            solution = block.get("value", {}).get("solution", "")
            block["value"]["solution"] = f"{solution}{conclusion}"
            return stream, True
    return stream, False


def forwards(apps, schema_editor):
    alias = schema_editor.connection.alias
    ProjectPage = apps.get_model("portfolio", "ProjectPage")
    Revision = apps.get_model("wagtailcore", "Revision")
    for page in ProjectPage.objects.using(alias).all():
        if page.conclusion:
            continue
        stream, conclusion = move_out(list(page.content.raw_data))
        if conclusion:
            page.content = stream
            page.conclusion = conclusion
            page.save(using=alias, update_fields=["content", "conclusion"])
        revision_ids = {page.latest_revision_id, page.live_revision_id} - {None}
        for revision in Revision.objects.using(alias).filter(pk__in=revision_ids):
            data = revision.content
            if data.get("conclusion"):
                continue
            raw = data.get("content")
            stored = json.loads(raw) if isinstance(raw, str) else raw
            stored, found = move_out(stored or [])
            if found:
                data["content"] = json.dumps(stored) if isinstance(raw, str) else stored
                data["conclusion"] = found
                revision.content = data
                revision.save(using=alias, update_fields=["content"])


def backwards(apps, schema_editor):
    alias = schema_editor.connection.alias
    ProjectPage = apps.get_model("portfolio", "ProjectPage")
    Revision = apps.get_model("wagtailcore", "Revision")
    # Preflight every selected page/revision before any writes. A later schema
    # reversal drops this field, so leaving an unmoved conclusion is unsafe.
    for page in ProjectPage.objects.using(alias).all():
        records = [(list(page.content.raw_data), page.conclusion)]
        revision_ids = {page.latest_revision_id, page.live_revision_id} - {None}
        for revision in Revision.objects.using(alias).filter(pk__in=revision_ids):
            data = revision.content
            raw = data.get("content")
            records.append((json.loads(raw) if isinstance(raw, str) else raw or [], data.get("conclusion", "")))
        for stream, conclusion in records:
            if conclusion and not any(block.get("type") == "challenge_solution" for block in stream):
                raise RuntimeError(
                    f"Cannot reverse portfolio conclusion migration for page {page.pk}: "
                    "restore a challenge_solution block on the page and its live/latest revisions "
                    "or move and clear their conclusions before retrying."
                )
    for page in ProjectPage.objects.using(alias).all():
        revision_ids = {page.latest_revision_id, page.live_revision_id} - {None}
        for revision in Revision.objects.using(alias).filter(pk__in=revision_ids):
            data = revision.content
            raw = data.get("content")
            stored = json.loads(raw) if isinstance(raw, str) else raw
            stored, moved = move_back(stored or [], data.get("conclusion", ""))
            if moved:
                data["content"] = json.dumps(stored) if isinstance(raw, str) else stored
                data["conclusion"] = ""
                revision.content = data
                revision.save(using=alias, update_fields=["content"])
        stream, moved = move_back(list(page.content.raw_data), page.conclusion)
        if moved:
            page.content = stream
            page.conclusion = ""
            page.save(using=alias, update_fields=["content", "conclusion"])


class Migration(migrations.Migration):
    dependencies = [
        ("portfolio", "0010_project_conclusion"),
        ("wagtailcore", "0098_apitoken"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
