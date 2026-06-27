# Editorial Résumé & Cover-Letter PDF Download — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce faithful, downloadable A4 PDFs of the editorial CV and cover letter, rendered from our own web layout.

**Architecture:** A print stylesheet (`@media print` / vendored `print.css` + a `@media print` block in `cover.css`) re-creates the reference A4 layout — forcing the two-column layout at A4 width, hiding the side illustrations + outer torn-edge lines, keeping the internal structural lines + handwriting frozen in final state. A Playwright management command pre-renders both pages (print media, reduced-motion) into static PDF files; screen-only download links point at them.

**Tech Stack:** Django, CSS `@media print` + `@page`, container queries, Playwright (sync API, already a dependency via `pytest-playwright`), `pypdf` (to be added, dev-only).

## Global Constraints

- django-resume is **frozen**: edit only the homepage shadow copies (`homepage/static/django_resume/...`, `homepage/static/cover-letter/...`, `homepage/templates/django_resume/...`). Never edit `.venv/.../django_resume/`.
- CSS-first / progressive enhancement: the print layout must be correct with the no-JS / reduced-motion static state (no animation in PDF).
- Reference targets (match these): `~/Documents/CV_Anschreiben/050326_Lebenslauf_Katharina_Wersdoerfer.pdf` (CV) and `~/Documents/CV_Anschreiben/050326_Anschreiben_Katharina_Wersdoerfer.pdf` (cover).
- "Content area only" — Removed in PDF: side illustrations (`.cv-bg-layer`), outer torn-edge lines (`.editorial-sheet::before`/`::after`), top black strip (`body.editorial-page::before`), cover footer bar (`.cover-footer-bar`), the CV "Resources" rail (the `.cv-rail` containing `.cv-resources`), edit chrome. Kept in final static state: all internal structural lines + handwriting labels/signature.
- Single-page for current content, but multi-page must flow gracefully (`break-inside: avoid` on entries; no scale-to-fit hacks).
- Dev resume server with seeded data runs on **:8003**; preview token `?token=localpreview2026`; slug `katharina`. CV URL `/resume/katharina/cv/`, cover URL `/resume/katharina/`.
- Commit convention: prefix `# `, no self-reference, no Claude/Anthropic attribution. Do not push (owner pushes).
- Run Python via `uv run` from the repo root.

---

## File Structure

