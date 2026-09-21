# Arbeitsstand Portfolio-Prototyp

Stand: 21. September 2026

## Wiedereinstieg

- Arbeitsbranch: `portfolio-site`
- Letzter vollständiger reiner Prototypstand: Commit `911c1d1`.
- Basis des aktuellen Wagtail-Paritätsstands: Commit `36aeb78`. Der vollständige
  Paritätsslice vom 21. September 2026 wurde in der laufenden Vorschau visuell abgenommen;
  die separat orchestrierte Claude-Review mit `REVIEW: CLEAN` bleibt vor der
  Veröffentlichung verbindliches Gate.
- Visuelle Quelle der Wahrheit: die aktuelle `portfolio-startseite.html`, lokal unter
  `http://127.0.0.1:8001/portfolio-startseite.html`, samt ihren aktuellen Unterseiten.
- Gemeinsame Gestaltung und Interaktionen: `motion.css`, `motion.js` und `site-shell.js`.
- Projektunterseiten: `projekte/`; `projekt.css` ist auch die kanonische Wagtail-
  Präsentation. `projekte/projekt.js` bleibt ausschließlich der clientseitige Generator
  des statischen Prototyps und wird von Wagtail bewusst **nicht** geladen.
- Rechtsseiten: statisch `impressum.html` und `datenschutz.html`; Wagtail unter
  `/impressum/` und `/datenschutz/`. Beide verwenden die kanonische `legal.css`.
- Ausführliche Design- und Verhaltensdokumentation: `README.md` in diesem Ordner.

## Wagtail-Parität — abgenommener Implementierungsstand

- Die gemeinsame Wagtail-Ausgabe verwendet die freigegebene variable Saira-Datei,
  lädt sie früh über eine manifestfähige Preload-URL und behält dank
  `font-display: swap` sichtbaren Systemfont-Fallback.
- Astagina ist als zentrale Wagtail-Fontressource eingebunden, aber nicht vorab geladen.
  Handschriftliche Inhalte stehen serverseitig als lesbarer SVG-Text im Dokument. Die
  Homepage lädt die exakten Pfaddaten aus `handwriting-glyphs.js` erst bei Bedarf;
  Projektseiten teilen sich das kleinere `handwriting-contact.js`. Bei reduzierter
  Bewegung wird keines der Pfadbündel angefordert.
- Globale Palette, Display-/Lesestufen, Rhythmus- und Trackingrollen sind in den
  unverändert geordneten Wagtail-CSS-Layern abgebildet. Viewportkomposition,
  Komponenteninputs und JavaScript-Messwerte wurden nicht zu globalen Tokens gemacht.
- Der komplette aktuelle Startseitenaufbau ist serverseitig vorhanden: Header und
  animiertes natives Menü, Verfügbarkeitsband, Hero mit lesbarem `MOIN`-Fallback und
  WebGL-Enhancement, Seitenraster, Leinentextur, Projekte, Leistungen, About, Kunden,
  Kontakt, Footer, Custom Cursor, Top-Anker, organische Formen und Handschrift/Motion.
- Wagtail nutzt die freigegebenen Prototype-Dateien direkt unter dem statischen Namespace
  `portfolio/prototype`; es gibt keine zweite kopierte CSS-, Motion- oder
  Handschriftquelle. `homepage.css` und `project-wagtail.css` sind nur schmale Adapter
  für abweichendes serverseitiges Markup und Wagtail-Renditions.
- Projektseiten und die 501-Seite verwenden den gemeinsamen Header, Footer und
  `related_project_card`. Jede Projektseite besitzt ihre eigenen editierbaren Felder
  und StreamField-Blöcke; responsive Bildrenditions und Alttextverträge bleiben
  erhalten. Neu angelegte Projekte erhalten einen editierbaren semantischen
  Starterinhalt, aber keine siteweiten Projekttext-Fallbacks. `/portfolio/501/` bleibt
  HTTP 501.
