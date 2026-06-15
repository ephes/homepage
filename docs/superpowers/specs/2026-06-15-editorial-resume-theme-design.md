# Design: „editorial" Resume-Theme + Plugins für CV & Anschreiben

**Datum:** 2026-06-15
**Status:** Spec / Designentwurf
**Repos:** `homepage` (Daten/Deployment) und `django-resume` (Theme + Plugins, upstream)

## Ziel

Katharina Wersdörfers Lebenslauf und Bewerbungsanschreiben sollen auf der Homepage
(`wersdoerfer.de`) gepflegt, als responsive Website dargestellt und als PDF (pixelnah
zur bestehenden InDesign-Vorlage) ausgegeben werden können — auf Basis von
[`django-resume`](../../../../django-resume), das bereits in die Homepage integriert ist.

Designvorlage (Source of Truth für Look & Inhalt):
- `/Users/katha/Documents/CV_Anschreiben/050326_Lebenslauf_Katharina_Wersdoerfer.pdf`
- `/Users/katha/Documents/CV_Anschreiben/050326_Anschreiben_Katharina_Wersdoerfer.pdf`
- InDesign-Quelle: `/Users/katha/Documents/Meine_Daten/050326_Lebenslauf_Katharina_Wersdoerfer/`
  (`VC.idml` → exakte Farben/Größen/Abstände; `Document fonts/`; `Links/` Portraitfoto)

## Scope

**In Scope (diese Spec):**
- Ein offizielles `django-resume`-Theme `editorial`, das die Vorlage nachbildet (Web + Print/PDF).
- Generische Plugins/Erweiterungen, die der CV/das Anschreiben brauchen.
- Befüllung von Katharinas Daten in der Homepage (Resume-Datensätze + Media).

**Out of Scope (eigene spätere Projekte):**
- Portfolio-Website (Webdesign/Illustration/Print) — später, eigenes Projekt, evtl. eigenes
  `django-resume`-Plugin. Eigene Spec.

## Architektur — Verortung der Artefakte

Leitprinzip: **Funktionalität und Optik gehen upstream nach `django-resume`; nur persönliche
Inhalte bleiben in der Homepage.**

| Artefakt | Gehört nach | Begründung |
|---|---|---|
| Plugins: `awards`, `languages` | `django-resume` (core) | generische Resume-Bausteine wie `skills`/`education`/`projects` |
| Erweiterungen: `cover` (Empfänger/Datum/Betreff/Anrede), `education` (Abschlusstitel) | `django-resume` (core) | generische Verbesserungen vorhandener Plugins |
| Theme `editorial` (Templates, CSS, Saira-Font, Script-Assets) | `django-resume` (offizielles Theme) | Theme = reine Präsentation; Saira ist OFL → frei mitlieferbar |
| Portraitfoto, Unterschrift, konkrete Texte/Daten | Homepage-DB / Media | persönliche Inhalte, nie im Paket |

**Template-Auflösung:** `django-resume` lädt Plugin-/Seiten-Templates über den Pfad
`django_resume/plugins/{plugin}/{theme}/{template}` bzw. `django_resume/pages/{theme}/...`.
Das Theme ist nur der String `theme` im `theme`-Plugin pro Resume; es gibt **keine
Theme-Registry** — jeder String mit passenden Templates funktioniert.

**Externe Plugins:** `django-resume` unterstützt projekt-/paketeigene Plugins via
`plugin_registry.register(...)` in `AppConfig.ready()` (siehe
`django-resume/docs/guide/creating_simple_plugins.txt`). Die neuen Plugins werden jedoch
**im Paket selbst** registriert (in `ResumeConfig.register_plugins()`), da sie upstream gehören.

## Mapping: PDF-Abschnitte → Plugins

