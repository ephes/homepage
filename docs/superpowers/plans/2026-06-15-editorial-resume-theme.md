# Editorial Resume Theme & Plugins — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Katharinas Lebenslauf und Bewerbungsanschreiben auf `wersdoerfer.de` als responsive Website + pixelnahes PDF abbilden — über ein neues offizielles `django-resume`-Theme `editorial` plus generische Plugins.

**Architecture:** Funktionalität (Plugins) und Optik (Theme) gehen upstream nach `django-resume`; nur persönliche Inhalte (Foto, Unterschrift, Texte) bleiben in der `homepage`-DB/Media. Plugins folgen den vorhandenen Mustern (`projects`=ListPlugin, `skills`/`education`=SimplePlugin). Das Theme ist ein String `editorial` mit Templates unter `django_resume/pages/editorial/` und `django_resume/plugins/<plugin>/editorial/`; PDF entsteht über `print.css` mit `@page` (Browser-Druck, kein Headless-Renderer).

**Tech Stack:** Django, `django-resume` (editable), pytest, Playwright (e2e/Screenshots), Saira (OFL Webfont), CSS (Every-Layout-Primitive, CSS-first).

**Begleitdokument (Source of Truth):** `docs/superpowers/specs/2026-06-15-editorial-resume-theme-design.md` und die PDFs/`VC.idml` unter `~/Documents/`.

---

## Repos & Pfade

- **homepage** — `/Users/katha/gitprojects/homepage` (Daten, Deployment, Konsument des Themes).
- **django-resume** — `/Users/katha/gitprojects/django-resume` (Theme + Plugins + deren Tests).
- Dev-Server läuft auf **Port 8001** (Port 8000 belegt durch anderes Projekt).

## Dateistruktur (was wird angefasst)

**django-resume (neu/erweitert):**
- `src/django_resume/plugins/awards.py` — neues ListPlugin (Awards).
- `src/django_resume/plugins/languages.py` — neues ListPlugin (Sprachen + Niveau).
- `src/django_resume/plugins/education.py` — Feld `degree` ergänzen.
- `src/django_resume/plugins/cover.py` — Flat-Form um `recipient`/`place_date`/`subject`/`salutation` erweitern.
- `src/django_resume/plugins/__init__.py` + `apps.py` — neue Plugins exportieren/registrieren.
- `src/django_resume/templates/django_resume/pages/editorial/*` — Seiten-Templates (CV + Cover + 403 + base + edit_panel).
- `src/django_resume/templates/django_resume/plugins/<plugin>/editorial/*` — Plugin-Templates pro Plugin.
- `src/django_resume/static/django_resume/css/editorial/*.css` — Screen- + Print-CSS.
- `src/django_resume/static/django_resume/fonts/saira/*` — Saira Webfont (OFL).
- `tests/awards_test.py`, `tests/languages_test.py`, Ergänzungen in `tests/plugins_data_test.py`, `tests/theme_test.py`, e2e.

**homepage (nur Daten/Integration/Override):**
- `pyproject.toml` — `django-resume` temporär als editable source (dev), via prek vor Commit zurück.
- `homepage/static/.../editorial-overrides.css` (optional) — Cervanttis-Override + persönliche Feinheiten (gitignored, NICHT ins Paket).
- Persönliche SVG-Platzhalter + Unterschrift + Foto → Media/Static, **gitignored**, nicht ins Paket.

---

## Phase 0 — Dev-Setup & Skeleton

### Task 0.1: django-resume editable einbinden

**Files:**
- Modify: `homepage/pyproject.toml` (`[tool.uv.sources]`)

- [ ] **Step 1: Prüfen, ob django-resume in den dev-sources fehlt**

Run: `grep -nA2 "tool.uv.sources" /Users/katha/gitprojects/homepage/pyproject.toml`
Expected: `django-resume` taucht dort (noch) nicht mit lokalem Pfad auf.

- [ ] **Step 2: Editable-Source ergänzen**

In `[tool.uv.sources]` ergänzen:
```toml
django-resume = { path = "../django-resume", editable = true }
```

- [ ] **Step 3: Sync & Verifikation**

Run: `cd /Users/katha/gitprojects/homepage && uv sync && uv run python -c "import django_resume, inspect, pathlib; print(pathlib.Path(inspect.getfile(django_resume)).resolve())"`
Expected: Pfad zeigt auf `…/gitprojects/django-resume/src/django_resume/__init__.py`.

- [ ] **Step 4: NICHT committen** — dieser Pfad bleibt nur lokal (prek-Hook erzwingt das vor Commit). Notiz im Branch belassen.

### Task 0.2: Katharina-User + CV-Resume anlegen (lokal)

**Files:**
- Keine Code-Datei; via Django-Shell gegen die lokale DB (Prod-Dump bereits eingespielt).

- [ ] **Step 1: Prüfen, welche User existieren**

Run: `cd /Users/katha/gitprojects/homepage && psql -tA homepage -c "select id, username from users_user order by id;"`
Expected: Jochens User(s). (Eigener Katharina-User wird angelegt, falls nicht vorhanden.)

- [ ] **Step 2: User + leeres Resume `katharina` anlegen**

