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
   **Custom Cursor über dem Hero:** ein reduzierter Mauszeiger (Pfeilspitze ohne Schweif) in
   einem **geschlossenen Schriftkreis** — **SEI DOCH MAL** über dem Scheitel, **KREATIV** auf
   der Unterlinie, dazwischen links und rechts je ein Trennpunkt. Zwei gegenläufige Bahnen
   sorgen dafür, dass beide Wörter richtig herum stehen; der Ring dreht sich deshalb nicht.
   Ihre Radien unterscheiden sich um die Versalhöhe (38,4 / 49,6 px bei 16 px Schrift), weil
   die Glyphen oben von der Grundlinie nach außen und unten nach innen wachsen — sonst lägen
   die Wörter in versetzten Ringen.
   Die Aufteilung ist **ausgerechnet**, nicht geschätzt: aus der gemessenen Laufweite der
   Wörter in Saira ergeben sich oben 180,4° in natürlicher Weite und unten 127,6°, per
   `textLength` gesperrt, weil KREATIV kürzer ist; dazu zwei Lücken von je 26° für die
   Trennpunkte. Summe exakt 360°, der Kreis ist damit lückenlos.
   **Zentrierung:** Der Ring ist um die *Bounding-Box* des Pfeils zentriert, nicht um dessen
   Spitze — sonst hinge der Pfeil sichtbar unten rechts im Ring. Damit die Spitze trotzdem
   auf dem Zeiger liegt, ist der Margin-Versatz ihre Position im viewBox (53/50), nicht die
   halbe Elementgröße. Er läuft dem Zeiger mit Lerp nach.
   `mix-blend-mode: difference` auf Weiß kehrt den Untergrund um — der Cursor bleibt über
   Creme wie über dem schwarzen MOIN sichtbar, ohne die Farbe zu wechseln. Der Ring schließt
   exakt, weil `textLength` auf den Kreisumfang (2π·48) gesetzt ist; damit hängt die Passung
   nicht an den Schriftmetriken. Nur bei `(hover: hover) and (pointer: fine)` aktiv, sonst
   bliebe auf Touch der Systemcursor weg. Er ersetzt die frühere Hinweiszeile im
   Milchglas-Feld.
2. **Projekte** — 4-Spalten-Grid im Wechselrhythmus (große Kachel span 2), Platzhalter-Kacheln;
   eine CTA-Kachel über die volle Breite schließt das Raster unten ab.
