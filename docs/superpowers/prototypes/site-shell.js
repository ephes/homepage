/* Gemeinsames Verhalten für Raster, Navigation und Seitenschale. Das Menü bleibt als
   natives details/summary auch ohne JavaScript vollständig bedienbar. */
(() => {
  const grid = document.querySelector(".pagegrid");
  if (!grid) return;

  const gradient = (light, dark) => {
    const bands = [...document.querySelectorAll(".on-dark")]
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return [rect.top + window.scrollY, rect.bottom + window.scrollY];
      })
      .sort((a, b) => a[0] - b[0]);
    const stops = [];
    let y = 0;
    bands.forEach(([top, bottom]) => {
      stops.push(`${light} ${y}px ${top}px`, `${dark} ${top}px ${bottom}px`);
      y = bottom;
    });
    stops.push(`${light} ${y}px 100%`);
    return `linear-gradient(to bottom,${stops.join(",")})`;
  };

  const syncGridColors = () => {
    grid.style.setProperty("--line-strong", gradient("var(--rule-strong)", "var(--dark-ink)"));
    grid.style.setProperty("--line-soft", gradient("var(--rule)", "var(--dark-rule)"));
  };

  syncGridColors();
  addEventListener("resize", syncGridColors, { passive: true });
  if ("ResizeObserver" in window) new ResizeObserver(syncGridColors).observe(document.body);
  if (document.fonts?.ready) document.fonts.ready.then(syncGridColors);
})();

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
  const menuStops = [...menu.querySelectorAll("nav a, nav summary")];
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
      const stops = [toggle, ...menuStops];
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
    if (["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "].includes(event.key)) event.preventDefault();
  });
  document.addEventListener("click", (event) => {
    if (menu.open && !menu.contains(event.target)) menu.removeAttribute("open");
  });
})();
