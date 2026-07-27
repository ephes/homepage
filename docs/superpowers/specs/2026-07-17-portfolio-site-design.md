# Design: Portfolio-Site „Katharina" (Wagtail, Nexola-Vorlage)

**Datum:** 2026-07-17
**Status:** Spec / Designentwurf
**Repo:** `homepage` (alles homepage-eigen, kein django-resume-Anteil)
**URL:** `https://wersdoerfer.de/portfolio/katharina/` (Unterbaum der bestehenden Site, kein Multi-Site)

## Ziel

Katharina bekommt eine repräsentative Portfolio-Site für potenzielle Kunden: 9–10 Projekte
(Web mit Live-URL, Print, Illustration), alle von der Startseite aus verlinkt, jedes mit
eigener Unterseite. Vollständig in Wagtail pflegbar: **neue Projektseite anlegen → Kachel
erscheint automatisch auf der Startseite** (Reihenfolge = Wagtail-Seitenreihenfolge).
Sprache: Deutsch.

**Designvorlage (Source of Truth für Look & Verhalten):** https://nexola.framer.website/
(Framer-Template). Wir übernehmen Optik und Verhalten so genau wie sinnvoll, bauen aber
komplett neu:

- **Every Layout ist Pflicht** — wo immer eine Komponente mit Every-Layout-Primitiven
  (Stack, Center, Cluster, Sidebar, Switcher, Grid, Frame, Cover) gebaut werden kann,
  tun wir das.
- **CSS-first** — JavaScript nur, wo es nicht anders geht. Nach jetzigem Stand einzige
  Kandidaten: Scroll-Trigger der Appear-Animationen (erst `animation-timeline: view()`
  probieren, sonst minimaler IntersectionObserver) und ggf. das Burger-Menü
  (erst `<details>`/`:popover` probieren).
- Fonts + Grundfarbwelt kommen vom Editorial-CV-Theme (Saira + Astagina Signature, Creme).

**Nicht-Ziele:**
- Keine Video-Case-Study-Section (Nexola-Home Section 5) — bewusst ausgespart; der Platz
  zwischen Projekt-Panel und About bleibt frei für eine spätere eigene Idee.
- Keine Mehrsprachigkeit (erst mal nur Deutsch), kein Wagtail-Multi-Site.
- Keine automatische Mockup-/Asset-Erzeugung — Bilder liefert Katharina, wir definieren
  nur die Formate (siehe unten).
- Keine separate Projekt-Übersichtsseite mit Filter (Nexola `/projects`) — alle Projekte
  hängen direkt an der Startseite.

## Nexola-Analyse (extrahierte Fakten)

Quellen: statisches Framer-HTML von Home, `/projects`, `/projects/auralis-living`, `/about`
(heruntergeladen 2026-07-17; Scratchpad, bei Bedarf neu ziehen — Struktur ist hier vollständig
dokumentiert).

### Farb-Tokens (Nexola → unsere Entsprechung)

| Rolle | Nexola | Bei uns |
|---|---|---|
| Grundfläche | `#f6f6f6` | **CV-Creme** (`--editorial-bg` `#F0ECE2`; InDesign-Original `#f4f1e8`) |
| Text | `#0f0f0f` | warmes Near-Black des CV (`#171410`) |
| Sekundärtext | `#6b6b6b` | warmgrauer Pendant, wird abgestimmt |
| **Haarlinien** | `#e0e0e0`, 1px | Haarlinien-Token des CV (`--editorial-rule`), **eher noch feiner** als im CV |
| Dunkle Flächen/Buttons | `#303030` / `#0f0f0f` | Near-Black |
| Akzent | Lime `rgb(179,255,0)`, sehr sparsam | **liefert Katharina noch** — bis dahin Platzhalter-Token `--portfolio-accent` |

Die „sichtbare Grid-Struktur" von Nexola ist kein Grid-Feature, sondern **selektive
1px-Borders an Section- und Kachel-Containern** (mal nur top, mal top+bottom, mal seitlich).
Genau so bauen wir sie: ein Haarlinien-Token, Borders an den Containern — die Linienstruktur
hält alles zusammen (wie im CV).

### Typo-Skala (Nexola-px, Desktop/Tablet/Phone → wird als clamp()-Skala auf Saira übertragen)

