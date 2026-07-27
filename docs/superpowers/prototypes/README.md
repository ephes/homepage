# Portfolio-Startseite — Design-Prototyp

`portfolio-startseite.html` ist ein **eigenständiger, gebauter Design-Prototyp** der
Portfolio-Startseite (Katharina Wersdörfer). Self-contained: Schriften (Saira, Astagina
Signature) und die Leinentextur sind als Base64 eingebettet — die Datei öffnet ohne Server
direkt im Browser.

Die zugehörige Design-Spec liegt unter
[`../specs/2026-07-17-portfolio-site-design.md`](../specs/2026-07-17-portfolio-site-design.md).

## Was der Prototyp zeigt

Eine durchgehende Startseite (Design-Stand, Inhalte noch Platzhalter):

1. **Hero** — Fullscreen, großes „MOIN" (echter HTML-Text). Beim Bewegen der Maus über den
   Schriftzug wird per **WebGL-Flüssigkeitssimulation** eine bunte Illustrationswelt darunter
   freigelegt (Verfahren analog zu noth.in, eigenständig implementiert); der Text schaltet
   deckungsgleich auf Outline um. Cremefarbener Grund, feine Gridlinien (4 Spalten, innere
   gestrichelt, Padding-Linien dunkel), Milchglas-Feld für die Subline, CV-Leinentextur über
   der ganzen Seite.
2. **Projekte** — 4-Spalten-Grid im Wechselrhythmus (große Kachel span 2), Platzhalter-Kacheln;
   eine CTA-Kachel über die volle Breite schließt das Raster unten ab.
3. **Leistungen** — 8 Kacheln (Icon + Einwort-Headline + Satz), aus dem CV-Skillboard gebündelt.
4. **About** — kurzes Statement + Fakten + Handschrift-Signatur.
5. **Kunden** — dunkle Section mit durchlaufendem Marquee-Band.
6. **Kontakt / Footer** — CTA + Impressum/Datenschutz-Links.

## Gridlinien-Gerüst (seitenweit)

Die Liniensprache des Heros läuft über die **ganze** Seite weiter und klammert die Sections
optisch zusammen:

- **Es gibt genau EINE Struktur dafür:** `<div class="pagegrid">`, absolut positioniert über
  dem gesamten Dokument (`body { position: relative }` + `inset: 0`), direkt vor der
  Leinentextur im Markup. Sie enthält die zwei kräftigen Padding-Linien (`--rule-strong`),
  die gestrichelten 50-%- und 75-%-Linien und die 1/4-Linie.
  **Nicht je Section wiederholen.** Gezeichnete Teilstücke pro Section lassen die Strichelung
  an jeder Sektionsgrenze neu beginnen — die Phase springt, und das ist als feiner Versatz
  sichtbar. Eine durchgehende Linie hat eine einzige Phase. (Genau diese Redundanz gab es
  vorher: Section-Pseudoelemente *und* ein zweiter Satz Vertikalen im Hero.)
- **Der Hero bringt keine eigenen Vertikalen mehr mit** — sein `.grid` enthält nur noch die
  waagerechten Linien (25 % / 75 %) und die Unterkante der Subline-Zelle.
- Die 1/4-Linie hat im Hero eine Lücke: sie setzt an der Oberkante der Subline-Doppelzelle aus
  und läuft unter deren Unterkante weiter (zwei Segmente, `.vsplit` / `.vsplit2`). Weil das
  Gerüst über der ganzen Seite liegt, misst `updateSubBottom()` die beiden Grenzen
  **dokument-absolut** in `--gap-start` / `--gap-end`.
- Das Gerüst liegt **über dem Inhalt** (`z-index: 30`, `pointer-events: none`), aber unter
  Header (40) und Leinentextur (60). Es muss über dem Inhalt liegen, weil der Hero-Canvas eine
  deckende Fläche ist — darunter wäre er im Hero unsichtbar. Konsequenz: die Linien laufen
  über die Projektbilder, so wie sie im Hero über die Illustration laufen.