- Die Rechtsseiten werden aus gemeinsamen `LegalPageSettings` ausschließlich für die
  Wagtail-Site mit einer veröffentlichten Portfolio-Startseite serverseitig gerendert.
  Eine vorhandene veröffentlichte Wagtail-Seite unter demselben Pfad hat auch dort
  Vorrang; das gilt ebenso für zugriffsbeschränkte Seiten, deren Anmeldung oder Passwort
  weiterhin Wagtail selbst durchsetzt. Auf anderen Sites gehen gleichnamige Pfade
  ebenfalls an Wagtails normale Seitenauflösung. So erscheinen weder fremde
  Portfolio-Personendaten noch werden eigene Seiten verdeckt.
  Semantische StreamFields halten Überschriften, Absätze,
  Adressen und Standhinweise editierbar; die Template-Hierarchie und das Layout bleiben
  geschützt. Sie verwenden Projekt-Shell, Leinentextur, Menü, Footer und `legal.css`,
  aber kein Handschriftbündel.
- Die Paritätsmigrationen reichen bis `0022`: `0007` ergänzt die semantischen
  Startseitenfelder und sortierbaren Leistungen/About-/Kundenlisten, `0008` und `0010`
  bilden die geteilte Kontaktheadline ab, `0009` ergänzt die Projektkategorie „Digital“;
  `0011` führt die per Site editierbaren Rechtsseiten ein, `0012` zentralisiert wiederkehrende
  redaktionelle Labels und übernimmt die bisherigen Statement-/Aufgabe-/Lösung-Platzhalter
  in leere Projekt-StreamFields; `0013` installiert den vollständigen editierbaren
  Starterinhalt für neue Projekte, ergänzt exakt diesen unveränderten zweiblöckigen
  Übergangsstarter unter Beibehaltung seiner IDs und befüllt ansonsten nur vollständig
  leere Projekt-Streams. Andere bestehende redaktionelle Inhalte und historische
  Revisionen bleiben dabei unangetastet;
  `0014` bis `0016` ergänzen den Teaser-Rich-Text, gemeinsame Wertelabels und den
  editierbaren Website-Buttontext. `0017` überführt die bisher festen Projektbereiche in
  zentral verwaltete Kategorien. Eigene Kategorien können im Projekt-Chooser oder über
  `Projekte → Kategorien` angelegt werden; bestehende Seiten und Revisionen behalten
  ihre Zuordnung. `0018` ergänzt das optionale Endjahr für mehrjährige Projekte.
  `0019` macht die bisherigen positionsabhängigen Startseiten-Hero-Kacheln pro Projekt
  editierbar und übernimmt die bestehende Optik ohne Neuordnung.
  `0020` markiert die abgelösten About-/Kontakt-Einzelfelder ausdrücklich als
  nicht editierbare Kompatibilitätsdaten; sichtbar bleiben die strukturierten Felder.
  `0021` blendet auch die abgelösten Impressums-/Datenschutz-URL-Spalten aus dem Editor
  aus und bindet die öffentlichen Ziele fest an die eingebauten benannten Routen; die
  Spalten bleiben nur für Migrationen und historische Revisionen erhalten. `0022`
  ersetzt den früher gespeicherten Legal-E-Mail-Platzhalter durch einen strukturellen
  Kontaktblock; die globale Site-Adresse wird erst beim Rendern eingesetzt. Ein aus
  einem Adressblock getrenntes Kontaktpaar erhält eine deterministische Zuordnung, damit
  die Rückwärtsmigration wieder genau einen Adressblock herstellt und unabhängig
  redigierte benachbarte Blöcke nicht zusammenführt.
- Ohne JavaScript bleiben alle Inhalte, Links, Sektionen, Fallbacks und das native Menü
  sichtbar und bedienbar. JavaScript ergänzt nur WebGL, Bewegung, Handschriftpfade,
  Fokus-/Scrollkomfort und konkrete Überlaufmessungen. Ein Font- oder Assetfehler lässt
  verständlichen Text stehen.
