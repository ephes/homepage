# Portfolio-Startseite — Design-Prototyp

`portfolio-startseite.html` ist ein **eigenständiger, gebauter Design-Prototyp** der
Portfolio-Startseite (Katharina Wersdörfer). Self-contained: Schriften (Saira, Astagina
Signature) und die Leinentextur sind als Base64 eingebettet — die Datei öffnet ohne Server
direkt im Browser.

Unter `projekte/` liegen zusätzlich neun verlinkte Projekt-Unterseiten. Sie teilen sich
`projekt.css` und `projekt.js`; die neun kleinen HTML-Dateien stellen die eigenständigen URLs
bereit und wählen jeweils nur ihren Datensatz. Das bildet die Trennung von gemeinsamem Aufbau
und Seiteninstanzen im Design-Prototyp ab, ist aber ausdrücklich kein Ersatz für das später
serverseitig gerenderte Wagtail-`ProjectPage`-Template.

Die zugehörige Design-Spec liegt unter
[`../specs/2026-07-17-portfolio-site-design.md`](../specs/2026-07-17-portfolio-site-design.md).

## Was der Prototyp zeigt

Eine durchgehende Startseite (Design-Stand, Inhalte noch Platzhalter):

0. **Navigation** — der direkte Kontaktbutton bleibt oben rechts erhalten; unmittelbar
   daneben sitzt ein dauerhaft eingeklappter, freistehender Burger ohne Buttonfläche. Das
   28 px breite Zweilinien-Icon liegt in einem 4,6 rem großen Headerfeld. Beim Öffnen
   laufen beide Linien zur Mitte und drehen sich mit der bereits verwendeten
   `.45s cubic-bezier(.75, 0, .25, 1)`-Kurve zum Schließen-X; bei
   `prefers-reduced-motion` wechselt der Zustand ohne Übergang. Das native `<details>` enthält nur die
   sechs Anker der Startseite einschließlich „Moin“ für den Hero. Die Projektseiten verwenden
   dieselbe Kombination aus Kontaktbutton und Burger; ihr „Moin“-Anker führt zurück an den
   Projektkopf, die übrigen springen in die Inhaltsabschnitte. Weil es sich nur um
   Anker handelt, gibt es bewusst keine dauerhaft sichtbare Navigationsleiste.
   Das Icon sitzt in einem 4,6 rem breiten Feld, dessen senkrechte Linien über die gesamte
   Headerhöhe laufen; der größere Abstand zum Kontaktbutton hält beide Aktionen optisch
   auseinander. Im offenen Zustand wird die untere Feldkante cremefarben und überdeckt die
   Headerlinie. So verbindet sich das Feld wie ein aktiver Reiter mit der cremefarbenen
   Menüfläche. Der Header bleibt mit 80 % Cremeanteil leicht transparent. Ein 20-px-Blur
   mit reduzierter Sättigung beruhigt dunkle Sections und Illustrationen dahinter, ohne die
   Durchlässigkeit aufzugeben. „Verfügbar für Projekte“ verwendet mit `#4B4F48` weiterhin
   einen zurückhaltenden Graugrünton statt des volltonigen warmen Schwarz; selbst über dem
   dunkelstmöglichen Mischgrund erreicht er rund 4,66:1 Kontrast.
   **Das ausgeklappte Panel ist als Statement angelegt:** Es beginnt direkt unter dem Header,
   reicht bis an den unteren Viewportrand und belegt auf dem Desktop die rechte Hälfte des
   Bildschirms; unter 52 rem nimmt es die gesamte Bildschirmbreite ein. Es fährt über
   `clip-path` und `translateX` in 450 ms seitlich von rechts ein und auf demselben Weg wieder
   heraus. Eine deckende Cremefläche, ein kräftiger zweistufig nach links fallender
   Desktopschatten sowie ein Tangerine-Balken links heben es über die gesamte Höhe vom
   Seiteninhalt ab;
   dessen Breite folgt mit
   `clamp(.7rem, 1.2vw, 1.1rem)` exakt dem Innenabstand der Projektkacheln. Eine untere
   Akzentlinie gibt es nicht. Die Links stehen ohne Zeilentrenner, Kästen oder Listenoptik
   als gemeinsamer linksbündiger Block zentriert in der Fläche. Vor jedem Link erscheint das
   schon für die Eyebrows verwendete ✳ in einer etwa doppelt so großen, proportional
   begrenzten Fassung. Beim Öffnen beginnt der erste Link erst nach 400 ms – wenn das Panel
   fast vollständig steht – und die weiteren folgen im klar wahrnehmbaren Abstand von je
   120 ms weich von rechts; `prefers-reduced-motion` entfernt auch diese Bewegung.
   Solange das Panel offen ist, bleibt die aktuelle Seitenposition gegen Mausrad, Touch,
   Tastatur und Scrollbarbewegungen gesperrt, während das Panel bei sehr geringer
   Viewporthöhe intern scrollbar bleibt. Ein Klick schließt das Menü und fährt weich zum
   jeweiligen lokalen Anker. Auf Desktopgeräten mit echter Maus fährt bereits das Hover
   über einen lokalen Menüpunkt die Seite dahinter weich zum Ziel; seitenübergreifende Links
   lösen keine Hover-Navigation aus. Die restliche Seite liegt unter einem Schleier aus
   **28 % warmem Schwarz** mit einer feinen, per SVG-Turbulenz erzeugten
   Filmkörnung. Er liegt über der gesamten Hintergrundfläche einschließlich des Headers;
   nur das aktive Menüfeld und das Panel bleiben darüber scharf. Der Schleier blendet in
   160 ms schneller ein als das Panel; dieses schiebt sich anschließend lückenlos über die
   bereits gedämpfte Fläche. Bewusst ohne Blur bleibt die Gestaltung erkennbar, wirkt aber klar zurückgesetzt;
   ein Klick auf den Schleier schließt das Panel. Eine cremefarbene Überdeckung unter dem
   Iconfeld unterbricht dort die obere Panel- und Headerlinie vollständig und schließt den
   Reiter sichtbar an die Menüfläche an.

   **Progressive Enhancement und Tastatur:** Das Menü selbst basiert auf
   `<details>/<summary>` und bleibt deshalb bei abgeschaltetem JavaScript mit Tab sowie
   Enter/Leertaste bedienbar; die Links sind echte Anker. Nach einem Sprung bleibt das
   native Disclosure ohne Skript offen und wird über den Summary-Schalter geschlossen.
   JavaScript ergänzt
   nur weiches Scrollen bzw. Desktop-Hover-Navigation, Scroll-Lock, Klick außerhalb,
   dynamische Beschriftung, `inert` für den abgedeckten Seiteninhalt, Escape zum Schließen
   und einen zyklischen Fokus innerhalb des offenen Panels. Bei
   `prefers-reduced-motion` werden Ankersprünge und Menüwechsel nicht animiert.

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
4. **About** — auf dem 4-Spalten-Raster: **die Spalten 1–3 tragen allen Text, Spalte 4 das
   Porträt.** Oben das **Statement** („ICH BIN Katharina / UND BLEIBE GERN NEUGIERIG."
   — der Umbruch steht als `<br>` fest im Markup), darunter **drei Akkordeon-Kacheln**
   (Verstehen / Gestalten / Umsetzen), darunter eine Abschlusszeile: links die Verortung
   „Digital Creative · Based in Düsseldorf", rechts **„Mehr im Lebenslauf"** (aus der
   Kontakt-Section hierher gewandert). Beide sitzen auf dem Textanschlag; eine eigene
   Trennlinie hat die Zeile nicht — die Unterkante der Kachelreihe trennt bereits, ein
   zweiter Strich wäre ein Doppelstrich.
   **Das Statement ist ein `<h2>`, die Kacheltitel sind `<h3>`.** Vorher war das Statement
   ein `<p>` — die Section hatte damit gar keine Überschrift, und `<h3>` hätte in der Luft
   gehangen. Eckdaten-Trio und Handschrift-Signatur sind entfallen; damit ist die Klasse
   `.script` im Markup nicht mehr in Gebrauch.
   **Der handschriftliche Vermerk der Section sitzt auf der Unterkante des Porträtfeldes**
   und sagt „that's me" — das frühere `hallo!` in der Eyebrow ist entfallen, samt der
   nun gegenstandslosen Regel `.sec-label .scr`. Technik und Fallstricke wie bei den
   Vermerken auf den Headlines (SVG-Text, `paint-order: stroke`, reale SVG-Größe statt
   0×0, `bottom` = Grundlinie); Größe ebenfalls `--scr-size`, damit alle Vermerke der
   Seite gleich groß sind. Er bleibt dabei innerhalb der Porträtspalte — nachgemessen bei
   1440/900/390 px: 62/38/76 px Luft links, 79/49/82 px rechts.
   Beim Vermerk „that's me“ wird ausschließlich die Apostroph-Glyphe um rund `0.156em`
   nach rechts gerückt, damit sie nicht in den hohen Abstrich des zweiten `t` klemmt.
   Das anschließende „s me“ behält seine originale Position. Animierter Outline- und
   Maskenpfad werden deckungsgleich verschoben; der statische SVG-Text ohne JavaScript
   gleicht den Versatz mit drei entsprechenden `tspan`-Elementen wieder aus. Der Versatz
   wird direkt in die Koordinaten des Apostroph-Teilpfads geschrieben, während der
   ursprüngliche zusammenhängende Compound-Path erhalten bleibt. Dadurch entstehen weder
   zusätzliche Konturkappen am `t` noch Maskennähte im `m` oder am Endschwung des `e`.
   Nur bei diesem Vermerk wird außerdem die generierte 12-Punkt-Kantenhilfslinie
   ausgeblendet: Sie verdoppelte an den engen Selbstüberschneidungen sichtbar den oberen
   `t`-Abschluss, den Übergang im `m` und den Endstrich des `e`. Tintenfläche,
   cremefarbene Außenkontur und beide Schreibmasken bleiben vollständig erhalten.
   **Größe und Versalien sind dieselben wie bei der Kunden-Headline** (`.clients h2.big`,
   `clamp(2rem, 5vw, 4rem)`, `line-height: 1`, `text-transform: uppercase`) — About ist damit
   eine Section-Headline unter Section-Headlines und keine Zwischenüberschrift mehr. Vorher
   stand sie mit `clamp(1.6rem, 3.6vw, 3.2rem)` bei 51,2 px im gemischten Satz und war die
   kleinste der Seite. Mit den Versalien kommen die beiden Werte, die daran hängen: der
   Eyebrow-Ausgleich `--dia` (0.139em wie bei Kunden statt der früheren 0.225em) und der
   optische Randausgleich `-0.082em`, mit dem Sairas Versalien gegen das ✳ fluchten.
   **Achtung, Umbruch:** Bei 64 px ist die zweite Zeile 925,7 px breit. Sie passt ab
   ~1330 px Viewport in die drei Textspalten (bei 1440 px bleiben 38,7 px Luft); darunter
   bricht die Headline **dreizeilig** um — bei 1280 px stehen 857,3 px zur Verfügung.
   Das ist kein Fehler (die Kunden-Headline ist ebenfalls dreizeilig), aber eine bewusste
   Folge: Wer zweizeilig erzwingen will, muss die vw-Stufe senken.
   **Der Name im Statement steht in der Handschrift**, als `<span class="katha">` mitten im
   Satz, in der Akzentfarbe — der einzigen Stelle neben dem ✳, an der sie Text trägt (bei
   64 px greift die Schwelle für große Schrift, 3:1; Tangerine liegt mit 3,4 darüber).
   Der Span trägt `text-transform: none` — „KATHARINA" in einer Signaturschrift wäre falsch
   gesetzt.
   Die Größe `1.75em` ist gemessen, nicht geschätzt: Astagina hat bei *gleicher* Größe eine
   kleinere x-Höhe als Saira, aber eine höhere Versalie — Cap- und x-Höhe fordern also
   gegensätzliche Werte. Verglichen wurden 1,30/1,50/1,70/1,90× am echten Font: bei 1,75 em
   trägt der Name wie eine Unterschrift, ab 1,90× wird das K zum Solisten. Neben den
   Versalien misst die Handschrift damit 85,4 px Tinte gegen 45,0 px Versalhöhe (bei 64 px).
   Weil der Umbruch vor „und" fest im Markup steht, kann sie breit laufen, ohne den
   Zeilenfall zu verschieben.
   Dazu `line-height: 0.571` am Span: `line-height` wird als Zahl vererbt, der Span bekäme
   sonst 1 × 1,75 em und zöge die beiden Headline-Zeilen auseinander. 0,571 × 1,75 ≈ 1,
   also genau die Zeilenhöhe des Absatzes.

   **Der Name liegt schräg ÜBER der Headline und bleibt optisch von der zweiten Zeile gelöst** — dieselbe
   Geste wie die Vermerke auf den anderen Sektionsköpfen, nur mitten im Satz. Damit kommt
   auch deren Technik: **SVG-Text**, weil nur dort die Kontur *glatt und rund* sein kann
   (`stroke-linejoin: round` + `paint-order: stroke`); ohne freigeschnittene Kontur
   verklumpten „Katharina" und „UND BLEIBE" ineinander. Die bekannten Fallstricke gelten
   auch hier: reale SVG-Größe statt 0×0 (Chrome malt es sonst nicht) und `bottom` auf der
   **Grundlinie**, nicht auf der Unterkante.

   | Wert | | warum |
   |---|---|---|
   | `font-size` | `1.3em` | auf die Span-Größe bezogen, also 1,3 × 1,75 em = 145,6 px bei 1440 px. Größer als der Platzhalter, damit die Schrift überhaupt in Zeile 2 reicht |
   | `bottom` | `0.24em` | gegenüber dem geometrischen Messwert `0.112em` optisch angehoben, damit der Name freier über der Headline sitzt |
   | `transform` | `rotate(-5deg)` | dieselbe Schräge wie die Headline-Vermerke |
   | `z-index` | `-1` am Span | legt die Handschrift hinter die übrige Headline; der lokale Stapelkontext am `<h2>` hält sie dabei sicher vor dem Seitenhintergrund |

   **Ausgerichtet wird links** (`left: 0` + `text-anchor: start`), nicht mittig wie die
   übrigen Vermerke: Der gezeichnete Name ist größer als sein Platzhalter: zentriert lief er
   nach links ins „N" von „ICH BIN" und machte es unlesbar (nachgemessen). Nach rechts ist
   Platz — die erste Zeile misst 471 px, die Textspalte 964 px.
   Zu beachten: `transform-origin: center` bezieht sich auf das 1×1-px-SVG, nicht auf den
   Text. Bei linksbündigem Text liegt dieser komplett rechts des Drehpunkts, die Rotation
   hebt ihn deshalb als Ganzes um rund 22 px an — `bottom` gleicht das zunächst geometrisch
   aus und wurde anschließend für die gewünschte optische Höhe auf `0.24em` angehoben.

   **Der Name steht zweimal im DOM.** Der HTML-Text bleibt als `color: transparent`
   Platzhalter stehen — er hält die Breite im Satz und ist für Screenreader und Seitensuche
   der eigentliche Inhalt; gezeichnet wird das SVG darüber. Damit das nicht durchschlägt:
   `aria-hidden="true"` am SVG (sonst läse der Screenreader den Namen doppelt) und
   `user-select: none` (sonst stünde beim Kopieren „KatharinaKatharina"; verifiziert — die
   Auswahl liefert „ICH BIN Katharina UND BLEIBE GERN NEUGIERIG."). Die Seitensuche findet
   zwei Treffer, beide an derselben Stelle.
   **Die Eyebrow braucht hier keine Sonderbehandlung mehr.** Solange das Porträt links lag
   und der Text erst in Spalte 2 begann, musste sie um eine Rasterspalte mitwandern
   (`margin-inline-start: 25 %`) — sonst hätte sie allein über dem Bild gestanden und die
   zwischen ✳ und Headline ausgemessene Tintenflucht (`-0.082em`) hinge in der Luft. Jetzt
   beginnt der Text in Spalte 1 und sie steht auf demselben Anschlag wie in jeder anderen
   Section; die Regel und ihre mobile Rücknahme sind entfallen.
   Spalte 4 trägt über alle Zeilen das Porträt als **Klecks** —
   `grid-row: 1 / span 3` mit `align-self: start`, **nicht** `1 / -1`: ohne
   `grid-template-rows` gibt es kein explizites Zeilenraster, `-1` zeigt dann auf Linie 1
   und der Klecks landet wieder in Zeile 1. Dort bestimmte seine Höhe die Zeilenhöhe, und
   unter dem zweizeiligen Statement stünden ~250 px Leere.
   Die Maske selbst: ein SVG-`clipPath` mit Hauptform und vier abgelösten Spritzern
   (mehrere Teilpfade in einem `clipPath` ergeben zusammen die Maske).
   `clipPathUnits="objectBoundingBox"`
   rechnet in Anteilen 0…1, die Form skaliert also mit dem Element. Border und Diagonalkreuz
   entfallen — eine Border würde von der Maske angeschnitten.
   **Das Feld steht 4:5** (Breite × 1,25), also hochkant: Die Spalte ist unter dem
   zweizeiligen Statement ohnehin frei, und ein Porträt steht hochkant besser als im
   Quadrat. Gerendert sind das 294 × 368 px bei 1280, **331 × 414 px bei 1440** und
   448 × 560 px bei 1920 px Viewport; gestapelt deckelt `max-width: 14rem` auf 224 × 280 px.
   Für 2× scharfe Bilder auf großen Screens also rund **1200 × 1500 px**.
   Die Maske wird durch das Seitenverhältnis mitgezogen — sie rechnet ja in Anteilen der
   Elementbox — die Klecksform steht dadurch länglicher als im Quadrat. Wer sie wieder
   rundlicher will, ohne das Feld zu ändern, müsste die y-Anteile im Pfad um denselben
   Faktor stauchen und die Form mittig setzen.
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
   jetzt in About. Der Button ist der einzige **Prio-1-Button** der Seite (s. unten).

## Buttons: drei Prioritäten

| Prio | Klasse | Aussehen | wo |
|---|---|---|---|
| **1** | `.pill.prio` | Tangerine-Fläche, Creme-Text, 19,2 px/700, mit Pfeil | **nur** „E-Mail schreiben" in Kontakt |
| 2 | `.pill` | warmes Schwarz, Creme-Text | Header-Kontakt, CTA-Kachel |
| 3 | `.pill.ghost` | transparent, nur Kontur | „Mehr im Lebenslauf" in About |

**Das Signal von Prio 1 ist die Farbe, nicht die Größe.** Tangerine kommt sonst nirgends als
Fläche vor — nur im ✳ der Eyebrows und im Namen „Katharina". Der Button ist damit der einzige
Farbfleck der Seite. Verworfen wurde die naheliegende Alternative, die vorhandene
schwarze Pille einfach XL zu setzen: Die Navigation trägt dieselbe Pille, die große Fassung
liest sich deshalb als *derselbe* Button in größer, nicht als andere Stufe (nebeneinander
verglichen). Ebenfalls verworfen: die Kontakt-Section auf Dunkel mit Limette-Button — Kunden
davor ist bereits dunkel und der Footer danach auch, drei dunkle Blöcke am Stück ließen die
Section verschwinden statt hervorstechen.

**Die Mindestgröße ist eine Kontrastfrage, kein Geschmack.** Tangerine trägt keinen Text in
Normalgröße:

| Text auf Tangerine | Ratio | AA normal (4,5) | AA groß (3,0) |
|---|---|---|---|
| Creme | 3,42 | nein | **ja** |
| Warmes Schwarz | 4,55 | **ja** | **ja** |

Der Button muss deshalb **mindestens 18,66 px fett** bleiben — bei 1.2rem/700 sind es
19,2 px. Creme ist die Entscheidung (Katharina); warmes Schwarz wäre mit 4,55 zwar auch in
Normalgröße zulässig, wirkt auf Tangerine aber stumpf. Der Puffer der gewählten Creme bleibt
mit 3,42 gegen 3,0 knapp, aber ausreichend.
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
  unterzugehen — die gestapelte Folge ist also Eyebrow, Porträt, Statement, Kacheln,
  Abschlusszeile, unabhängig davon, dass das Porträt auf dem Desktop rechts steht.
- **Slide-Indicator** unter jedem Reel: eine Spur mit Anfasser für alle, die nicht wischen
  wollen. Breite des Anfassers = sichtbarer Anteil, Position = Scrollfortschritt; ziehbar per
  Pointer-Events, bedienbar per Tastatur (`role="slider"`, Pfeiltasten, Home/End). Er zeigt
  sich nur, wenn der Reel wirklich überläuft (`.is-scrollable` setzt das Skript).
  Die Spur ist auf den **Textanschlag** eingerückt (Padding-Linie + `--hero-inset`, gemessen
  28…362 px bei 390 px Viewport) und sitzt eng unter dem Reel, aber mit deutlich mehr Abstand
  zur CTA-Kachel darunter (14 px oben / 40 px unten) — sonst liest sie sich als deren Zubehör.
- Beide Reels verstecken die native Scrollbar, weil der Indicator ihre Rolle übernimmt.

## Farben

Alle fünf Rollen aus `farbpalette.html` sind integriert; dort stehen Herleitung,
Kontrastmatrix und die verworfenen Kandidaten.

| Rolle | Token | Wert | Einsatz |
|---|---|---|---|
| Grundton | `--creme` | `#F0ECE2` | Fläche der ganzen Seite |
| Warmes Schwarz | `--warm-black` | `#171410` | Schrift auf Hell, dunkle Sections, Footer |
| Akzent | `--tangerine` | `#EB3D00` | trägt auf hell (3,42) wie dunkel (4,55) |
| Zweitakzent | `--limette` | `#C7F03C` | reserviert, aktuell nicht eingesetzt |
| Mittlere Fläche | `--pine` | `#294122` | als Fläche noch **reserviert** |

**Eine Quelle statt drei.** Die Tokens standen vorher auf zwei `:root`-Blöcke verteilt,
plus einen toten `[data-theme="light"]`-Rest des entfernten Dark Mode. Dadurch waren
`--pill-bg`/`--pill-ink` faktisch tot (eine zweite `.pill`-Regel überschrieb sie) und
`--smaragd` war definiert, aber nirgends benutzt. Alles liegt jetzt in einem Block.

**Der Akzent bleibt auf dunklem Grund Tangerine** — `.on-dark { --accent:
var(--tangerine) }` gilt einheitlich für alle Flächen. Tangerine kommt auf warmem Schwarz
auf 4,55:1 und trägt damit die grafischen Eyebrow-Zeichen und die große handschriftliche
Ergänzung. Auf Hell bleibt der Vermerk dunkel: Tangerine wäre dort mit 3,42 zu schwach für
eine Schreibschrift.
Der Verfügbarkeits-Punkt ist unabhängig davon ein Statussignal und bleibt oben wie im
dunklen Footer Smaragdgrün; auf warmem Schwarz erreicht er 5,04:1.

**Pine ist als Fläche nicht vergeben.** Zwei Versuche sind verworfen (beide Entscheidung
Katharina):

- **CTA-Kachel** — sie bleibt auf dem Nahschwarz der dunklen Sections und liest damit als
  deren zweite Ebene statt als eigene Farbe.
- **About-Section auf Pine** — technisch lief das über die vorhandene `.on-dark`-Mechanik
  mit `--dark-bg: var(--pine)`, die Kontraste trugen alle (Creme 9,50 · Limette 8,52).
  Gegen die Variante sprach die Nachbarschaft: About liegt direkt über der Kunden-Section
  im damaligen Sacramento, und die beiden dunklen Grüntöne stießen ohne helle Zäsur aneinander — das
  liest sich eher wie ein Fehler in derselben Fläche als wie zwei Ebenen. Dazu verlöre die
  Seite ihren hellen Grundcharakter: zwei von fünf Sections wären dann dunkel.

Pine trägt damit nur den Verfügbarkeits-Punkt auf hellem Grund. Sein vorgesehener Platz
laut Palettenseite sind **Hover-Zustände** — die gibt es im Prototyp noch nicht. Wichtig
dabei: Tangerine erreicht auf Pine nur 2,78, ein Akzent kann auf dieser Fläche also nicht
mitkommen.

**Linien und Platzhalter sind warmes Schwarz mit Deckkraft**, keine eigenen Farben — so bleiben
sie beim Ton, wenn der Grundton wechselt.

**`--muted` ist nachgerechnet:** `#686D62` erreicht auf Creme **4,50:1**. Der frühere
warme Grauton `#7d766a` lag bei 3,81 und riss damit alle Eyebrows, Kachel-Metazeilen und
Leistungssätze unter AA. `--dark-muted` ist aus demselben Grund von 55 % auf 62 % Deckkraft
gegangen (5,18 → 6,20).

Bleibt bewusst außerhalb der Palette: die **Platzhalter-Illustration** hinter dem MOIN
(bunte Blobs im Skript) — sie wird durch Katharinas echtes Bild ersetzt.

## Projekt-Unterseiten

Die neun Kacheln der Startseite führen auf neun eigene URLs unter `projekte/`. Der Aufbau
orientiert sich strukturell an der Nexis-Health-Referenz, übernimmt aber ausschließlich die
bereits vorhandene Sprache des Prototyps: Saira, Vier-Spalten-Raster, Eyebrows mit ✳,
Platzhalterflächen, dunkle Ergebnis-Section, Pill-Buttons und Footer.

Die gemeinsame Reihenfolge lautet: Projekttitel und Metadaten, Titelbild, Case Study mit
Projekt/Aufgabe/Lösung, flexible Galerie, optionale Ergebnisse, optionales Kundenstatement,
zwei weitere Projekte und Kontakt-CTA. Der Kontakt-CTA übernimmt dabei unverändert die
Komponente der Startseite – einschließlich Label, Headlineskalierung, Astagina-Vermerk,
Abständen und Button. Noch unbekannte Inhalte stehen in eckigen Klammern;
es wurden keine Kunden, Leistungen, Kennzahlen oder Zitate erfunden. Die inzwischen
ergänzten Effekte folgen ausschließlich dem unten beschriebenen gemeinsamen Motion-System.

„Weitere Projekte“ wiederholt keine neue Card-Variante, sondern exakt die Konstruktion der
großen Startseiten-Projektkacheln: zwei Kacheln nebeneinander im Vier-Spalten-Raster, je zwei
Spalten breit, mit `21:9`-Bildfeld, identischem Innenabstand, Subline-Größe für den Titel und
Eyebrow-Größe für Bereich/Jahr. Mobil stapeln sie sich wie das bestehende Projektraster. Ein
kleiner Pfeil rechts gehört wie auf der Startseite zur Titelzeile. Kacheln, Projektanfrage
und Kontaktbuttons verwenden dieselbe fontunabhängige CSS-Geometrie: eine 1,25-px-Haarlinie
mit kleiner Pfeilspitze. Damit sind Form, Tangerine-Farbe und kurze Hoverbewegung auf Start-
und Unterseiten identisch; eine abweichende Unicode-Glyphe kann nicht mehr dazwischenfunken.

Der vertikale Rhythmus von Start- und Projektseiten verwendet drei gemeinsame Tokens:
`--space-section` für das Section-Padding, `--space-eyebrow-title` für den kleinen optischen
Abstand zwischen Eyebrow und Headline sowie `--space-title-content` zwischen Headline und
nachfolgendem Inhalt. Der zuvor nur auf den Unterseiten gesetzte Eyebrow-Abstand von
`clamp(1.5rem, 3vw, 2.5rem)` entfällt; vor Headlines gilt nun wie auf der Startseite die
deutlich engere, schriftproportionale Distanz von `.086em`. Eyebrows ohne folgende Headline,
etwa vor dem Kundenstatement, verwenden weiterhin den größeren Inhaltsabstand.

Die vier zentralen Display-Stufen `--headline-xl`, `--headline-l`, `--headline-m` und
`--headline-s` halten die Überschriften auf Start- und Projektseiten zusammen. Jede Stufe
verwendet genau eine durchgängige `clamp()`-Formel mit Grenzen in `rem` und einer fluiden
Viewport-Komponente; Schriftgrößen werden weder am Mobile- noch am Desktop-Breakpoint
überschrieben. Das About-Statement verwendet wie die kleinere Markenheadline die M-Stufe;
die Akkordeon- und Leistungstitel verwenden gemeinsam S.

Für die kleinen Textebenen gibt es zwei gemeinsame fluide Größen: `--type-eyebrow` für alle
Eyebrows und eyebrowartigen Rasterlabels sowie `--type-subline` für About-Sublines,
„Digital Creative · Based in Düsseldorf“, normale
Buttontexte und Leistungs-Sublines. Die Leistungstitel verwenden wie die About-
Akkordeontitel `--headline-s`. Hero-Subline, Projekt-Lead und der priorisierte
Tangerine-Kontaktbutton teilen sich die fluide Stufe `--type-lead`; deren Untergrenze von
`1.2rem` hält die cremefarbene, fette Buttonschrift weiterhin in der erforderlichen
Großtext-Stufe.

Über Startseite und alle neun Projektseiten bleiben damit **10 eigenständige
Schriftgrößen-Rollen**:

1. Eyebrow/Rasterlabel (`--type-eyebrow`)
2. Subline, normale Buttons, UI-Text und normaler Case-Fließtext (`--type-subline`)
3. Hero-Subline, Projekt-Lead und priorisierter Kontaktbutton (`--type-lead`)
4. Headline S, Kunden-Marquee und Projektnummer (`--headline-s`)
5. Headline M und Menüpunkte (`--headline-m`)
6. Headline L (`--headline-l`)
7. Headline XL (`--headline-xl`)
8. handschriftliche Vermerke (`--scr-size`)
9. Hero-Wort „MOIN“ (Canvas und HTML-Fallback sind dieselbe Rolle)
10. großer Case-Fließtext und Kundenstatement (`--type-case-large`)

Das ✳ vor den Menüpunkten ist kein eigener Textstil mehr: Es skaliert relativ zum
Menüpunkt und wird durch die bestehende Headline-S-Stufe gedeckelt. Inhaltlich besteht das
reguläre Typografiesystem damit aus acht Größen; Astagina-Handschrift und das geometrisch
eingepasste „MOIN“ bleiben zwei bewusste Signature-Sonderfälle.

Die zusätzlichen `em`-Werte an `sup`, ✳ und den intern verschachtelten
Handschrift-Ebenen sind relative Skalierungsfaktoren ihrer jeweiligen Eltern und daher keine
eigenständigen Textstufen. Es gibt in den produktiven Start-/Projektstyles keine
`font-size` in Pixeln und keine Schriftgrößen-Überschreibung innerhalb einer
Viewport-Media-Query; alle eigenständigen Stufen sind über `clamp()` mit `rem`-Grenzen fluid.
Der normale Case-Fließtext verwendet bewusst nicht die Eyebrow-Stufe: Deren
`0.72rem`–`0.82rem` sind für kurze Labels gedacht und für längere Lesetexte zu klein.

Auch die zentralen Laufweiten sind semantisch vereinheitlicht: `--tracking-display`
setzt große, eng laufende Headlines und Menüpunkte auf `-0.03em`,
`--tracking-action` verbindet Namensbranding und Fold-Buttons bei `0.01em`, und
`--tracking-label` setzt Verfügbarkeitsanzeige, Eyebrows, Case-Labels und vergleichbare
Versal-Labels auf `0.1em`. Projektmetadaten (`0.04em`), Cursor-Ring (`0.06em`) und reine
Bildformat-Platzhalter (`0.08em`) bleiben als funktional andere Textarten separat.

## Motion-System

`motion.css` und `motion.js` werden von Startseite und Projektseiten gemeinsam verwendet.
Headlines bewegen sich beim Eintritt von unten nach oben an ihre Position (`Reveal`).
Deckkraft und Buchstabenproportionen bleiben dabei unverändert; eine Maske oder Schnittkante
wird nicht verwendet. So können auch überstehende handschriftliche Vermerke nicht am
Headline-Rechteck beschnitten werden. Mit JavaScript setzt ein kleines Scroll-Skript dafür
nur den Eintrittsstatus; die Bewegung selbst bleibt CSS. Es misst die unveränderte Layoutbox über
`offsetTop`/`offsetHeight` statt das transformierte sichtbare Rechteck. Dadurch kann die
Reveal-Bewegung am unteren Viewportrand ihre eigene Sichtbarkeit nicht verändern oder bei
langsamem Scrollen flackern. Dadurch funktioniert der Effekt
allein auf Projektunterseiten ebenso wie vor einer nachgelagerten Handschriftanimation auf
der Startseite. Ohne JavaScript übernimmt – sofern der Browser sie unterstützt – eine
native CSS-View-Timeline: Eine `entry`-Animation führt die Headline von unten an ihre
Ruheposition, eine getrennte `exit`-Animation bewegt sie oben hinaus und läuft beim
Zurückscrollen automatisch rückwärts. `html:not(.has-js)` trennt diesen CSS-Weg von der
zeitbasierten JavaScript-Fassung, sodass beide nie gleichzeitig auf `transform` schreiben.
Die Grunddarstellung bleibt bewusst fail-open: Fehlt auch View-Timeline-Support, steht die
Headline sichtbar an ihrer normalen Position; es fehlt nur die Bewegung.
Headline-Reveals werden zurückgesetzt, sobald die jeweilige Überschrift vollständig aus dem
Viewport verschwunden ist. Beim erneuten Eintritt laufen sie daher auch nach Vor- oder
Zurückscrollen wieder. Beim Herunterscrollen kommt die Headline von unten, beim Rückweg von
oben. Zwölf Pixel Eintritt und 24 Pixel Austrittshysterese halten den Zustand zusätzlich
stabil, wenn eine Headline genau auf der Viewportkante steht. Die
Astagina-Schreibanimationen bleiben davon unabhängig einmalig:
Ein bereits geschriebener Vermerk wird in derselben Seitenansicht nicht erneut geschrieben.
Gefüllte Buttons verwenden die gemeinsame `Fold`-Bewegung; deren Darstellung sowie Kachel-Hover, Pfeil und
Link-Haarlinien sind CSS.

Die Fließtexte auf den Projektseiten (`project-lead`, alle Case-Texte und das
Kundenstatement) sortieren sich über native CSS-View-Timelines ruhig von rechts an ihrer
Satzkante ein. Die Leistungskacheln verwenden dagegen bewusst keine CSS-View-Timeline mehr:
Bei schnellem Scrollen sprang deren Fortschritt unmittelbar mit der Scrollposition. Ein
kleiner `IntersectionObserver` meldet stattdessen ausschließlich Eintritt, Austritt und
Scrollrichtung; Bewegung, Easing und Staffelung liegen weiterhin im CSS. Dadurch laufen die
Animationen nach dem Auslösen mit stabiler Zeitbasis weiter, unabhängig von der
Scrollgeschwindigkeit. Beim Herunterscrollen sammelt der Observer die sichtbaren Kacheln,
bis die normale `headline-reveal`-Animation der großen Leistungen-Headline beendet ist.
Bereits beim Start dieser Headline werden die räumlich nahen Kacheln vorgemerkt, damit nach
ihrem Ende nicht noch die eigene 20-Prozent-Sichtbarkeitsschwelle der Kacheln abgewartet
wird. Unmittelbar mit dem Headline-Ende beginnt die Kachelfolge; die Astagina-Handschrift
ist ausdrücklich kein Teil dieses Gates. Ein 1.700-ms-Fallback verhindert Stillstand,
falls die Headline bei einem extremen Sprung vollständig überscrollt wurde.

Der Eintritt dauert 1.350 Millisekunden, der Austritt 1.050 Millisekunden. Die acht Kacheln
folgen mit 85 Millisekunden Abstand; innerhalb jeder Kachel folgen Titel und Text 100 bzw.
210 Millisekunden nach dem Icon. Beim Austritt läuft eine etwas engere Staffelung in
Scrollrichtung. So bleibt die gewünschte Bewegung der Einzelelemente erhalten, während
Kacheln und Reihen eine kontinuierliche Sequenz bilden. Beim Rückweg werden Richtung und
Reihenfolge umgekehrt. Es gibt weiterhin keinerlei Hover-Reaktion.

Der Bewegungsweg wächst über `clamp(2rem, 3vw, 3.75rem)` fluid mit dem Viewport: Auf einem
1.920 px breiten Screen sind es 3,6 rem, auf kleinen Geräten mindestens 2 rem. Damit bleibt
der Effekt auf großen Displays deutlich lesbar, ohne die Zellen selbst zu verschieben.
Die Effekte verändern weder Deckkraft noch Textproportionen. Ohne JavaScript stehen alle
Inhalte sichtbar an ihrer normalen Position; `prefers-reduced-motion` schaltet die Bewegung
vollständig ab.

Die drei geschlossenen About-Akkordeons „Verstehen“, „Gestalten“ und „Umsetzen“ übernehmen
dieselbe zeitbasierte Ein- und Austrittswelle. Innerhalb jeder Kachel folgt die Subline dem
Titel leicht verzögert; die drei Kacheln folgen einander ebenfalls versetzt. Animiert werden
ausschließlich Titel und Subline. Das Plus/Minus, die Rasterfläche und die vorhandene
Akkordeonbewegung bleiben vollständig unangetastet. Beim Herunterscrollen schließt die Welle
ohne zusätzliche Sichtbarkeitspause an: Sie beginnt bereits in der ruhigen Endphase der
normalen About-Headline-Animation und damit unabhängig von der parallel laufenden
Astagina-Handschrift.

Die Case-Labels „Das Projekt“, „Die Aufgabe“ und „Die Lösung“ fluchten auf breiten
Projektseiten mit der Textkante der Eyebrow „Case Study“, sodass deren Tangerine-Asterix
optisch links heraushängt. Der zusätzliche Einzug wächst über `clamp()` fluid von `0` auf
die Breite aus Asterix und Eyebrow-Gap; die Mobile-Position bleibt deshalb ohne zusätzliche
Viewport-Media-Query unverändert.

Die Projektanzahl an der Startseitenheadline wird als `[9]` in eckigen Klammern und mit
derselben fluiden `--type-subline`-Stufe wie die Titel der Projektkacheln gesetzt.
Das Namensbranding steht bewusst ohne Markensymbol, da keine eingetragene Marke bezeichnet
wird; dies gilt für Header, Footer, Projekt-Template und JavaScript-freie Projekt-Fallbacks.

Die About-Section bleibt mindestens so hoch wie die sichtbare Fläche unter der Navigation
und unterschreitet dabei nie `50svh`. Die Marken-Section „Mit diesen Marken & Menschen“
belegt ebenfalls mindestens `50svh`; beide Sections wachsen bei mehr Inhalt weiterhin mit.
Der untere rechte, freischwebende Spritzer der Porträtmaske liegt gegenüber seiner früheren
Position um sieben Prozentpunkte weiter rechts und 7,5 Prozentpunkte höher. Damit bleibt er
auch während seiner Eigenbewegung frei vom Vermerk „that's me“.
Der handschriftlich gezeichnete Name „Katharina“ im About-Statement sitzt mit
`bottom: 0.24em` etwas höher als sein transparenter Platzhalter und bleibt dadurch klar oberhalb der
zweiten Statement-Zeile.

Die sichtbare Kundenfolge im Marquee lautet: ALDI Nord, Kerrygold, L’Oréal, Thomy,
Maybelline, essie, Weight Watchers, Miele, Yokohama, McCann, Marina Adler, Fabian Heis,
Villa Kunterbunt e.V., Ökologische Tierzucht gGmbH, django chat, GGS Lennéstraße und
erneut McCann. Für den nahtlosen Lauf folgt im Markup dieselbe Sequenz ein zweites Mal;
diese technische Kopie ist mit `aria-hidden` vor assistiven Technologien verborgen.

Die `Write`-Animation der Astagina-Vermerke verwendet dieselbe, im CV-/Coverletter-Projekt
bewährte Pipeline: `handwriting-glyphs.js` enthält die echten, in Pfade umgewandelten
Font-Outlines und die handgetracten Mittellinien aus `handwriting-anim`. Die Mittellinien
dienen nur als Maske; sichtbar werden die Original-Outlines mit derselben cremefarbenen
0,11-em-Kontur auf hellem Grund, Größe, Drehung und Grundlinienposition wie im gestalteten
statischen SVG. Tinte und Kontur laufen synchron auf getrennten Masken: Die Tinte behält
die schmale originale Stiftbreite, damit auch separate Querstriche und Schnörkel geschrieben
statt flächig aufgedeckt wirken; die breitere Maske deckt ausschließlich die Kontur ab. Runde Maskenkappen
und eine sehr kurze Opacity-Schwelle verhindern sowohl eckige Abrisse als auch isolierte
Startpunkte. Fehlen JavaScript oder die generierten Outlines, bleibt das Original-SVG aus
dem Markup unverändert sichtbar. `prefers-reduced-motion` zeigt ebenfalls sofort die
unveränderte Endansicht.

Der Schreibstart besitzt nur noch eine Freigabebedingung: Die unveränderte Layoutbox der
zugehörigen Headline muss vollständig zwischen Sticky Header und unterem Viewportrand
stehen. Weder das Ende des Headline-Reveals noch eine zuvor geschriebene Handschrift ist
Voraussetzung. „that's me“ liegt zwar am Porträt, wird aber derselben About-Headline wie
„Katharina“ zugeordnet.

Alle gleichzeitig freigegebenen Vermerke laufen in eine gemeinsame, nach DOM-Reihenfolge
sortierte Queue und werden ausschließlich nacheinander geschrieben. Damit bleibt innerhalb
von About „Katharina“ vor „that's me“; stehen auf einem großen Screen zusätzlich die
Kunden-Headline oder eine weitere Sektionsheadline vollständig im Viewport, wartet deren
Vermerk ebenfalls auf den vorherigen. Verlässt eine noch wartende Headline den vollständigen
Sichtbereich, wird ihr Queue-Eintrag verworfen und erst bei einem späteren vollständigen
Eintritt erneut freigegeben.

Beim Fold liegt die farbige Vorderfläche als eigene Ebene tatsächlich über dem
Button-Untergrund. Ihr unterer Rand bleibt angeschlagen, während die Fläche über
`perspective` und ein positives `rotateX` nach hinten unten kippt; Text und Pfeil liegen unbewegt auf einer
dritten Ebene. Das vermeidet die frühere, durch die negative Stapelreihenfolge praktisch
unsichtbare Klappe, bei der nur ein zweidimensionaler Farbwechsel wahrnehmbar war. Der
Prio-Button öffnet von seiner tangerinefarbenen Vorderfläche auf einen warm-schwarzen
Untergrund. Sämtliche Flächen bleiben entsprechend dem Flat-System ohne Außen- oder
Klappenschatten. Am unteren Anschlag federt die Klappe einmal deutlich und ein zweites Mal
nur minimal zurück, bevor sie waagerecht liegen bleibt. Dadurch liest sich das Ende als
kurzer mechanischer Aufprall statt als gleichmäßiges Ausblenden. Bei reduzierter Bewegung
entfällt auch dieser Bounce vollständig.

Beim Ghost-Button „Mehr im Lebenslauf“ bleibt die Schrift schwarz, solange seine
cremefarbene Vorderfläche sichtbar ist. Erst kurz vor deren unterem Anschlag wechselt sie
auf Creme über dem ausdrücklich warm-schwarzen Untergrund. So entsteht während des Folds
kein cremefarbener Text auf cremefarbener Fläche.

Die Projektkacheln behalten ihren Platz und ihre vorhandene Kontur im Raster. Beim Hover bzw.
Tastaturfokus sinkt ausschließlich der gemeinsame Inhaltswrapper `.tile-depth`
perspektivisch nach innen; Nachbarzellen und Gridkanten werden nicht verschoben. Dafür bewegt
`perspective(45rem) translateZ(-.5rem)` den Inhalt optisch hinter die Rasterebene. Der
ausschließlich innere Schatten sitzt dagegen fest an der tatsächlichen Außenkante des
Rasterfelds. So bleibt die Gridkontur stehen, während Bild und Text gemeinsam zurückweichen,
ohne den flachen Stil durch einen äußeren Schlagschatten zu verlassen. Die Kacheln bleiben unter
den seitenweiten Begrenzungslinien und erhalten im aktiven Zustand einen deckenden Cremegrund.
Ein kurzer Druckpunkt macht die Bewegung taktil: Der Inhalt sinkt zunächst geringfügig über
die Endtiefe hinaus, federt einmal zurück und setzt sich dann; der Innenschatten verdichtet
sich synchron und entspannt sich auf seinen Endwert.
Bei reduzierter Bewegung entfällt die perspektivische Verschiebung vollständig. Auf der Startseite
wechseln Titel und der dort bereits gestaltete Pfeil gemeinsam auf Tangerine; nur der Pfeil
bewegt sich zusätzlich. Die „Weitersehen“-Projektteaser der Unterseiten verwenden nun
denselben Pfeil und dieselbe Reaktion, damit sie tatsächlich dieselbe Kachelkomponente
abbilden. Bis der
Bildeffekt der Nexola-Referenz live verifiziert ist, bleibt das
Bild selbst unbewegt. Pfeile innerhalb gefüllter Buttons erben dagegen stets die jeweilige
Textfarbe des Buttons; nur ihre kurze horizontale Bewegung bleibt erhalten. Einfache Footerlinks verwenden genau eine bereits
tangerinefarbene, von links einfahrende Haarlinie und erzeugen daher keinen Farbblitz.
`prefers-reduced-motion` zeigt Headlines und Handschrift sofort und entfernt alle
Bewegungsübergänge.

Die breite Projektanfrage unter dem Kachelraster ist ausdrücklich kein Button und keine
weitere Projektkachel. Ihre dunkle Rasterzeile bleibt unbewegt. Beim Hover oder
Tastaturfokus wächst die Tangerine-Fläche in einer kurzen Anlaufphase von etwa einer
Viertelsekunde vollständig unter „Projekt anfragen“ samt Pfeil. Anschließend läuft sie
bewusst langsam weiter und erreicht nach insgesamt 6,4 Sekunden die Layoutmitte. Die Fläche
füllt die komplette Balkenhöhe, schließt rechts bündig ab und ist nur links pillförmig
gerundet. Beim Verlassen zieht sie
sich in 640 Millisekunden vollständig zur rechten Kante zurück und verschwindet erst danach.
Die Füllung läuft nicht über die gesamte Zeile.

`projekt.js` ist nur die clientseitige Templating-Abkürzung des eigenständig öffnenden
Design-Prototyps; es ist **nicht** die Zielarchitektur. Das Repository besitzt bereits einen
lokalen Django-/PostgreSQL-/Wagtail-Stack (`just dev`, Django auf Port 8000). Bei der
Überführung muss Wagtail das gemeinsame Projekt-Template serverseitig rendern: Titel,
Bereich, Jahr, Kunde, Leistungen und Lead werden feste Felder; Case-Study-Abschnitte,
Galerie, Ergebnisse und Statement optionale Blöcke. Bis dahin enthalten die neun
Prototyp-URLs eine statische `<noscript>`-Fassung mit Projekttitel, Hauptnavigation und
Rückweg zur Projektübersicht. So bleiben zumindest Navigation und Projektzugang ohne
JavaScript nutzbar; der vollständige Projektinhalt darf vor Veröffentlichung nicht vom
Browser-JavaScript abhängen.

## Accessibility-Stand

Der statische Audit prüft Startseite und alle neun Projekt-URLs auf Landmarken,
Überschriftenhierarchie, doppelte IDs, interne Sprungziele, Bildalternativen,
Tastaturpfade, Fokusdarstellung, Bewegungsreduktion und die verwendeten Farbpaare.

- Ein Skip-Link führt direkt zu `main`. Navigation und About-Akkordeons verwenden native
  HTML-Elemente. Das offene Menü schließt mit Escape, hält den Tastaturfokus im Panel und
  nimmt den verdeckten Seiteninhalt per `inert` aus der Fokusreihenfolge. Ohne JavaScript
  bleibt die native Menübedienung erhalten.
- Alle Hover-Reaktionen besitzen ein `:focus-visible`-Gegenstück. Die mobilen Reel-Anfasser
  sind horizontale, beschriftete Slider mit Pfeiltasten sowie Home/End und einer
  24-px-Trefferfläche.
- Dekorative Canvas-, Handschrift-, Raster- und Service-Icon-Grafiken sind aus dem
  Accessibility-Baum genommen. Medienplatzhalter der Projektseiten besitzen dagegen eine
  Textalternative.
- Der Kunden-Marquee stoppt bei Hover und Tastaturfokus; bei
  `prefers-reduced-motion` läuft er gar nicht und wird als statische Liste gesetzt.
- Warmes Schwarz auf Creme erreicht ca. 15,56:1, warmes Schwarz auf Tangerine ca. 4,55:1.
  Weiß auf Tangerine erreicht ca. 4,04:1, Creme auf Tangerine ca. 3,42:1. Der große, fette
  Prio-Button erfüllt damit die 3:1-Anforderung für große Schrift. Beim deutlich kleineren
  Kontaktbutton im Header ist die ausdrücklich gewünschte weiße Hover-Schrift mit dem
  bestehenden Tangerine noch keine AA-konforme Normaltext-Kombination; dafür braucht es vor
  Veröffentlichung entweder einen dunkleren Hoverton oder wieder warmes Schwarz.

Vor einer Veröffentlichung bleiben zwei inhaltliche Blocker: Sechs als Links gestaltete
Platzhalter tragen noch `href="#"` (Lebenslauf, LinkedIn, Mastodon, Impressum,
Datenschutz und „Mehr im Lebenslauf“), und `mail@example.com` muss durch die echte Adresse
ersetzt werden. Ziele werden nicht erfunden; bis echte Werte vorliegen, sind diese Links
nicht releasefähig. Zusätzlich ist nach der Wagtail-Überführung ein Lauf mit Browser-Audit
und Screenreader erforderlich. Der aktuelle In-App-Browser war während dieses Audits nicht
verfügbar; Syntax-, Django- und statische DOM-Prüfungen ersetzen keinen manuellen Test mit
NVDA/VoiceOver und 200-%-Zoom.


## About-Akkordeon

Drei Kacheln nebeneinander, je eine Rasterspalte breit — **keine Karten, sondern
Rasterzellen** (Vorbild: das Skillset bei Nexola). Begrenzt wird die Reihe nur oben und
unten; die senkrechten Kanten übernimmt das Seitenraster, dessen gestrichelte
Spaltenlinien ohnehin genau dort liegen.

**`<details>` statt eigener Klapp-Logik.** Der Fließtext bleibt im Dokument, ist per
Tastatur erreichbar und wird von der Seitensuche gefunden — bei About wichtiger als
anderswo, weil dort die Selbstbeschreibung steht. Bewusst **ohne `name`**: das Attribut
machte daraus ein exklusives Akkordeon, bei dem sich beim Öffnen der einen die andere
schließt. Beim Laden ist keine offen. Die ganze Kachel schließt, nicht nur die Kopfzeile —
außer man hat im Text etwas markiert, dann wollte man lesen und nicht klappen.

**Die Kacheln stehen auf gleicher Höhe** (Rastervorgabe, kein `align-items: start`).
Daraus folgt der Kerneffekt der Reihe — der Kopf jeder Kachel richtet sich nach ihrem
**eigenen** Zustand:

| Kachel | Kopf | Fließtext |
|---|---|---|
| **zu** | mittig in der vollen Kachelhöhe — wächst die Kachel, weil die Nachbarin geöffnet wurde, wandert er mit nach unten | – |
| **offen** | auf der Grundhöhe (`min-block-size`), macht dem Text Platz | beginnt an ebendieser Kante |

Weil die Grundhöhe für alle drei dieselbe ist, fluchten Köpfe *und* Textanfänge von selbst,
sobald mehrere Kacheln offen sind — ohne dass etwas dafür gerechnet werden müsste.
Ein Zwischenstand, der über `.me-text:has(.me-row[open])` **alle drei zugleich** umschaltete,
ist genau daran gescheitert: Er stellte zwar dieselbe Flucht her, nahm der Reihe aber die
Bewegung, um die es geht — der Kopf soll erst dann hochrücken, wenn unter *ihm* der Text
aufgeht.

**Der Übergang ist animiert — über `flex-grow`.** Der naheliegende Weg, `justify-content`
umzuschalten, ist daran gescheitert: **diese Eigenschaft springt, sie animiert nicht** — die
Köpfe standen richtig, kamen aber ohne Bewegung dorthin. `flex-grow` ist dagegen eine Zahl
und interpoliert. Umgeschaltet wird an zwei Stellen, beide mit derselben Kurve und Dauer wie
die Kachelhöhe, sodass alles als *eine* Bewegung läuft:

1. **am Kopf selbst** (`1 → 0`) — er schrumpft von der vollen Kachelhöhe auf seine
   `min-block-size`. Das setzt die Textkante.
2. **an zwei Flex-Spacern** (`summary::before` / `::after`, ebenfalls `1 → 0`) — sie
   ersetzen `justify-content: center`. Zwei gleiche Spacer oben und unten zentrieren
   genauso, aber ihr Wegfall richtet den Inhalt an der Oberkante aus. Das ist der Punkt für
   die Flucht der Titel: bei *zentriertem* Inhalt hängt die Höhe des `h3` an der Höhe des
   ganzen Kopfes — eine dreizeilige Subline (bei 1024 px die dritte Kachel) schöbe ihren
   Titel 10 px über die der Nachbarn. Der `gap` des Kopfes musste dafür weichen, er hätte
   auch zwischen Spacer und Inhalt gewirkt; der Abstand Titel/Subline sitzt jetzt als
   Margin an der Subline.

Nachgemessen bei 1024 und 1440 px, je alle zu / eine offen / alle offen: geöffnete Kacheln
beginnen ihren Text immer auf **145 px**, bei mehreren offenen fluchten die Titel auf
**0,0 px** — auch bei dreizeiliger Subline. Der Kopf einer geschlossenen Nachbarkachel
wandert stetig mit (bei 1440 px von 32 px auf 187 px über rund 300 ms), er springt nicht.

Der ganze Übergang ist **reines CSS** — er läuft mit abgeschaltetem JavaScript identisch
(gegengemessen).

Die Abschlusslinie sitzt am Container statt an den Kacheln — bei gleicher Höhe dasselbe
Ergebnis, aber unabhängig davon, ob eine Kachel einmal ausschert.

### Wie der Fließtext erscheint

Alle Zeilen starten eine Zeilenhöhe tiefer und rücken **nacheinander** an ihren Platz:
erst die oberste dichter an die Kopfzeile, dann die zweite an die erste. Keine Zeile
entfaltet oder blendet sich ein — reine Bewegung, keine Deckkraft, keine Kante, hinter der
etwas hervorkommt.

**Das Verhältnis von Dauer zu Versatz bestimmt den Charakter** und war die eigentliche
Stellschraube:

| Dauer / Versatz | Verhältnis | Wirkung |
|---|---|---|
| 660 ms / 70 ms | 9,4 | alle zugleich unterwegs — der Absatz ist durchgehend auseinandergezogen |
| 190 ms / 105 ms | 1,8 | genau eine Fuge, aber jede Zeile springt für sich: Staccato |
| **640 ms / 105 ms** | **3,5 sichtbar** | die Fuge wird übergeben, bevor sie zu ist: eine durchlaufende Welle |

Als Kurve eine **echte Feder** statt einer Bézier-Näherung: die Sprungantwort eines
gedämpften Feder-Masse-Systems, über `linear()` als Stützstellen
hinterlegt — anders lässt sich das Ausschwingen in CSS nicht sauber ausdrücken.
**Dämpfungsgrad 0,86**: praktisch kein Überschwingen (0,5 %) und ein gemächlicher Anlauf —
90 % des Wegs erst bei 46 % der Zeit. Straffere Federn wirkten schnappend (0,58 kam auf
10,6 % Überschwingen und 90 % bereits bei 19 %). Deshalb 640 ms Dauer, obwohl die Zeile nur
rund 371 ms *sichtbar* in Bewegung ist; für das Verhältnis oben zählt die sichtbare
Bewegung.

### Zeilen zerlegen — und der Fallstrick dabei

CSS kann einzelne Zeilen eines umbrochenen Absatzes nicht ansprechen. Ein Skript zerlegt
ihn deshalb beim Öffnen in seine **gesetzten** Zeilen und nimmt das nach dem Lauf zurück —
so bleibt der Absatz für Seitensuche und Screenreader ein zusammenhängender Satz. Das
Zurücksetzen löst zugleich den Resize-Fall: Zeilen-Spans tragen festen Inhalt und `nowrap`,
sie brechen bei einer Fensteränderung nicht neu um; als reiner Text tut der Absatz das von
selbst. Zusätzlich setzt ein Resize *während* der Animation sofort zurück.

**Gemessen wird erst im nächsten Frame**, nicht im `toggle`-Ereignis selbst: Dort ist der
Inhalt teilweise noch `content-visibility: hidden` mit Höhe 0, die Zerlegung findet dann
keine Zeilen und die Animation fällt ersatzlos aus. Schlägt es auch dann fehl, wird bis zu
dreimal erneut versucht — ein Frame ist unsichtbar, ein sporadisch ausbleibender Effekt
fühlt sich dagegen kaputt an. **Achtung: sporadische Ausfälle sind gemeldet, aber in 96
protokollierten Öffnungen mit zufälligen Klickfolgen und dichter Abtastung des Versatzes
nicht reproduzierbar.** Die Wiederholversuche decken die bekannte Ursache ab; falls es
erneut auftritt, braucht es die genaue Klickfolge und den Browser.

Zurückgesetzt wird beim `animationend` der **letzten** Zeile, nicht nach einer gerechneten
Wartezeit — sonst müsste die bei jeder Änderung an Dauer oder Versatz nachgezogen werden.
Ein Zeitgeber bleibt als Netz, falls das Ereignis ausbleibt.

**Der Fallstrick**, der zweimal falsche Trennungen erzeugt hat: Das erste Zeichen nach
einem *getrennten* Umbruch meldet **zwei** Rechtecke — eines am Ende der alten Zeile, wo
der erzeugte Trennstrich sitzt, und eines am Anfang der neuen:

```
's': tops=[3695, 3695]   ← Zeilenende
'm': tops=[3695, 3720]   ← erstes Zeichen der neuen Zeile
```

`getBoundingClientRect()` bildet daraus die **Vereinigung** und meldet die obere Kante. Das
Zeichen sieht damit aus, als gehörte es noch zur alten Zeile, und die Umbruchstelle landet
eins zu spät: aus „aus-macht" wird „ausm-acht". Die Lösung ist, nicht die Vereinigung zu
nehmen, sondern das **unterste** der Rechtecke. Über sechs Breiten gegengemessen: alle
nicht getrennten Zeilen stimmen auf 3 px, getrennte liegen um genau eine Trennstrichbreite
(5–9 px) daneben — der Strich gehört nicht zum Textknoten und fehlt deshalb im gemessenen
Rechteck. Vorher lag der Fehler bei 18 px, also einer ganzen Silbe.

Der Trennstrich muss beim Zerlegen **von Hand zurück**, weil er beim Setzen erzeugt wird
und nicht im Text steht. Die Leerzeichen an den Zeilenenden bleiben stehen: ohne sie
klebten beim Auslesen die Wörter aneinander („schon denganzen Weg").

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
  aber auf 64 bis 128 px. Je kleiner die Headline, desto knapper fällt der Abstand aus —
  gemessen von Tinte zu Tinte, vor dem Ausgleich:

  | Section | Headline | ohne `--dia` | `--dia` | jetzt |
  |---|---|---|---|---|
  | Projekte, Leistungen | 128 px | 28,8 px | — | 28,8 px |
  | Kontakt | 96 px | 25,3 px | — | 25,3 px |
  | Kunden, About | 64 px | 19,9 px | `0.139em` | 28,8 px |

  **Offen:** Kontakt liegt mit 25,3 px noch 3,5 px unter den übrigen.
  About teilt die Zeile jetzt mit Kunden — beide stehen auf 64 px in Versalien und brauchen
  denselben Ausgleich. Die früheren 0.225em galten der 51-px-Fassung im gemischten Satz.

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

  Die beiden Außenlinien begrenzen die Seite und liegen deshalb über dem Inhalt — auch über
  einem Slider, der bis an den Rand scrollt. Die Projektkacheln bleiben ebenfalls unter
  diesen Linien: Ihr aktiver Zustand hebt sie nicht mehr aus dem Raster, sondern versenkt
  sie perspektivisch darin. Damit die Linien in *einer* Struktur bleiben können,
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
  bei 1440 px Viewport, linke Porträt-Kante exakt auf 1051,20 px = 75-%-Linie). Textblöcke rücken
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
Die kurzen Sublines in den Leistungskacheln sind eine eigene Ausnahme: Sie verwenden
`text-wrap: pretty` als Fallback, bevorzugt `text-wrap: balance`, und `hyphens: none`.
Damit werden zwei vorhandene Zeilen möglichst gleichmäßig verteilt statt automatisch
getrennt; auf schmalen Screens darf der Text ohne Quetschen auf weitere Zeilen umbrechen.
Vor Gedankenstrichen steht dort ein geschütztes Leerzeichen (`&nbsp;`): Das Balancing darf
weiterhin frei umbrechen, kann den Gedankenstrich aber nie allein an den Anfang der
nächsten Zeile stellen. Hinter dem Gedankenstrich bleibt der normale Umbruch erlaubt.

## Technische Notizen (wichtig für die Weiterarbeit)

- **Die Subline beginnt an der 75-%-Linie, weicht aber nach oben aus.** Reicht der Platz
  darunter nicht — kurzer Viewport oder längerer Text —, setzt das Skript `--sub-top` so weit
  nach oben, dass die Zelle nicht unten aus der Stage geschnitten wird (die clippt).
  Geprüft bei 1440×900, 1440×700, 1280×800, 2560×1440 und 820×1180.
- **Hero-Höhe = genau EIN Bildschirm, Navigation eingerechnet:**
  `min-height: clamp(var(--hero-floor), calc(100svh - var(--header-h)), 1600px)`.
  Ein `clamp` erledigt beide Grenzen ohne Media Query.
  **Der Header-Abzug ist der Punkt:** `header.site` ist `sticky` und steht damit IM FLUSS —
  seine Höhe kam zur vollen `100svh` der Stage hinzu. Die erste Bildschirmseite war dadurch
  auf *jeder* Größe um exakt die Header-Höhe zu hoch (gemessen: 62,3 px bei 1366/1440/1512/
  1680/1920/2560 px Breite), und die Subline wurde unten um denselben Betrag angeschnitten.
  `--header-h` setzt ein **ResizeObserver** am Header — keine Media Query, und es folgt auch
  dem Umbruch der Wortmarke auf schmalen Breiten.
  `--hero-floor` (33 rem) greift erst unterhalb von ~590 px Viewporthöhe; darüber ist der Hero
  immer exakt ein Bildschirm.
  Die Obergrenze von 1600 px ist kein Designwert, sondern Schutz: in der Artifact-/iframe-
  Vorschau wird der Frame auf die volle Seitenhöhe gestreckt, `100svh` ist dann die gesamte
  Seitenhöhe. Ohne Deckel wüchse der Hero auf mehrere tausend Pixel, die WebGL-Textur spränge
  das Limit und der Canvas (inkl. MOIN) verschwände. 1600 px lässt einen 27-Zöller
  (1440 px Viewport + Header = 1378 px) noch voll durch.
- **Leistungen und About sind ebenfalls mindestens ein sichtbarer Bildschirm**, dieselbe
  Rechnung wie der Hero (`100svh` minus `--header-h`). Die Mehrhöhe wird verschieden
  verteilt: Bei den Leistungen füllt sie das Raster (`grid-auto-rows: 1fr`), damit die
  Haarlinien bis ans Ende reichen; bei About gibt es kein Raster zu füllen, dort steht der
  Block mittig. In den Leistungskacheln sitzt der Inhalt **optisch** mittig statt
  geometrisch — angehoben um die halbe Höhe von Icon plus Zeilenfuge, weil das Icon oben
  leicht und der Textblock darunter schwer ist.
- **Scroll-Hinweis (`.scrollcue`).** Weil der Hero jetzt exakt auf dem Viewport endet, fehlt
  das „hier geht es weiter", das die frühere Überlänge unfreiwillig geliefert hat. Eine
  Haarlinie mit wanderndem Segment — dieselbe Liniensprache wie das Seitenraster, nur in
  Bewegung. Ohne Text: der Custom Cursor über dem Hero trägt schon welchen. Sie sitzt am
  rechten Textanschlag (Padding-Linie + `--hero-inset`), also gegenüber der Subline, und
  blendet aus, sobald gescrollt wurde — ein Hinweis, der nach dem Befolgen stehen bleibt,
  ist nur noch Dekoration. `prefers-reduced-motion` friert das Segment oben ein.
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
