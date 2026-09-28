# Weeknote Links Block Plan

## Scope

Add a homepage-local structured StreamField block for weeknote link collections, replacing the hand-authored `h2 + ul` HTML sections currently embedded in overview RichText paragraphs. The block must validate link data, render consistently across the homepage themes, and be easy for daybook to emit deterministically.

This slice covers:

- A `weeknote_links` custom Wagtail block registered under `CAST_POST_BODY_BLOCKS["overview"]`.
- Plain, Bootstrap 4, Bootstrap 5, and Vue-theme server-rendered templates in homepage.
- A converter/dry-run management command for existing weeknote overview paragraphs.
- Tests for block factories, registration, rendering, validation, converter behavior, and command safety.
- Homepage documentation plus a django-cast backlog item for editor API custom-block support.

This slice does not implement daybook integration or django-cast editor API support.

## Precedent

The implementation follows the sibling show-notes pattern:

- `django-chat`: project-local block classes and factories in `django_chat.show_notes.blocks`, registered in `CAST_POST_BODY_BLOCKS["detail"]`.
- `python-podcast`: same pattern in `python_podcast.pp.show_notes.blocks`.
- `django-cast`: `cast.post_body_blocks` loads dotted no-argument factories returning `(name, block)`, appends them to django-cast built-ins per section, and validates the setting through system checks.

Weeknotes are authored in `overview`, so homepage registers only the overview block. Adding a configured block is not a database schema change because `Post.body` is JSON StreamField and `ContentBlock.deconstruct()` stores only the section, not custom block definitions.

## Block Shape

Create `homepage.core.weeknotes.blocks`:

```python
RICH_TEXT_FEATURES = ["bold", "italic", "code", "link"]

CATEGORY_CHOICES = [
    ("articles", "Articles"),
    ("software", "Software"),
    ("videos", "Videos"),
    ("podcasts", "Podcasts"),
    ("social", "Social"),
    ("weeknotes", "Weeknotes"),
    ("books", "Books"),
    ("papers", "Papers"),
    ("links", "Links"),
]

KIND_CHOICES = [
    ("article", "Article"),
    ("video", "Video"),
    ("podcast_episode", "Podcast episode"),
    ("social_post", "Social post"),
    ("link", "Link"),
]
```

`WeeknoteLinkItemBlock` fields:

- `category`: required `ChoiceBlock` from `CATEGORY_CHOICES`.
- `kind`: required `ChoiceBlock` from `KIND_CHOICES`, default `"link"`. This is not used for grouping in v1, but preserves machine intent for future icons.
- `title`: required `CharBlock`.
- `url`: required `URLBlock`.
- `source`: optional `CharBlock`, plain display attribution such as `LF Energy`, `Working Draft`, or `Johannes`.
- `source_url`: optional `URLBlock`, used by the legacy converter when the old source was a linked show/site name.
- `description`: optional `RichTextBlock(features=RICH_TEXT_FEATURES)`, used for the old pipe comment or daybook `short_summary`.

`WeeknoteLinkItemBlock.clean()` enforces cross-field invariants:

- `source_url` is invalid unless `source` is also set.
- `category` and `kind` must be one of the configured choices. Wagtail's `ChoiceBlock` handles this, but tests should assert the resulting validation errors are field-specific enough for future API use.
- `description` is validated through Wagtail's `RichTextBlock` clean path so unsupported rich-text content is rejected or normalized consistently with the admin.

`WeeknoteLinksBlock` is a flat `ListBlock(WeeknoteLinkItemBlock(), min_num=1)` with `Meta.template = "cast/weeknotes/links.html"` and `Meta.label = "Weeknote links"`. It implements `get_context()` to expose pre-grouped data to the template:

- `grouped_categories`: a list of `{key, label, items}` in fixed display order, with empty categories omitted.
- `category_labels`: the stable category label mapping, for tests and any theme-specific template.

Grouping in Python avoids brittle Django-template-only grouping logic.

Factory:

```python
def weeknote_links_block() -> tuple[str, blocks.Block]:
    return "weeknote_links", WeeknoteLinksBlock()
```

## Value Contract

There are two related shapes:

1. The **author/editor-facing contract** daybook should emit once django-cast supports configured custom blocks through the editor API.
2. The **stored Wagtail JSON shape** created by `ListBlock.get_prep_value()`.

Daybook should target the author/editor-facing contract. The future django-cast editor API work should adapt that shape through the configured Wagtail block's `to_python()`, `clean()`, and `get_prep_value()` path.

Author/editor-facing block:

```json
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
```

Stored Wagtail JSON uses `ListBlock` item wrappers with generated item IDs:

```json
{
  "type": "weeknote_links",
  "value": [
    {
      "type": "item",
      "value": {
        "category": "articles",
        "kind": "article",
        "title": "Grid Security at Scale: How TenneT Built a 10x Faster Analysis Platform on PowSyBl",
        "url": "https://lfenergy.org/grid-security-at-scale-tennet-powsybl/",
        "source": "LF Energy",
        "source_url": "",
        "description": "<p>TenneT got a 10x speedup on grid security analysis by building ReFlow on top of the open-source PowSyBl framework.</p>"
      },
      "id": "<uuid>"
    }
  ]
}
```

