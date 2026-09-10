document.documentElement.classList.add("has-js");

const projects = [
  { slug: "studio-website-relaunch", title: "Studio-Website Relaunch", field: "Web", year: "2026" },
  { slug: "buchgestaltung", title: "Buchgestaltung", field: "Print", year: "2025" },
  { slug: "plakatserie", title: "Plakatserie", field: "Print", year: "2025" },
  { slug: "illustrationsserie", title: "Illustrationsserie", field: "Illustration", year: "2025" },
  { slug: "magazin-layout", title: "Magazin-Layout", field: "Print", year: "2024" },
  { slug: "onlineshop-redesign", title: "Onlineshop Redesign", field: "Digital", year: "2024" },
  { slug: "markenauftritt-praxis", title: "Markenauftritt Praxis", field: "Web", year: "2024" },
  { slug: "kinderbuch", title: "Kinderbuch", field: "Illustration", year: "2023" },
  { slug: "geschaeftsausstattung", title: "Geschäftsausstattung", field: "Print", year: "2023" },
];

const slug = document.body.dataset.project;
const index = projects.findIndex((project) => project.slug === slug);
const project = projects[index] || projects[0];
const moreProjects = [projects[(index + 1) % projects.length], projects[(index + 2) % projects.length]];

/* Später kommen beide Listen aus wiederholbaren Wagtail-Blöcken. Das Hero-Bild bleibt
   ein eigenes Pflichtfeld; die Galerie verlangt mindestens zwei Einträge, hat aber keine
   feste Obergrenze. `shape` steuert nur den vorhandenen Rasterplatz, nicht den Inhalt.
   `large` entspricht dabei dem späteren Wagtail-Schalter „Großes Motiv“; die bestehende
   `wide`-Klasse bleibt als kompatible Prototyp-Abkürzung erhalten. */
const rawGalleryItems = project.gallery || [
  { shape: "wide landscape", ratio: "3:2", label: "breites Projektbild" },
  { shape: "landscape", ratio: "3:2", label: "Projektbild im Querformat" },
  { shape: "portrait", ratio: "4:5", label: "Projektbild im Hochformat" },
];

/* Auf schmalen Ansichten werden ausschließlich unmittelbar aufeinanderfolgende,
   gewöhnliche Hochformate paarweise gesetzt. Ein einzelnes oder ungerades letztes
   Hochformat erhält eine volle Zeile; dadurch bleibt niemals eine leere halbe Zeile.
   Redaktionell große Motive bilden unabhängig vom Format immer eine volle Zeile. */
function layoutGalleryItems(items) {
  const laidOut = items.map((item) => {
    const classes = new Set(String(item.shape || "").split(/\s+/).filter(Boolean));
    if (item.large) classes.add("wide");
    return { ...item, classes };
  });

  for (let itemIndex = 0; itemIndex < laidOut.length; itemIndex += 1) {
    const item = laidOut[itemIndex];
    if (!item.classes.has("portrait") || item.classes.has("wide")) continue;
    const next = laidOut[itemIndex + 1];
    if (next && next.classes.has("portrait") && !next.classes.has("wide")) {
      item.classes.add("portrait-paired");
      next.classes.add("portrait-paired");
      itemIndex += 1;
    }
  }

  return laidOut.map((item) => ({ ...item, className: [...item.classes].join(" ") }));
}

const galleryItems = layoutGalleryItems(rawGalleryItems);

/* Auch „Was bleibt“ ist eine beliebig lange, optionale Liste. Die sichtbaren Nummern
   werden aus der Reihenfolge erzeugt und sind keine vier fest angelegten Felder. */
const resultItems = project.results ?? [
  "[Ergebnis oder Kennzahl]",
  "[Ergebnis oder Kennzahl]",
  "[Ergebnis oder Kennzahl]",
  "[Ergebnis oder Kennzahl]",
];