- Die öffentlichen Every-Layout-Primitives und die Layerreihenfolge bleiben unverändert.
  Kanonische, bereits freigegebene Media-/Feature-Queries werden mit den Prototype-
  Dateien übernommen; die Wagtail-Adapter führen kein konkurrierendes Breakpointsystem ein.
- Die integrierten Prototype- und Wagtail-Browseraudits sind einschließlich beider
  Rechtsseiten bestanden: JavaScript an/aus, native Menüs, 320-Pixel-Reflow,
  Reduced Motion und Forced Colors, jeweils ohne axe-Verstoß. Die reduzierten
  Wagtail-Rechtsseiten sind bei 1200, 375 und 320 px pixelidentisch zur Prototype-Quelle.
- Alle neun Wagtail-Projektseiten sind im stabilisierten Reduced-Motion-Vergleich bei
  1200, 375 und 320 px pixelidentisch zur jeweiligen Prototype-Seite; Geometrie und
  Gesamthöhe stimmen, bei 320 px entsteht kein Dokumentüberlauf. Eine semantische
  Soft-Hyphen-Stelle hält ausschließlich die freigegebene mobile Trennung von
  „Weitersehen.“ stabil, ohne den lesbaren Text oder Desktop zu ändern.
- Der aktuelle isolierte Mobile-Lighthouse-Lauf misst Wagtail mit 85/100/100/100,
  FCP 2,6 s, LCP 3,8 s, Speed Index 2,6 s, TBT 30 ms, CLS 0,033, 14 Requests und
  478 KiB; der jüngste Prototype-Lauf misst 81/100/92/90, FCP 3,6 s, LCP 3,8 s,
  Speed Index 3,6 s, TBT 0 ms, CLS 0,034, 12 Requests und 521 KiB. Das ist nur der
  gemessene Vergleich, keine allgemeine Performancebehauptung. Das Performance-Gate
  von 90 ist mit 85 weiterhin offen. Erster dokumentierter Cleanup-Kandidat ist der
  überholte Block „Sections (Wireframe)“ in `portfolio-startseite.css`: spätere
  Fluid-Hero-Regeln überschreiben dort doppelte Selektoren, weitere Selektoren treffen
  kein aktuelles Markup mehr. Die Entfernung erfolgt erst in einem eigenen,
  Screenshot-Diff-abgesicherten Performance-Pass, weil diese Datei die kanonische
  visuelle Quelle für Prototype und Wagtail ist.
- Der daemonlose Portfolio-Testlauf besteht mit 201 Tests und überspringt nur die zwei
  separat gegen Colima bestandenen Docker-Build-Context-Tests. Die Vollsuite erreicht
  259 bestandene Tests, dieselben Skips und genau den bekannten Webmentions-Fehler.

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
  Breakpoints misst im statischen Prototyp `projekt.js` und in Wagtail das gemeinsame
  `project-teasers.js` das konkrete Kartenpaar nach dem Rendern, nach geladenen
  Fonts und bei Viewportänderungen in seiner zweispaltigen Form. Nur ein tatsächlich
  überlaufendes Titel-/Pfeil-Paar erhält die einspaltige Stapelklasse. Die Messung lauscht
  absichtlich nicht auf die eigene Rastergröße und kann deshalb nicht oszillieren. Der Pfeil
  sitzt visuell mittig auf der ersten Titelzeile, auch wenn der Titel mehrzeilig umbricht.

Wichtige technische Erkenntnis: Externe SVG-Symbole über
`<use href="datei.svg#symbol">` wurden beim direkten Öffnen der HTML-Dateien in Helium
nicht zuverlässig dargestellt. Für diesen Prototyp deshalb die Icons inline belassen.

## Ausdrücklich noch offen

