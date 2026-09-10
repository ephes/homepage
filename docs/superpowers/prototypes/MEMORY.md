# Arbeitsstand Portfolio-Prototyp

Stand: 9. September 2026

## Wiedereinstieg

- Arbeitsbranch: `portfolio-site`
- Letzter vollständiger Implementierungsstand: Commit `911c1d1`
- Haupteinstieg: `portfolio-startseite.html` direkt in Helium öffnen.
- Gemeinsame Gestaltung und Interaktionen: `motion.css`, `motion.js` und `site-shell.js`.
- Projektunterseiten: `projekte/`; gemeinsamer Aufbau in `projekt.css` und `projekt.js`.
- Rechtsseiten: `impressum.html`, `datenschutz.html` und `legal.css`.
- Ausführliche Design- und Verhaltensdokumentation: `README.md` in diesem Ordner.

## Zuletzt bearbeitet

- Der mobile Startseiten-LIDI nutzt im Telefon-Hochformat die volle verfügbare Stage-Breite
  und endet am dynamischen Visual Viewport; nur sein reguläres inneres `--hero-inset` und
  eine vorhandene Bottom Safe Area bleiben. Die 1,8-rem-Statusleiste wird nach ihrem
  Stage-Höhenabzug nicht doppelt als Bottom-Margin addiert; `dvh` folgt mobilen Browserleisten.
  Der feste Top-Anker bleibt als unabhängiges Overlay in der Seitenkante.
- Das mobile Menü spannt seine opake Fläche von der Headerunterkante bis `bottom: 0`.
  Root-Overscroll ist im offenen Zustand gesperrt; der Touch-Guard verhindert iOS-
  Rubberbanding nur an den beiden Panelgrenzen und erhält internes Scrollen und Zoom.
- Die mobile Leinentextur blendet an der oberen Viewport-/Safe-Area-Kante aus und erreicht
  erst unterhalb des Headers wieder ihre volle Deckkraft. Der bestehende cremefarbene
  Headergrund, seine feste Position, Menüschleier und Shader bleiben unverändert; oberhalb
  von 52 rem ist keine Maske aktiv.
- Die mobile Footer-Abschlusszeile ist ein echtes Zweispaltenraster ohne separate
  Top-Anker-Spalte. Copyright und „Designed in Düsseldorf“ verwenden wieder die
  reguläre fluide Eyebrow-Größe; der Ortsvermerk beginnt mit demselben inneren Abstand wie
  die Projektspalte direkt darüber. Nur sein rechtes Zellpadding reserviert die sichtbare
  transparente 44-px-Trefferfläche mit L-Kontur, sodass Text niemals darunterläuft;
  auf schmalen Viewports darf er dafür
  umbrechen. Auch das längere Copyright darf innerhalb der linken Spalte umbrechen.
  Unteres Padding und Pfeilposition berücksichtigen weiterhin die
  Safe Area, während Desktop unverändert bleibt.
- Der Top-Anker wird bei geöffnetem Hauptmenü auf allen Viewportgrößen über dessen nativen
  `.site-nav[open]`-Zustand vollständig verborgen und aus dem Pointer-Hit-Testing genommen.
  Das greift gemeinsam auf Start-, Rechts- und Projektseiten sowie ohne JavaScript. Nach dem
  Schließen kehren der kleine Pfeil und seine auf den zugänglichen Mindestwert begrenzte
  44×44-px-Trefferfläche zurück. Eine kontrastadaptive obere/linke L-Kontur macht die
  belegte Trefferfläche erkennbar; ihr transparenter Grund verdeckt dabei keinen Text.
  Vorhandene Safe-Area-Inserts versetzen Ziel und Pfeil gemeinsam, damit das sichtbare
  Zeichen immer vollständig innerhalb seiner Trefferfläche bleibt.
- Die About-Reveal-Logik setzt ihre layoutwirksame mobile Höhenreserve nicht mehr zurück,
  nachdem eine Kachel beim Hinunterscrollen schon hinter dem festen Header verschwunden
  ist. Der frühere Top-Exit vergrößerte drei Zeilen nachträglich um zusammen 96 px und ließ
  Chromium `scrollY` per Scroll Anchoring von 3400 auf 3496 px nachführen. Der Reset findet
  nun ausschließlich beim Bottom-Exit unterhalb des Viewports statt; sichtbare Reveal- und
  native Akkordeonanimation sowie die ResizeObserver-basierten Rasterfarbkanten bleiben
  erhalten.
