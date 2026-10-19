"""Move the closing, fully bold paragraph of each solution into the new Fazit field.

Every project ended its solution with one bold paragraph that worked as a conclusion. The
page now shows it in bold at the end of the solution, so it becomes its own field.
The live page and its latest revision are both updated, so drafts keep the same split.
"""

import json

from bs4 import BeautifulSoup, NavigableString
from django.db import migrations

BOLD_TAGS = {"b", "strong"}


def split_conclusion(html):
    """Return (solution without its closing bold paragraph, that paragraph) or (html, "")."""

    soup = BeautifulSoup(html or "", "html.parser")
    blocks = [node for node in soup.find_all(recursive=False)]
    filled = [node for node in blocks if node.get_text(strip=True)]
    if not filled or filled[-1].name != "p":
        return html, ""
    last = filled[-1]
    children = [child for child in last.contents if not (isinstance(child, NavigableString) and not child.strip())]
    if not children or any(getattr(child, "name", None) not in BOLD_TAGS for child in children):
        return html, ""
    conclusion = str(last)
    for node in blocks[blocks.index(last) :]:
        node.extract()
    remaining = soup.find_all(recursive=False)
    while remaining and not remaining[-1].get_text(strip=True):
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
    ProjectPage = apps.get_model("portfolio", "ProjectPage")
    Revision = apps.get_model("wagtailcore", "Revision")
    for page in ProjectPage.objects.all():
        if page.conclusion:
            continue
        stream, conclusion = move_out(list(page.content.raw_data))
        if conclusion:
            page.content = stream
            page.conclusion = conclusion
            page.save(update_fields=["content", "conclusion"])
        revision_ids = {page.latest_revision_id, page.live_revision_id} - {None}
        for revision in Revision.objects.filter(pk__in=revision_ids):
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
                revision.save(update_fields=["content"])


def backwards(apps, schema_editor):
    ProjectPage = apps.get_model("portfolio", "ProjectPage")
    Revision = apps.get_model("wagtailcore", "Revision")
    for page in ProjectPage.objects.all():
        revision_ids = {page.latest_revision_id, page.live_revision_id} - {None}
        for revision in Revision.objects.filter(pk__in=revision_ids):
            data = revision.content
            raw = data.get("content")
            stored = json.loads(raw) if isinstance(raw, str) else raw
            stored, moved = move_back(stored or [], data.get("conclusion", ""))
            if moved:
                data["content"] = json.dumps(stored) if isinstance(raw, str) else stored
                data["conclusion"] = ""
                revision.content = data
                revision.save(update_fields=["content"])
        stream, moved = move_back(list(page.content.raw_data), page.conclusion)
        if moved:
            page.content = stream
            page.conclusion = ""
            page.save(update_fields=["content", "conclusion"])


class Migration(migrations.Migration):
    dependencies = [
        ("portfolio", "0010_project_conclusion"),
        ("wagtailcore", "0098_apitoken"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