| Rolle | Desktop | Phone | Weight | line-height |
|---|---|---|---|---|
| Display (Hero-Wortmarke) | 130 (bis 200 auf 4k) | 76 | 800 | 0.8 |
| Section-Titel („Projects") | 95 (120) | 58 | 600 | 1.0 |
| Sub-Titel / Result-Zahlen | 68 (90) | 54 | 600 | 0.9 |
| Statement (Intro-h3) | 50 (54) | 38 | 600 | 1.0 |
| Zwischengröße (Kennzahlen, Projekt-Intro) | 32 (38) | 27 | 600 | 1.1 |
| h5 (Kachel-Titel groß) | 25 (28) | 22 | 600 | 1.1 |
| Fließtext/Zitate | 19 (21) | 17 | 500 | 1.1 |
| Metrik-Chips | 17 (21) | 13 | 600 | 1.1 |
| Labels („Available for Projects") | 12 (14) | 12 | 600 | 1.2 |
| Kleintext | 14 (16) | 14 | 400 | 1.2 |

Nexola nutzt Inter Display; wir setzen **Saira**. Saira ist schmaler/anders im Grauwert —
Weights werden live im Browser abgestimmt (bewährter Workflow aus dem CV-Projekt).

### Verhalten / Animation

- Fast alles erscheint animiert (Opacity 0 → 1 + Translate) mit zwei Timing-Kurven:
  **0.8s `cubic-bezier(0.75, 0, 0.25, 1)`** und **1s `cubic-bezier(0.5, 0, 0.5, 1)`**.
- Hero hat einen Bild-Reveal (zwei Ebenen „Unrevealed/Revealed Image").
- Buttons: Pills (`border-radius: 100px`) mit Punkt-Indikatoren (Dot-Swap beim Hover),
  helle und dunkle Variante.
- Header mit `backdrop-filter`-Blur, „Available for Projects"-Indicator mit grünem Punkt.
- Hover-Feinheiten und Animations-Choreografie stecken im kompilierten Framer-JS →
  werden **durch Beobachten der Live-Seite** (Playwright) nachgestellt, nicht aus dem Code.
- Umsetzung CSS-first: Appear als `@keyframes` + Scroll-Trigger s. o.; Reveals mit
  `clip-path`-Transitions; `prefers-reduced-motion` wird respektiert (alles sofort sichtbar).

### Nexola-Seitenaufbau (Referenz)

- **Home:** Header → Hero (Headline + Kennzahlen mit „(01)"-Nummerierung + Bild-Reveal +
  2 Buttons) → Intro (Statement + Zitat + 3 Kennzahlen) → Projects (3 große Teaser) →
  Case Study *(bei uns gestrichen)* → Skillset mit Metrik-Chips → Kontakt-CTA/Footer.
- **Projektseite:** Hero (Projektname h1 + Metadaten-Raster: Field / Delivery / Outcome /
  Focus / Zeit) → Hero-Bild → Intro-Statement → Challenge → Solution → Results (4 große
  Zahlen) → 2×2-Galerie → Testimonial → More Projects (2 Teaser) → Kontakt-CTA.

## Unsere Startseite (PortfolioIndexPage)

Reihenfolge (Entscheidung Katharina): **Hero (welcome) → Recent Projects → About → Contact.**

1. **Header** — schlank: Wortmarke/Name, „Verfügbar für Projekte"-Indicator (optional
   an-/abschaltbar), Kontakt-Button. Sticky mit Blur wie Nexola.
2. **Hero** — kurz: Welcome-Headline (Display-Größe), evtl. Unterzeile. Kein großes
   Bild-Feature nötig; Bild-Reveal-Baustein steht aber als Komponente bereit.
3. **Recent Projects — das Teaser-Panel (Herzstück), Entscheidung Katharina:**
   **4-Spalten-Grid im Wechselrhythmus**: eine Karte über 2 Spalten + zwei über je 1,
   nächste Reihe gespiegelt (klein, klein, groß), immer abwechselnd.
   - Muster wiederholt sich alle 6 Kacheln → **reine CSS-Steuerung über
     `:nth-child(6n+1)` und `:nth-child(6n)`** (= die `span 2`-Karten). Kein
     Featured-Flag, keine Extra-Klassen; die Wagtail-Seitenreihenfolge bestimmt alles.
     Auto-Placement füllt die Reihen von selbst korrekt (1=span2,2,3 / 4,5,6=span2 / …).
   - 9 Projekte = exakt 3 Reihen. Beim 10. Projekt bleibt eine Restreihe mit 1 Kachel —
     Vorschlag: die Lücke füllt eine **CTA-Kachel** („Projekt anfragen →"), dann geht die
     Reihe nie leer aus. (Offener Punkt, s. u.)
   - Kachel-Inhalt: Bild (Frame) + Titel + Kategorie + Jahr + Pfeil, wie Nexolas
     Teaser-Karten; Haarlinien trennen die Zellen (Grid ohne Gap, Trennung über Borders,
     Innenabstand in den Zellen — so entsteht die durchgezogene Linienstruktur).
   - Bildverhältnisse im Grid: **beide Kachelgrößen Querformat** (Entscheidung Katharina —
     keine Quadrate; Nexolas Kartenbilder sind real **1.83:1** / 11:6). Da große und kleine
     Kacheln bei uns in EINER Reihe liegen, gilt: gleiche Bildhöhe erzwingt für die große
     Kachel ca. das doppelte Format der kleinen. **Entschieden (vorläufig, Katharina
     2026-07-17): Variante B** — klein **3:2**, groß **21:9**, Bilder oben bündig (große
     ~30 % höher, der Text darunter fängt den Unterschied auf, die Haarlinie schließt die
     Reihe unten bündig ab). Vorbehalt: wird am echten Aufbau mit echten Bildern noch
     einmal verifiziert (verworfen wurde A = klein 3:2 / groß ≈3:1 Panorama mit bündiger
     Bildzeile — Sorge: das Panoramaformat ist schwer zu bespielen; Platzhalter-Mock
     beider Varianten als Artifact „Teaser-Grid: Format-Varianten").
     Einheitsformat für alle (11:6 wie Nexola) scheidet aus — im gemischten Grid wird die
     große Kachel dann doppelt so hoch (bei Nexola liegen nie groß+klein in einer Reihe).
     Beide Crops entstehen per **Wagtail-Renditions mit Focal Point aus einem einzigen
     Teaser-Bild** — Katharina pflegt pro Projekt nur ein Bild, egal ob es groß oder
     klein liegt.
   - Responsive (Switcher-Logik): 4 Spalten → 2 Spalten (große Karte = volle Breite) →
     1 Spalte.
4. **(frei)** — hier saß bei Nexola die Video-Case-Study; bewusst offen gelassen.
5. **About** — kurz, keine Unterseite (Entscheidung): Statement-Satz (50px-Klasse),
   kleines Porträt, 2–3 Fakten. Vorbild: Nexolas „Intro"-Section.
6. **Contact** — CTA-Zeile („Lass uns sprechen") + Mail-Button.
7. **Footer (entschieden 2026-07-27)** — schwarze Fläche mit **Sitemap in vier Spalten**:
   Marke/Kurzbeschreibung, Seitenabschnitte, **alle Projekte einzeln verlinkt** (Auffindbarkeit
   + SEO), Kontakt/Social sowie Rechtliches; darunter eine schmale Copyright-Zeile. In Wagtail
   speist sich die Projektspalte aus denselben Kindseiten wie die Kacheln. Offen: echte
   E-Mail-Adresse und Social-Profile (aktuell Platzhalter).

### Mobile-Verhalten (entschieden 2026-07-27)

- **Projekte:** erste Kachel als Hero über die volle Breite, alle weiteren darunter als
  horizontaler **Reel** (Every Layout). `--item-width` unter 50 %, damit immer mindestens
  zwei Kacheln sichtbar sind.
- **Leistungen:** derselbe Reel (Entscheidung Katharina: gleiches Bedienmuster wie Projekte).
- **Slide-Indicator** unter jedem Reel: Spur mit Anfasser, dessen Breite den sichtbaren Anteil
  spiegelt — ziehbar und per Tastatur bedienbar, für alle, die nicht wischen wollen.
- Für die Wagtail-Umsetzung heißt das: Das Kachel-Template muss die **erste** Kindseite
  gesondert ausgeben und den Rest in einen Reel-Container — auf dem Desktop lösen sich beide
  Wrapper per `display: contents` auf, damit der Wechselrhythmus erhalten bleibt. Achtung: die
  `:nth-child`-Regeln zählen dann innerhalb des Reels und sind um eins verschoben.

## Projekt-Unterseite (ProjectPage)

**Ein Template für alle drei Projektarten** (Web / Print / Illustration) — die Arten
unterscheiden sich nur durch die Block-Mischung im StreamField, nicht durchs Template.

**Strukturierte Kopf-Felder** (immer gleich, ergibt den Hero wie bei Nexola):
- `title` (h1), `teaser_text` (für die Kachel + Intro), `category`
  (Choice: Web / Print / Illustration), `year`, `services` (Tag-Liste, z. B.
  „Webdesign, UX", ersetzt Nexolas Field/Outcome/Focus-Raster),
- `live_url` (optional — **„Website ansehen"-Button erscheint nur, wenn gesetzt**;
  Print/Illu lassen das Feld einfach leer),
- `teaser_image` (das eine Kachelbild, Focal Point gepflegt).

**StreamField-Blöcke** (Body):
- Großbild (16:9, full-width) · Bildpaar (2×) · Galerie 2×2 (4:3) · Hochformat-Duo (4:5)
- Text-Statement (die 50px-Klasse)
- Aufgabe/Lösung-Abschnitt (Nexolas Challenge/Solution, ohne Zwang zur Ergebnis-Sektion)
- Zahlen-Stats (2–4 große Zahlen mit Label — für Projekte, die Messbares haben)
- Zitat/Testimonial (Text + Name + Rolle)

**Automatisch am Seitenende:** „Weitere Projekte" (2 Teaser, Vor-/Nachfolger in der
Seitenreihenfolge) + Kontakt-CTA — kommt aus dem Template, wird nicht gepflegt.

## Asset-Formate (verbindlich, Katharina produziert)

| Einsatz | Verhältnis | Empfohlene Mindestgröße |
|---|---|---|
| Teaser-Bild (1 pro Projekt) | flexibel, Focal Point gesetzt | 2000px Kante (Renditions croppen auf die zwei Kachel-Querformate, s. Grid-Abschnitt) |
| Detail-Hero / Großbild | 16:9 | 2400×1350 |
| Galerie-Bilder | 4:3 | 1600×1200 |
| Hochformat (Poster, Cover) | 4:5 | 1200×1500 |

Trick für Print/Illu: Mockups immer auf eine einheitliche ruhige Leinwand setzen
(Objekt frei auf Creme-/Studiofläche), dann funktioniert jedes Projekt im selben Raster.
Auslieferung als Wagtail-Renditions (AVIF/WebP, `<picture>`).

## Handschrift (Astagina Signature) — Vorschläge, Katharina wählt

Sparsam, 3–4 Orte maximal (die Handschrift übernimmt zusammen mit der Akzentfarbe die
Rolle von Nexolas Lime-Akzenten):

1. **Hero:** handschriftliches „willkommen"/Namenszug als Geste über/neben der Headline.
2. **Sektions-Marginalien:** kleine handschriftliche Labels neben den „(01)"-Nummern
   („recent work", „about", „contact") — analog zu den Script-Labels des CV.
3. **About:** Signatur unter dem Statement.
4. **Optional:** Bleistift-Annotationen an einzelnen Projektbildern, im Stil der
   CV-Seiten-Sketches.

## Architektur (Wagtail)

- **Neue Django-App `homepage.portfolio`** (Models + Templates + CSS homepage-eigen;
  bewusst KEINE Kopplung an das django-resume-Paket — Tokens werden als eigene
  `--portfolio-*`-Tokens angelegt, auch wenn die Werte mit dem CV übereinstimmen).
- **Seitentypen:**
  - `PortfolioIndexPage` — die Startseite; `subpage_types = [ProjectPage]`;
    Kacheln = `self.get_children().live().specific()` in Seitenreihenfolge.
    Felder für Hero-Text, About-Statement, Porträt, Kontakt-Daten.
  - `ProjectPage` — `parent_page_types = [PortfolioIndexPage]`, Felder s. o.
  - Impressum/Datenschutz: **erst prüfen, ob die bestehenden Seiten der Homepage
    verlinkt werden können** (offener Punkt) — sonst schlichter `PortfolioStandardPage`-Typ
    (RichText).
- **Einhängung:** Elternseite `portfolio` (reiner Ordner/Redirect) unter der Site-Root,
  darunter `katharina` = `PortfolioIndexPage` → `wersdoerfer.de/portfolio/katharina/`,
  Projekte darunter (`…/katharina/<projekt-slug>/`).
- **Templates:** `homepage/templates/portfolio/…`, eigenes Stylesheet
  (`homepage/static/css/portfolio.css` bzw. Sass-Quelle im bestehenden Build) — kein
  Bootstrap in diesen Templates, das Portfolio bringt sein eigenes, schlankes CSS mit
  (Every-Layout-Primitiven + Tokens).
- **Tests:** pytest + factory-boy (Seiten-Hierarchie, Kachel-Reihenfolge,
  live_url-Button-Logik, Block-Rendering), wie im Projekt üblich.

## Arbeitsweise

Wie beim CV-Projekt bewährt: Schritt für Schritt pro Task, Diff-Review mit Codex,
visuelle Abstimmung **live im Browser** (Dev-Server Port 8001), Playwright-Screenshots
zur Verifikation. Erst statisches Template mit Beispielinhalten pixelig ans
Nexola-Verhalten heranbauen, dann die Wagtail-Modelle druntersetzen — aber von Anfang an
in Komponenten geschnitten, die 1:1 zu Wagtail-Templates/Blöcken werden.

## Offene Punkte

0. **Kachel-Bildformate** — vorläufig entschieden: Variante B (klein 3:2 / groß 21:9,
   oben bündig); am echten Aufbau mit echten Bildern verifizieren. Noch klären, wie die
   Texte unter den Bildern sitzen (Mock zeigt Titel + Kategorie·Jahr + Pfeil).
1. **Akzentfarbe** — liefert Katharina; bis dahin Platzhalter-Token.
2. **Handschrift-Einsatzorte** — Katharina wählt aus den Vorschlägen oben.
3. **Freier Bereich** zwischen Projekt-Panel und About (Ex-Case-Study-Platz) — Idee folgt.
4. ~~**10.-Projekt-Restreihe** — CTA-Kachel als Lückenfüller ok?~~ **Entschieden
   (2026-07-27):** Die CTA-Kachel läuft über die volle Breite (`grid-column: 1 / -1`) und
   schließt das Raster als schmales dunkles Band ab — 9 Projekte ergeben exakt 3 Reihen,
   die CTA beginnt also immer eine neue; als Einzelkachel bliebe die Reihe offen.
5. **Impressum/Datenschutz** — bestehende Seiten der Homepage nutzen oder eigene
   (ggf. Katharina-spezifisches Impressum nötig)?
6. **Saira-Weights** — Grauwert-Abstimmung live im Browser (Nexola-800/600 ≠ Saira-800/600).

## Stand & Hero-Umsetzung (2026-07-27)

Der **Hero** ist als Design-Prototyp fertig und in eine durchgehende Startseite integriert.
Gebauter, self-contained Prototyp im Repo:
[`../prototypes/portfolio-startseite.html`](../prototypes/portfolio-startseite.html)
(README dort erklärt Aufbau + technische Caveats). Live-Vorschau:
`https://claude.ai/code/artifact/cf27d96b-59b6-43a6-8361-b521401280f7`.

**Hero-Konzept (final abgestimmt):** Fullscreen, „MOIN" als echter HTML-Text. Maus-Reveal legt
per **WebGL-Flüssigkeitssimulation** (Stable-Fluids/Navier-Stokes, Verfahren wie noth.in,
eigenständig implementiert — MIT-Open-Source-Technik) eine bunte Fullscreen-Illustration frei;
der Text schaltet deckungsgleich auf Outline (Innen-Kontur). Trade-off der exakten Kopie: „MOIN"
ist aus Saira in die zwei Texturen (clean / illustration) eingebrannt, KEIN Live-DOM-Text — ein
unsichtbares `<h1>` liegt für a11y/SEO darüber. Feine Gridlinien: 4 Spalten, innere gestrichelt,
äußere Padding-Linien + Header-Unterkante dunkel (`#171410`), waagerechte zart; Aufteilung
1/4·2/4·1/4, MOIN grid-verankert (gleicher Gap links/rechts/oben, pixel-gemessen). Subline sitzt
in einer randlosen **Milchglas-Doppelzelle** (2 Spalten, `backdrop-filter`), auf schmalen Screens
über MOIN gelegt. **CV-Leinentextur** (`white-linen.png`, multiply) liegt über der ganzen Seite.
Nur hell.

**WICHTIGER Fix:** Hero-Höhe auf `min(100svh, 1200px)` gedeckelt (+ Canvas ≤ 4096px). Ohne Deckel
sprengt die iframe-Streckung der Vorschau `100svh` auf die volle Seitenhöhe → Canvas-Absturz →
MOIN verschwindet. Siehe Prototyp-README.

**Illustration bleibt bewusst bis ganz zum Schluss** (User-Wunsch): aktuell bunter Platzhalter;
Katharina liefert die zwei deckungsgleichen Fullscreen-Bilder (clean = Creme + MOIN gefüllt;
reveal = Illustration + MOIN-Outline) zuletzt.

## Gridlinien-Gerüst über die ganze Seite (2026-07-27)

Erster Schritt des Design-Ausbaus der Sections unter dem Hero: Das Liniensystem des Heros
läuft jetzt **über die ganze Seite** — zwei kräftige Padding-Linien links/rechts plus drei
gestrichelte Spaltenlinien auf den Viertelmarken.

**Als GENAU EINE Struktur** (`<div class="pagegrid">`, absolut über dem gesamten Dokument),
nicht je Section wiederholt — Vorgabe Katharina: „keine redundanten Strukturen, alles so
reduziert wie möglich an einer Stelle". Der erste Versuch zeichnete die Linien pro Section
(`::before`/`::after`) und der Hero brachte zusätzlich seinen eigenen Satz Vertikalen mit;
dadurch begann die Strichelung an jeder Sektionsgrenze neu und der Phasensprung war als
feiner Versatz sichtbar. Für die Wagtail-Umsetzung heißt das: **das Gerüst gehört ins
Basis-Template, nicht in die Section-Includes.** Details siehe Prototyp-README.

**Schichtung (Vorgabe Katharina, 2026-07-27): Flächen dürfen unter das Grid, alle Inhalte
liegen darüber — Bilder und alles andere.** Das Gerüst läuft also im Hintergrund
(`z-index: -1`), darunter die Hero-Canvas-Fläche (`-3`) sowie die dunklen Sektionsflächen und
die Milchglas-Fläche der Subline (`-2`, jeweils als `::before` statt als `background`, sonst
decken sie die Linien zu); aller Inhalt liegt darüber. Wichtig: Bildflächen müssen **deckend**
sein, sonst scheinen die Linien durch und es sieht aus, als läge das Grid obenauf.
Das Gerüst behält auf **allen** Breiten vier gleich breite Spalten, auch wenn die Raster
darüber auf zwei Spalten fallen.

Die daraus folgende Grundregel: **Raster bündig, Text eingerückt.** Die 4-spaltigen Raster
liegen exakt auf den Linien (Außenkanten = Padding-Linien, Zelllinien = gestrichelte
Spaltenlinien, per Playwright nachgemessen); Textblöcke rücken um `--hero-inset` ein — derselbe
Gap, mit dem das MOIN in seiner Gridzelle sitzt. Damit das trägt, wurden zwei Blöcke ans
System angepasst: **About** liegt jetzt im 4-Spalten-Raster (Statement über drei Spalten,
Porträt füllt bündig die vierte zwischen 75-%-Linie und rechter Padding-Linie, vorher
2,2fr/1fr und damit unverankert), und die **CTA-Kachel** schließt das Projektraster über die
volle Breite ab (offener Punkt 4, s. o.).

**Nächste Schritte:** (a) übrige Sections gestalterisch ausbauen + echte Inhalte; (b) Wagtail-
Umsetzung `homepage.portfolio` gemäß Architektur oben, Fluid-Hero als wiederverwendbare Komponente
(zwei Bilder als Media-Felder); (c) echte Illustration einsetzen; (d) Akzentfarbe + Handschrift-
Orte finalisieren.