- `homepage/static/django_resume/css/editorial/print.css` — **create** (shadows the upstream incomplete copy; already linked via `<link media="print">` in the editorial `base.html`). Shared print resets + CV two-column print layout. (Tasks 1–2)
- `homepage/static/cover-letter/cover.css` — **modify**: add an `@media print` block. (Task 3)
- `homepage/resume_cover/management/__init__.py`, `homepage/resume_cover/management/commands/__init__.py`, `homepage/resume_cover/management/commands/render_resume_pdfs.py` — **create**: the render command. (Task 4)
- `homepage/templates/django_resume/pages/editorial/resume_cv.html` — **modify**: real CV download link. (Task 5)
- `homepage/templates/django_resume/pages/editorial/resume_detail.html` — **modify**: cover download link. (Task 5)
- `homepage/static/resume/.gitignore` — **create**: ignore generated `*.pdf`. (Task 5)
- `justfile` — **modify**: `render-pdfs` recipe. (Task 5)
- Verification scripts (run against the :8003 dev server, the project's established check method): kept in the scratchpad during iteration; the durable page-count check uses `pypdf`.

> **Note on testing:** the seeded résumé data lives in the dev DB (:8003), not a pytest fixture, so layout verification uses Playwright scripts against the running dev server (the same method used throughout this editorial work), not isolated pytest. Each task's "test" is a concrete Playwright check that fails before the CSS/code exists and passes after.

---

## Task 1: Vendor print.css + shared print resets (hide chrome, freeze handwriting)

**Files:**
- Create: `homepage/static/django_resume/css/editorial/print.css`
- Verify: `<scratchpad>/check_print_base.py`

**Interfaces:**
- Produces: the homepage-shadowed `print.css` (linked already by base.html). Later tasks append CV rules to it.

- [ ] **Step 1: Write the failing verification script**

Create `<scratchpad>/check_print_base.py`:

```python
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8003"
TOKEN = "?token=localpreview2026"
PAGES = {"cv": "/resume/katharina/cv/", "cover": "/resume/katharina/"}

CHECK = """() => {
  const vis = (el) => el && getComputedStyle(el).display !== 'none'
    && getComputedStyle(el).visibility !== 'hidden';
  const bg = document.querySelector('.cv-bg-layer');
  const strip = getComputedStyle(document.querySelector('body'), '::before').content;
  const pen = document.querySelector('.hw-pen');
  const penCs = pen ? getComputedStyle(pen) : null;
  const inkGroup = document.querySelector('.hw-ink-group');
  return {
    bgLayerVisible: vis(bg),
    penDashoffset: penCs ? penCs.strokeDashoffset : null,
    inkVisible: inkGroup ? getComputedStyle(inkGroup).visibility : null,
  };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    for label, path in PAGES.items():
        page = b.new_page()
        page.emulate_media(media="print", reduced_motion="reduce")
        page.goto(BASE + path + TOKEN, wait_until="networkidle")
        page.wait_for_timeout(400)
        print(label, page.evaluate(CHECK))
        page.close()
    b.close()
```

- [ ] **Step 2: Run it to capture the BEFORE state**

Run: `cd /Users/katha/gitprojects/homepage && uv run python <scratchpad>/check_print_base.py`
Expected (before): `bgLayerVisible: True` (illustrations still shown in print), `penDashoffset` non-zero on at least one run.

- [ ] **Step 3: Create the vendored print.css with shared resets**

Create `homepage/static/django_resume/css/editorial/print.css`:

```css
/* Editorial theme — print / PDF. Homepage-vendored copy that SHADOWS the package
 * print.css (linked via <link media="print"> in base.html). Produces a faithful
 * A4 of the CONTENT AREA only: no side illustrations, no outer torn-edge lines,
 * internal structural lines + handwriting kept frozen in final drawn state.
 * CV two-column layout is forced here (Task 2); cover specifics live in cover.css. */

@page {
  size: A4;
  /* full-bleed creme + dark bars to the page edges, like the reference; the sheet's
     own padding provides the text inset (no white @page frame). */
  margin: 0;
}

body.editorial-page {
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;       /* keep creme bg, filled tags, dark bars on paper */
}

/* --- remove: illustrations + the outer lines that border them + page chrome --- */
.cv-bg-layer { display: none !important; }                 /* peeking side illustrations */
.editorial-sheet::before,
.editorial-sheet::after { display: none !important; }      /* outer torn-paper edges */
body.editorial-page::before { display: none !important; }  /* thin black top strip */
.cover-footer-bar { display: none !important; }            /* cover's decorative dark footer */

/* web-only chrome that must not appear inside the PDF */
.cv-rail:has(.cv-resources) { display: none !important; }  /* "Resources" rail: CV-PDF + Portfolio links */
.cover-head-edit { display: none !important; }             /* inline edit affordance */

/* --- keep, frozen: handwriting labels + signature in final drawn state --- */
/* mirrors the existing prefers-reduced-motion rule in handwriting.css */
html.js-hw .hw-ink-group { visibility: visible !important; }
.hw-pen { stroke-dashoffset: 0 !important; animation: none !important; }
```

- [ ] **Step 4: Re-run the verification script**

Run: `cd /Users/katha/gitprojects/homepage && uv run python <scratchpad>/check_print_base.py`
Expected (after): `bgLayerVisible: False` for both; `penDashoffset: "0px"`; `inkVisible: "visible"`.

- [ ] **Step 5: Commit**

```bash
git add homepage/static/django_resume/css/editorial/print.css
git commit -m "# Editorial print.css: hide illustrations + torn edges, freeze handwriting"
```

---

## Task 2: Force the CV two-column A4 layout + density + page breaks

**Files:**
- Modify: `homepage/static/django_resume/css/editorial/print.css` (append)
- Verify: `<scratchpad>/check_print_cv.py`

**Interfaces:**
- Consumes: the print.css shared resets from Task 1.
- Produces: a CV that prints two-column at A4 (aside beside main, awards bar full-bleed at the bottom).

**Background:** A4 print width (~700–794px ≈ 44–50rem) is below the CV's `@container editorial (min-width: 61rem)` two-column breakpoint, so the CV otherwise prints single-column. Re-assert the desktop two-column rules un-gated in `@media print`, MINUS the side-art overlay mechanics (no `-100dvh` pull, no `--cv-peek` subtraction, no sticky bg-layer), so the sheet fills the page.

- [ ] **Step 1: Write the failing verification script**

Create `<scratchpad>/check_print_cv.py`:

```python
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8003/resume/katharina/cv/?token=localpreview2026"

CHECK = """() => {
  const main = document.querySelector('.cv-main');
  const aside = document.querySelector('.cv-aside');
  if (!main || !aside) return {err: 'missing'};
  const m = main.getBoundingClientRect(), a = aside.getBoundingClientRect();
  return {
    twoColumn: a.left >= m.right - 2,         // aside sits to the RIGHT of main
    asideTop: Math.round(a.top),
    mainTop: Math.round(m.top),
    sideBySide: Math.abs(a.top - m.top) < 80,  // roughly same row
  };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    page.emulate_media(media="print", reduced_motion="reduce")
    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(400)
    print(page.evaluate(CHECK))
    b.close()
```

- [ ] **Step 2: Run it to capture the BEFORE state**

Run: `cd /Users/katha/gitprojects/homepage && uv run python <scratchpad>/check_print_cv.py`
Expected (before): `twoColumn: False` (single-column in print — aside below main).

- [ ] **Step 3: Append the forced two-column + density rules to print.css**

Append to `homepage/static/django_resume/css/editorial/print.css`:

```css
/* ---------------------------------------------------------------------------
 * CV: force the desktop two-column architecture at A4 (the container is narrower
 * than the 61rem screen breakpoint on paper). These mirror the screen.css
 * @container (min-width: 61rem) block, but WITHOUT the side-art overlay: the
 * sheet is not pulled up (-100dvh) and not narrowed for a peek — it fills the page.
 * ------------------------------------------------------------------------- */
@media print {
  .cv-root { display: block; padding: 0; background-color: transparent; max-inline-size: none; margin-inline: 0; }
  .cv-root::after { content: none; }              /* no single-column creme panel */
  .cv-stage { display: block; }

  .editorial-sheet:not(.cover-sheet) {
    display: flex;
    margin-block-start: 0;                          /* no desktop -100dvh overlay pull */
    max-inline-size: none;                          /* fill the page (no side-art peek) */
    margin-inline: 0;
  }

  /* header back to the full-width two-column row */
  .editorial-sheet:not(.cover-sheet) .cv-header { flex-direction: row; padding-block-end: var(--s1); max-inline-size: none; margin-inline: 0; }
  .editorial-sheet:not(.cover-sheet) .cv-header-name { align-self: flex-end; margin-inline-start: 0; transform: none; }
  .editorial-sheet:not(.cover-sheet) .cv-firstname { text-indent: -0.085em; }
  .editorial-sheet:not(.cover-sheet) .cv-role { text-align: end; font-size: var(--role-size); }
  .editorial-sheet:not(.cover-sheet) .cv-header-aside {
    border-inline-start: var(--editorial-rule) solid var(--editorial-line);
    padding-inline-start: var(--s-1);
    flex: 0 0 var(--aside-basis);
    margin-block-start: 0;
    margin-inline-start: 0;
  }
  html.js-lines .editorial-sheet:not(.cover-sheet) .cv-header-aside::before { display: block; }
  .editorial-sheet:not(.cover-sheet) .cv-header-aside .cv-rail-body { padding-inline-start: var(--s1); }
  .editorial-sheet:not(.cover-sheet) .cv-header-aside .cv-rail-body::before { inset-block-start: 0; inset-block-end: 0; }
  .editorial-sheet:not(.cover-sheet) .cv-header-aside .cv-rail-label { transform: rotate(180deg); }

  /* two-column body */
  .cv-body { display: flex; }
  .cv-aside { display: flex; }
  .cv-main {
    display: flex;
    flex: 0 1 auto; flex-basis: 0; flex-grow: 999;
    min-inline-size: 50%;
    padding-inline-end: var(--s2);
    padding-block-end: 0;                           /* drop the huge screen bottom gap */
  }
  .cv-main h2 { text-align: start; }
  .cv-photo {
    inline-size: min(calc(100% + var(--photo-bleed-left)), 60vw);
    margin-block-start: calc(-1 * (var(--s-1) + var(--editorial-rule)));
    margin-inline-start: calc(-1 * var(--photo-bleed-left));
    margin-inline-end: 0;
    transform: none;
  }

  /* awards: full-bleed dark bar at the bottom edge, 3-column like desktop */
  .cv-awards-bar { margin-inline: 0; margin-block-end: 0; }
  .cv-awards-bar section { grid-template-columns: 0.5fr 1.2fr var(--aside-basis); gap: 0; }
  .cv-awards-inner { max-inline-size: none; padding-block: var(--s2); padding-inline: var(--sheet-pad-inline); }
  .cv-awards-bar h2 { text-align: start; line-height: 1.4; padding-block-end: 0; border-block-end: 0; margin-block-end: 0; }

  /* density: condense the screen's generous per-entry breathing room to reference
     density so today's content fills exactly one A4 */
  :root { --entry-pad: var(--s-2); --entry-pad-top: calc(var(--date-tab-block) + var(--s-2)); }
  .cv-main { padding-block-end: 0; }

  /* multi-page: never split an entry/award/education item across a page break */
  .timeline-entry, .cv-awards-bar .award-box, .cv-rail-body li { break-inside: avoid; }
}
```

- [ ] **Step 4: Re-run the verification script**

Run: `cd /Users/katha/gitprojects/homepage && uv run python <scratchpad>/check_print_cv.py`
Expected (after): `twoColumn: True`, `sideBySide: True`.

- [ ] **Step 5: Commit**

```bash
git add homepage/static/django_resume/css/editorial/print.css
git commit -m "# Editorial print.css: force the two-column CV layout + density at A4"
```

---

## Task 3: Cover-letter print rules (two-column header at A4, drop chrome)

**Files:**
- Modify: `homepage/static/cover-letter/cover.css` (append an `@media print` block)
- Verify: `<scratchpad>/check_print_cover.py`

**Interfaces:**
- Consumes: the shared resets in print.css (cover footer / torn edges / illustrations already hidden there).
- Produces: a cover letter that prints with the two-column header + meta-head grid at A4.

**Background:** the cover's two-column header lives in `cover.css @container editorial (min-width: 53rem)` and its date/recipient grid in `@container editorial (min-width: 53rem)`. A4 print width (~44–50rem) is below 53rem, so without intervention the cover prints its single-column header. Re-assert both at print.

- [ ] **Step 1: Write the failing verification script**

Create `<scratchpad>/check_print_cover.py`:

```python
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8003/resume/katharina/?token=localpreview2026"

CHECK = """() => {
  const header = document.querySelector('.cover-sheet .cv-header');
  const footer = document.querySelector('.cover-footer-bar');
  const sig = document.querySelector('.cover-signature-hw .hw-pen, .cover-signature-img');
  return {
    headerRow: header ? getComputedStyle(header).flexDirection : null,
    footerVisible: footer ? getComputedStyle(footer).display !== 'none' : null,
    hasSignature: !!sig,
  };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    page.emulate_media(media="print", reduced_motion="reduce")
    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(400)
    print(page.evaluate(CHECK))
    b.close()
```

- [ ] **Step 2: Run it to capture the BEFORE state**

Run: `cd /Users/katha/gitprojects/homepage && uv run python <scratchpad>/check_print_cover.py`
Expected (before): `headerRow: "column"` (single-column header on paper), `footerVisible: False` (already hidden by Task 1).

- [ ] **Step 3: Append the cover `@media print` block to cover.css**

Append to `homepage/static/cover-letter/cover.css`:

```css
/* ----------------------------------------------------- print / PDF --------- */
/* A4 print width is below the cover's 53rem two-column breakpoints, so re-assert
 * the two-column header + the date/recipient grid here. The shared print.css
 * already hides the footer bar, torn edges and illustrations and freezes the
 * handwriting; this block only restores the two-column header geometry on paper. */
@media print {
  .cover-sheet { --aside-basis: 20rem; }
  .cover-sheet .cv-header { flex-direction: row; padding-block-end: var(--s1); max-inline-size: none; margin-inline: 0; }
  .cover-sheet .cv-header-name { align-self: flex-end; margin-inline-start: 0; transform: none; }
  .cover-sheet .cv-firstname { text-indent: -0.085em; }
  .cover-sheet .cv-role { text-align: end; font-size: var(--role-size); }
  .cover-sheet .cv-header-aside {
    border-inline-start: var(--editorial-rule) solid var(--editorial-line);
    padding-inline-start: var(--s-1);
    flex: 0 0 var(--aside-basis);
    margin-block-start: 0;
    margin-inline-start: 0;
  }
  html.js-lines .cover-sheet .cv-header-aside::before { display: block; }
  .cover-sheet .cv-header-aside .cv-rail-body { padding-inline-start: var(--s1); }
  .cover-sheet .cv-header-aside .cv-rail-body::before { inset-block-start: 0; inset-block-end: 0; }
  .cover-sheet .cv-header-aside .cv-rail-label { transform: rotate(180deg); }

  /* date/recipient meta-head grid (mirrors the >=53rem screen rules) */
  .cover-head {
    display: grid;
    grid-template-columns: 1fr calc(var(--aside-basis) - var(--cover-gutter));
    grid-template-areas: "recipient date" "subject subject";
    column-gap: var(--s1);
    align-items: start;
  }
  .cover-recipient { grid-area: recipient; margin-block-start: var(--s2); }
  .cover-place-date {
    grid-area: date; text-align: start;
    padding-inline-start: calc(var(--s-1) + var(--editorial-rule) + var(--script-rail) + var(--s1) + 1.6em);
  }
  .cover-subject { grid-area: subject; }

  /* signature shows its final written state (mirrors the screen rule with !important) */
  .cover-signature-hw .hw-ink-group { visibility: visible !important; }
  .cover-signature-hw .hw-pen { stroke-dashoffset: 0 !important; animation: none !important; }

  /* never split the letter card across a page break for the current one-pager */
  .cover-card { break-inside: avoid; }
}
```

- [ ] **Step 4: Re-run the verification script**

Run: `cd /Users/katha/gitprojects/homepage && uv run python <scratchpad>/check_print_cover.py`
Expected (after): `headerRow: "row"`, `footerVisible: False`, `hasSignature: True`.

- [ ] **Step 5: Commit**

```bash
git add homepage/static/cover-letter/cover.css
git commit -m "# Cover letter: A4 print rules — two-column header + meta-head, drop chrome"
```

---

## Task 4: `render_resume_pdfs` management command

**Files:**
- Create: `homepage/resume_cover/management/__init__.py` (empty)
- Create: `homepage/resume_cover/management/commands/__init__.py` (empty)
- Create: `homepage/resume_cover/management/commands/render_resume_pdfs.py`
- Verify: page count via `pypdf`

**Interfaces:**
- Produces: `homepage/static/resume/katharina-lebenslauf.pdf` and `homepage/static/resume/katharina-anschreiben.pdf`.
- CLI: `uv run python manage.py render_resume_pdfs [--base-url URL] [--token TOKEN] [--out DIR]`.

- [ ] **Step 1: Add pypdf (dev) for the page-count check**

Run: `cd /Users/katha/gitprojects/homepage && uv add --dev pypdf`
Expected: pypdf added to dev dependencies; `uv run python -c "import pypdf"` succeeds.

- [ ] **Step 2: Create the management package files**

Create empty `homepage/resume_cover/management/__init__.py` and `homepage/resume_cover/management/commands/__init__.py`.

- [ ] **Step 3: Write the command**

Create `homepage/resume_cover/management/commands/render_resume_pdfs.py`:

```python
"""Pre-render the editorial CV and cover letter to A4 PDF files via headless Chromium.

Approach B from the design spec: the PDFs are build/deploy artifacts, not generated
in the live request path. Run against a running site (dev :8003, or the deployed URL):

    uv run python manage.py render_resume_pdfs --base-url http://127.0.0.1:8003

Output goes to homepage/static/resume/ so WhiteNoise serves it (re-run collectstatic
after rendering in production).
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from playwright.sync_api import sync_playwright

DOCUMENTS = [
    ("/resume/katharina/cv/", "katharina-lebenslauf.pdf"),
    ("/resume/katharina/", "katharina-anschreiben.pdf"),
]


class Command(BaseCommand):
    help = "Render the editorial CV and cover letter to A4 PDF files."

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default="http://127.0.0.1:8003")
        parser.add_argument("--token", default="localpreview2026")
        parser.add_argument(
            "--out",
            default=str(Path(settings.APPS_DIR) / "static" / "resume"),
            help="Output directory for the PDF files.",
        )

    def handle(self, *args, **opts):
        out_dir = Path(opts["out"])
        out_dir.mkdir(parents=True, exist_ok=True)
        base, token = opts["base_url"].rstrip("/"), opts["token"]

        with sync_playwright() as p:
            browser = p.chromium.launch()
            for path, filename in DOCUMENTS:
                page = browser.new_page()
                # print media + reduced-motion => print CSS applies and the handwriting
                # + drawn structural lines jump to their final state (editorial-lines.js
                # adds cv-line-drawn immediately under reduced-motion).
                page.emulate_media(media="print", reduced_motion="reduce")
                url = f"{base}{path}?token={token}"
                page.goto(url, wait_until="networkidle")
                page.wait_for_timeout(500)
                target = out_dir / filename
                page.pdf(
                    path=str(target),
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                )
                page.close()
                self.stdout.write(self.style.SUCCESS(f"wrote {target}"))
            browser.close()
```

> If `settings.APPS_DIR` is not exposed, use `Path(settings.STATICFILES_DIRS[0])` instead — both resolve to `homepage/static`. Confirm which is importable before writing (`grep -n "APPS_DIR" config/settings/base.py`).

- [ ] **Step 4: Run the command against the dev server**

Precondition: the resume dev server is running on :8003 with seeded data.
Run: `cd /Users/katha/gitprojects/homepage && uv run python manage.py render_resume_pdfs`
Expected: two `wrote …` lines; both PDF files exist in `homepage/static/resume/`.

- [ ] **Step 5: Verify each PDF is a single page**

Run:
```bash
cd /Users/katha/gitprojects/homepage && uv run python -c "
from pypdf import PdfReader
for f in ('katharina-lebenslauf.pdf','katharina-anschreiben.pdf'):
    n = len(PdfReader(f'homepage/static/resume/{f}').pages)
    print(f, n)
    assert n == 1, f'{f} is {n} pages, expected 1'
print('OK: both single-page')
"
```
Expected: both report `1`, prints `OK: both single-page`.

- [ ] **Step 6: Commit**

```bash
git add homepage/resume_cover/management pyproject.toml uv.lock
git commit -m "# Add render_resume_pdfs command: pre-render CV + cover to A4 PDFs"
```

---

## Task 5: Download links + gitignore + justfile recipe

**Files:**
- Modify: `homepage/templates/django_resume/pages/editorial/resume_cv.html:95`
- Modify: `homepage/templates/django_resume/pages/editorial/resume_detail.html`
- Create: `homepage/static/resume/.gitignore`
- Modify: `justfile`
- Verify: `<scratchpad>/check_links.py`

**Interfaces:**
- Consumes: the rendered PDF files from Task 4 (served at `{% static 'resume/...' %}`).

- [ ] **Step 1: Write the failing verification script**

Create `<scratchpad>/check_links.py`:

```python
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8003"
TOKEN = "?token=localpreview2026"

def link_info(page, sel):
    el = page.query_selector(sel)
    if not el:
        return None
    return {"href": el.get_attribute("href"), "download": el.get_attribute("download")}

with sync_playwright() as p:
    b = p.chromium.launch()
    # CV: screen link present and pointing at the PDF
    cv = b.new_page()
    cv.goto(f"{BASE}/resume/katharina/cv/{TOKEN}", wait_until="networkidle")
    print("cv link:", link_info(cv, "a[href*='lebenslauf']"))
    # CV: link absent in print
    cv.emulate_media(media="print")
    print("cv resources visible in print:",
          cv.evaluate("() => { const r=document.querySelector('.cv-rail:has(.cv-resources)'); return r ? getComputedStyle(r).display !== 'none' : false; }"))
    # cover: screen link present
    cover = b.new_page()
    cover.goto(f"{BASE}/resume/katharina/{TOKEN}", wait_until="networkidle")
    print("cover link:", link_info(cover, "a[href*='anschreiben']"))
    b.close()
```

- [ ] **Step 2: Run it to capture the BEFORE state**

Run: `cd /Users/katha/gitprojects/homepage && uv run python <scratchpad>/check_links.py`
Expected (before): `cv link: None` (placeholder `href="#"` doesn't match `*lebenslauf`), `cover link: None`.

- [ ] **Step 3: Wire the CV download link**

In `homepage/templates/django_resume/pages/editorial/resume_cv.html`, replace the placeholder line (currently `<li><a href="#">Lebenslauf als PDF</a></li>`):

```html
            <li><a href="{% static 'resume/katharina-lebenslauf.pdf' %}" download>Lebenslauf als PDF</a></li>
```

(The `Portfolio` line stays a placeholder for now. `{% load static %}` is already loaded in this template.)

- [ ] **Step 4: Add the cover download link (screen-only)**

In `homepage/templates/django_resume/pages/editorial/resume_detail.html`, add a screen-only link inside the `.cover-card` after the letter include (around line 63). Add a small block that the print CSS already hides via a new class:

```html
    <p class="cover-download">
      <a href="{% static 'resume/katharina-anschreiben.pdf' %}" download>Anschreiben als PDF</a>
    </p>
```

Then add to `homepage/static/cover-letter/cover.css` a screen rule and a print-hide:

```css
.cover-download { margin-block-start: var(--s2); font-size: var(--s0); }
@media print { .cover-download { display: none !important; } }
```

(Place the `@media print { .cover-download … }` inside the existing print block from Task 3, or keep it adjacent — either is fine.)

- [ ] **Step 5: Re-run the verification script**

Run: `cd /Users/katha/gitprojects/homepage && uv run python <scratchpad>/check_links.py`
Expected (after): `cv link: {'href': '/static/resume/katharina-lebenslauf.pdf', 'download': ''}`, `cv resources visible in print: False`, `cover link` non-null pointing at the anschreiben PDF.

- [ ] **Step 6: Ignore the generated PDFs**

Create `homepage/static/resume/.gitignore`:

```gitignore
# Generated by `manage.py render_resume_pdfs` at build/deploy time.
*.pdf
```

- [ ] **Step 7: Add the justfile recipe**

Add to `justfile`:

```just
# Render the editorial CV + cover letter to downloadable A4 PDFs (needs the dev server on :8003)
render-pdfs:
    uv run python manage.py render_resume_pdfs
```

- [ ] **Step 8: Commit**

```bash
git add homepage/templates/django_resume/pages/editorial/resume_cv.html \
        homepage/templates/django_resume/pages/editorial/resume_detail.html \
        homepage/static/cover-letter/cover.css homepage/static/resume/.gitignore justfile
git commit -m "# Wire CV + cover PDF download links (screen-only) + render-pdfs recipe"
```

---

## Final verification (after all tasks)

- [ ] Render both PDFs (`just render-pdfs`) and open them; compare side-by-side with the two reference PDFs: two-column CV with the dark Awards bar at the bottom edge, handwriting labels present, **no** illustrations / torn edges, internal rules present; cover with two-column header, letter card frame, handwritten signature, no footer bar.
- [ ] Confirm both are single-page via the pypdf check.
- [ ] Confirm the download links work on screen and are absent inside the PDFs.
- [ ] Confirm the screen CV/cover are visually unchanged (the work is all `@media print` / new screen-only links).

## Future (out of scope, noted)

- Auto-regenerate on CMS edit; optional upgrade to on-demand rendering (design spec option A).
- `@page` margin / density fine-tuning against the reference frame once two-column print is in.
- Final cover download-link placement polish.
```