- Die Kunden-Section ist nur im Telefon-Hochformat bis 35 rem mindestens `66svh` hoch und
  zentriert ihren Inhalt. Dort laufen zwei direkt gestapelte, identische Marquees in 96 s
  gegenläufig; die zweite Sichtkopie ist dekorativ und komplett `aria-hidden`. Bei
  `prefers-reduced-motion` verschwindet sie und die erste Liste steht statisch. Landscape,
  Tablet und Desktop verwenden weiterhin exakt ein Band mit 42 s und die alte Mindesthöhe.
- Der Fluid-Hero sperrt die Touch-Gestenrichtung nach 6 px einmalig: Nur eine klar
  horizontale Bewegung (mindestens Faktor 1,2 gegenüber der Vertikalen) steuert den Reveal.
  Vertikale und uneindeutig diagonale Gesten bleiben natives Scrollen, Mehrfinger-Gesten
  werden ignoriert. Pointer Events und der alte Touch-Event-Fallback laufen exklusiv statt
  doppelt. Auf touchfähigen Browsern ist Touch Events der einzige Touch-Pfad; sein
  nicht-passives `touchmove` stoppt erst nach horizontaler Klassifikation die Standardaktion.
  Damit kann iOS Safari die Interaktion nicht vorher per Pointer-Cancel an Scrollen abgeben.
  Touch Events nutzt `touch-action: auto`, damit auch uneindeutig diagonale Gesten nativ
  scrollen und Pinch-Zoom erhalten bleibt. Nur der Pointer-Touch-Fallback nutzt die
  alte-WebKit-kompatible Basis `pan-y`; `pinch-zoom` folgt dort per `@supports`. Maus und
  Stift reagieren weiterhin direkt.
- Die automatische Fluid-Einladung läuft nur auf Touchgeräten: nach 700 ms Ruhe mit 30 Hz
  und 28 % Gestenkraft auf einer langsam organisch variierenden Bahn im mittleren Hero.
  Echte Berührung übernimmt ohne Sprung; nach ihrem Ende wartet die Automation 3,2 s.
  Außerhalb des sichtbaren Heros, bei verborgenem Tab, offenem Menü, Reduced Motion und
  fehlendem WebGL bleibt sie aus. Desktop ohne Touch erhält keine automatische Bewegung.
- Die Social-Links wurden als runde Outline-Buttons in das Menü integriert.
- Alle Iconformen liegen direkt als Inline-SVG im Seiten-Markup; es gibt keine externe
  Icon-CDN und keine ausgelagerten SVG-`use`-Referenzen.
- LinkedIn verwendet eine rahmenlose, hohle `in`-Kontur ohne zusätzlichen quadratischen
  Rahmen. Mastodon verwendet die luftigere Light-Variante von Phosphor Icons.
- Das geöffnete Menü ist am Viewport verankert und endet bei allen geprüften Breiten exakt
  an der rechten Bildschirmkante.
- Die Trennlinie über den Social-Icons reicht über die gesamte nutzbare Innenbreite des
  Menüpanels: von der inneren Kante des Tangerine-Balkens ohne rechten Leerraum bis an den
  Viewportrand. Ihre separate 2-rem-Überzeichnung reicht auch unter den reservierten Bereich
  klassischer Scrollbars und wird erst an der Panelkante horizontal gekappt.
- Ihre Ausgangshöhe folgt pixelgenau der 75-%-Linie des Hero-Rasters. Der Linkblock ist im
  oberen Bereich vertikal zentriert; `motion.js` misst die echte geschlossene Höhe der je
  nach Seitentyp vorhandenen Top-Level-Zeilen und verteilt den freien Raum über zwei gleich
  große Spacer. Ein geöffneter Projektindex wächst nach unten und schiebt Linie und
  Social-Zone mit, statt die Navigation nach oben zu versetzen. Auch ein Resize bei offenem
  Index vermisst nur dessen Summary und erhält damit die geschlossene Spacerbasis.