document.title = `${project.title} — Katharina Wersdörfer`;
document.body.innerHTML = `
  <a class="skip-link" href="#main-content">Zum Hauptinhalt</a>
  <header class="site-header">
    <a class="brand" href="../portfolio-startseite.html">Katharina Wersdörfer</a>
    <span class="avail">Verfügbar für Projekte</span>
    <div class="header-actions">
      <a class="pill" href="mailto:katharina@wersdoerfer.de"><span class="pill-label">Kontakt</span></a>
      <details class="site-nav">
        <summary class="menu-toggle" aria-label="Menü"><span class="menu-icon" aria-hidden="true"></span></summary>
        <nav aria-label="Seitennavigation">
          <div class="menu-primary">
          <a href="#projektstart">Moin</a>
          <details class="project-menu">
            <summary><a class="project-overview" href="../portfolio-startseite.html#projekte">Projekte</a></summary>
            <div class="project-menu-links">
              ${projects.map((item) => `<a href="${item.slug}.html">${item.title}</a>`).join("")}
            </div>
          </details>
          <a href="#case-study">Case Study</a>
          <a href="#galerie">Galerie</a>
          ${resultItems.length ? '<a href="#ergebnisse">Ergebnisse</a>' : ""}
          <a href="#kontakt">Kontakt</a>
          </div>
          <div class="menu-socials" aria-label="Direkte Kontaktwege">
            <div class="menu-social-links">
            <a class="mail-link" href="mailto:katharina@wersdoerfer.de" aria-label="E-Mail schreiben"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="1.5"/><path d="m4 7 8 6 8-6"/></svg></a>
            <a class="linkedin-link" href="https://www.linkedin.com/in/katharina-wersd%C3%B6rfer-7a41181a2" aria-label="LinkedIn"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="6.25" cy="4.75" r="1.85"/><path d="M4.4 9h3.7v11H4.4z"/><path d="M10.35 20V9h3.7v1.55a4.3 4.3 0 0 1 3.45-1.8c2.55 0 4.1 1.75 4.1 5V20h-3.7v-5.7c0-1.4-.55-2.15-1.65-2.15-1.4 0-2.2.95-2.2 2.75V20z"/></svg></a>
            <a href="https://github.com/federfuxx" aria-label="GitHub"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 19c-4 1.2-4-2-5-2.5M14.5 21v-3.1c0-.9.3-1.6.8-2.1 2.7-.3 5.5-1.3 5.5-6a4.7 4.7 0 0 0-1.3-3.3 4.4 4.4 0 0 0-.1-3.3s-1-.3-3.5 1.3a12 12 0 0 0-6.4 0C7 2.9 6 3.2 6 3.2a4.4 4.4 0 0 0-.1 3.3 4.7 4.7 0 0 0-1.3 3.3c0 4.7 2.8 5.7 5.5 6 .5.5.8 1.1.8 2.1V21"/></svg></a>
            <a href="https://fedi.wersdoerfer.de/@katharina" rel="me" aria-label="Mastodon"><svg class="phosphor-icon" viewBox="0 0 256 256" aria-hidden="true"><path d="M184 34H72a38 38 0 0 0-38 38v120a38 38 0 0 0 38 38h88a6 6 0 0 0 0-12H72a26 26 0 0 1-26-26v-10h138a38 38 0 0 0 38-38V72a38 38 0 0 0-38-38Zm26 110a26 26 0 0 1-26 26H46V72a26 26 0 0 1 26-26h112a26 26 0 0 1 26 26Zm-28-40v32a6 6 0 0 1-12 0v-32a18 18 0 0 0-36 0v32a6 6 0 0 1-12 0v-32a18 18 0 0 0-36 0v32a6 6 0 0 1-12 0v-32a30 30 0 0 1 54-18 30 30 0 0 1 54 18Z"/></svg></a>
            </div>
          </div>
        </nav>
      </details>
    </div>
  </header>
  <div class="availability-strip" aria-label="Projektstatus">
    <span class="avail">Verfügbar für Projekte</span>
  </div>
  <main id="main-content">
    <article>
      <header class="project-hero" id="projektstart">
        <p class="eyebrow">Projekt ${String(index + 1).padStart(2, "0")} / ${String(projects.length).padStart(2, "0")}</p>
        <h1 class="motion-heading">${project.title}</h1>
        <div class="intro-grid">
          <p class="project-lead">[Kurze Projektzusammenfassung: Aufgabe, Haltung und wichtigste Wirkung.]</p>
          <dl class="project-meta">
            <div><dt>Bereich</dt><dd>${project.field}</dd></div>
            <div><dt>Jahr</dt><dd>${project.year}</dd></div>
            <div><dt>Kunde</dt><dd>[Kundenname]</dd></div>
            <div><dt>Leistungen</dt><dd>[Leistungen]</dd></div>
          </dl>
        </div>
      </header>

      <div class="media-placeholder hero-media" role="img" aria-label="Platzhalter für das Projekt-Titelbild">Projekt-Titelbild · 21:9</div>

      <section class="block" id="case-study">
        <p class="eyebrow">Case Study</p>
        <div class="case-row">
          <h2 class="case-label">Das Projekt</h2>
          <p class="case-copy large">[Ein prägnanter Satz, der das Projekt und seinen gestalterischen Kern erklärt.]</p>
        </div>
        <div class="case-row">
          <h2 class="case-label">Die Aufgabe</h2>
          <p class="case-copy">[Ausgangslage, Ziel und Rahmenbedingungen. Dieser Bereich wird später als redaktionelles Wagtail-Feld gepflegt.]</p>
        </div>
        <div class="case-row">
          <h2 class="case-label">Die Lösung</h2>
          <p class="case-copy">[Konzept, gestalterische Entscheidungen und Umsetzung. Bilder und Textblöcke können im späteren Template einzeln ein- oder ausgeblendet werden.]</p>
        </div>
      </section>

      <section class="gallery" id="galerie" aria-label="Projektgalerie">
        ${galleryItems.map((item) => `
          <div class="media-placeholder ${item.className}" role="img" aria-label="Platzhalter für ${item.label}">Projektbild · ${item.ratio}</div>`).join("")}
      </section>

      ${resultItems.length ? `
        <section class="block results on-dark" id="ergebnisse">
          <p class="eyebrow">Ergebnisse</p>
          <h2 class="block-title motion-heading">Was bleibt.</h2>
          <div class="result-grid">
            ${resultItems.map((item, itemIndex) => `
              <div class="result"><strong>${String(itemIndex + 1).padStart(2, "0")}</strong><span>${item}</span></div>`).join("")}
          </div>
        </section>` : ""}

      <section class="block">
        <p class="eyebrow">Rückmeldung</p>
        <blockquote class="quote">
          <p>„[Optionales Kundenstatement zum Projekt.]“</p>
          <footer>[Name · Rolle]</footer>
        </blockquote>
      </section>

      <section class="block more-projects">
        <p class="eyebrow">Weitere Projekte</p>
        <h2 class="block-title motion-heading">Weitersehen.</h2>
        <div class="more-grid">
          ${moreProjects.map((item) => `
            <a class="more-card" href="${item.slug}.html">
              <div class="tile-depth">
                <div class="frame"><span>21:9</span></div>
                <div class="meta">
                  <div class="row1"><h3>${item.title}</h3><span class="tile-arrow" aria-hidden="true">→</span></div>
                  <div class="row2">${item.field} · ${item.year}</div>
                </div>
              </div>
            </a>`).join("")}
        </div>
      </section>

      <section class="block contact" id="kontakt">
        <div class="sec-label"><span>Auf ein Wort</span></div>
        <div class="stack">
          <h2 class="big motion-heading">Ein Projekt im Kopf?<br><span class="lastline">Schreib mir.<svg class="scr" aria-hidden="true"><text>tell me more</text></svg></span></h2>
          <div class="buttons">
            <a class="pill prio" href="mailto:katharina@wersdoerfer.de"><span class="pill-label">E-Mail schreiben <span class="ar" aria-hidden="true">→</span></span></a>
          </div>
        </div>
      </section>
    </article>
  </main>
  <footer class="site on-dark" lang="de">
    <div class="foot-cols pad">
      <div class="foot-col foot-profile">
        <span class="brand">Katharina Wersdörfer</span>
        <p>Web &amp; Digital Design, Illustration und Print — aus Düsseldorf.</p>
        <span class="avail">Verfügbar für Projekte</span>
      </div>
      <nav class="foot-col foot-pages" aria-labelledby="ft-seite">
          <h2 class="foot-h" id="ft-seite">Seite</h2>
          <ul>
            <li><a href="../portfolio-startseite.html#stage">Moin</a></li>
            <li><a href="../portfolio-startseite.html#projekte">Projekte</a></li>
            <li><a href="../portfolio-startseite.html#leistungen">Leistungen</a></li>
            <li><a href="../portfolio-startseite.html#about">Über mich</a></li>
            <li><a href="../portfolio-startseite.html#kunden">Kunden</a></li>
            <li><a href="#kontakt">Kontakt</a></li>
          </ul>
      </nav>
      <nav class="foot-col foot-projects" aria-labelledby="ft-projekte">
        <h2 class="foot-h" id="ft-projekte">Projekte</h2>
        <ul>
          ${projects.map((item) => `<li><a href="${item.slug}.html">${item.title}</a></li>`).join("")}
        </ul>
      </nav>
      <nav class="foot-col foot-legal" aria-labelledby="ft-recht">
        <h2 class="foot-h" id="ft-recht">Rechtliches</h2>
        <ul>
          <li><a href="../impressum.html">Impressum</a></li>
          <li><a href="../datenschutz.html">Datenschutz</a></li>
        </ul>
      </nav>
    </div>
    <div class="foot-bar pad">
      <span>© 2026 Katharina Wersdörfer</span>
      <span>Designed in Düsseldorf</span>
      <a class="to-top" href="#projektstart" aria-label="Zurück nach oben"><span class="tile-arrow" aria-hidden="true">→</span></a>
    </div>
  </footer>
  <div class="pagegrid" aria-hidden="true">
    <div class="pads"></div>
    <div class="cols"><i></i><i></i><i></i><i></i></div>
  </div>
  <div class="linen" aria-hidden="true"></div>`;

