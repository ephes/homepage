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
   der ganzen Seite. In der äußersten rechten Gridzelle oben steht ein Kurztext
   („15+ years in branding."), unten in der Zelle ausgerichtet mit `--hero-inset` Abstand zur
   25-%-Linie, in Schriftgröße der Wortmarke. Unter 46 rem ausgeblendet — dort wäre die
   vierte Spalte nur gut 80 px breit.
   **Custom Cursor über dem Hero:** ein Punkt mit umlaufendem Schriftring in Versalien
   („MOIN · FAHR MAL DRÜBER"), der langsam rotiert und dem Zeiger mit Lerp nachläuft.
   `mix-blend-mode: difference` auf Weiß kehrt den Untergrund um — der Cursor bleibt über
   Creme wie über dem schwarzen MOIN sichtbar, ohne die Farbe zu wechseln. Der Ring schließt
   exakt, weil `textLength` auf den Kreisumfang (2π·48) gesetzt ist; damit hängt die Passung
   nicht an den Schriftmetriken. Nur bei `(hover: hover) and (pointer: fine)` aktiv, sonst
   bliebe auf Touch der Systemcursor weg. Er ersetzt die frühere Hinweiszeile im
   Milchglas-Feld.
2. **Projekte** — 4-Spalten-Grid im Wechselrhythmus (große Kachel span 2), Platzhalter-Kacheln;
   eine CTA-Kachel über die volle Breite schließt das Raster unten ab.
3. **Leistungen** — 8 Kacheln (Icon + Einwort-Headline + Satz), aus dem CV-Skillboard gebündelt.
4. **About** — kurzes Statement + Fakten + Handschrift-Signatur, dazu das Porträt als
   **Klecks**: ein SVG-`clipPath` mit Hauptform und vier abgelösten Spritzern (mehrere
   Teilpfade in einem `clipPath` ergeben zusammen die Maske). `clipPathUnits="objectBoundingBox"`
   rechnet in Anteilen 0…1, die Form skaliert also mit dem Element; das Feld ist quadratisch,
   damit die Spritzer ringsum Platz haben. Border und Diagonalkreuz entfallen — eine Border
   würde von der Maske angeschnitten.
   Die Hauptform **wabert langsam** (SMIL, 24 s): drei Varianten derselben Kurvenfolge —
   gleiche Befehlsstruktur, nur verschobene Punkte — werden ineinander übergeblendet. Das
   kostet nur das Neuzeichnen dieses einen Elements, kein Layout und kein Reflow, und es
   läuft ohne JavaScript pro Frame. Die Spritzer bleiben ruhig; bewegte Punkte lesen sich
   als Flimmern. Bei `prefers-reduced-motion` friert `pauseAnimations()` die Form ein —
   SMIL wertet die Einstellung nicht selbst aus, und `display: none` auf dem `<animate>`
   stoppt sie nicht zuverlässig (nachgemessen).
5. **Kunden** — dunkle Section mit durchlaufendem Marquee-Band.
6. **Kontakt** — CTA + zwei Buttons.
7. **Footer** — schwarz, mit Sitemap in vier Spalten: Marke, Seitenabschnitte, alle Projekte
   einzeln, Kontakt/Social und Rechtliches. Darunter eine schmale Zeile mit Copyright.

## Mobile (unter 52rem)

- **Projekte:** die erste Kachel steht als Hero über die volle Breite (16:9), alle weiteren
  laufen darunter als **Reel** (Every Layout) horizontal durch. `--item-width` liegt mit
  `min(45%, 17rem)` unter der Hälfte, damit immer **mindestens zwei Kacheln** gleichzeitig zu
  sehen sind und die angeschnittene dritte zeigt, dass es weitergeht (gemessen: 2,2 Kacheln).
  Die CTA-Kachel bleibt darunter über die volle Breite.
- **Leistungen:** derselbe Reel. `.svc-grid` trägt zusätzlich die Klasse `reel`; die
  Reel-Regeln greifen nur in der Mobile-Query, auf dem Desktop bleibt es ein 4er-Raster.
- **About:** Der Klecks eröffnet auf dem Smartphone die Section (`order: -1`) statt am Ende
  unterzugehen.
- **Slide-Indicator** unter jedem Reel: eine Spur mit Anfasser für alle, die nicht wischen
  wollen. Breite des Anfassers = sichtbarer Anteil, Position = Scrollfortschritt; ziehbar per
  Pointer-Events, bedienbar per Tastatur (`role="slider"`, Pfeiltasten, Home/End). Er zeigt
  sich nur, wenn der Reel wirklich überläuft (`.is-scrollable` setzt das Skript).
  Die Spur ist auf den **Textanschlag** eingerückt (Padding-Linie + `--hero-inset`, gemessen
  28…362 px bei 390 px Viewport) und sitzt eng unter dem Reel, aber mit deutlich mehr Abstand
  zur CTA-Kachel darunter (14 px oben / 40 px unten) — sonst liest sie sich als deren Zubehör.
- Beide Reels verstecken die native Scrollbar, weil der Indicator ihre Rolle übernimmt.

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
  waagerechten Linien (25 % / 75 %) und die Unterkante der Subline-Zelle. Letztere endet an
  der 50-%-Linie und schließt damit nur die Doppelzelle ab — in den beiden freien Zellen
  rechts daneben liefe sie ins Leere.
- Die 1/4-Linie hat im Hero eine Lücke: sie setzt an der Oberkante der Subline-Doppelzelle aus
  und läuft unter deren Unterkante weiter (zwei Segmente, `.vsplit` / `.vsplit2`). Weil das
  Gerüst über der ganzen Seite liegt, misst `updateSubBottom()` die beiden Grenzen
  **dokument-absolut** in `--gap-start` / `--gap-end`.
- **Das Gerüst läuft im Hintergrund** (`z-index: -1`). Die Regel dahinter (Vorgabe Katharina):
  **Flächen dürfen unter das Grid, Bilder liegen immer darüber.** Daraus die Schichtung:

  | Ebene | Was |
  |---|---|
  | `-3` | Hero-Canvas (Fläche) |
  | `-2` | dunkle Sektionsflächen + Milchglas der Subline (jeweils `::before`) |
  | `-1` | innere Gridlinien + waagerechte Hero-Linien |
  | ab `0` | aller Inhalt: Kacheln, Bilder, Texte |
  | `30` | **die beiden äußeren Padding-Linien** |
  | `40` / `60` | Header / Leinentextur |

  **Ausnahme für die Seitenberandung:** Die beiden Außenlinien begrenzen die Seite und dürfen
  von nichts überlaufen werden — auch nicht von einem Slider, der bis an den Rand scrollt.
  Sie liegen deshalb als einzige über dem Inhalt. Damit das in *einer* Struktur möglich ist,
  trägt `.pagegrid` **bewusst kein `z-index`**: sonst machte es einen Stacking-Kontext auf und
  alle Linien lägen zwangsläufig auf derselben Ebene. So wählt jede Linienart ihre eigene.

  Zwei Dinge sind dafür nötig: `.stage` darf **kein** `isolation: isolate` tragen, sonst käme
  der Canvas nicht unter das seitenweite Gerüst; und die dunkle Fläche einer `.on-dark`-Section
  liegt als `::before` auf `-2` statt als deren `background` — sonst deckte sie die Linien zu,
  sobald diese im Hintergrund laufen.
  Nach derselben Regel liegt auch die **Milchglas-Fläche der Subline** auf `-2`: als
  `.sub::before` statt als `background` der `.sub` — sonst deckte sie die Außenlinien ab.
  `.sub` muss dafür `z-index: auto` behalten, sonst macht sie einen eigenen Stacking-Kontext
  auf und die Fläche käme nicht unter die Linien. Der Blur greift auf den Canvas (`-3`) zu,
  die Linien darüber bleiben scharf; der Text darin ist normaler Inhalt und liegt oben.
- **Platzhalterflächen müssen deckend sein.** `.frame` hatte nur `rgba(…, 0.06)` und ließ die
  Linien durchscheinen — es sah aus, als läge das Grid über den Bildern. Jetzt Creme-Grund
  plus Tonung darüber. Echte Bilder sind ohnehin deckend.
- **Das Liniengerüst behält auf allen Breiten vier gleich breite Spalten** (gemessen bei
  390 px: 88/87/88/87). Die Raster darüber dürfen auf zwei Spalten fallen, das Grundraster
  bleibt dasselbe. Unter 46 rem läuft die 1/4-Linie in einem Stück durch, weil die Subline
  dort über MOIN liegt und keine Lücke mehr braucht.
- **Über dunklen Sections kehren die Linien ins Helle** — ohne zweite Struktur: die
  Linienfarbe ist eine Funktion von y. `buildLineGradients()` misst die Kanten **jeder**
  Section mit der Klasse `.on-dark` (aktuell Kunden und Footer) und baut daraus die Verläufe
  mit harten Stopps — beliebig viele Bänder statt eines fest verdrahteten. Dieselbe Klasse
  liefert auch die Farbgebung der Section selbst, die Umschaltung steht also an einer Stelle.
  Deshalb sind die
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

- **Die Subline beginnt an der 75-%-Linie, weicht aber nach oben aus.** Reicht der Platz
  darunter nicht — kurzer Viewport oder längerer Text —, setzt das Skript `--sub-top` so weit
  nach oben, dass die Zelle nicht unten aus der Stage geschnitten wird (die clippt).
  Geprüft bei 1440×900, 1440×700, 1280×800, 2560×1440 und 820×1180.
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