- Der Projektindex verändert die horizontale Menügeometrie nicht mehr. Zuvor verbreiterte
  sein sichtbarer Inhalt den mittleren `auto`-Track; beim Schließen blieb diese Breite nur
  während der `details-content`-Transition erhalten und fiel mit dem diskreten Wechsel zu
  `content-visibility: hidden` zurück. Dadurch sprangen Linkblock und Social-Icons gemeinsam
  nach rechts. `motion.js` misst nun intrinsische Breite und geschlossene Höhe der
  Hauptnavigation gemeinsam an einer synchron angehängten, unsichtbaren Kopie. Dadurch
  existiert die Höhenmessung schon vor dem allerersten Öffnen, obwohl das echte native
  Disclosure bis dahin keine Layoutbox besitzt. Die Breite bleibt über
  `--menu-primary-measured-inline-size` im gesamten Zyklus fest und ist zugleich auf die
  tatsächliche responsive Panelbreite begrenzt. Ohne
  JavaScript bleibt die intrinsische `max-content`-Fallbackbreite aktiv; der Projektindex bricht
  darin um und wächst nur vertikal. Resize und fertig geladene Fonts erneuern die Messung;
  der sichtbare Disclosure-, Fokus- und Scrollzustand bleibt dabei unangetastet. Die
  Messkopie trägt eine eigene `is-measuring`-Kennzeichnung und löst deshalb weder Scrim und
  Scroll-Lock noch das Ausblenden des Top-Ankers aus.
- Die vergrößerten Social-Buttons stehen mit identischen Zwischenräumen innerhalb der
  linken Stern- und rechten Textkante; ihre Außenkanten bilden die Grenzen der zentrierten
  Reihe. Auch auf kleinen Telefonen bleiben Trefferfläche und Kreis mindestens 44 × 44 px;
  die Iconzeichnung selbst bleibt mindestens 28 × 28 px. Die 1,5-px-Außenkontur wird nativ
  auf einer auf ganze Layoutpixel gerundeten
  Kreisbox gezeichnet und wirkt dadurch ruhiger als der frühere halb-pixelige Inset-Ring.
  Ein `@supports`-Test auf einer echten Größenproperty schützt `round()`; ältere Browser
  behalten die fluide `clamp()`-Größe. Der Briefumschlag nutzt `.mail-link` statt seines
  übersetzbaren `aria-label` als Stil-Hook.
  Unterhalb von 320 px hält eine gemeinsame Mindestbreite zusätzlich vier Ziele und drei
  2-px-Zwischenräume zusammen; die Reihe bleibt dabei auf der Hauptnavigation zentriert.
  Hover und Tastaturfokus bewegen ausschließlich die getrennte Kreisfassung mit kurzem
  Nachfedern und schmaler innerer Licht-/Schattenkante. Icon, Trefferfläche, Größe und
  transparenter Grund bleiben still; eine Flächenabdunklung oder ein kompletter
  Button-Schlagschatten wird ausdrücklich nicht verwendet.
  LinkedIn wurde innen etwas leichter und Mastodon mit einer feinen Zusatzkontur etwas
  kräftiger gesetzt, damit die vier Zeichen optisch gleich schwer wirken. Am Briefumschlag
  ist ausschließlich das äußere Rechteck minimal leichter; die Klappenspitze bleibt bestehen.
- Der Header und das darin liegende Panel sind nun explizit viewportfest und bleiben bei den
  Desktop-Hover-Sprüngen sowie nach vorherigem Scrollen sichtbar. Der Hauptinhalt gleicht die
  aus dem Fluss genommene Headerhöhe aus; mobil übernimmt das die Verfügbarkeitszeile. Ursache
  des früheren Wegscrollens war
  `overflow-x: hidden` am Body: Chromium machte ihn dadurch auch vertikal zum
  Scroll-Container und löste den damaligen Sticky-Header vom Viewport. `overflow-x: clip`
  begrenzt den Überlauf, ohne diese Nebenwirkung. Main und mobiles Statusband besitzen einen
  gemeinsamen `4.6rem`-Fallback für die erst per JavaScript präzisierte Headerhöhe; ohne
  direktes Statusband bleibt der Main-Abstand auf Telefonen bestehen.