Tests should assert `WeeknoteLinksBlock.get_prep_value()` produces the internal wrapper shape and that the converter/command writes the prepared value through the Wagtail block API rather than hand-constructing internal ListBlock JSON.

Daybook mapping:

- `original_url` -> `url`
- `title` -> `title`
- `kind` -> `kind`
- `source` -> `source`
- `short_summary` -> `description`, HTML-escaped and wrapped as a simple rich-text paragraph (`<p>...</p>`) when non-empty.
- `category` is selected by daybook from its own classification. A default fallback of `"links"` is valid.
- `source_url` may be omitted or set to `""`.

The block is intentionally flat so daybook can emit one `weeknote_links` block in overview without constructing section objects. The template performs grouping.

## Rendering

Use one shared template path, `homepage/templates/cast/weeknotes/links.html`, where possible. It renders:

```html
<section class="weeknote-links">
  <h2>Articles</h2>
  <ul class="weeknote-link-list">
    <li class="weeknote-link-item weeknote-link-item--article">
      <a class="weeknote-link-title" href="...">Title</a>
      <span class="weeknote-link-source">(<a href="...">Source</a>)</span>
      <span class="weeknote-link-description">...</span>
    </li>
  </ul>
</section>
```

Rendering rules:

- Group by fixed category order using `WeeknoteLinksBlock.get_context()`: Articles, Software, Videos, Podcasts, Social, Weeknotes, Books, Papers, Links.
- Skip categories with no items.
- Preserve item order within each category.
- Render the same semantic `h2 + ul + li` shape as old weeknotes.
- Keep visual treatment plain; no cards and no icons in v1.
- Include `kind` as a CSS class (`weeknote-link-item--video`, etc.) for future icons.
- Source renders inline in parentheses. If `source_url` is set, link the source label; otherwise render plain text.
- Description renders after the source. CSS may keep simple rich-text paragraphs inline for the current pipe-comment feel.
- For `render_for_feed`, render the same safe semantic markup and avoid theme-specific decoration.

Theme support:

- Bootstrap 5: include CSS in `homepage/static/css/site-overrides.css`.
- Bootstrap 4, plain, and Vue: use the same block template unless theme-specific path resolution is needed.
- If a theme-specific template is necessary, add homepage overrides under `homepage/templates/cast/bootstrap4/weeknote_links.html`, `homepage/templates/cast/bootstrap5/weeknote_links.html`, `homepage/templates/cast/plain/weeknote_links.html`, and `homepage/templates/cast/vue/weeknote_links.html`, with a `get_template()` fallback in the block similar to django-cast gallery blocks.
- Prefer one shared template first, because custom block templates are included directly by Wagtail and do not need to duplicate surrounding theme layout.

## Registration

Add to `config/settings/base.py`:

```python
CAST_POST_BODY_BLOCKS = {
    "overview": [
        "homepage.core.weeknotes.blocks.weeknote_links_block",
    ],
}
```

Do not list built-ins; django-cast appends custom blocks after built-ins automatically.

## Migration Decision

No Django schema migration is expected. Verify with:

```bash
uv run python manage.py makemigrations --check --dry-run
```

Existing posts need content conversion, implemented as a management command rather than a Django data migration so the conversion can be dry-run, reviewed, and re-run safely.

## Legacy Conversion

Add `homepage.core.weeknotes.converter` and a management command, likely `convert_weeknote_links`.

Command behavior:

- Default mode is dry-run.
- Scope defaults to posts whose slug starts with `weeknotes-`.
- `--slug` limits to one post.
- `--write` saves converted bodies.
- `--report PATH` writes a JSON report.
- `--fail-on-warnings` exits non-zero when any candidate section cannot be converted cleanly.

Conversion rules:

- Inspect each overview section block.
- For paragraph RichText HTML, parse with BeautifulSoup.
- Detect consecutive `h2`/`h3` followed immediately by `ul` where heading maps to a known category or alias.
- Known heading aliases:
  - `Articles` -> `articles`
  - `Software`, `Open Source` -> `software`
  - `Videos`, `YouTube`, `Lectures` -> `videos`
  - `Podcasts` -> `podcasts`
  - `Podcasts / Videos` -> preserve as warnings unless items can be classified confidently; otherwise keep original paragraph fragment.
  - `Mastodon`, `Twitter`, `Mastodon / Twitter` -> `social`
  - `Weeknotes`, `Weeklogs` -> `weeknotes`
  - `Books` -> `books`
  - `Papers` -> `papers`
  - generic `Links` -> `links`
- Convert simple list items with one primary link:
  - Primary first `<a>` -> `title` and `url`.
  - Text prefix before the first link is preserved only when simple; otherwise warn and preserve original HTML.
  - Parenthesized source after primary link becomes `source`; if it contains a single link, capture `source` and `source_url`.
  - Text after `|` or a simple dash separator becomes `description`.
  - Extra inline rich content in the description is preserved as limited rich text when it only uses allowed tags; otherwise warn and preserve the original section.
