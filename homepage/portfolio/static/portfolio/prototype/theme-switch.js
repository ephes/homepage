/* Darstellung: System, Hell oder Dunkel. Das Inline-Skript im Kopf setzt die gespeicherte
   Wahl schon vor dem ersten Zeichnen (data-theme-choice, bei Hell/Dunkel auch data-theme);
   dieses Skript bedient Schalter und Menü unten links und speichert die Wahl. */
(() => {
  const STORAGE_KEY = "portfolio-theme";
  const root = document.documentElement;
  const switcher = document.querySelector("[data-theme-switch]");
  if (!switcher) return;
  const toggle = switcher.querySelector(".theme-switch__toggle");
  const menu = switcher.querySelector(".theme-switch__menu");
  const options = [...menu.querySelectorAll("[data-theme-value]")];

  const apply = (choice) => {
    root.dataset.themeChoice = choice;
    if (choice === "system") delete root.dataset.theme;
    else root.dataset.theme = choice;
    options.forEach((option) => {
      const active = option.dataset.themeValue === choice;
      option.setAttribute("aria-checked", String(active));
      if (active) toggle.setAttribute("aria-label", `${toggle.dataset.label}: ${option.textContent.trim()}`);
    });
  };
  const store = (choice) => {
    try {
      if (choice === "system") localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, choice);
    } catch (error) {
      /* Ohne Speicher gilt die Wahl nur für diese Seite. */
    }
  };

  /* is-open hält Feld und Ecke im geöffneten Zustand, bis das Menü auch beim Schließen
     ganz eingefahren ist (Dauer wie in motion.css). */
  const CLOSE_DURATION = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 450;
  let closeTimer = 0;
  const isOpen = () => !menu.hidden;
  const open = () => {
    clearTimeout(closeTimer);
    switcher.classList.add("is-open");
    menu.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
    (options.find((option) => option.getAttribute("aria-checked") === "true") || options[0]).focus();
  };
  const close = (returnFocus) => {
    if (!isOpen()) return;
    menu.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    /* Etwas Reserve, damit die Ecke erst nach dem letzten Bild des Menüs zurückwechselt. */
    closeTimer = setTimeout(() => switcher.classList.remove("is-open"), CLOSE_DURATION && CLOSE_DURATION + 60);
    if (returnFocus) toggle.focus();
  };

  apply(root.dataset.themeChoice || "system");

  toggle.addEventListener("click", () => (isOpen() ? close(false) : open()));
  options.forEach((option, index) => {
    option.addEventListener("click", () => {
      apply(option.dataset.themeValue);
      store(option.dataset.themeValue);
      close(true);
    });
    option.addEventListener("keydown", (event) => {
      const step = { ArrowDown: 1, ArrowUp: -1 }[event.key];
      if (step) {
        event.preventDefault();
        options[(index + step + options.length) % options.length].focus();
      } else if (event.key === "Home" || event.key === "End") {
        event.preventDefault();
        options[event.key === "Home" ? 0 : options.length - 1].focus();
      }
    });
  });
  switcher.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isOpen()) {
      event.preventDefault();
      close(true);
    }
  });
  document.addEventListener("pointerdown", (event) => {
    if (isOpen() && !switcher.contains(event.target)) close(false);
  });
  /* Nur wenn der Fokus per Tastatur woandershin wandert; Safari fokussiert Buttons beim
     Klicken nicht (relatedTarget leer), dort schließt der pointerdown-Handler. */
  switcher.addEventListener("focusout", (event) => {
    if (isOpen() && event.relatedTarget && !switcher.contains(event.relatedTarget)) close(false);
  });
})();
