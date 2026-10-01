(() => {
  "use strict";

  const resultGrid = document.querySelector(".result-grid");
  if (!resultGrid) return;

  const mobileLayout = matchMedia("(max-width: 52rem)");
  let layoutFrame = 0;

  function syncResultGrid() {
    resultGrid.classList.remove("result-grid-stacked");
    if (!mobileLayout.matches) return;

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

  function requestLayout() {
    cancelAnimationFrame(layoutFrame);
    layoutFrame = requestAnimationFrame(syncResultGrid);
  }

  syncResultGrid();
  addEventListener("resize", requestLayout, { passive: true });
  mobileLayout.addEventListener?.("change", requestLayout);
  if (document.fonts) {
    document.fonts.ready.then(requestLayout);
    document.fonts.addEventListener?.("loadingdone", requestLayout);
  }
})();