- Der Footer nutzt auf Desktop wieder vier eigenständige Geschwister in identischer DOM-,
  Fokus- und Rasterreihenfolge: Profil, Seite, sämtliche Projekte in einer einzigen Spalte
  und Rechtliches am rechten Schluss. Nur unter 52 rem werden Seite und Rechtliches visuell
  links untereinander angeordnet; die rechte Projektspalte behält dabei ihr Außenpadding.
- Die Hell-/Dunkelverläufe der äußeren und inneren Seitenlinien rechnen ihre Sectionkanten
  nun relativ zur tatsächlichen `.pagegrid`-Oberkante. Auf schmalen Ansichten beginnt das
  absolut positionierte Gerüst wegen des kollabierenden Abstands der mobilen
  Verfügbarkeitszeile erst 74,59 px unter Dokument-y=0; Dokumentkoordinaten hatten deshalb
  jeden Farbwechsel genau um die Headerhöhe nach unten versetzt. Auch `--gap-start`,
  `--gap-end` und der nicht bei null beginnende Verlauf von `.vsplit2` verwenden denselben
  lokalen Ursprung.
- Projektgalerien schließen mobil jede Zeile: Nur zwei unmittelbar benachbarte gewöhnliche
  Hochformate teilen sie hälftig. Einzelne und ungerade letzte Hochformate sowie jedes in
  Wagtail mit „Großes Motiv“ markierte Bild (`large`, Prototyp-Alias `wide`) sind vollbreit.
- Die Ergebnis-Karten unter „Was bleibt“ bilden mobil grundsätzlich ein kompaktes 2×n-Raster.
  Nur tatsächlicher horizontaler Inhaltsüberlauf schaltet das ganze Raster einspaltig; ein
  ungerades letztes Ergebnis wird ohne leere Halbzelle vollbreit. Auf schmalen Ansichten
  wechseln „Was bleibt.“ und „Weitersehen.“ von XL auf dieselbe L-Stufe wie die
  Kontaktheadline; Desktop bleibt unverändert.
- Die beiden „Weitere Projekte“-Teaser bleiben auch mobil grundsätzlich nebeneinander;
  echte Bilder dürfen ihre `21:9`-Box per `object-fit: cover` füllen. Statt eines globalen
  Breakpoints misst `projekt.js` das konkrete Kartenpaar nach dem Rendern, nach geladenen
  Fonts und bei Viewportänderungen in seiner zweispaltigen Form. Nur ein tatsächlich
  überlaufendes Titel-/Pfeil-Paar erhält die einspaltige Stapelklasse. Die Messung lauscht
  absichtlich nicht auf die eigene Rastergröße und kann deshalb nicht oszillieren. Der Pfeil
  sitzt visuell mittig auf der ersten Titelzeile, auch wenn der Titel mehrzeilig umbricht.

Wichtige technische Erkenntnis: Externe SVG-Symbole über
`<use href="datei.svg#symbol">` wurden beim direkten Öffnen der HTML-Dateien in Helium
nicht zuverlässig dargestellt. Für diesen Prototyp deshalb die Icons inline belassen.

## Ausdrücklich noch offen

Das Menü ist **noch nicht fertig**. Beim nächsten Termin zuerst dort weiterarbeiten:

- endgültige Auswahl und optische Gewichtung der Social-Icons prüfen;
- endgültige Gewichtung der neu ausgerichteten Iconreihe im Gesamtbild gemeinsam abnehmen.

Die technische Menü-Geometrie, geringe Viewporthöhen, Tastaturbedienung und
`prefers-reduced-motion` sind erneut geprüft. Für die endgültige Gestaltung bleibt damit
nur die subjektive Abnahme der vier Social-Icons; ein realer iOS-Touch-Test gehört weiterhin
zur Abnahme vor Veröffentlichung.

Der durchgehende technische Mobile-Regressionstest ab 320 px ist abgeschlossen. Als
nächster Schritt folgt die gemeinsame gestalterische Abnahme: Social-Icons sowie
Typohierarchie und Handschriftgrößen im Mobile-Gesamtbild. Kachel-, Slider-, About-,
Footer- und Top-Anker-Geometrie sind technisch belastbar; weitere Änderungen daran sollten
von einem konkreten visuellen Änderungswunsch ausgehen.