3. **Leistungen** — 8 Kacheln (Icon + Einwort-Headline + Satz), aus dem CV-Skillboard gebündelt.
4. **About** — auf dem 4-Spalten-Raster: **Spalte 1 trägt das Porträt, die Spalten 2–4
   allen Text.** Oben das **Statement** („Ich bin Katharina / und bleibe gern neugierig."
   — der Umbruch steht als `<br>` fest im Markup), darunter der Fließtext als **drei
   Rasterspalten**, jede mit einer **Ein-Wort-Kopfzeile**: Verstehen / Gestalten /
   Umsetzen. Das ist der Effekt: Fließtext, der als eine Spalte unter der Headline
   weiterliefe, bliebe Fließtext; so wird ein Magazinsatz daraus, und die Kopfzeilen geben
   ihm seine Gliederung. Die drei Spalten stehen bei 1440 px gleich hoch (10/10/10 Zeilen).
   Die Kopfzeilen sind wie die übrigen kleinen Überschriften der Seite behandelt (versal,
   gesperrt, klein), aber in `--ink` statt `--muted`, weil sie einen Absatz anführen und
   nicht nur beschriften.
   **Das Statement ist ein `<h2>`, die Kopfzeilen sind `<h3>`.** Vorher war das Statement
   ein `<p>` — die Section hatte damit gar keine Überschrift, und `<h3>`-Kopfzeilen hätten
   in der Luft gehangen. Darunter schließt eine **eigene Rasterzeile** ab, durch eine
   **Trennlinie** vom Fließtext abgesetzt: links die Verortung „Digital Creative ·
   Based in Düsseldorf", rechts **„Mehr im Lebenslauf"** (aus der Kontakt-Section hierher
   gewandert). Die Linie läuft über die **Textbahn** (Spalten 2–4), nicht über die volle
   Breite: sonst ragte sie links unter dem Porträt hervor und schösse über die Kante
   hinaus, an der alle drei Textzeilen beginnen. Ihre Kanten fallen auf die Spaltenlinie
   und die rechte Padding-Linie; der Inhalt der Zeile rückt davon noch um `--hero-inset`
   ein, es ist ja Text und UI, kein Raster.
   Die Luft um die Linie kommt aus zwei Quellen: der `row-gap` des About-Grids bemisst den
   Abstand **Text → Linie**, die größere Fuge nach dem Statement liegt separat als `margin`
   auf dem Statement. Ein einziger gap-Wert zöge sonst beide Fugen gleich weit auf. Eckdaten-Trio und Handschrift-Signatur sind an dieser Stelle **entfallen**;
   damit ist die Klasse `.script` im Markup nicht mehr in Gebrauch.
   **Der handschriftliche Vermerk der Section sitzt auf der Unterkante des Porträtfeldes**
   und sagt „that's me" — das frühere `hallo!` in der Eyebrow ist entfallen, samt der
   nun gegenstandslosen Regel `.sec-label .scr`. Technik und Fallstricke wie bei den
   Vermerken auf den Headlines (SVG-Text, `paint-order: stroke`, reale SVG-Größe statt
   0×0, `bottom` = Grundlinie); Größe ebenfalls `--scr-size`, damit alle Vermerke der
   Seite gleich groß sind. Er bleibt dabei innerhalb der Porträtspalte — nachgemessen bei
   1440/900/390 px: 62/38/76 px Luft links, 79/49/82 px rechts.
   **Der Name im Statement steht in der Handschrift**, als `<span class="katha">` mitten im
   Satz, in der Akzentfarbe — der einzigen Stelle neben dem ✳, an der sie Text trägt (bei
   51 px greift die Schwelle für große Schrift, 3:1; Tangerine liegt mit 3,4 darüber).
   Die Größe `1.75em` ist gemessen, nicht geschätzt: Astagina hat bei *gleicher* Größe eine
   kleinere x-Höhe als Saira (19,2 gegen 26,1 px bei 51,2 px), aber eine höhere Versalie
   (36,2 gegen 35,2) — Cap- und x-Höhe fordern also gegensätzliche Werte (0,97 em bzw.
   1,36 em). Verglichen wurden 1,30/1,50/1,70/1,90× am echten Font: bei 1,75 em trägt der
   Name wie eine Unterschrift, ab 1,90× wird das K zum Solisten. Weil der Umbruch vor
   „und" fest im Markup steht, kann die Handschrift breit laufen, ohne den Zeilenfall zu
   verschieben.
   Dazu `line-height: 0.63` am Span: `line-height` wird als Zahl vererbt, der Span bekäme
   sonst 1,1 × 1,75 em und zöge die beiden Headline-Zeilen auseinander. 0,63 × 1,75 ≈ 1,1,
   also genau die Zeilenhöhe des Absatzes.
   Dazu ein gemessener Tiefstand `top: 0.15em` (auf die **Span**-Größe bezogen): auf der
   Grundlinie säße die Handschrift 13,7 px zu hoch, weil Astaginas Oberlänge über Sairas
   Versalhöhe hinausragt. Bei 0,15 em treffen sich die Tintenmitten auf 0,3 px genau.
   Der Wert hängt an der Schriftgröße — bei Änderung neu messen, nicht mitskalieren.
   **Die Eyebrow wandert mit** in Spalte 2 (`margin-inline-start: 25 %` — 25 % der
   Sektionsbreite ist genau eine Rasterspalte, weil der Innenbereich nach `--pad` in vier
   gleiche Spalten geteilt ist). Bliebe sie am linken Rand, stünde sie allein über dem
   Bild, und die zwischen ✳ und Headline ausgemessene Tintenflucht (`-0.082em`) hinge in
   der Luft. Auf dem Smartphone wird der Versatz zurückgenommen.
   Spalte 1 trägt über alle Zeilen das Porträt als **Klecks** —
   `grid-row: 1 / span 3` mit `align-self: start`, **nicht** `1 / -1`: ohne
   `grid-template-rows` gibt es kein explizites Zeilenraster, `-1` zeigt dann auf Linie 1
   und der Klecks landet wieder in Zeile 1. Dort bestimmte seine quadratische Höhe
   (331 px bei 1440 px) die Zeilenhöhe, und unter dem zweizeiligen Statement stünden
   ~250 px Leere.
   Die Maske selbst: ein SVG-`clipPath` mit Hauptform und vier abgelösten Spritzern
   (mehrere Teilpfade in einem `clipPath` ergeben zusammen die Maske).
   `clipPathUnits="objectBoundingBox"`
   rechnet in Anteilen 0…1, die Form skaliert also mit dem Element; das Feld ist quadratisch,
   damit die Spritzer ringsum Platz haben. Border und Diagonalkreuz entfallen — eine Border
   würde von der Maske angeschnitten.
   Die Form **wabert** (SMIL, 16 s): drei Varianten derselben Kurvenfolge — gleiche
   Befehlsstruktur, nur verschobene Punkte — werden ineinander übergeblendet. Die vier
   Spritzer driften eigenständig mit (`animateTransform`, 13/17/21/15 s, damit sie nicht
   im Gleichtakt laufen). Das kostet nur das Neuzeichnen dieses einen Elements, kein Layout
   und kein Reflow, und es läuft ohne JavaScript pro Frame.
   Bei `prefers-reduced-motion` friert `pauseAnimations()` alles ein —
   SMIL wertet die Einstellung nicht selbst aus, und `display: none` auf dem `<animate>`
   stoppt sie nicht zuverlässig (nachgemessen).
