(() => {
  const mobileProjectGrids = matchMedia("(max-width: 52rem)");
  let layoutFrame = 0;

  /* Stapelt Titel und Pfeil der Folgeprojekt-Kacheln (related_project_card.html),
     wenn sie auf schmalen Bildschirmen nicht nebeneinander passen. */
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

  window.PortfolioProjectTeasers = { sync: requestLayout };
  sync();
  addEventListener("resize", requestLayout, { passive: true });
  mobileProjectGrids.addEventListener?.("change", requestLayout);
  if (document.fonts) {
    document.fonts.ready.then(requestLayout);
    document.fonts.addEventListener?.("loadingdone", requestLayout);
  }
})();