## Letzte Prüfungen

- Finaler Chromium-Menüaudit auf Startseite, Impressum, Datenschutz und generierter
  Projektseite in zwölf Viewports von 320×480 bis 2048×1152: 48 Kombinationen ohne
  horizontalen Dokumentüberlauf, Panelversatz, verlorene Headerfixierung oder
  JavaScript-Fehler. Die mobile Panelkante endet bis auf 0,02 px am Viewport, die vier
  Social-Flächen bleiben quadratisch und innerhalb des Panels, der Top-Anker ist bei
  offenem Menü unsichtbar und nicht anklickbar. Das Öffnen des Projektindex erzeugt 0 px
  horizontalen Drift; bei geringer Höhe scrollt ausschließlich das Panel. Escape schließt
  auf allen Seiten und gibt den Fokus an den Menüschalter zurück. Fünf repräsentative
  geschlossene und geöffnete Zustände von 320 bis 2048 px wurden zusätzlich visuell geprüft.
  Dabei fiel ein zu enger Reduced-Motion-Selektor auf: Der Einflug des Projekt-Menüpunkts
  behielt 0,4/0,65 s Transition und 0,52 s Verzögerung. Der korrigierte Selektor deaktiviert
  ihn nun gemeinsam mit Disclosure-Inhalt, Projektlinks und Social-Reaktion vollständig.
- Durchgehender Chromium-Mobile-Audit auf Startseite, beiden Rechtsseiten und allen neun
  Projektseiten bei 320, 360, 390, 414, 430, 476, 576, 736 und 832 px: 108 Kombinationen
  ohne horizontalen Dokumentüberlauf, überlappende Hauptsections, kollidierende
  Footerspalten oder JavaScript-Fehler. Die einzigen bewusst überstehenden Elemente sind
  die gekappten Kunden-Marquees, die 1-px-Screenreader-Überschrift und der dokumentierte
  optische Randausgleich der Markenheadline. Ganzseitenansichten der Start-, Datenschutz-
  und Projektseite bei 320/390/430 px wurden zusätzlich visuell geprüft; Text, Kacheln,
  Slider, About, Ergebnisraster, Folgeprojekte, Footer und Top-Anker bleiben vollständig
  lesbar und ohne Überschneidung.
- Startseiten-LIDI in Chromium und WebKit bei 320/390/430 px sowie dynamischen Höhen von
  667 bis 932 px: Stage-Unterkante innerhalb 0,02 px am Visual Viewport, LIDI-Hintergrund
  endet dort ebenfalls (Text bleibt nur um das reguläre `--hero-inset` gepolstert). Die
  Lead-Breite läuft wieder über die volle Stage-Innenbreite; die 44-px-Top-Ankerfläche
  verkürzt sie nicht. Bei 320×568 wächst die intrinsische Stage weiterhin sicher; Text,
  MOIN und Top-Anker kollidieren nicht.
- Offenes Menü auf Startseite, Impressum, Datenschutz und Projektseite in Chromium und
  WebKit geprüft: opake Panel-Unterkante maximal 0,02 px neben dem Visual Viewport,
  Body-Scrollposition stabil. Touch am oberen/unteren Scrollende und außerhalb wird
  verhindert, in der Panelmitte bleibt er nativ. Geschlossenes vertikales Hero-Wischen
  bleibt frei, die horizontale Reveal-Geste greift weiterhin.
- Header/Textur und Footerabschluss auf Start-, Rechts- und generierter Projektseite in
  Chromium und WebKit bei 320, 390, 430 und 1280 px geprüft: Mobile berechnet einen gültigen
  Texturverlauf von transparenter Oberkante bis zur vollen Deckkraft bei rund 94,6 px,
  Desktop weiterhin `mask-image: none`. Dasselbe gilt auf der Startseite ohne JavaScript.
  Geschlossenes und geöffnetes Menü behalten Headerfarbe, Panelanschluss und Overlay.
  „Designed in Düsseldorf“ beginnt in allen mobilen Fällen pixelgenau auf der Textachse der
  Projektspalte; bei 320 px bleiben zwischen Ortsvermerk und sichtbarem Seitenpfeil rund
  19 px, bei 390/430 px mehr. Copyright und Ortsvermerk kollidieren nicht, alle getesteten
  Seiten bleiben ohne horizontalen Dokumentüberlauf. Die mobile Schrift wächst gegenüber
  dem früheren Sonderwert von 7,20/8,58/9,46 px auf 11,42/11,51/11,56 px.
