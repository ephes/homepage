# Arbeitsstand Portfolio-Prototyp

Stand: 7. September 2026

## Wiedereinstieg

- Arbeitsbranch: `portfolio-site`
- Letzter vollständiger Implementierungsstand: Commit `911c1d1`
- Haupteinstieg: `portfolio-startseite.html` direkt in Helium öffnen.
- Gemeinsame Gestaltung und Interaktionen: `motion.css`, `motion.js` und `site-shell.js`.
- Projektunterseiten: `projekte/`; gemeinsamer Aufbau in `projekt.css` und `projekt.js`.
- Rechtsseiten: `impressum.html`, `datenschutz.html` und `legal.css`.
- Ausführliche Design- und Verhaltensdokumentation: `README.md` in diesem Ordner.

## Zuletzt bearbeitet

- Die Social-Links wurden als runde Outline-Buttons in das Menü integriert.
- Alle Iconformen liegen direkt als Inline-SVG im Seiten-Markup; es gibt keine externe
  Icon-CDN und keine ausgelagerten SVG-`use`-Referenzen.
- LinkedIn verwendet eine rahmenlose, hohle `in`-Kontur ohne zusätzlichen quadratischen
  Rahmen. Mastodon verwendet die luftigere Light-Variante von Phosphor Icons.
- Das geöffnete Menü ist am Viewport verankert und endet bei allen geprüften Breiten exakt
  an der rechten Bildschirmkante.
- Die Trennlinie über den Social-Icons reicht über die gesamte nutzbare Innenbreite des
  Menüpanels.

Wichtige technische Erkenntnis: Externe SVG-Symbole über
`<use href="datei.svg#symbol">` wurden beim direkten Öffnen der HTML-Dateien in Helium
nicht zuverlässig dargestellt. Für diesen Prototyp deshalb die Icons inline belassen.

## Ausdrücklich noch offen

Das Menü ist **noch nicht fertig**. Beim nächsten Termin zuerst dort weiterarbeiten:

- endgültige Auswahl und optische Gewichtung der Social-Icons prüfen;
- Größe, Abstand und Zentrierung der Iconreihe auf Telefon, Tablet und Desktop verfeinern;
- Projekt-Disclosure, Zeilen-/Spaltenaufteilung und Scrollverhalten bei geringer Höhe erneut
  im Zusammenhang testen;
- Panelbreite, rechte Außenkante, Akzentbalken, Trennlinie und Öffnungsanimation über die
  vollständige Breitenpalette auf Regressionen prüfen;
- Tastaturbedienung, Touch und `prefers-reduced-motion` beim finalen Menüstand erneut testen.

Danach folgen weitere Layout-Optimierungen für Mobile. Schwerpunkt ist ein durchgehender
Regressionstest ab 320 px aufwärts: keine horizontalen Überläufe, keine Überschneidungen,
stimmige Typohierarchie und Handschriftgrößen sowie belastbare Kachel-, Slider-, About-,
Footer- und Top-Anker-Geometrie.

## Letzte Prüfungen

- JavaScript-Syntaxprüfung für `motion.js`, `site-shell.js` und `projekte/projekt.js`: bestanden.
- Browser-Smoke-Test für Startseite, Impressum, Datenschutz und eine Projektseite bei
  320, 390, 768 und 1280 px: 16 Kombinationen bestanden.
- Dabei geprüft: vier sichtbare Inline-SVGs und eine exakt an der Viewportkante endende
  Menüfläche.
- `git diff --check`: bestanden.
- Vollständige Django-Suite: 9 Tests bestanden; 50 Tests konnten ohne laufendes lokales
  PostgreSQL ausschließlich beim Datenbank-Setup nicht starten. Das betraf nicht die
  statischen Prototypänderungen.

## Repository-Hinweis

Der Materialordner ist versioniert. `BG_CV.psd` ist ungefähr 72 MB groß und wurde von
GitHub akzeptiert, liegt aber über der dort empfohlenen Einzeldateigröße von 50 MB.