Die technische Menü- und Motion-Implementierung ist in den Wagtail-Paritätskandidaten
übernommen. Nicht ohne gemeinsame visuelle Entscheidung verändern:

- endgültige Auswahl und optische Gewichtung der Social-Icons prüfen;
- endgültige Gewichtung der neu ausgerichteten Iconreihe im Gesamtbild gemeinsam abnehmen.

Die technische Menü-Geometrie, geringe Viewporthöhen, Tastaturbedienung und
`prefers-reduced-motion` sind für den kanonischen Prototyp und den aktuellen Wagtail-
Kandidaten geprüft. Für die endgültige Gestaltung bleibt die subjektive Abnahme der vier
Social-Icons; ein realer iOS-Touch-Test gehört weiterhin zur Abnahme vor Veröffentlichung.

Der durchgehende technische Mobile-Regressionstest ab 320 px ist abgeschlossen. Als
nächster Schritt folgt die gemeinsame gestalterische Abnahme: Social-Icons sowie
Typohierarchie und Handschriftgrößen im Mobile-Gesamtbild. Kachel-, Slider-, About-,
Footer- und Top-Anker-Geometrie sind technisch belastbar; weitere Änderungen daran sollten
von einem konkreten visuellen Änderungswunsch ausgehen.

## Letzte Prüfungen

Die folgende umfangreiche Liste dokumentiert die freigegebene statische Prototype-
Baseline. Sie ist weiterhin der Vergleichsvertrag. Der integrierte Wagtail-Endlauf des
Paritätsslices ist ebenfalls bestanden:

- Prototype- und Wagtail-Audit einschließlich Startseite, 501, Projekt, Impressum und
  Datenschutz: bestanden; axe 0, 320-Pixel-Reflow, Reduced Motion und Forced Colors
  ohne Befund.
- Wagtail-Rechtsseiten bei 1200, 375 und 320 px unter Reduced Motion: pixelidentisch zur
  jeweiligen kanonischen Prototype-Seite.
- Portfolio-Django-Tests: 201 bestanden, zwei separat gegen Colima bestandene
  Docker-Integrationstests im daemonlosen Lauf übersprungen.
- Vollständige Django-Suite: 259 bestanden, dieselben Skips und ein bekannter bestehender Fehler in
  `test_webmention_display_template_tags` (`list.count()` wird ohne Argument aufgerufen).
- Lighthouse Wagtail: 85/100/100/100; Prototype: 81/100/92/90. Der Performance-Zielwert
  90 ist damit weiterhin nicht erreicht.

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
- Den nach dem Wagtail-Port noch sichtbaren Menü-Kaskadenrest entfernt: Das gemeinsame
  Layer-Stylesheet erzwingt weder eine Header-Mindesthöhe noch eine zweite Social-Trennlinie,
  ein konkurrierendes Social-Grid oder 4,5 rem hohe Social-Links. Dadurch sind die Buttons
  wieder 46 × 46 px große Kreise und die Trennlinie wieder genau einen Pixel stark. Der
  vollständige offene Header-/Panel-Ausschnitt ist bei 1400 × 1800 px pixelidentisch zum
  aktuellen Prototyp; Header- und Hero-Grenzen stimmen zusätzlich bei 1454 × 898,
  1200 × 900, 375 × 667 und 320 × 700 px überein.
- Die Standards-Mode-Anpassung der Wagtail-Startseite begrenzt nur die Blocklinks im
  Footer-Projektverzeichnis intrinsisch mit `fit-content`. Damit fährt die Hoverlinie wie
  im Prototyp nur unter dem Projekttitel ein und nicht über die gesamte Spaltenbreite;
  Seiten- und Rechtslinks bleiben unangetastet. Der Hover-Footer ist bei 576 px weiterhin
  pixelidentisch, die Linkbreite stimmt zusätzlich bei 375 und 320 px exakt überein.