- Menü/Top-Anker auf Startseite, Impressum, Datenschutz und Projektseite bei 320×667,
  390×844 und 768×1024 geprüft: offen jeweils `visibility: hidden`,
  `pointer-events: none`, kein Anchor-Hit oder Klick in der unteren rechten Ecke; nach dem
  Schließen jeweils wieder sichtbar und interaktiv mit 44×44-px-Box exakt
  am Viewportrand. Startseite und beide Rechtsseiten bestanden denselben nativen
  Open/Close-Test ohne JavaScript.
- About-Top-Exit bei 390 × 844 nach vollständigem Eintritt nachgemessen: über 1,25 s bleiben
  `scrollY` (3400 px), Dokumenthöhe (4992 px), Kundenkante im Viewport (84,08 px) und alle
  drei Kachelhöhen konstant. Im alten Stand wuchsen Dokument und `scrollY` im selben Test
  von 4761/3400 auf 4857/3496 px. Öffnen/Schließen sichtbarer Kacheln, Bottom-Exit/erneuter
  Eintritt und aktualisierte Hell-/Dunkelstopps des Linienrasters bleiben funktionsfähig.
- Kundenbereich bei 320/390/430 px und kurzen wie hohen Portrait-Viewports geprüft:
  382,20/440,22/615,11 px reale Höhe, zwei Bänder mit 96 s und entgegengesetzter Richtung,
  kein horizontaler Dokumentüberlauf. Bei 568 × 320, 844 × 390, 576 × 900, 768 × 1024 und
  1280 × 800 bleiben Einzelband, 42 s und bisheriges Layout erhalten. Reduzierte Bewegung:
  eine statische zugängliche Liste, keine zweite Sichtkopie und keine Track-Animation.
- Fluid-Hero-Gesten bei 320 und 390 px in Chromium und WebKit mit Touch Events geprüft:
  7/5 px sperrt horizontal, 7/6 px scrollorientiert; beide Zuordnungen bleiben auch bei
  späterem Richtungswechsel stabil. Ein realer Chromium-Touch-Swipe scrollte vertikal
  135 px und diagonal 23 px bei null Shader-Splats; reales leicht diagonales Hin-und-her-
  Wischen erzeugte vier Shader-Uniform-Schreibvorgänge bei `scrollY = 0`. Mehrfingerkontakt
  auch außerhalb des Heros, `touchcancel`/`pointercancel`, der Pointer-Touch-Fallback, Maus
  und Stift bei 1280 px, `prefers-reduced-motion` sowie der No-WebGL-Fallback bestanden.
- Mobile Idle-Einladung in Chromium und WebKit bei 320/390 px geprüft: Start erst nach
  700 ms, rund 30 Splats/s, gemessene Spitzenkraft unter 4 statt voller Gestenkraft und alle
  Messpunkte innerhalb der dokumentierten UV-Bahn. Touch übernimmt sofort; vor Ablauf von
  3,2 s nach Touchende entstehen null Idle-Splats, danach setzt die Bahn ohne Positionssprung
  wieder ein. Offener Menüzustand, simulierter versteckter Tab und ein vollständig aus dem
  Viewport gescrollter Hero pausieren; Rückkehr und Drehung 390×700 ↔ 700×390 laufen ohne
  Fehler. Reale Chromium-Gesten bei 320/390 px: horizontal vier Shader-Schreibvorgänge bei
  `scrollY = 0`, vertikal 135 px Scrollweg bei null Schreibvorgängen. Desktop erzeugt nach
  1,2 s null Idle-Splats, Mausbewegung bleibt wirksam; Reduced Motion und No-WebGL bleiben aus.
