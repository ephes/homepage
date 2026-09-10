(() => {
  const mobileProjectGrids = matchMedia("(max-width: 52rem)");
  let layoutFrame = 0;

  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

  /* Eine gemeinsame Prototyp-Komponente für die Folgeprojekt-Kacheln. In Wagtail
     übernimmt related_project_card.html dieselbe serverseitig gerenderte Struktur. */
  function render(items, { pathPrefix = "" } = {}) {
    return items.map((item) => {
      const title = escapeHtml(item.title);
      const field = escapeHtml(item.field);
      const year = escapeHtml(item.year);
      const image = item.image
        ? `<img src="${escapeHtml(item.image)}" alt="" loading="lazy">`
        : '<span aria-hidden="true">21:9</span>';
      return `
        <a class="more-card" href="${pathPrefix}${escapeHtml(item.slug)}.html">
          <div class="tile-depth">
            <div class="frame">${image}</div>
            <div class="meta">
              <div class="row1"><h3>${title}</h3><span class="tile-arrow" aria-hidden="true">→</span></div>
              <div class="row2">${field} · ${year}</div>
            </div>
          </div>
        </a>`;
    }).join("");
  }

  function syncGrid(grid) {
    grid.classList.remove("more-grid-stacked");
    if (!mobileProjectGrids.matches) return;

    const needsStack = [...grid.querySelectorAll(".row1")].some((row) => {
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

    grid.classList.toggle("more-grid-stacked", needsStack);
  }

  function sync() {
    document.querySelectorAll(".more-grid").forEach(syncGrid);
  }

  function requestLayout() {
    cancelAnimationFrame(layoutFrame);
    layoutFrame = requestAnimationFrame(sync);
  }

  window.PortfolioProjectTeasers = { render, sync: requestLayout };
  sync();
  addEventListener("resize", requestLayout, { passive: true });
  mobileProjectGrids.addEventListener?.("change", requestLayout);
  if (document.fonts) {
    document.fonts.ready.then(requestLayout);
    document.fonts.addEventListener?.("loadingdone", requestLayout);
  }
})();