5. **Kunden** — dunkle Section mit durchlaufendem Marquee-Band.
6. **Kontakt** — CTA + ein Button („E-Mail schreiben"); der Lebenslauf-Link steht
   jetzt in About.
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

## Farben (Entwurf, 2026-09-01)

Grundton (Creme `#F0ECE2`) und warmes Schwarz bleiben vorerst unverändert; dazugekommen ist
**ein Akzent**:

- **Tangerine `#EB3D00`** — trägt auf beiden Gründen (3,4 auf Creme, 4,6 auf Dunkel) und
  bleibt deshalb seitenweit derselbe. Er hängt an `--accent`.
- **Smaragd `#1C995C`** ist als Token vorhanden, aber **für Sonderfälle reserviert**
  (Entscheidung Katharina). Die frühere Umschaltung auf Grün in dunklen Sections ist raus.

Zur Auswahl siehe `farbpalette.html` (Tokenkarte mit Kontrastmatrix) — dort stehen auch die
verworfenen Kandidaten samt Begründung. Noch offen: ob das warme Schwarz durch Sacramento
`#162114` ersetzt wird (grünlicher) und ob Pine `#294122` als mittlere Fläche dazukommt.

## Sektionskopf

Reihenfolge: **Eyebrow → Headline → handschriftlicher Vermerk.** Der Vermerk hängt nicht in
der Eyebrow, sondern liegt **auf** der Headline — als hätte jemand mit der Hand
darübergeschrieben.

**Der Vermerk ist SVG-Text, kein HTML-Text.** Das ist der Kern: Nur dort kann die Kontur
gleichzeitig *glatt* und *rund* sein. Beide CSS-Wege scheitern an je einem Detail —
`-webkit-text-stroke` verbindet die Ecken spitz und erzeugt Zacken an den Strichenden; ein
Ring aus Schattenkopien rundet zwar, bekommt aber eine sichtbare **Wellenkante**, weil der
Browser die Versätze auf ganze Pixel rundet und aus dem Kreis ein Vieleck wird.
`stroke-linejoin: round` + `paint-order: stroke` löst beides exakt.
Zwei Fallstricke dabei: Ein **0×0-SVG malt Chrome gar nicht**, trotz `overflow: visible` — es
braucht eine reale Größe (1 px genügt). Und der Anker verschiebt sich: `bottom` liegt bei
SVG-Text auf der **Grundlinie**, nicht auf der Unterkante wie bei HTML-Text.

**Größe absolut, nicht proportional.** `--scr-size: clamp(1.96rem, 6.3vw, 5.6rem)` (= 0,70 ×
der Sektionstitel-Skala). Damit ist der Vermerk über **allen** Headlines gleich groß — auch
über den kleineren zweizeiligen, wo er sonst auf die Hälfte schrumpfte. Das SVG trägt die
Schriftgröße selbst, wodurch `bottom` und `stroke-width` sich auf die Handschrift beziehen
statt auf die Headline.

**Platzierung:**
- Einzeilige Headlines (Projekte, Leistungen): mittig im Wort (`left: 50%`).
- Zweizeilige (Kunden, Kontakt): mittig auf dem **Zeilenende** der letzten Zeile
  (`left: 100%`) — der Vermerk ragt zur Hälfte über die kürzere Schlusszeile hinaus, wie eine
  Notiz ans Satzende. Die letzte Zeile bekommt dafür einen eigenen Bezugsrahmen
  (`.lastline`, `inline-block`), sonst zentrierte er auf der Containerbreite.
- `bottom: -0.271em`, 5° geneigt, `stroke-width: 0.11em`. Die Konturbreite ist gemessen: Die
  Zahl der dünnen dunklen Reste hat ihr **Minimum bei ~0,105 em** und steigt danach wieder,
  weil eine breitere Kontur von außen in die Headline frisst und dort neue Reste erzeugt.
  Es gibt also keine Breite, bei der alles restlos geschlossen ist.

**Optischer Randausgleich:** Sairas Versalien haben eine linke Seitenverkleinerung, das ✳ der
Eyebrow praktisch keine. Ohne Korrektur stünde die Headline 10,5 px (bei 128 px) weiter rechts
als das Zeichen darüber — die *Kästen* sind bündig, die *Tinte* ist es nicht.
`margin-left: -0.082em` gleicht das aus, bei allen vier Headlines. Wichtig: Der Wert muss in
derselben Regel stehen wie das `margin: 0` der Headline, ein früherer `margin-inline-start`
würde überschrieben.

**Abstand Eyebrow → Headline:** proportional zur Headline (`0.086em` ≈ 11 px bei 128 px),
damit er bei jeder Größe gleich *wirkt* — ein fester rem-Wert sieht unter einer 64-px-Headline
nach mehr Luft aus als unter einer mit 128 px. Dazu `--dia` als **optischer Ausgleich pro
Headline**, von Tinte zu Tinte gemessen (nicht an den Kästen). Zwei Anlässe dafür:

- **Diakritika:** Bei „FÜR DIESE MARKEN" ragten die Umlautpunkte 12,5 px über die Versalhöhe,
  die Eyebrow rückte dort optisch zu nah heran. Die aktuelle Headline „MIT DIESEN MARKEN"
  hat keine mehr — Überstand 0,5 px.
- **Größe:** Der em-proportionale Grundabstand geht nicht auf, wenn nur *eine* Seite der
  Lücke mitskaliert. Die Eyebrow steht in allen Sections fix auf `0.75rem`, die Headlines
  aber auf 51 bis 128 px. Je kleiner die Headline, desto knapper fällt der Abstand aus —
  gemessen von Tinte zu Tinte, vor dem Ausgleich:

  | Section | Headline | ohne `--dia` | `--dia` | jetzt |
  |---|---|---|---|---|
  | Projekte, Leistungen | 128 px | 28,8 px | — | 28,8 px |
  | Kontakt | 96 px | 25,3 px | — | 25,3 px |
  | Kunden | 64 px | 19,9 px | `0.139em` | 28,8 px |
  | About | 51 px | 12,9 px | `0.225em` | 28,8 px |

  **Offen:** Kontakt liegt mit 25,3 px noch 3,5 px unter den übrigen.
  Bei About kommt ein zweiter Effekt dazu: der Ausgleich rückt auch den Aufstrich des
  handschriftlichen K von der Eyebrow ab, unter der er sonst fast hängt.

Der Wert ist **textabhängig und größenabhängig** — bei geänderter Headline neu messen.

**Eyebrow-Auftakt:** Die Nummerierung `(01)`…`(05)` ist entfallen; stattdessen leitet das
**✳ aus dem Kunden-Marquee** die Zeile ein, in der Akzentfarbe. Es steckt als `::before` am
`.sec-label`, damit im Markup nichts Dekoratives steht. Zwei Details: `align-items: center`
statt `baseline`, weil das Zeichen keine sinnvolle Grundlinie hat, und `line-height: 0`, sonst
schöbe sein Zeilenkasten die Eyebrow auseinander. Alternativen siehe `eyebrow-zeichen.html`.

**Eyebrow-Texte:** Sie sollen einen *Ton* setzen statt die Headline zu wiederholen. In
Seitenreihenfolge gelesen ergeben die fünf einen Satz — das ist der Grund für die Auswahl,
nicht Zufall:

> *Ein kleiner Einblick, was ich anbiete, wie ich arbeite, über die Jahre — auf ein Wort.*

| Section | Eyebrow | vorher |
|---|---|---|
| Projekte | Ein kleiner Einblick | „Ausgewählte Arbeiten" (doppelte „recent work") |
| Leistungen | Was ich anbiete | — |
| About | Wie ich arbeite | „Über mich", dann „Wer dahinter steckt" |
| Kunden | Über die Jahre | „Vertrauen", dann „Gute Gesellschaft" |
| Kontakt | Auf ein Wort | „Kontakt" (doppelte die Headline) |