/* Ergebnisse und Folgeprojekt-Karten bleiben mobil so lange zweispaltig, wie ihr konkret
   gerenderter Inhalt hineinpasst. Eine globale Breite wäre unnötig grob. Für jede Messung
   wird kurz die zweispaltige Ausgangsform hergestellt. Da ausschließlich Viewport- und
   Font-Ereignisse neu messen (kein Layout-ResizeObserver), können die danach gesetzten
   Stapelklassen keine Mess-/Layout-Oszillation auslösen. Ohne JavaScript bleibt jeweils die
   sinnvolle zweispaltige CSS-Ausgangsform erhalten. */
const resultGrid = document.querySelector(".result-grid");
const moreGrid = document.querySelector(".more-grid");
const mobileProjectGrids = matchMedia("(max-width: 52rem)");
let projectGridFrame = 0;

function syncResultGridLayout() {
  if (!resultGrid) return;
  resultGrid.classList.remove("result-grid-stacked");
  if (!mobileProjectGrids.matches) return;

  const epsilon = 0.5;
  const needsStack = [...resultGrid.querySelectorAll(".result")].some((card) => {
    const cardRect = card.getBoundingClientRect();
    const cardStyle = getComputedStyle(card);
    const contentRight = cardRect.right - (parseFloat(cardStyle.paddingRight) || 0);
    return card.scrollWidth > card.clientWidth + epsilon
      || [...card.children].some((item) => {
        const itemRect = item.getBoundingClientRect();
        return item.scrollWidth > item.clientWidth + epsilon
          || itemRect.right > contentRight + epsilon;
      });
  });

  resultGrid.classList.toggle("result-grid-stacked", needsStack);
}