- Der aktuelle Editorvertrag trennt feste Gestaltung von redaktionellem Inhalt:
  ``Moin`` sowie die geprüften Handschrift- und Cursor-Vektortexte bleiben fest; alle
  übrigen sichtbaren Redaktionstexte kommen aus Seitenfeldern, semantischen
  Projektblöcken oder gruppierten Site-/501-/Rechtsseiten-Einstellungen. Die öffentliche
  E-Mail-Adresse und LinkedIn-, GitHub- und Mastodon-Ziele liegen ausschließlich in
  ``PortfolioSiteSettings``. Auch Rechtstext-Mail-Links werden daraus gerendert; das
  frühere Startseiten-Mailfeld bleibt nur verborgen zur Migrationskompatibilität.
- Jedes Portfolio-Projekt ist eine eigene editierbare ``ProjectPage`` unter dem
  Portfolio-Index. Titel, Teasertext, Kategorie, Jahr beziehungsweise Zeitraum, Kunde, Leistungen, Bilder,
  Statement, Aufgabe/Lösung, Ergebnisse und Testimonial gehören zum jeweiligen Projekt;
  projektbezogene Platzhalter liegen nicht in den globalen Site Settings. Neue Seiten
  erhalten vier editierbare Starterblöcke. Veröffentlichen beziehungsweise Zurückziehen
  steuert automatisch Startseitenteaser, Menü, Footer, Zähler und Folgeprojekte, deren
  Titel/Kategorie/Jahr oder Zeitraum/Bild direkt aus derselben Projektseite kommen.
- Migration ``0018`` ergänzt pro Projekt ein optionales Endjahr. Ohne Endjahr bleibt die
  bisherige Einzeljahresausgabe unverändert; mit Endjahr verwenden Projektseite,
  Startseitenteaser und Folgeprojektkarten automatisch denselben kompakten Zeitraum wie
  ``2021–2024``. Ein Endjahr vor dem Startjahr wird im Editor abgewiesen.
- Die Projekt-Unterseiten bleiben die einzige Quelle für Startseitenteaser. Im
  Wagtail-Menü öffnet ``Projekte → Reihenfolge`` die native Drag-and-drop-Sortierung;
  sie steuert Grid, Menü, Footer und Folgeprojekte gemeinsam. Das Projektfeld
  ``Hero-Kachel auf der Startseite`` schaltet die zweispaltige 21:9-Kachel im
  Desktop-Raster. Mobil bleibt das erste sortierte Projekt der 16:9-Einstieg, alle
  weiteren Karten behalten das einheitliche Reel. Keine zusätzliche Media Query wurde
  eingeführt.
- Der Projekt-Teasertext ist ein eng begrenztes Rich-Text-Feld: einzelne Wörter oder
  Passagen dürfen fett gesetzt, als Inline-Link eingefügt oder über ``Kein Umbruch`` als
  zusammenhängender Markenname geschützt werden; weitere Struktur- oder Layoutoptionen
  bleiben templategeführt. Statement, Aufgabe und Lösung erlauben dieselben Funktionen.
  Die No-Break-Auszeichnung ist ein semantischer ``span[data-no-break]`` und benötigt
  öffentlich kein JavaScript. Auf Creme bleibt der Linktext in Ruhe warm-schwarz und
  hat dieselbe 600er Stärke wie die Leistungswerte; bei Hover oder Tastaturfokus werden
  Text und die von links einfahrende Haarlinie Tangerine. Reduzierte Bewegung
  entfernt die Transition, nicht Linkunterscheidung oder Fokus. Die sichtbare Einleitung
  rendert Fettung und Link; die Meta-Description übernimmt denselben Inhalt ohne HTML.
- Migration `0015` benennt die Projektabschnitte samt Wagtail-Editorlabels von
  „Ergebnisse“ in „Mehrwert“ und von „Testimonial“/„Rückmeldung“ in „Kundenstimmen“
  um. Nur die bisherigen globalen Standardwerte werden migriert; bereits individuell
  gepflegte Bezeichnungen bleiben erhalten. Der stabile Fragmentanker `#ergebnisse`
  bleibt für bestehende Deep Links unverändert.
