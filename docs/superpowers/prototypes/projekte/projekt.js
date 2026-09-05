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

document.title = `${project.title} — Katharina Wersdörfer`;
document.body.innerHTML = `
  <a class="skip-link" href="#main-content">Zum Hauptinhalt</a>
  <header class="site-header">
    <a class="brand" href="../portfolio-startseite.html">Katharina Wersdörfer</a>
    <span class="avail">Verfügbar für Projekte</span>
    <div class="header-actions">
      <a class="pill" href="#kontakt"><span class="pill-label">Kontakt</span></a>
      <details class="site-nav">
        <summary class="menu-toggle" aria-label="Menü"><span class="menu-icon" aria-hidden="true"></span></summary>
        <nav aria-label="Seitennavigation">
          <a href="#projektstart">Moin</a>
          <a href="../portfolio-startseite.html#projekte">Projekte</a>
          <a href="#case-study">Case Study</a>
          <a href="#galerie">Galerie</a>
          <a href="#ergebnisse">Ergebnisse</a>
          <a href="#kontakt">Kontakt</a>
        </nav>
      </details>
    </div>
  </header>
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
        <div class="media-placeholder landscape wide" role="img" aria-label="Platzhalter für ein breites Projektbild">Projektbild · 3:2</div>
        <div class="media-placeholder landscape" role="img" aria-label="Platzhalter für ein Projektbild im Querformat">Projektbild · 3:2</div>
        <div class="media-placeholder portrait" role="img" aria-label="Platzhalter für ein Projektbild im Hochformat">Projektbild · 4:5</div>
      </section>

      <section class="block results" id="ergebnisse">
        <p class="eyebrow">Ergebnisse</p>
        <h2 class="block-title motion-heading">Was bleibt.</h2>
        <div class="result-grid">
          <div class="result"><strong>01</strong><span>[Ergebnis oder Kennzahl]</span></div>
          <div class="result"><strong>02</strong><span>[Ergebnis oder Kennzahl]</span></div>
          <div class="result"><strong>03</strong><span>[Ergebnis oder Kennzahl]</span></div>
          <div class="result"><strong>04</strong><span>[Ergebnis oder Kennzahl]</span></div>
        </div>
      </section>

      <section class="block">
        <p class="eyebrow">Rückmeldung</p>
        <blockquote class="quote">
          <p>„[Optionales Kundenstatement zum Projekt.]“</p>
          <footer>[Name · Rolle]</footer>
        </blockquote>
      </section>

      <section class="block">
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
            <a class="pill prio" href="mailto:mail@example.com"><span class="pill-label">E-Mail schreiben <span class="ar" aria-hidden="true">→</span></span></a>
          </div>
        </div>
      </section>
    </article>
  </main>
  <footer class="project-footer">
    <div class="footer-grid">
      <p>Web &amp; Digital Design, Illustration und Print — aus Düsseldorf.</p>
      <nav aria-label="Fußnavigation"><a href="../portfolio-startseite.html">Startseite</a><a href="../portfolio-startseite.html#projekte">Alle Projekte</a></nav>
    </div>
  </footer>`;

// Das offene Panel sperrt normale Seitenbewegungen. Nur Klicks und – auf Geräten mit
// echtem Hover – das bewusste Überfahren lokaler Anker dürfen den Hintergrund bewegen.
(() => {
  const menu = document.querySelector(".site-nav");
  if (!menu) return;
  let lockedY = null;
  let anchorFlight = false;
  let flightTimer = 0;
  const desktopHover = matchMedia("(min-width: 52.001rem) and (hover: hover) and (pointer: fine)");
  const motionReduce = matchMedia("(prefers-reduced-motion: reduce)");
  const toggle = menu.querySelector("summary");
  const menuLinks = [...menu.querySelectorAll("nav a")];
  const inertTargets = [...document.querySelectorAll(
    "main, body > footer, .site-header > .brand, .site-header > .avail, .site-header > .header-actions > .pill"
  )];

  const localTarget = (link) => {
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname || !url.hash) return null;
    return document.getElementById(decodeURIComponent(url.hash.slice(1)));
  };
  const flyTo = (link, keepOpen) => {
    const target = localTarget(link);
    if (!target) return false;
    clearTimeout(flightTimer);
    anchorFlight = true;
    if (!keepOpen) {
      lockedY = null;
      menu.removeAttribute("open");
      history.pushState(null, "", link.hash);
    }
    requestAnimationFrame(() => target.scrollIntoView({ behavior: motionReduce.matches ? "auto" : "smooth", block: "start" }));
    flightTimer = window.setTimeout(() => {
      anchorFlight = false;
      if (menu.open) lockedY = window.scrollY;
    }, 850);
    return true;
  };

  menu.addEventListener("toggle", () => {
    lockedY = menu.open ? window.scrollY : null;
    toggle.setAttribute("aria-label", menu.open ? "Menü schließen" : "Menü");
    inertTargets.forEach((node) => { node.inert = menu.open; });
    if (!menu.open) anchorFlight = false;
  });
  menuLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      if (flyTo(link, false)) event.preventDefault();
      else menu.removeAttribute("open");
    });
    link.addEventListener("pointerenter", () => {
      if (desktopHover.matches) flyTo(link, true);
    });
  });
  const insidePanel = (target) => target instanceof Element && !!target.closest(".site-nav nav");
  const stopOutsidePanel = (event) => {
    if (lockedY !== null && !insidePanel(event.target)) event.preventDefault();
  };
  addEventListener("wheel", stopOutsidePanel, { passive: false });
  addEventListener("touchmove", stopOutsidePanel, { passive: false });
  addEventListener("scroll", () => {
    if (lockedY !== null && !anchorFlight && window.scrollY !== lockedY) window.scrollTo(0, lockedY);
  }, { passive: true });
  document.addEventListener("keydown", (event) => {
    if (!menu.open) return;
    if (event.key === "Escape") {
      menu.removeAttribute("open");
      toggle.focus();
      event.preventDefault();
      return;
    }
    if (event.key === "Tab") {
      const stops = [toggle, ...menuLinks];
      const first = stops[0];
      const last = stops[stops.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        last.focus();
        event.preventDefault();
      } else if (!event.shiftKey && document.activeElement === last) {
        first.focus();
        event.preventDefault();
      }
      return;
    }
    if (lockedY === null || insidePanel(event.target)) return;
    if (["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "].includes(event.key)) {
      event.preventDefault();
    }
  });
  document.addEventListener("click", (event) => {
    if (menu.open && !menu.contains(event.target)) menu.removeAttribute("open");
  });
})();