Run: `cd /Users/katha/gitprojects/homepage && uv run python manage.py shell -c "
from django.contrib.auth import get_user_model
from django_resume.models import Resume
U=get_user_model()
u,_=U.objects.get_or_create(username='katharina', defaults={'email':'katharina@wersdoerfer.de'})
r,created=Resume.objects.get_or_create(slug='katharina', defaults={'name':'Katharina Wersdörfer','owner':u})
print('resume', r.pk, 'created', created)
"`
Expected: Ausgabe `resume <pk> created True`.

- [ ] **Step 3: Theme auf `editorial` setzen**

Run: `cd /Users/katha/gitprojects/homepage && uv run python manage.py shell -c "
from django_resume.models import Resume
r=Resume.objects.get(slug='katharina')
d=dict(r.plugin_data); d['theme']={'name':'editorial'}; r.plugin_data=d; r.save()
print(r.current_theme)
"`
Expected: `editorial`.

### Task 0.3: Theme vollständig bootstrappen (kompletter `plain`-Klon)

> **Wichtig (Codex-Review):** Es gibt **keinen Theme-Fallback** — bei `theme=editorial` werden ALLE Templates unter `pages/editorial/` und `plugins/<plugin>/editorial/` gesucht. `plain/base.html` inkludiert zudem `icons.svg`, und `resume_cv.html` inkludiert die Plugin-Templates aller Plugins. Fehlt eines → `TemplateDoesNotExist`. Deshalb klonen wir zuerst den **gesamten** `plain`-Theme-Baum (Seiten **und** alle Plugin-Verzeichnisse, inkl. `icons.svg` und Nicht-`.html`-Dateien) nach `editorial`. Danach restylen die Folgephasen nur noch.

**Files:**
- Create: `…/templates/django_resume/pages/editorial/` (komplette Kopie von `pages/plain/`)
- Create: `…/templates/django_resume/plugins/<jedes Plugin>/editorial/` (komplette Kopien der `plain`-Unterordner)

- [ ] **Step 1: Gesamten `plain`-Seitenbaum klonen (inkl. icons.svg & Assets)**

Run: `cd /Users/katha/gitprojects/django-resume && rm -rf src/django_resume/templates/django_resume/pages/editorial && cp -R src/django_resume/templates/django_resume/pages/plain src/django_resume/templates/django_resume/pages/editorial`
Expected: `editorial/` enthält alle Dateien aus `plain/` (auch `icons.svg`).

- [ ] **Step 2: Für JEDES Plugin den `plain`-Ordner nach `editorial` klonen**

Run: `cd /Users/katha/gitprojects/django-resume && for d in src/django_resume/templates/django_resume/plugins/*/; do p="$(basename "$d")"; if [ -d "$d/plain" ]; then rm -rf "$d/editorial"; cp -R "$d/plain" "$d/editorial"; fi; done && find src/django_resume/templates/django_resume/plugins -maxdepth 2 -name editorial -type d | sort`
Expected: Für jedes Plugin mit `plain/` existiert nun `editorial/`.

- [ ] **Step 3: CSS-Referenz in `pages/editorial/base.html` umbiegen**

In `base.html` den `<link rel="stylesheet">` auf `django_resume/css/editorial/screen.css` setzen und einen zweiten `<link … media="print" href="django_resume/css/editorial/print.css">` ergänzen. (CSS-Dateien folgen in Phase 2/3; vorerst 404 = kein Crash.)

- [ ] **Step 4: Verifikation — CV rendert mit 200, kein `TemplateDoesNotExist`**

Voraussetzung: als `katharina` (oder Superuser) eingeloggt **oder** gültiger CV-Token (siehe Task 0.4).
Run: `cd /Users/katha/gitprojects/homepage && curl -s -o /dev/null -w "%{http_code}\n" --cookie "$COOKIE" "http://localhost:8001/resume/katharina/cv/"`
Expected: `200`. Kein `500`/`TemplateDoesNotExist` in `logs/dev.log` (prüfen: `just logs-grep TemplateDoesNotExist`).

- [ ] **Step 5: Commit (nur django-resume)**

```bash
cd /Users/katha/gitprojects/django-resume
git checkout -b editorial-theme
git add src/django_resume/templates/django_resume/pages/editorial src/django_resume/templates/django_resume/plugins/*/editorial
git commit -m "Bootstrap editorial theme as full clone of plain theme"
```

### Task 0.4: Zugriffsschutz klären (CV-Token / Anschreiben)

> **Codex-Review / Produktentscheidung:** Der CV ist standardmäßig token-geschützt (fehlende Token-Daten ⇒ `token_is_required=True`, `resume_cv` liefert 403). `resume_detail` (Anschreiben) prüft **keine** Tokens. **Default dieser Spec:** CV **öffentlich** (kein Token nötig), Anschreiben **unlisted** über einen schwer ratbaren Slug. Vor der Umsetzung bestätigen/anpassen.

**Files:** keine Code-Datei; Django-Shell + ggf. Doku.

- [ ] **Step 1: CV öffentlich schalten** (Token-Plugin-Daten so setzen, dass `token_is_required` `False` ist) ODER bewusst einen Token anlegen, falls der CV privat bleiben soll.