- **Über der dunklen Kunden-Section kehren die Linien ins Helle** — ohne zweite Struktur:
  die Linienfarbe ist eine Funktion von y (ein Verlauf mit harten Stopps an
  `--dark-top` / `--dark-bottom`, ebenfalls dokument-absolut gemessen). Deshalb sind die
  Linien **Hintergrund-Ebenen statt Borders** (eine Border kann keinen Verlauf tragen) und die
  Strichelung kommt als `mask-image` dazu, damit Farbe und Muster unabhängig bleiben.
  Nebeneffekt: alle Linien nutzen jetzt dasselbe Strichmuster — vorher mischten sich
  browser-gerenderte `dashed`-Borders und Gradient-Striche.
- **Bündig vs. eingerückt:** Die 4-spaltigen Raster (Kacheln, Leistungen, About-Porträt)
  liegen bündig — ihre Außenkanten fallen mit den Padding-Linien zusammen, ihre Zelllinien
  mit den gestrichelten Spaltenlinien (per Playwright nachgemessen: 57,59 px / 1382,41 px
  bei 1440 px Viewport, Porträt-Kante exakt auf 1051,20 px = 75-%-Linie). Textblöcke rücken
  dagegen um `--hero-inset` ein — derselbe Gap, mit dem das MOIN in seiner Zelle sitzt.

## Technische Notizen (wichtig für die Weiterarbeit)

- **Hero-Höhe ist auf `min(100svh, 1200px)` gedeckelt.** Grund: In der Artifact-/iframe-Vorschau
  wird der Frame auf die volle Seitenhöhe gestreckt, wodurch `100svh` = gesamte Seitenhöhe wird.
  Ohne Deckel wächst der Hero auf mehrere tausend Pixel, die WebGL-Textur sprengt das Limit und
  der Canvas (inkl. MOIN) verschwindet.
- **Der Canvas deckelt den MASSSTAB, nicht die Kanten einzeln** (`scale = min(dpr, 4096/cw,
  4096/ch)`). Würde nur die Breite gekappt — auf einem 27-Zoll-Retina ist 2560 × 2 = 5120 → 4096,
  die Höhe bleibt darunter —, stimmte das Seitenverhältnis des Canvas nicht mehr mit dem der
  Textur überein. Der Composite-Shader macht einen *cover*-Fit und zoomte die Textur dann
  seitlich aus dem Bild: MOIN lief links und rechts aus dem Screen.
- **Die Texturbreite folgt der Canvas-Breite** (vorher fix auf 2048 gedeckelt). Da MOIN in die
  Textur eingebrannt ist, wird jede zu kleine Textur hochskaliert — auf großen Screens um
  Faktor 2, mit sichtbar ausgefransten Buchstabenkanten.
  Verifiziert über 390 / 1440 / 2560 / 3008 px CSS-Breite bei dpr 2: MOIN-Ink-Box weicht ≤ 0,1 px
  von der Sollposition (Padding-Linie + `--hero-inset`) ab.
- **Nur hell** (`color-scheme: light`), Dark-Mode bewusst entfernt (helle Start-Section).
- Bei fehlendem WebGL greift ein DOM-Fallback (statisches MOIN).
- Der Prototyp ist der Design-Stand; die produktive Umsetzung erfolgt als **Wagtail**-App
  `homepage.portfolio` (siehe Spec). Der Fluid-Hero wird dabei zu einer wiederverwendbaren
  Komponente; die zwei Hero-Bilder (clean/illustration) liefert Katharina zum Schluss.

## Live-Artifacts (Vorschau, jederzeit neu deploybar)

- Integrierte Startseite: `https://claude.ai/code/artifact/cf27d96b-59b6-43a6-8361-b521401280f7`
- Fluid-Hero solo: `https://claude.ai/code/artifact/ace3afee-487e-49f9-8fd5-488e63d6e543`