- JavaScript-Syntaxprüfung für `motion.js`, `site-shell.js` und `projekte/projekt.js`: bestanden.
- Browser-Smoke-Test für Startseite, Impressum, Datenschutz und eine Projektseite bei
  320, 390, 768 und 1280 px: 16 Kombinationen bestanden; nach der Header-Fixierung erneut
  auf Headerposition, Inhaltsausgleich und Panelanschluss geprüft.
- Dabei geprüft: vier sichtbare Inline-SVGs, eine exakt an der Viewportkante endende
  Menüfläche, eine randlose Social-Trennlinie ohne horizontalen Überlauf sowie die nach
  unten mitwandernde Social-Zone beim Öffnen des Projektindex.
- Auf der Startseite zusätzlich geprüft: Trennlinie und 75-%-Hero-Linie liegen bei allen
  Breiten mit sichtbarer Rasterlinie innerhalb von 0,25 px übereinander. Die äußeren
  Kreiskanten fluchten innerhalb von 0,1 px mit der linken Stern- und rechten Textkante.
- Die vertikale Zentrierung des Linkblocks wurde bei 320, 390, 768, 1280 und 2048 px
  geprüft: oberer und unterer Freiraum sind bis auf höchstens 0,35 px gleich. Die drei
  sichtbaren Zwischenräume der Icons weichen durch Subpixelrundung um höchstens 0,02 px
  voneinander ab; die Kreisboxen landen auf ganzen Layoutpixeln. Alle vier Außenkonturen
  verwenden dieselbe native 1,5-px-Kontur; LinkedIn und Mastodon sind innen individuell
  gewichtet. Beim taktilen Hoverzustand bleiben Trefferfläche, Icongeometrie, transparenter
  Grund und der Button selbst unverändert; ausschließlich die separate Außenkontur bewegt
  sich um 1 px und erhält zwei schmale innere Licht-/Schattenkanten.
- Nach dem variablen Zeilenfix wurde die geschlossene Dividerposition erneut auf Start-,
  Impressum-, Datenschutz- und Projektseite bei 320, 390, 736 und 1280 px sowie DPR 1 und 2
  geprüft: 32 Kombinationen liegen höchstens 0,03 px neben der 75-%-Position. Synthetische
  Projektmenüs mit vier und fünf Top-Level-Zeilen treffen dieselbe Position. Beim echten
  Plus-Klick wächst die Dividerposition bei 390 und 1280 px exakt mit der Akkordeonhöhe;
  die geschlossene Messbasis bleibt auch nach Resize bestehen.
- Den Projektindex auf Startseite, beiden Rechtsseiten und einer generierten Projektseite
  bei 320, 390 und 1280 px in Chromium und WebKit jeweils zweimal vollständig geöffnet und
  geschlossen. `requestAnimationFrame`-Messungen liefen durch beide Übergänge bis 1,05 s
  nach dem Schließklick und schlossen damit auch den diskreten
  `details-content`-Endzustand ein. Panel-/Clientbreite, Scrollbar-Gutter,
  Dokumentviewport, mittlerer Grid-Track, `.menu-primary`, `.project-menu`, alle
  Top-Level-Zeilen, Social-Zone, Divider, `scrollTop` und alle vier Iconmittelpunkte hatten
  währenddessen einschließlich des tatsächlichen letzten Frames maximal **0 px**
  horizontalen Drift. Die Akkordeonhöhe wächst weiterhin vertikal; beispielsweise wandert
  der Divider bei 390 px von 651,63 auf 971,09 px und exakt auf 651,63 px zurück.
- Einen 20-px-Classic-Scrollbar-Gutter erzwungen: Die Social-Trennlinie überzeichnet den
  Scrollport bis über die reale Panelkante, das Panel bleibt vertikal scrollbar und erzeugt
  keinen Dokumentüberlauf. Die vier Markupquellen besitzen `.mail-link`; dessen
  Briefumschlag-Rechteck erhält weiterhin 1,35 px.
- Ohne JavaScript beginnen Start-, Rechts- und Projektinhalt bei 320 und 1280 px unter dem
  festen Header. Insbesondere behält die in `<noscript>` liegende Projektseite ohne mobiles
  Statusband ihren `4.6rem`-Fallback.