- Die drei Case-Study-Zeilen richten die sichtbare Oberkante von linkem Label und erster
  Textzeile aus. Der Wagtail-Adapter entfernt nur die zusätzlichen Außenabstände der
  RichText-Absatzwrapper; zwischen den Zeilen gilt der lokale fluide Rhythmus
  `clamp(2rem, 3.5vw, 3rem)` statt des bisherigen Sektionsabstands. Dafür kam kein
  Breakpoint hinzu.
- Projektmetadaten stapeln Bereich, optionalen Kunden und Jahr beziehungsweise Zeitraum in einer Spalte. Die
  Leistungen stehen in ihrer redaktionellen Reihenfolge jeweils einzeln in der nächsten
  Spalte. Sie sind eine echte ungeordnete Liste und verwenden das gemeinsame
  `.marker-list`-Pattern: eine größere, linksbündige warm-schwarze Dreiecksspitze wird
  ohne zusätzlichen Markup-Span per CSS erzeugt. Redaktionelle `.rich-text`-ULs nutzen
  dasselbe Pattern; nummerierte und Navigationslisten bleiben unberührt.
  Die große Projektüberschrift nutzt intrinsisch bis zu ``18ch`` der
  verfügbaren Breite. Ihre Zeilenhöhe ``1.03`` gleicht den sichtbaren Abstand der
  Umlautpunkte zur Versalie und zur vorherigen Zeile aus; sie verwendet nur manuelle
  Trennstellen. Dadurch bleibt unter anderem ``Leistungen``
  als Wort zusammen; ein neuer Media Query war dafür nicht nötig.
- Das Projektintro verwendet zwei verschachtelte intrinsische Switcher statt eines
  Viewport-Breakpoints: Anleser plus Projektdetails-`aside`, darin Fakten plus Leistungen.
  Nur im nebeneinanderliegenden Zustand reserviert der Anleser `2rem` Luft zum Aside;
  gestapelt erhält er seine volle verfügbare Tablet-/Mobile-Breite zurück. Sein
  Summary-Stack hält mindestens `1.875rem`/30 px Abstand zum Website-Button. Freier
  vertikaler Raum wandert vor den Button, sodass dessen Unterkante normalerweise mit
  der letzten Leistungszeile fluchtet; längerer Anlesetext hat Vorrang, vergrößert die
  Gesamtzeile und drückt den Button weiter nach unten. Die Metadatenlabels werden nur
  optisch um `1px` angehoben, damit ihre Versaloberkante mit dem Anleser fluchtet, ohne
  die Box- oder Buttonausrichtung zu verändern.
- Der optionale externe Projektlink verwendet nun den kompakten gemeinsamen Pill-Button
  statt des für die Startseite gedachten, hier unvollständigen Rasterzeilen-Links.
  Er kombiniert die Prio-1-Farbfläche mit der Außenhöhe und dem horizontalen Padding des
  Prio-2-Headerbuttons. Die 1,2-rem/700-Beschriftung wahrt dabei den Großtextkontrast;
  reduziertes Block-Padding hält die Außenhöhe kompakt. Der Pfeilabstand kommt vom
  vorhandenen gemeinsamen Pill-Gap, nicht von einer neuen Buttonvariante.
  Migration ``0016`` ergänzt dafür einen optionalen Text pro Projekt; leer bleibt der
  vorhandene globale Standard wirksam. Der Button ist weiterhin semantisch ein Link.
- Redaktionelle Inline-Links verwenden nun dieselbe 600er Stärke wie die Leistungswerte.
  Bei Hover und Tastaturfokus färben sich Text und einfahrende Haarlinie Tangerine. Eine
  gleichzeitig gesetzte Link-, Fett- und ``Kein Umbruch``-Auszeichnung bleibt als ein
  zusammenhängender ``span[data-no-break]`` erhalten; ein frischer Render bestätigt
  ``white-space: nowrap`` für den vollständigen markierten Namen.