Der Footer-Navigationspunkt heißt weiterhin schlicht „Über mich" — Sprungmarken dürfen
nüchterner sein als die Eyebrows, die einen Ton setzen sollen.

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

## Sprache, Dokumentkopf und Silbentrennung

Die Datei hat **bewusst kein `<html>`/`<head>`**: sie wird auch als Artifact veröffentlicht,
und dort liefert der Wrapper das Grundgerüst — eigene Dokument-Tags kollidierten damit.
Browser bauen die fehlenden Elemente selbst und ziehen `<title>`, `<meta>` und `<script>`
vom Dateianfang in den impliziten `<head>`. Was sich dort *nicht* raten lässt, muss man
trotzdem liefern:

- `<meta charset>` und `<meta name="viewport">` stehen am Dateianfang. Ohne Viewport-Meta
  rendert ein echtes Telefon mit ~980 px Layoutbreite und zoomt heraus — die gesamte
  Mobile-Arbeit (Reel, Indicator, Subline über MOIN) liefe ins Leere.
- **Die Sprache** geht ohne `<html>`-Tag nur per Skript ans Wurzelelement
  (`document.documentElement.lang = "de"`). Damit sie auch ohne JavaScript wirkt, steht
  `lang="de"` zusätzlich an `<header>`, `<main>` und `<footer>`; die Silbentrennung erbt
  von dort.

Soll die Datei einmal **nicht** mehr als Artifact veröffentlicht werden, ist der saubere
Weg ein echter `<!doctype html><html lang="de"><head>…` — dann entfällt das Skript.

**Silbentrennung:** `hyphens: auto` mit `hyphenate-limit-chars: 6 3 3` (Wörter erst ab
6 Zeichen trennen, mindestens 3 Zeichen vor und nach dem Bindestrich — sonst entstehen
Zwergsilben). Sie greift **nur** bei gesetzter Sprache. Deutsch trennt deutlich häufiger
als Englisch, und die Textspalten sind schmal (About: 331 px bei 1440 px) — ohne Trennung
reißen dort einzelne lange Wörter ganze Zeilen auf.
**Displayzeilen trennen nicht** (`hyphens: manual` auf Headlines, Wortmarke, Kopfzeilen,
Kachel- und Leistungstiteln): ein Bindestrich in einer 128-px-Headline ist ein Bruch im
Bild, kein Lesehilfsmittel.

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