- Non-convertible sections remain in a paragraph block unchanged.
- Surrounding prose before, between, and after converted sections remains as paragraph blocks.
- Consecutive converted sections in the same old paragraph collapse into one `weeknote_links` block at the first converted section position, preserving category and item ordering.
- If meaningful prose, unsupported HTML, media embeds, or preserved non-convertible sections appear between converted sections, do not collapse across that boundary. Emit separate paragraph/`weeknote_links`/paragraph blocks in the original order.
- The command report lists converted sections, preserved sections, warnings, and per-post changes.

This is deliberately semi-automated. A clean dry-run on production/staging data is required before `--write`.

### Revision and Publish Semantics

The command must not only assign `post.body` and call `save()`.

Write behavior:

- Build a new body value through the configured StreamField/Wagtail block clean path.
- Save a Wagtail revision with a clear log message, for example `Converted weeknote link sections to structured weeknote_links block`.
- Preserve live/draft state by default:
  - If a page is live and has no unpublished changes, `--write --publish` publishes the new revision.
  - If a page has unpublished changes, default `--write` creates a new draft revision and reports that it was not published.
  - If a page is not live, default `--write` creates a draft revision only.
- Require an explicit `--publish` flag before publishing converted live pages.
- The report records `changed`, `revision_id`, and `published` per post.
- Tests should cover dry-run no-save, draft revision creation, and publish behavior for a live page.

## django-cast Backlog Item

Create a backlog note in `../django-cast/backlog/` documenting that the editor API currently accepts only built-in body block types. Follow-up goal:

- Extend the editor API to accept custom `CAST_POST_BODY_BLOCKS` block types.
- Accept an author-facing value shape for configured custom blocks, then validate and prepare values through the configured Wagtail block `to_python()`, `clean()`, and `get_prep_value()` path.
- Serialize configured custom blocks back through the author API instead of returning `unsupported` placeholders.
- Cover overview and detail sections.
- Confirm daybook can round-trip `weeknote_links` through create/update/read.

No django-cast code change is included in this homepage feature.

## Tests

Homepage tests:

- `weeknote_links_block()` returns stable name `weeknote_links`.
- `configured_content_blocks("overview")` includes `weeknote_links`; `detail` does not.
- `validate_post_body_block_setting()` returns no errors.
- The block rejects invalid category/kind and invalid URLs through Wagtail validation.
- The block rejects `source_url` without `source`.
- `WeeknoteLinksBlock.get_context()` returns grouped categories in fixed order and omits empty groups.
- `WeeknoteLinksBlock.get_prep_value()` produces Wagtail's internal `ListBlock` wrapper shape with `type`, `value`, and `id`.
- Rendering groups categories in fixed order while preserving item order inside each category.
- Rendering outputs linked source when `source_url` is present and plain source otherwise.
- Rendering supports limited rich text description.
- Rendering does not output empty category headings.
- Converter turns simple `h2 + ul/li` legacy HTML into one `weeknote_links` block.
- Converter preserves prose around converted sections.
- Converter preserves/warns on ambiguous or unsupported sections.
- Management command dry-run does not save; `--write` saves converted bodies; report contains warnings.
- Management command writes via Wagtail revisions and only publishes with explicit `--publish`.
- Theme rendering tests include Bootstrap 5, Bootstrap 4, plain, Vue, and feed contexts through the relevant `post_body.html` path, not only the shared block template.
- `makemigrations --check --dry-run` has no model/schema changes.

Where database setup is expensive, keep unit tests focused on converter functions and use a small number of Django DB tests for command integration.

## Docs

Update homepage docs with:

- The block purpose.
- The exact daybook JSON shape.
- Category and kind choices.
- Converter command usage and dry-run-first workflow.
- Note that editor API round-trip support is blocked on the django-cast backlog item.

There does not appear to be an existing homepage release-notes file. If none exists, document in `docs/development.rst` or a new focused docs page included from `docs/index.rst`.

## Slice Breakdown

1. **Block and registration**
   - Add `homepage.core.weeknotes` package.
   - Add block classes/factory.
   - Register under overview.
   - Add block/registration/validation tests.
   - Run focused tests and migration check.
   - pi code-review slice.

2. **Rendering**
   - Add shared template and any required theme-specific fallback.
   - Add Bootstrap 5 CSS in `site-overrides.css`, keeping plain output usable without CSS.
   - Add rendering tests for grouping, source, rich description, feed context, and future icon class hooks.
   - Run focused tests.
   - pi code-review slice.

3. **Legacy converter**
   - Add converter module and management command.
   - Add unit and command tests.
   - Run focused tests.
   - pi code-review slice.

4. **Docs and django-cast backlog**
   - Update homepage docs.
   - Add django-cast backlog item.
   - Run docs build if practical, otherwise at least docs link checks through Sphinx import/build.
   - pi code-review slice.

5. **Final gate**
   - Run homepage test/lint/migration checks.
   - Run `codex review --base main`.
   - Fix real findings until clean.
   - Commit per slice and merge to main after all gates are clean.