- Desktop-Hover-Sprünge über Start- und Projektseite geprüft: Header bleibt bei `top: 0`,
  Panel direkt darunter und geöffnet; ein anschließender Linkklick schließt das Menü.
- Mobile bei 320 und 390 px nach vorherigem Seitenscroll geprüft: Header und Panel bleiben
  am Viewport, externer Scroll bleibt gesperrt und der geöffnete Projektindex lässt sich im
  Panel selbst bis zum Ende scrollen.
- Footer auf Startseite, Impressum, Datenschutz und einer generierten Projektseite bei 319,
  320, 768 und 1280 px geprüft: DOM- und Desktop-Reihenfolge Profil → Seite → Projekte →
  Rechtliches, neun Projektlinks in genau einer vertikalen Liste, mobile Anordnung von Seite
  und Rechtlichem links untereinander sowie identisches linkes und rechtes Außenpadding ohne
  Horizontalüberlauf.
- Rasterfarben auf Startseite, Impressum, Datenschutz und Projektseite bei 320, 390, 476,
  576, 736 und 832 px sowie DPR 1, 1,5 und 2 geprüft: 72 Kombinationen ohne Überlauf; alle
  harten Verlaufsstopps stimmen bis auf höchstens 0,02 px mit den realen Sectionkanten
  überein.
- `.vsplit2` zusätzlich bei künstlich um 73 px verschobenem `.pagegrid` geprüft: Split-Top,
  lokaler Dark-Section-Abstand und nicht-nulliger Verlaufsstopp stimmen bis auf 0,001 px.
- Alle neun Projektseiten bei 320, 360, 390, 414, 476, 576, 736, 832 und 833 px geprüft:
  Jedes konkrete Teaserpaar ist genau dann zweispaltig, wenn beide Titel-/Pfeilzeilen
  hineinpassen, andernfalls einspaltig; nirgends Titel-/Pfeilkollision oder horizontaler
  Überlauf. Bei 390 px bleibt die Studio-Seite mit „Buchgestaltung“ und „Plakatserie“
  zweispaltig, während Seitenpaare mit „Geschäftsausstattung“ korrekt stapeln.
  Die gezeichnete Pfeilmitte weicht bei 320, 390, 768 und 1280 px auf allen neun
  Projektseiten höchstens 0,015 px von der Mitte der ersten Titelzeile ab; dasselbe gilt für synthetische Titel mit
  zwei und drei Zeilen. Bei keiner Breite entsteht horizontaler Überlauf.
  Galerievarianten mit einem, zwei und drei Hochformaten, mit großem Motiv sowie mit durch
  ein Querformat getrennten Hochformaten schließen ohne halbe Lücken.
- Ergebnisraster auf allen neun Projektseiten bei 320, 390, 768 und 1280 px geprüft:
  mobil jeweils zwei gleich breite Spalten, Desktop weiterhin vier. Listen mit einem, drei
  und fünf Einträgen schließen mit einer exakt vollbreiten letzten Karte. Normal umbrechender
  langer Text bleibt zweispaltig; eine untrennbare 20-stellige Kennzahl stapelt bei 320 und
  390 px, passt bei 768 px dagegen noch in die Halbzelle. Auch der vollbreite Fallback einer
  längeren Testkennzahl bleibt ohne Inhalts- oder Seitenüberlauf. Bei 320/390/768 px messen
  „Was bleibt.“, „Weitersehen.“ und Kontaktheadline 42/48/48 px; bei 1280 px bleiben die
  ersten beiden mit 102,4 px gegenüber der 76,8-px-Kontaktheadline bewusst groß.
- `git diff --check`: bestanden.
- Vollständige Django-Suite: 9 Tests bestanden; 50 Tests konnten ohne laufendes lokales
  PostgreSQL ausschließlich beim Datenbank-Setup nicht starten. Das betraf nicht die
  statischen Prototypänderungen.

## Repository-Hinweis

Der Materialordner ist versioniert. `BG_CV.psd` ist ungefähr 72 MB groß und wurde von
GitHub akzeptiert, liegt aber über der dort empfohlenen Einzeldateigröße von 50 MB.