function syncMoreGridLayout() {
  if (!moreGrid) return;
  moreGrid.classList.remove("more-grid-stacked");
  if (!mobileProjectGrids.matches) return;

  const needsStack = [...moreGrid.querySelectorAll(".row1")].some((row) => {
    const title = row.querySelector("h3");
    const arrow = row.querySelector(".tile-arrow");
    if (!title || !arrow) return false;
    const rowRect = row.getBoundingClientRect();
    const titleRect = title.getBoundingClientRect();
    const arrowRect = arrow.getBoundingClientRect();
    const rowStyle = getComputedStyle(row);
    const minimumGap = parseFloat(rowStyle.columnGap || rowStyle.gap) || 0;
    const epsilon = 0.5;
    return row.scrollWidth > row.clientWidth + epsilon
      || arrowRect.right > rowRect.right + epsilon
      || titleRect.right + minimumGap > arrowRect.left + epsilon;
  });

  moreGrid.classList.toggle("more-grid-stacked", needsStack);
}

function syncProjectGridLayouts() {
  syncResultGridLayout();
  syncMoreGridLayout();
}

function requestProjectGridLayouts() {
  cancelAnimationFrame(projectGridFrame);
  projectGridFrame = requestAnimationFrame(syncProjectGridLayouts);
}

syncProjectGridLayouts();
addEventListener("resize", requestProjectGridLayouts, { passive: true });
mobileProjectGrids.addEventListener?.("change", requestProjectGridLayouts);
if (document.fonts) {
  document.fonts.ready.then(requestProjectGridLayouts);
  document.fonts.addEventListener?.("loadingdone", requestProjectGridLayouts);
}