- Das Wagtail-Hauptmenü bietet direkte Shortcuts ``Startseite`` und ``Projekte``. Die
  aufklappbare Projektliste enthält ``Neues Projekt`` sowie alle bearbeitbaren Projekte;
  Entwürfe bleiben dort erreichbar, erscheinen aber nicht öffentlich. Projekt-Hero und
  Teaserkarten verwenden Wagtails Focal-Point-fähige ``fill``-Renditions. Bilder für
  Case Study und Galerie werden als semantische StreamField-Blöcke eingefügt und
  proportional ohne Beschnitt ausgegeben.
- Das Wagtail-Admin verwendet über einen manifestfähigen globalen Stylesheet-Hook die
  Portfolio-Palette Creme/Warm-Schwarz/Tangerine. Das Theme überschreibt ausschließlich
  semantische Wagtail-Farbvariablen, unterstützt Light, Dark, System und Forced Colors
  und lässt die responsive Admin-Geometrie unangetastet. Für kleinen Linktext und
  aktive Navigation wird eine kontraststärkere dunkle Tangerine-Variante verwendet;
  die großen Untermenüflächen nutzen das freigegebene Warmgrau `#393734`, das sich vom
  warm-schwarzen Hauptmenü absetzt, mit cremefarbenem aktiven und gedämpftem hell-warmem
  inaktiven Linktext. Bestätigende Hauptaktionen wie Speichern,
  Veröffentlichen und Hinzufügen verwenden das freigegebene Smaragdgrün mit
  warm-schwarzem Text.
- Das Admin-Theme hängt am offiziellen globalen Wagtail-CSS-Hook und ersetzt keine
  Wagtail-Templates. Wagtail bleibt auf die `7.4`-Minorserie begrenzt; ein fail-closed
  Test prüft bei Updates alle verwendeten semantischen Farbvariablen und die wenigen
  Untermenü-Selektoren gegen das tatsächlich installierte Wagtail-CSS. Im lokalen
  DEBUG-Betrieb verhindert eine aus dem Dateiänderungszeitpunkt gebildete Query-Version,
  dass Browser nach Theme-Änderungen eine alte Admin-CSS aus ihrem Cache zeigen.
- Dieselbe rein lokale Cache-Sicherung gilt nun für alle öffentlichen Wagtail-CSS-
  Dateien: `versioned_static` ergänzt im DEBUG-Betrieb deren Dateiänderungszeitpunkt,
  lässt die manifest-gehashte Produktions-URL aber unverändert. Damit zeigt auch eine
  normale Aktualisierung auf `127.0.0.1` zuverlässig aktuelle Regeln wie
  `white-space: nowrap` für kombinierte Link-/Fett-/Kein-Umbruch-Auszeichnungen.
- Die dunklen Draftail-Werkzeugleisten erhalten lokal cremefarbene Bedienelemente;
  dadurch bleiben Fett- und weitere Rich-Text-Aktionen sichtbar, ohne die warm-schwarze
  Beschriftung der grünen Bestätigungsbuttons zu verändern.
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
- Aktueller vollständiger daemonloser Django-Lauf: 259 Tests bestanden, zwei separat gegen
  Colima bestandene Docker-Integrationstests übersprungen; ausschließlich der bekannte
  Webmentions-Test `test_webmention_display_template_tags` schlägt fehl, weil er auf einer
  Liste noch `count()` ohne Argument aufruft.

## Repository-Hinweis

Der Materialordner ist versioniert. `BG_CV.psd` ist ungefähr 72 MB groß und wurde von
GitHub akzeptiert, liegt aber über der dort empfohlenen Einzeldateigröße von 50 MB.