Run (öffentlich): `cd /Users/katha/gitprojects/homepage && uv run python manage.py shell -c "
from django_resume.models import Resume
from django_resume.plugins.tokens import TokenPlugin
r=Resume.objects.get(slug='katharina')
print('token_is_required vorher:', r.token_is_required)
# Erwartung/Doku: token_is_required soll False sein; konkrete Felder aus tokens.py ableiten
"`
Expected: dokumentierter, bewusster Zustand (öffentlich vs. Token).

- [ ] **Step 2: Entscheidung in der Spec festhalten** (`…/specs/2026-06-15-editorial-resume-theme-design.md`, Abschnitt „Daten & Persönliche Assets"): CV öffentlich, Anschreiben unlisted. Commit der Spec-Ergänzung.

---

## Phase 1 — Plugins (django-resume, TDD)

> Muster: `awards`/`languages` = `ListPlugin` (wie `projects`); `education`-Erweiterung = `SimplePlugin`-Form; `cover`-Erweiterung = Flat-Form. Tests in `django-resume/tests/`. Test-Runner: `cd /Users/katha/gitprojects/django-resume && uv run pytest`.

### Task 1.1: Education — Feld `degree`

**Files:**
- Modify: `src/django_resume/plugins/education.py`
- Test: `tests/plugins_data_test.py` (neuer Test) — Muster aus vorhandenen Tests übernehmen.

- [ ] **Step 1: Failing Test schreiben**

In `tests/plugins_data_test.py` ergänzen:
```python
def test_education_degree_field_roundtrips():
    from django_resume.plugins.education import EducationForm
    form = EducationForm(data={
        "school_name": "Rhein-Sieg-Akademie Hennef",
        "school_url": "https://example.com",
        "degree": "Diplom Grafik- und Kommunikations-Design",
        "start": "", "end": "2007",
    })
    assert form.is_valid(), form.errors
    assert form.cleaned_data["degree"] == "Diplom Grafik- und Kommunikations-Design"
```

- [ ] **Step 2: Test rot laufen lassen**

Run: `cd /Users/katha/gitprojects/django-resume && uv run pytest tests/plugins_data_test.py::test_education_degree_field_roundtrips -v`
Expected: FAIL (`degree` ist kein Feld).

- [ ] **Step 3: Feld ergänzen**

In `EducationForm` (nach `school_url`) einfügen:
```python
    degree = forms.CharField(
        label="Degree", max_length=200, required=False, initial="Degree"
    )
```

- [ ] **Step 4: Test grün**

Run: `cd /Users/katha/gitprojects/django-resume && uv run pytest tests/plugins_data_test.py::test_education_degree_field_roundtrips -v`
Expected: PASS.

- [ ] **Step 5: `degree`-Feld in ALLE Theme-Form-Templates aufnehmen (sonst Datenverlust beim Editieren)**

> **Codex-Review:** Das `education`-Form-Template rendert nur explizit gelistete Felder; beim Speichern wird `plugin_data` ersetzt. Ein nicht gepostetes Feld geht verloren. Daher das Input in `plain`, `headwind` **und** `editorial` ergänzen.

In `education/plain/form.html`, `education/headwind/form.html` und `education/editorial/form.html` neben den vorhandenen Feldern (`school_name` etc.) das Degree-Feld rendern, z. B.:
```html
<label>{{ form.degree.label }}{{ form.degree }}</label>
```
(Markup an das jeweils vorhandene Feld-Markup des Templates angleichen.)

- [ ] **Step 6: Roundtrip-Verifikation im Edit-Modus** — im Browser (`?edit=true`) Education editieren, `degree` setzen, speichern, neu laden → `degree` bleibt erhalten. (Bestätigt, dass kein Datenverlust auftritt.)

- [ ] **Step 7: Commit**

```bash
git add src/django_resume/plugins/education.py tests/plugins_data_test.py src/django_resume/templates/django_resume/plugins/education
git commit -m "Add degree field to education plugin and render it in all themes"
```

### Task 1.2: Awards-Plugin (ListPlugin)

**Files:**
- Create: `src/django_resume/plugins/awards.py`
- Modify: `src/django_resume/plugins/__init__.py`, `src/django_resume/apps.py`
- Test: `tests/awards_test.py`

- [ ] **Step 1: Failing Test schreiben**

Create `tests/awards_test.py` (nutzt die vorhandene `resume`-Fixture aus `tests/conftest.py`; `ListItemFormMixin.__init__` macht `kwargs.pop("resume")` → `resume` ist Pflicht):
```python
def test_awards_item_form_valid_and_context(resume):
    from django_resume.plugins.awards import AwardsItemForm
    form = AwardsItemForm(
        data={
            "id": "a1", "title": "ADC Germany 2024: Two Bronze awards",
            "project": "Project: Tomy Saurk", "year": "2024", "position": 0,
        },
        resume=resume,
        existing_items=[],
    )
    assert form.is_valid(), form.errors
    ctx = form.set_context(form.cleaned_data, {"edit_url": "#", "delete_url": "#"})
    assert ctx["award"]["title"].startswith("ADC Germany 2024")
    assert ctx["award"]["year"] == "2024"

def test_awards_plugin_registered():
    from django_resume.plugins import plugin_registry
    assert plugin_registry.get_plugin("awards") is not None
```

- [ ] **Step 2: Test rot**

Run: `cd /Users/katha/gitprojects/django-resume && uv run pytest tests/awards_test.py -v`
Expected: FAIL (`awards`-Modul fehlt).

- [ ] **Step 3: Plugin implementieren (Muster `projects`, ohne Markdown/Badges)**

Create `src/django_resume/plugins/awards.py`:
```python
from typing import Type, cast, Any

from django import forms

from .base import ListPlugin, ListItemFormMixin, ListInline, ContextDict


class AwardsItemForm(ListItemFormMixin, forms.Form):
    title = forms.CharField(widget=forms.TextInput())
    project = forms.CharField(widget=forms.TextInput(), required=False)
    year = forms.CharField(widget=forms.TextInput(), required=False)
    position = forms.IntegerField(widget=forms.NumberInput(), required=False)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.set_initial_position()

    @staticmethod
    def get_initial() -> ContextDict:
        return {"title": "Award Title", "project": "Project: …", "year": "2024"}

    def set_context(self, item: dict, context: ContextDict) -> ContextDict:
        context["award"] = {
            "id": item.get("id"),
            "title": item["title"],
            "project": item.get("project", ""),
            "year": item.get("year", ""),
            "edit_url": context.get("edit_url"),
            "delete_url": context.get("delete_url"),
        }
        return context

    @staticmethod
    def get_max_position(items: list[dict]) -> int:
        positions = [item.get("position", 0) for item in items]
        return max(positions) if positions else -1

    def set_initial_position(self) -> None:
        initial = cast(dict[str, Any], self.initial)
        if "position" not in initial:
            initial["position"] = self.get_max_position(self.existing_items) + 1
        self.initial = initial

    def clean_position(self) -> int:
        position = self.cleaned_data.get("position", 0) or 0
        if position < 0:
            raise forms.ValidationError("Position must be a positive integer.")
        for item in self.existing_items:
            if item["id"] == self.cleaned_data["id"]:
                continue
            if item.get("position") == position:
                max_position = self.get_max_position(self.existing_items)
                raise forms.ValidationError(
                    f"Position must be unique - take {max_position + 1} instead."
                )
        return position


class AwardsFlatForm(forms.Form):
    title = forms.CharField(
        widget=forms.TextInput(), required=False, max_length=50, initial="Awards"
    )

    @staticmethod
    def set_context(item: dict, context: ContextDict) -> ContextDict:
        context["awards"] = {"title": item.get("title", "")}
        context["awards"]["edit_flat_url"] = context["edit_flat_url"]
        return context


class AwardsPlugin(ListPlugin):
    name: str = "awards"
    verbose_name: str = "Awards"
    inline: ListInline
    flat_form_class = AwardsFlatForm
    sort_by_reverse_position: bool = False

    @staticmethod
    def get_form_classes() -> dict[str, Type[forms.Form]]:
        return {"item": AwardsItemForm, "flat": AwardsFlatForm}
```

- [ ] **Step 4: Export + Registrierung**

In `plugins/__init__.py`: `from .awards import AwardsPlugin` ergänzen und `"AwardsPlugin"` in `__all__`.
In `apps.py` `register_plugins()`: `plugins.AwardsPlugin,` in die Liste.

- [ ] **Step 5: Default-Templates (`plain` + `editorial`) anlegen, damit Rendering nicht crasht**

Run: `cd /Users/katha/gitprojects/django-resume && for t in plain editorial; do mkdir -p src/django_resume/templates/django_resume/plugins/awards/$t; for f in content flat flat_form item item_form; do cp src/django_resume/templates/django_resume/plugins/projects/plain/$f.html src/django_resume/templates/django_resume/plugins/awards/$t/$f.html; done; done`
Dann in den kopierten `awards`-Templates die Variablen `project`→`award`, `projects`→`awards` anpassen (Felder: title/project/year statt url/description/badges).

- [ ] **Step 6: Tests grün**

Run: `cd /Users/katha/gitprojects/django-resume && uv run pytest tests/awards_test.py -v`
Expected: PASS (beide).

- [ ] **Step 7: Commit**

```bash
git add src/django_resume/plugins/awards.py src/django_resume/plugins/__init__.py src/django_resume/apps.py src/django_resume/templates/django_resume/plugins/awards tests/awards_test.py
git commit -m "Add awards list plugin"
```

### Task 1.3: Languages-Plugin (ListPlugin mit Niveau)

**Files:**
- Create: `src/django_resume/plugins/languages.py`
- Modify: `plugins/__init__.py`, `apps.py`
- Test: `tests/languages_test.py`

- [ ] **Step 1: Failing Test**

Create `tests/languages_test.py` (ebenfalls mit `resume`-Fixture):
```python
def test_languages_item_form_builds_context(resume):
    from django_resume.plugins.languages import LanguagesItemForm
    form = LanguagesItemForm(
        data={"id": "l1", "name": "Deutsch", "level": 100, "position": 0},
        resume=resume,
        existing_items=[],
    )
    assert form.is_valid(), form.errors
    ctx = form.set_context(form.cleaned_data, {"edit_url": "#", "delete_url": "#"})
    assert ctx["language"]["name"] == "Deutsch"
    assert ctx["language"]["level"] == 100

def test_languages_level_out_of_range_invalid(resume):
    from django_resume.plugins.languages import LanguagesItemForm
    form = LanguagesItemForm(
        data={"id": "l2", "name": "Englisch", "level": 250, "position": 1},
        resume=resume,
        existing_items=[],
    )
    assert not form.is_valid()  # level > 100 (max_value=100)
```

- [ ] **Step 2: Test rot**

Run: `cd /Users/katha/gitprojects/django-resume && uv run pytest tests/languages_test.py -v`
Expected: FAIL (Modul fehlt).

- [ ] **Step 3: Implementieren (Muster wie Awards, Feld `level` 0–100)**

Create `src/django_resume/plugins/languages.py` — wie `awards.py`, aber Item-Felder:
```python
    name = forms.CharField(widget=forms.TextInput())
    level = forms.IntegerField(
        widget=forms.NumberInput(attrs={"min": 0, "max": 100}),
        min_value=0, max_value=100,
    )
    position = forms.IntegerField(widget=forms.NumberInput(), required=False)
```
`get_initial` → `{"name": "Sprache", "level": 80}`.
`set_context` → `context["language"] = {"id":…, "name": item["name"], "level": item["level"], "edit_url":…, "delete_url":…}`.
Flat-Form `title` initial `"Languages"`, `set_context` → `context["languages"] = {...}`.
Plugin `name="languages"`, `verbose_name="Languages"`, `flat_form_class=LanguagesFlatForm`, `get_form_classes` → item/flat.
(`set_initial_position`/`clean_position`/`get_max_position` analog Awards übernehmen.)

- [ ] **Step 4: Export + Registrierung** (`plugins/__init__.py`, `apps.py`) wie Task 1.2 Step 4.

- [ ] **Step 5: Templates (`plain` + `editorial`) aus `awards` kopieren und Variablen `award→language`, `awards→languages` anpassen.** Im `item.html` den Balken rein per CSS: `<span class="bar" style="--level: {{ language.level }}%"></span>` (Breite via CSS-Custom-Property, CSS-first).

- [ ] **Step 6: Tests grün**

Run: `cd /Users/katha/gitprojects/django-resume && uv run pytest tests/languages_test.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/django_resume/plugins/languages.py src/django_resume/plugins/__init__.py src/django_resume/apps.py src/django_resume/templates/django_resume/plugins/languages tests/languages_test.py
git commit -m "Add languages list plugin with proficiency level"
```

### Task 1.4: Cover-Erweiterung (Empfänger/Ort+Datum/Betreff/Anrede)

**Files:**
- Modify: `src/django_resume/plugins/cover.py` (`CoverFlatForm`)
- Test: `tests/plugins_data_test.py` (neuer Test)

- [ ] **Step 1: Failing Test**

In `tests/plugins_data_test.py` ergänzen:
```python
def test_cover_flat_form_carries_letter_meta():
    from django_resume.plugins.cover import CoverFlatForm
    item = {
        "title": "Bewerbung",
        "recipient": "An Musterfrau\nXYZ Firmenname\nMusterstraße 1234\n12345 Musterstadt",
        "place_date": "Düsseldorf, den XX.XX.26",
        "subject": "Bewerbung als Senior Art Directorin (Teilzeit, 25 Std./Woche)",
        "salutation": "Sehr geehrte Frau Musterfrau,",
    }
    ctx = CoverFlatForm.set_context(item, {"edit_flat_url": "#"})
    assert ctx["cover"]["subject"].startswith("Bewerbung als")
    assert ctx["cover"]["place_date"] == "Düsseldorf, den XX.XX.26"
    assert "Musterstraße" in ctx["cover"]["recipient"]
    assert ctx["cover"]["salutation"].startswith("Sehr geehrte")
```

- [ ] **Step 2: Test rot**

Run: `cd /Users/katha/gitprojects/django-resume && uv run pytest tests/plugins_data_test.py::test_cover_flat_form_carries_letter_meta -v`
Expected: FAIL (Keys fehlen).

- [ ] **Step 3: Felder + Kontext ergänzen**

In `CoverFlatForm` ergänzen:
```python
    recipient = forms.CharField(widget=forms.Textarea(), required=False)
    place_date = forms.CharField(widget=forms.TextInput(), required=False, max_length=100)
    subject = forms.CharField(widget=forms.TextInput(), required=False, max_length=200)
    salutation = forms.CharField(widget=forms.TextInput(), required=False, max_length=200)
```
In `CoverFlatForm.set_context` die vier Keys **direkt in das `context["cover"] = {...}`-Literal** aufnehmen (nicht per `.update` davor — das `cover`-Dict wird in dieser Methode erst erzeugt, siehe `cover.py` `set_context`). Das Literal also erweitern um:
```python
            "recipient": item.get("recipient", ""),
            "place_date": item.get("place_date", ""),
            "subject": item.get("subject", ""),
            "salutation": item.get("salutation", ""),
```

- [ ] **Step 4: Test grün**

Run: `cd /Users/katha/gitprojects/django-resume && uv run pytest tests/plugins_data_test.py::test_cover_flat_form_carries_letter_meta -v`
Expected: PASS.

- [ ] **Step 5: Cover-Felder in ALLE Flat-Form-Templates aufnehmen (sonst Datenverlust beim Editieren)**

> **Codex-Review:** Wie bei Education — nicht gepostete Felder gehen beim Speichern verloren. Die vier Inputs in `cover/plain/flat_form.html`, `cover/headwind/flat_form.html` und `cover/editorial/flat_form.html` ergänzen (Markup an vorhandene Felder angleichen):
```html
<label>{{ form.subject.label }}{{ form.subject }}</label>
<label>{{ form.recipient.label }}{{ form.recipient }}</label>
<label>{{ form.place_date.label }}{{ form.place_date }}</label>
<label>{{ form.salutation.label }}{{ form.salutation }}</label>
```

- [ ] **Step 6: Volle Plugin-Suite grün halten**

Run: `cd /Users/katha/gitprojects/django-resume && uv run pytest tests/plugins_data_test.py tests/awards_test.py tests/languages_test.py -q`
Expected: alle PASS.

- [ ] **Step 7: Roundtrip-Verifikation im Edit-Modus** — Cover-Flat editieren, alle vier Felder setzen, speichern, neu laden → Werte bleiben erhalten.

- [ ] **Step 8: Commit**

```bash
git add src/django_resume/plugins/cover.py tests/plugins_data_test.py src/django_resume/templates/django_resume/plugins/cover
git commit -m "Add recipient, place/date, subject and salutation to cover plugin (all themes)"
```

---

## Phase 2 — Editorial-Theme: CV Web (Layout & CSS)

> Visuelle Arbeit → kein Pixel-TDD, sondern **Verify-Loop**: Template/CSS bauen, mit echten Daten rendern, per Playwright Screenshot gegen das PDF abgleichen. Source of Truth: `050326_Lebenslauf…pdf` + `VC.idml` (Farbe Creme `#F2F2E5`, Text Schwarz). Every-Layout-Primitive bevorzugen.

### Task 2.1: Saira-Webfont einbinden

**Files:**
- Create: `src/django_resume/static/django_resume/fonts/saira/*` (Saira Variable, OFL)
- Create: `src/django_resume/static/django_resume/css/editorial/screen.css`

- [ ] **Step 1: Saira-Variable-Fonts ins Theme legen** (aus `~/Documents/Meine_Daten/050326…/Document fonts/Saira-*VariableFont*.ttf`, in `woff2` konvertiert) + OFL-License-Datei daneben.
- [ ] **Step 2: `@font-face` (normal + italic) in `screen.css`** mit `font-display: swap`.
- [ ] **Step 3: Verifikation** — `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8001/static/django_resume/css/editorial/screen.css` → `200` (nach `collectstatic`/Dev-Serve).
- [ ] **Step 4: Commit** `git commit -m "Add Saira webfont to editorial theme"`.

### Task 2.2: CV-Daten befüllen (lokal, für realistische Vorschau)

**Files:** keine; Django-Shell gegen lokale DB.

- [ ] **Step 1: Resume `katharina` mit identity/timelines/skills/education/awards/languages aus dem PDF befüllen** (ein Shell-Skript, das `plugin_data` setzt — Werte 1:1 aus `050326_Lebenslauf…pdf`).
- [ ] **Step 2: Foto** aus `…/Links/` als `identity.avatar_img` hochladen (Media).
- [ ] **Step 3: Verifikation** — CV rendert mit echten Inhalten unter `http://localhost:8001/resume/katharina/cv/` (eingeloggt). Kein Fehler, Inhalte sichtbar.

### Task 2.3: CV-Layout (Header + Work Experience + rechte Spalte)

**Files:**
- Modify: `…/pages/editorial/resume_cv.html`
- Modify: `…/plugins/identity/editorial/content.html`, `…/plugins/timelines/editorial/*`, `…/plugins/skills/editorial/*`
- Modify: `src/django_resume/static/django_resume/css/editorial/screen.css`

- [ ] **Step 1: Grid-Grundgerüst** — zweispaltig (Haupt: Work Experience; rechte Spalte: Foto, Skills, Sprachen, Education, Awards), Header oben über die volle Breite (großes „Katharina" in Saira Thin + „WERSDÖRFER" bold + „Senior Art Director" + Kontaktblock rechts). Every-Layout: Sidebar/Stack/Cluster.
- [ ] **Step 2: Responsive** — unter Breakpoint kollabiert die rechte Spalte unter den Hauptteil (CSS, ohne JS).
- [ ] **Step 3: Verify-Loop (Screenshot vs. PDF)** — Playwright MCP: `browser_navigate` auf den CV, `browser_take_screenshot`, visuell mit PDF-Seite 1 vergleichen, CSS iterieren bis Layout/Typo/Abstände passen.
- [ ] **Step 4: Commit** `git commit -m "Lay out editorial CV: header, work experience, right column"`.

### Task 2.4: Skills- & Sprachen-Darstellung (Tags + Balken)

- [ ] **Step 1: Skills als Tag-/Badge-Cluster** („Let's talk about"), zweifarbig wie Vorlage (gefüllte vs. umrandete Tags) per CSS.
- [ ] **Step 2: Sprach-Balken** — `languages/editorial/item.html` rendert `.bar` mit `--level`; CSS zeichnet Fortschritt (CSS-first, kein JS).
- [ ] **Step 3: Verify-Loop** gegen PDF (rechte Spalte).
- [ ] **Step 4: Commit** `git commit -m "Style skills tags and language bars in editorial theme"`.

### Task 2.5: Education- & Awards-Darstellung

- [ ] **Step 1: Education** (Jahr groß, Abschluss bold, Schule darunter) via `education/editorial/content.html` (+ `degree`).
- [ ] **Step 2: Awards-Leiste** unten (zwei Spalten, ADC 2024 / 2020) via `awards/editorial/*`.
- [ ] **Step 3: Verify-Loop** gegen PDF-Fußbereich.
- [ ] **Step 4: Commit** `git commit -m "Style education and awards in editorial theme"`.

### Task 2.6: Script-Label-SVG-Platzhalter (Cervanttis)

**Files:**
- Create: `src/django_resume/static/django_resume/img/editorial/labels/*.svg` **(gitignored — Cervanttis, NICHT ins Paket committen)**
- Modify: `screen.css` + betroffene Templates

- [ ] **Step 1: SVGs aus Cervanttis erzeugen** für „Contact", „Work Experience", „Education", „Awards", „Let's talk about" (Text→Pfad).
- [ ] **Step 2: In den Templates die Section-Labels durch die SVGs ersetzen** (als `<img>`/inline-SVG, rotierte Platzierung wie Vorlage).
- [ ] **Step 3: `.gitignore` in django-resume** um `static/django_resume/img/editorial/labels/` ergänzen, damit die kommerziellen SVGs nicht ins Paket gelangen. **Verweis auf Release-Blocker (Phase 6).**
- [ ] **Step 4: Verify-Loop** + **Step 5: Commit** (nur Template/CSS-Hooks, KEINE SVGs) `git commit -m "Wire script label placeholders into editorial theme (assets gitignored)"`.

---

## Phase 3 — Editorial-Theme: CV Print/PDF

**Files:**
- Create: `src/django_resume/static/django_resume/css/editorial/print.css`
- Modify: `…/pages/editorial/base.html` (Print-CSS via `media="print"`)

- [ ] **Step 1: `@page`-Setup** — **A4**, exakte Ränder aus `VC.idml` übernehmen; Creme-Hintergrund (`#F2F2E5`) via `print-color-adjust: exact` erzwingen.
- [ ] **Step 2: Print-Layout** — Bildschirm-Layout für A4 adaptieren; `break-inside: avoid` für Timeline-Einträge/Awards; saubere Seitenumbrüche, längere Inhalte erzeugen Folgeseiten korrekt.
- [ ] **Step 3: Verify (reproduzierbar, festgelegtes Akzeptanzkriterium)** — Referenz-Renderer = **Chromium via Playwright**, `page.pdf({format: 'A4', printBackground: true, margin: <aus IDML>})`. Erzeugtes PDF Seite-für-Seite gegen `050326_Lebenslauf…pdf` vergleichen (Screenshot-Diff). **Akzeptanz:** Header, Spaltenaufteilung, Typo-Größen und Awards-Leiste stimmen visuell überein; keine ungewollten Umbrüche mitten in Einträgen. **Hinweis:** Der interaktive Browser-Druckdialog kann je nach Browser leicht abweichen; maßgeblich ist die Chromium/Playwright-Ausgabe.
- [ ] **Step 4: Commit** `git commit -m "Add print stylesheet for editorial CV (PDF parity)"`.

---

## Phase 4 — Editorial-Theme: Anschreiben (Web + Print)

**Files:**
- Modify: `…/pages/editorial/resume_detail.html`
- Modify: `…/plugins/cover/editorial/*` (flat + items + forms)
- Modify: `screen.css`, `print.css`

- [ ] **Step 1: Cover-Layout** — gleicher Header wie CV; darunter Empfängerblock + Ort/Datum (rechts), Betreff (bold), Anrede, Absätze (cover-items), Grußformel + Unterschrift-Bild.
- [ ] **Step 2: Unterschrift** als persönliches Media-Bild einbinden (gitignored, nicht ins Paket).
- [ ] **Step 3: Zweites Anschreiben anlegen** (eigener Resume-Slug, z. B. `katharina-musterfirma`) zur Verifikation, dass mehrere Anschreiben unabhängig sind.
- [ ] **Step 4: Verify-Loop** (Web + Print) gegen `050326_Anschreiben…pdf`.
- [ ] **Step 5: Commit** `git commit -m "Style cover letter (Anschreiben) in editorial theme"`.

---

## Phase 5 — Integration, Tests & Theme-Test

**Files:**
- Modify: `django-resume/tests/theme_test.py` (editorial-Theme rendert), e2e-Test in `e2e_tests/`
- Modify: `homepage/pyproject.toml` (zurück auf Git-Source vor Merge)

- [ ] **Step 1: Theme-Test** (`tests/theme_test.py`) — Resume mit `theme=editorial` rendert CV + Cover mit Status 200. **Explizit prüfen (Codex-Review):** dass die gerenderte CV-Seite die Awards- **und** Sprach-Inhalte enthält (z. B. „ADC Germany 2024" und „Deutsch") — das verifiziert, dass die aus `projects` geklonten/umbenannten ListPlugin-Templates (`content/flat/flat_form/item/item_form`) mit den richtigen Context-Keys (`award`/`awards`, `language`/`languages`) rendern.
- [ ] **Step 2: e2e (Playwright in django-resume)** — Edit-Modus: ein Award hinzufügen, speichern, erscheint gerendert; analog ein Language-Eintrag.
- [ ] **Step 3: Volle Suite** `cd /Users/katha/gitprojects/django-resume && uv run pytest -q` → grün.
- [ ] **Step 4: Lokale Integration (KEIN offizieller Release)** — in homepage `pyproject.toml` `django-resume` auf den **Branch/Commit** `editorial-theme` pinnen (Git-Source, kein PyPI-Release), `uv sync`, prek-Hook prüfen. **Wichtig:** Das `editorial`-Theme ist hier noch NICHT offiziell freigegeben — die Cervanttis/SVG-Platzhalter sind noch drin (Release-Blocker, Phase 6).
- [ ] **Step 5: Homepage-seitiger Smoke-Test** auf `:8001` (CV + Anschreiben rendern aus der gepinnten Git-Source).
- [ ] **Step 6: Commit (homepage)** `git commit -m "Pin django-resume to editorial-theme branch; render Katharina CV and cover"`.

---

## Phase 6 — Release-Blocker: Freie Script-Font

> **⚠️ Das editorial-Theme darf erst offiziell freigegeben/veröffentlicht werden, wenn dieser Schritt erledigt ist.** Die Cervanttis-SVG-Platzhalter sind kommerziell und nicht redistribuierbar.

- [ ] **Step 1: 2–3 OFL-Script-Fonts vorschlagen** (nah an Cervanttis) und eine auswählen.
- [ ] **Step 2: Gewählte OFL-Font als Webfont ins Theme** (`static/.../fonts/script/`, OFL-License) und Section-Labels von SVG zurück auf **echten Text** im Script-Font umstellen.
- [ ] **Step 3: `.gitignore`-Eintrag der Platzhalter-SVGs entfernen** ist nicht nötig — die SVGs verschwinden ganz; sicherstellen, dass keine Cervanttis-Artefakte im Paket sind (`git grep -i cervanttis` in django-resume → leer).
- [ ] **Step 4: Verify-Loop** — Look bleibt nah an der Vorlage; Katharinas Deployment kann optional Cervanttis via Override (homepage, gitignored) nutzen.
- [ ] **Step 5: Commit** `git commit -m "Ship free OFL script font; editorial theme fully redistributable"`.
- [ ] **Step 6: JETZT offizieller Release** — `django-resume` mergen + Tag/Release (PyPI nach Wahl); erst hier ist `editorial` redistribuierbar, weil keine kommerziellen Assets mehr enthalten sind (`git grep -i cervanttis` leer).
- [ ] **Step 7: Homepage auf Release umpinnen** — in homepage `pyproject.toml` `django-resume` von der `editorial-theme`-Branch auf den **veröffentlichten Tag/Release** stellen; `uv sync`; prek-Hook; Smoke-Test auf `:8001`; Commit `git commit -m "Pin django-resume to released version with editorial theme"`.

---

## Phase 7 — Ausblick: Portfolio (zukünftiges, eigenes Projekt)

> **Bewusst vorgesehen, aber außerhalb dieses Plans.** Wird in einer späteren, gemeinsamen Session als **eigene Spec + eigener Plan** umgesetzt.

Geplante Richtung (Notiz, keine Tasks hier):
- Portfolio (Webdesign / Illustration / Print-Beispiele, ausgewählte Projekte) als **neues django-resume-Plugin** (z. B. `portfolio`/`gallery`) mit Medien-Galerie und Kategorien — analog zu `projects`, aber bildlastig.
- Eigenes Theme oder Erweiterung des `editorial`-Themes für die Galerie-Ansichten.
- Eingehängt in dasselbe Seitenkonstrukt (eigener Resume-Slug bzw. eigene Route).
- Material, das dann gebraucht wird: kuratierte Projektbilder, Kategorien, kurze Beschreigungen.
- Architekturentscheidung Plugin-vs-eigenes-App in der Portfolio-Spec treffen; die hier etablierten Muster (ListPlugin, Theme-Templating, CSS-first, Print-Parität) wiederverwenden.

---

## Self-Review (durchgeführt)

- **Spec-Abdeckung:** identity/timelines/skills ✓ (Phase 2); education+degree ✓ (1.1/2.5); awards ✓ (1.2/2.5); languages ✓ (1.3/2.4); cover-Erweiterung ✓ (1.4/4); Theme web ✓ (2); print/PDF ✓ (3); Anschreiben ✓ (4); editierbarkeit/mehrere Anschreiben ✓ (0.2/4); freie Script-Font/Release-Blocker ✓ (6); Portfolio-Ausblick ✓ (7); Dev-Workflow/editable/Tests ✓ (0.1/5).
- **Platzhalter-Scan:** keine TBD/TODO; visuelle Tasks bewusst als Verify-Loop statt Pixel-TDD (begründet).
- **Typ-Konsistenz:** Kontext-Keys konsistent (`award`/`awards`, `language`/`languages`, `cover.{recipient,place_date,subject,salutation}`); Plugin-`name`-Strings (`awards`,`languages`) = Template-Verzeichnisnamen = Registrierungsnamen.