| PDF-Abschnitt | Plugin | Status |
|---|---|---|
| Name, Rolle, Foto, Kontakt (Adresse/Tel./Mail) | `identity` | vorhanden |
| Work Experience (Timeline: Zeitraum, Firma, Rolle, Bullets, „Kunden:") | `timelines` | vorhanden |
| Skills-Tags „Let's talk about" | `skills` | vorhanden |
| Education | `education` | **erweitern**: Abschlusstitel ergänzen (aktuell nur Schule + Jahr) |
| Awards (ADC 2024/2020 + Projekt) | `awards` | **neu** |
| Sprachen mit Niveau-Balken (Deutsch/Englisch) | `languages` | **neu** |
| Anschreiben (Absätze + Foto) | `cover` | **erweitern**: Empfänger / Ort+Datum / Betreff / Anrede |
| Look + Zugriffsschutz CV | `theme`, `tokens` | vorhanden |

### Neues Plugin: `awards`
Listen-Plugin (analog `projects`). Felder je Eintrag:
- `title` (z. B. „ADC Germany 2024: Two Bronze awards")
- `year` / `date` (Anzeige-String)
- `project` (z. B. „Project: Tomy Saurk")
- `position` (Sortierung)

### Neues Plugin: `languages`
Listen-Plugin für die Niveau-Balken. Felder je Eintrag:
- `name` (z. B. „Deutsch")
- `level` (numerisch, z. B. 0–100, für die Balkenbreite — CSS-gesteuert)
- `position`

### Erweiterung: `cover`
Heute: `title`, `avatar`, Liste von Absatz-Items (`text`, Markdown). Ergänzen (Flat-Form), damit
jedes Anschreiben pro Stelle anpassbar ist:
- `recipient` (mehrzeilig: „An … / Firma / Straße / PLZ Ort")
- `place_date` (z. B. „Düsseldorf, den XX.XX.26")
- `subject` (Betreff, z. B. „Bewerbung als Senior Art Directorin (Teilzeit, 25 Std./Woche)")
- `salutation` (z. B. „Sehr geehrte Frau Musterfrau,")
- Unterschrift = persönliches Media-Bild (kein Plugin-Feld; Theme bindet es ein)

Jedes Anschreiben ist ein **eigener `Resume`-Datensatz mit eigenem Slug** (z. B.
`/resume/katharina-firma-x/`). Der CV liegt unter `/resume/katharina/cv/`.

### Erweiterung: `education`
Feld `degree` (Abschlusstitel, z. B. „Diplom Grafik- und Kommunikations-Design") ergänzen.

## Theme `editorial`

- **Schriften:**
  - **Saira** (Variable, OFL) — Headline „Katharina", Fließtext, Daten. Wird als Webfont
    **im Theme mitgeliefert**.
  - **Script (dekorativ):** „Contact", „Work Experience", „Education", „Awards",
    „Let's talk about" sowie die Unterschrift. Vorlage nutzt **Cervanttis** (Creatype Studio,
    kommerziell). Für die Labels: vorerst **SVG-Platzhalter** (aus Cervanttis erzeugt).
- **Farben:** Hintergrund Creme `#F2F2E5` (CMYK 5/5/10/0 aus `VC.idml`), Text Schwarz.
  Exakte weitere Werte werden aus der IDML übernommen.
- **Web:** responsive auf allen Geräten (Every-Layout-Primitive bevorzugt, CSS-first).
- **Print/PDF:** über `print.css` mit `@page` (Browser „Drucken → PDF", kein Headless-Renderer).
  Saubere Seitenumbrüche; zusätzliche Seiten werden bei längeren Inhalten korrekt erzeugt.
  PDF-Ausgabe = pixelnah zur Vorlage.

### ⚠️ Release-Blocker (offizielles Theme)
Die aus **Cervanttis** erzeugten **SVG-Platzhalter dürfen NICHT ins öffentliche
`django-resume`-Paket committet werden** (kommerzielle Schrift). Sie bleiben lokal/persönlich
(gitignored). **Bevor das `editorial`-Theme offiziell freigegeben/veröffentlicht werden darf,
müssen die Platzhalter durch eine frei lizenzierte Script-Font (OFL) ersetzt werden** —
mitgeliefert als Webfont, sodass das Theme vollständig redistribuierbar ist und die Labels
echter Text bleiben. Katharinas eigenes Deployment kann Cervanttis weiterhin als Override nutzen.

## Daten & Persönliche Assets (Homepage)

- **Resume-Datensätze:** `katharina` (CV) + pro Anschreiben ein eigener Slug.
- **Inhalte:** aus den PDFs übernommen (Work Experience, Skills, Education, Awards, Sprachen,
  Kontakt, Anschreiben-Text).
- **Media benötigt:** Portraitfoto (vorhanden in `…/Links/`, AI-generiert — ggf. später ersetzen),
  **Unterschrift** als transparentes PNG/SVG.
- **Pflege:** Inline-Editing im Browser (`?edit=true`), kein Admin-Zwang.

## Dev-Workflow

- **Lokale DB:** Produktions-Dump bereits eingespielt (`just`/`commands.py production-db-to-local`
  bzw. manuell), Migrationen angewendet. Dev-Server läuft auf **Port 8001** (Port 8000 ist durch
  ein anderes Projekt belegt).
- **Editable `django-resume`:** `../django-resume` editierbar einbinden (uv source path), damit
  Theme + Plugins live entwickelt werden und die Homepage sie konsumiert.
- **Tests:** Unit-/e2e-Tests für die neuen Plugins und das Theme **in `django-resume`** (pytest;
  e2e dort vorhanden). Homepage-seitig nur, was die Integration/Daten betrifft.
- **prek-Hook:** verhindert das Committen lokaler Editable-Pfade in `pyproject.toml` — vor dem
  Commit zurück auf Git-Source schalten.

## Phasen

1. **Setup** — `../django-resume` editierbar einbinden; Katharina-User + Resume `katharina`
   anlegen und aus PDF-Daten befüllen; Theme-Gerüst `editorial` (Seiten-Templates + Basis-CSS).
2. **Lebenslauf (Web)** — Plugins fertigstellen (vorhanden: identity/timelines/skills/education
   +degree; neu: `awards`, `languages`) inkl. Default-Rendering + Tests → dann `editorial`-Templates
   & CSS responsiv nach Vorlage. Script als SVG-Platzhalter.
3. **Lebenslauf (Print/PDF)** — `print.css` mit `@page`, Seitenumbrüche, PDF = pixelnah.
4. **Anschreiben** — `cover`-Erweiterung + `editorial`-Templates (Web + Print). Mehrere
   Anschreiben = mehrere Resume-Slugs.
5. **Politur & freie Script-Font** — Swap der SVG-Platzhalter auf OFL-Script-Font (erfüllt den
   Release-Blocker), e2e in `django-resume`.

## Offene Punkte / Defaults

- **Theme-Name:** Default `editorial` (kann vor Implementierung noch geändert werden).
- **Freie Script-Font:** 2–3 OFL-Kandidaten nahe Cervanttis werden in Phase 5 vorgeschlagen.
- **Portraitfoto:** vorerst das vorhandene AI-Foto; ggf. später ersetzen.
