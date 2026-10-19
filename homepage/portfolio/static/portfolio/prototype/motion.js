/* Shared portfolio motion: headline reveal + traced Astagina writing. */
(function () {
  "use strict";

  var root = document.documentElement;
  root.classList.add("has-js");
  var reduce = matchMedia("(prefers-reduced-motion: reduce)");
  var glyphs = {};
  var handwritingScript = document.currentScript;
  var handwritingSource = handwritingScript && handwritingScript.src;

  /* Der geschlossene Linkblock ist je nach Seitentyp unterschiedlich lang. Seine echte
     Höhe bestimmt die zwei gleich großen Spacer bis zur 75-%-Linie; beim Öffnen des
     Projektindex bleiben diese Basis-Spacer stehen, sodass dessen Zusatzinhalt die Linie
     nach unten schiebt. Bei offenem Index wird dessen Summary statt des gesamten Details
     vermessen. So bleibt die geschlossene Basishöhe auch bei einem Viewportwechsel korrekt.

     Die zentrale Auto-Spalte ist dagegen von Anfang an so breit wie die Hauptnavigation
     mit aufgeklapptem Projektindex, damit jeder Projekttitel einzeilig bleibt. Native
     details-Inhalte würden sonst beim Öffnen den Track verbreitern und am Ende ihrer
     diskreten content-visibility-Schließtransition wieder freigeben. Eine unsichtbare, nur
     während der synchronen Messung angehängte Kopie liefert beide Maße, ohne den echten
     Disclosure-Zustand oder die Fokus-/Scrollposition anzutasten. */
  var menuGeometryFrame = 0;
  function closedPrimaryGeometry(primary) {
    var shell = document.createElement("details");
    var measuringNav = document.createElement("nav");
    var measuringPrimary = primary.cloneNode(true);
    var measuringDisclosure = measuringPrimary.querySelector(":scope > .project-menu");

    /* Die Messkopie darf keine dokumentweiten `:has(.site-nav[open])`-Zustände wie
       Scroll-Lock, Scrim oder ausgeblendeten Top-Anker auslösen. */
    shell.className = "site-nav is-measuring";
    shell.open = true;
    shell.inert = true;
    shell.setAttribute("aria-hidden", "true");
    shell.style.cssText = "position:fixed;inset:auto;inset-inline-start:-10000px;inset-block-start:0;visibility:hidden";
    measuringNav.style.cssText = [
      "position:fixed",
      "inset:auto",
      "inset-inline-start:-10000px",
      "inset-block-start:0",
      "inline-size:max-content",
      "block-size:auto",
      "display:block",
      "padding:0",
      "border:0",
      "overflow:visible",
      "scrollbar-gutter:auto",
      "transform:none",
      "clip-path:none",
      "visibility:hidden"
    ].join(";");
    if (measuringDisclosure) measuringDisclosure.open = false;
    measuringNav.appendChild(measuringPrimary);
    shell.appendChild(measuringNav);
    document.body.appendChild(shell);
    var rect = measuringPrimary.getBoundingClientRect();
    var geometry = { width: rect.width, height: rect.height };
    if (measuringDisclosure) {
      measuringDisclosure.open = true;
      geometry.width = Math.max(geometry.width, measuringPrimary.getBoundingClientRect().width);
    }
    shell.remove();
    return geometry;
  }
  function syncMenuGeometry() {
    menuGeometryFrame = 0;
    [].slice.call(document.querySelectorAll(".site-nav nav")).forEach(function (nav) {
      var primary = nav.querySelector(".menu-primary");
      if (!primary) return;
      /* Das echte Primary liegt beim Initiallauf in einem geschlossenen details und hat
         deshalb keine messbare Box. Die gerenderte Kopie liefert beide Achsen in einem
         Layoutdurchlauf, unabhängig vom sichtbaren Disclosure-Zustand. */
      var geometry = closedPrimaryGeometry(primary);
      if (geometry.height > 0) {
        nav.style.setProperty("--menu-primary-measured-size", geometry.height + "px");
      }
      if (geometry.width > 0) {
        nav.style.setProperty("--menu-primary-measured-inline-size", geometry.width + "px");
      }
    });
  }
  function requestMenuGeometry() {
    if (!menuGeometryFrame) menuGeometryFrame = requestAnimationFrame(syncMenuGeometry);
  }
  syncMenuGeometry();
  addEventListener("resize", requestMenuGeometry, { passive: true });
  if (document.fonts) {
    document.fonts.ready.then(requestMenuGeometry);
    if (document.fonts.addEventListener) {
      document.fonts.addEventListener("loadingdone", requestMenuGeometry);
    }
  }

  /* Der feste Top-Anker liegt außerhalb des normalen Dokumentflusses. Seine Kontur
     übernimmt deshalb die Farbe der Fläche, die optisch unter seiner Mitte liegt.
     So kann die linke Kante exakt auf der Rasterlinie liegen, ohne dass `difference`
     zwei deckungsgleiche Linien gegenseitig auslöscht. */
  var topAnchors = [].slice.call(document.querySelectorAll(".to-top"));
  if (topAnchors.length) {
    var topAnchorFrame = 0;
    function syncTopAnchorContrast() {
      topAnchorFrame = 0;
      topAnchors.forEach(function (anchor) {
        var rect = anchor.getBoundingClientRect();
        var under = document.elementsFromPoint(
          Math.min(innerWidth - 1, rect.left + 2),
          Math.min(innerHeight - 1, rect.top + rect.height / 2)
        );
        var dark = under.some(function (node) {
          return node !== anchor && !anchor.contains(node) && !!node.closest(".on-dark");
        });
        anchor.classList.toggle("is-on-dark", dark);
      });
    }
    function requestTopAnchorContrast() {
      if (!topAnchorFrame) topAnchorFrame = requestAnimationFrame(syncTopAnchorContrast);
    }
    addEventListener("scroll", requestTopAnchorContrast, { passive: true });
    addEventListener("resize", requestTopAnchorContrast, { passive: true });
    requestTopAnchorContrast();
  }

  /* Die unveränderte Dokumentposition bleibt unabhängig von Reveal-Transforms. */
  function documentTop(node) {
    var top = 0;
    do {
      top += node.offsetTop;
      node = node.offsetParent;
    } while (node);
    return top;
  }

  function startHeadlineReveal() {
    if (reduce.matches) return;
    /* `.motion-reveal` bewegt Texte wie den Projekt-Anleser genauso wie die Headlines,
       ohne den optischen Randausgleich, der an `.motion-heading` hängt. */
    var headings = [].slice.call(document.querySelectorAll(".motion-heading, .motion-reveal"))
      .filter(function (node) { return !node.parentElement.closest(".motion-reveal"); });
    if (!headings.length) return;
    var frame = 0;
    var ENTER = 12;
    var EXIT = 24;

    function update() {
      frame = 0;
      var viewTop = window.scrollY;
      var viewBottom = viewTop + window.innerHeight;
      headings.forEach(function (heading) {
        var top = documentTop(heading);
        var bottom = top + heading.offsetHeight;
        /* Die kompaktere About-Headline wäre beim gemeinsamen 12-px-Trigger fast schon
           animiert, bevor sie bewusst wahrgenommen wird. Ihr Einsatz wandert deshalb
           fluid etwas tiefer in den Viewport; alle anderen Headlines bleiben gleich. */
        var enterInset = heading.closest("#about")
          ? Math.min(120, Math.max(64, window.innerHeight * .1))
          : ENTER;
        var entered = bottom >= viewTop + enterInset && top <= viewBottom - enterInset;
        if (entered) {
          if (!heading.classList.contains("is-visible")) {
            heading.style.setProperty("--motion-enter-direction", top < viewTop ? "-1" : "1");
            heading.classList.add("is-visible");
          }
        } else if (bottom < viewTop - EXIT || top > viewBottom + EXIT) {
          heading.classList.remove("is-visible");
        }
      });
    }

    function requestUpdate() {
      if (!frame) frame = requestAnimationFrame(update);
    }
    addEventListener("scroll", requestUpdate, { passive: true });
    addEventListener("resize", requestUpdate, { passive: true });
    requestUpdate();
  }

  startHeadlineReveal();

  /* Projektseiten, breites Layout: Vom Kopf über die Stationen der Fallstudie und die
     Projektdetails bis zu den Bildern geht jede Scrollgeste (Trackpad-Geste, Mausrad-Klick,
     Wischen, Taste) genau einen Schritt weiter oder zurück; die Seite gleitet weich zur
     nächsten Position. Der Nachschwung einer Geste wird ignoriert, damit nichts
     übersprungen wird. Davor und danach scrollt die Seite normal. Aktiv nur, wenn das CSS
     die Bühne zweispaltig zeigt und keine reduzierte Bewegung gewünscht ist. */
  function startProjectChapters() {
    var stage = document.querySelector(".project-stage");
    if (!stage) return;
    var head = stage.querySelector(".project-intro__head");
    var study = stage.querySelector(".project-content");
    var meta = stage.querySelector(":scope > .project-meta");
    var gallery = stage.nextElementSibling;
    var busyUntil = 0;
    var lastWheel = 0;
    var touchY = null;

    function active() {
      return !reduce.matches &&
        getComputedStyle(stage).gridTemplateColumns.split(" ").length === 2;
    }
    function headerHeight() {
      var header = document.querySelector(".site-header");
      return header ? header.getBoundingClientRect().height : 0;
    }
    function scrollTop(element) {
      return element.getBoundingClientRect().top + window.scrollY - headerHeight();
    }
    // Alle Haltepunkte in Scrollposition: Kopf, jede Station der Bühne, Details, Bilder.
    function positions() {
      var list = [scrollTop(head)];
      if (study) {
        // Die Bühne beginnt unter der Oberkante des Abschnitts (clientTop = Linienstärke).
        var start = scrollTop(study) + study.clientTop;
        var caseStage = study.querySelector(".case-stage");
        var staged = study.classList.contains("is-staged") && caseStage;
        var stops = staged ? caseStage.querySelectorAll(".case-part").length : 0;
        if (staged && stops > 1) {
          var step = (study.offsetHeight - study.clientTop - caseStage.offsetHeight) / (stops - 1);
          for (var i = 0; i < stops; i++) list.push(start + i * step);
        } else {
          list.push(start);
        }
      }
      if (meta && meta.closest(".case-stage") === null) {
        list.push(scrollTop(meta) - (window.innerHeight - headerHeight() - meta.offsetHeight) / 2);
      }
      if (gallery) list.push(scrollTop(gallery));
      return list;
    }
    function target(down) {
      var y = window.scrollY;
      var list = positions();
      if (y > list[list.length - 1] + 2 || y < list[0] - 2) return null;
      if (down) {
        for (var i = 0; i < list.length; i++) if (list[i] > y + 2) return list[i];
      } else {
        for (var j = list.length - 1; j >= 0; j--) if (list[j] < y - 2) return list[j];
      }
      return null;
    }
    function go(down, event) {
      if (!active() || document.querySelector(".site-nav[open]")) return false;
      var now = Date.now();
      if (now < busyUntil) { if (event) event.preventDefault(); return true; }
      var to = target(down);
      if (to === null) return false;
      if (event) event.preventDefault();
      busyUntil = now + 450;
      window.scrollTo({ top: Math.round(to), behavior: "smooth" });
      return true;
    }

    // Eine neue Geste beginnt nach einer kurzen Pause oder wenn die Scrollstärke wieder
    // deutlich ansteigt (der Nachschwung einer Trackpad-Geste wird nur schwächer). Hat eine
    // Geste einen Schritt ausgelöst, schluckt sie ihren Nachschwung, damit nichts
    // übersprungen wird.
    var gestureHandled = false;
    var lastStrength = 0;
    addEventListener("wheel", function (event) {
      if (Math.abs(event.deltaY) < 1 || event.ctrlKey) return;
      var now = Date.now();
      var strength = Math.abs(event.deltaY);
      var rising = strength > lastStrength * 1.6 && strength > 12;
      if (now - lastWheel > 120 || (rising && now >= busyUntil)) gestureHandled = false;
      lastWheel = now;
      lastStrength = strength;
      if (gestureHandled) { event.preventDefault(); return; }
      if (go(event.deltaY > 0, event)) gestureHandled = true;
    }, { passive: false });
    addEventListener("touchstart", function (event) {
      touchY = event.touches.length === 1 ? event.touches[0].clientY : null;
    }, { passive: true });
    addEventListener("touchmove", function (event) {
      if (touchY === null) return;
      var delta = touchY - event.touches[0].clientY;
      if (Math.abs(delta) < 8) { if (active() && target(delta > 0) !== null) event.preventDefault(); return; }
      if (go(delta > 0, event)) touchY = null;
    }, { passive: false });
    addEventListener("keydown", function (event) {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
      var control = event.target instanceof Element &&
        event.target.closest("a, button, summary, input, select, textarea, [contenteditable]");
      // Auf Bedienelementen behalten Leertaste und Pfeile ihre eigene Funktion.
      if (control) return;
      var down = { ArrowDown: true, PageDown: true, " ": !event.shiftKey, ArrowUp: false, PageUp: false }[event.key];
      if (down === undefined) return;
      go(down, event);
    });
  }

  /* Fallstudie: Jeder Absatz (bzw. jede Liste) wird eine eigene Station (.case-part);
     mehrteilige Texte bekommen darunter einen Teilzähler wie „1 von 3“ (das
     Verbindungswort kommt aus den Site-Einstellungen, data-part-of). Im breiten Layout und
     ohne reduzierte Bewegung wird daraus eine Bühne (.is-staged): Sie steht, während man
     scrollt, und zeigt je eine Station; nach jeder Scrollstrecke tauscht der Inhalt mit
     leichtem Lift-up (Übergänge im CSS). Sonst bleibt der Text ein normaler Fluss; ohne
     JavaScript erscheint auch kein Zähler. */
  function startCaseStage() {
    var study = document.querySelector(".project-content[data-part-of]");
    if (!study) return;
    var stageGrid = study.closest(".project-stage");
    var partOf = study.getAttribute("data-part-of");
    var rows = [].slice.call(study.querySelectorAll(".case-row"));
    var stations = [];
    rows.forEach(function (row) {
      var copy = row.querySelector(".case-copy");
      var label = row.querySelector(".case-label");
      if (!copy) return;
      // Leere Absätze aus dem Editor zählen nicht als Station; das Fazit steht nie allein,
      // sondern mit dem letzten Absatz der Lösung in einer Station.
      var all = [].slice.call(copy.children).filter(function (block) {
        return block.textContent.trim() || block.querySelector("img");
      });
      var conclusion = all.filter(function (block) { return block.classList.contains("case-conclusion"); })[0];
      var blocks = all.filter(function (block) { return block !== conclusion; });
      blocks.forEach(function (block, index) {
        var part = document.createElement("div");
        part.className = "case-part";
        copy.insertBefore(part, block);
        // Jede Station trägt ihre Headline mit, damit sie als Ganzes wechselt; die
        // eigentliche Headline bleibt für Screenreader, die Kopie ist ausgeblendet.
        if (label) {
          var heading = document.createElement("p");
          heading.className = "case-part__label";
          heading.setAttribute("aria-hidden", "true");
          heading.textContent = label.textContent.trim();
          part.appendChild(heading);
        }
        part.appendChild(block);
        if (conclusion && index === blocks.length - 1) part.appendChild(conclusion);
        // Die Projektdetails unter dem Statement gehören zu dessen Station.
        var details = row.querySelector(":scope > .project-meta");
        if (details && index === blocks.length - 1) part.appendChild(details);
        if (blocks.length > 1) {
          var count = document.createElement("p");
          count.className = "case-part__count";
          count.setAttribute("aria-hidden", "true");
          count.textContent = (index + 1) + " " + partOf + " " + blocks.length;
          part.appendChild(count);
        }
        stations.push({ row: row, part: part });
      });
    });
    if (!stations.length) return;

    var stage = document.createElement("div");
    stage.className = "case-stage";
    rows.forEach(function (row) { stage.appendChild(row); });
    // Fortschritt der Stationen: zeigt, wo man ist und dass noch etwas folgt.
    var progress = document.createElement("ol");
    progress.className = "case-progress";
    progress.setAttribute("aria-hidden", "true");
    var marks = stations.map(function () {
      var mark = document.createElement("li");
      progress.appendChild(mark);
      return mark;
    });
    stage.appendChild(progress);
    var cue = document.createElement("div");
    cue.className = "scrollcue";
    cue.setAttribute("aria-hidden", "true");
    cue.appendChild(document.createElement("i"));
    stage.appendChild(cue);
    study.appendChild(stage);
    study.style.setProperty("--case-steps", stations.length);

    var frame = 0;
    function staged() {
      return !reduce.matches && stageGrid &&
        getComputedStyle(stageGrid).gridTemplateColumns.split(" ").length === 2;
    }
    function update() {
      frame = 0;
      var on = staged();
      study.classList.toggle("is-staged", on);
      if (!on) return;
      var header = document.querySelector(".site-header");
      var headerHeight = header ? header.getBoundingClientRect().height : 0;
      var travel = study.offsetHeight - study.clientTop - stage.offsetHeight;
      var step = stations.length > 1 ? travel / (stations.length - 1) : 1;
      var position = (window.scrollY - (study.getBoundingClientRect().top + window.scrollY + study.clientTop - headerHeight)) / step;
      var active = Math.max(0, Math.min(stations.length - 1, Math.round(position)));
      var activeRow = stations[active].row;
      var activeRowIndex = rows.indexOf(activeRow);
      rows.forEach(function (row, index) {
        row.classList.toggle("is-active", row === activeRow);
        row.classList.toggle("is-past", index < activeRowIndex);
      });
      stations.forEach(function (station, index) {
        station.part.classList.toggle("is-active", index === active);
        station.part.classList.toggle("is-past", index < active);
        marks[index].classList.toggle("is-active", index === active);
      });
    }
    function request() { if (!frame) frame = requestAnimationFrame(update); }
    addEventListener("scroll", request, { passive: true });
    addEventListener("resize", request, { passive: true });
    if (reduce.addEventListener) reduce.addEventListener("change", request);
    update();
  }

  startCaseStage();
  startProjectChapters();

  /* Optischer Randausgleich der Headlines: Das CSS zieht jede Headline pauschal um die
     linke Vorbreite eines geraden Versalstamms (Saira: .082em) nach links. Schräge und
     runde Glyphen (A, T, V, Y, Z, O …) haben eine kleinere Vorbreite und stünden dann
     vor. Das Skript misst für den ersten Buchstaben JEDER Zeile die Vorbreite in der
     echten Schrift und rückt die Zeile um die Differenz zum Stamm (H) ein. Ohne Skript
     bleibt der pauschale Ausgleich. */
  function alignHeadingInk() {
    var headings = [].slice.call(document.querySelectorAll(".motion-heading"));
    if (!headings.length || !document.createRange) return;
    var context = document.createElement("canvas").getContext("2d");
    if (!context) return;

    function sideBearing(style, character) {
      context.font = style.fontStyle + " " + style.fontWeight + " 1000px " + style.fontFamily;
      return -context.measureText(character).actualBoundingBoxLeft / 1000;
    }

    function unwrap(heading) {
      [].forEach.call(heading.querySelectorAll(".ink-start"), function (span) {
        span.replaceWith(span.firstChild);
      });
      heading.normalize();
    }

    function lineStarts(heading) {
      var walker = document.createTreeWalker(heading, NodeFilter.SHOW_TEXT, {
        acceptNode: function (node) {
          return node.parentNode.closest("svg, .sr-only")
            ? NodeFilter.FILTER_REJECT
            : NodeFilter.FILTER_ACCEPT;
        }
      });
      var starts = [], lastTop = null, range = document.createRange();
      while (walker.nextNode()) {
        var node = walker.currentNode;
        for (var i = 0; i < node.length; i++) {
          if (/\s/.test(node.data[i])) continue;
          range.setStart(node, i);
          range.setEnd(node, i + 1);
          // Nach einer Silbentrennung liefert das erste Zeichen der neuen Zeile zwei
          // Rechtecke (Trennstrich am Zeilenende + Zeichen); maßgeblich ist das letzte.
          var rects = range.getClientRects();
          var rect = rects[rects.length - 1];
          if (!rect) continue;
          if (lastTop === null || rect.top > lastTop + rect.height / 2) {
            starts.push({ node: node, offset: i });
          }
          lastTop = rect.top;
        }
      }
      return starts;
    }

    function shiftFor(style, character) {
      var upper = style.textTransform === "uppercase";
      var glyph = upper ? character.toUpperCase() : character;
      return (sideBearing(style, "H") - sideBearing(style, glyph)) * parseFloat(style.fontSize);
    }

    // Das Einrücken kann den (ausgeglichenen) Zeilenfall verschieben. Deshalb wird so lange
    // nachkorrigiert, bis jede Zeile genau dann mit einem Ausgleich beginnt, wenn sie einen
    // braucht — höchstens viermal.
    function align(heading) {
      unwrap(heading);
      var style = getComputedStyle(heading);
      for (var pass = 0; pass < 4; pass++) {
        var starts = lineStarts(heading);
        var changed = false;
        var keep = [];
        for (var i = starts.length - 1; i >= 0; i--) {
          var start = starts[i];
          var wrapper = start.node.parentNode;
          if (wrapper.classList && wrapper.classList.contains("ink-start")) {
            keep.push(wrapper);
            continue;
          }
          var shift = shiftFor(style, start.node.data[start.offset]);
          if (Math.abs(shift) < .5) continue;
          var glyph = start.node.splitText(start.offset);
          glyph.splitText(1);
          var span = document.createElement("span");
          span.className = "ink-start";
          span.style.marginInlineStart = shift.toFixed(2) + "px";
          glyph.replaceWith(span);
          span.appendChild(glyph);
          keep.push(span);
          changed = true;
        }
        [].forEach.call(heading.querySelectorAll(".ink-start"), function (span) {
          if (keep.indexOf(span) === -1) {
            span.replaceWith(span.firstChild);
            changed = true;
          }
        });
        heading.normalize();
        if (!changed) break;
      }
    }

    var frame = 0;
    function alignAll() {
      frame = 0;
      headings.forEach(align);
    }
    function requestAlign() {
      if (!frame) frame = requestAnimationFrame(alignAll);
    }
    var fontsReady = document.fonts && document.fonts.ready;
    if (fontsReady) fontsReady.then(requestAlign, requestAlign);
    else requestAlign();
    addEventListener("resize", requestAlign, { passive: true });
  }

  alignHeadingInk();

  /* Die Leistungsinhalte laufen zeitbasiert, damit ein schneller Scrollsprung ihre
     Bewegung nicht vorspult. Beim Herunterscrollen startet die normale Leistungen-Headline
     dieselbe Welle; die Astagina-Handschrift gehört ausdrücklich nicht zu diesem Gate. */
  function startServiceMotion() {
    var cards = [].slice.call(document.querySelectorAll(".svc"));
    if (!cards.length || reduce.matches || !("IntersectionObserver" in window)) return;

    var heading = document.querySelector("#leistungen .motion-heading");
    var headlineReady = !heading;
    var headlineTimer = 0;
    var fallbackTimer = 0;
    var pending = new Set();
    var states = new WeakMap();
    var direction = 1;
    var previousY = window.scrollY;

    function setDirection() {
      var nextY = window.scrollY;
      if (Math.abs(nextY - previousY) > 1) direction = nextY > previousY ? 1 : -1;
      previousY = nextY;
    }
    addEventListener("scroll", setDirection, { passive: true });

    function orderFor(card, scrollDirection) {
      var index = cards.indexOf(card);
      return scrollDirection > 0 ? index : cards.length - 1 - index;
    }

    function enter(card, scrollDirection) {
      var order = orderFor(card, scrollDirection);
      card.style.setProperty(
        "--service-enter-y",
        scrollDirection > 0
          ? "var(--service-travel)"
          : "calc(-1 * var(--service-travel))"
      );
      card.style.setProperty("--service-card-delay", order * 85 + "ms");
      card.classList.remove("is-service-leaving");
      card.classList.add("is-service-entering");
      states.set(card, "visible");
    }

    function leave(card, scrollDirection) {
      var order = orderFor(card, scrollDirection);
      pending.delete(card);
      card.style.setProperty(
        "--service-exit-y",
        scrollDirection > 0
          ? "calc(-1 * var(--service-travel))"
          : "var(--service-travel)"
      );
      card.style.setProperty("--service-leave-delay", order * 55 + "ms");
      card.classList.remove("is-service-entering");
      card.classList.add("is-service-leaving");
      states.set(card, "outside");
    }

    function releasePending() {
      headlineReady = true;
      clearTimeout(fallbackTimer);
      fallbackTimer = 0;
      pending.forEach(function (card) { enter(card, 1); });
      pending.clear();
    }

    function releaseShortlyAfterHeadline() {
      clearTimeout(headlineTimer);
      headlineTimer = setTimeout(releasePending, 0);
    }

    /* Die Kacheln liegen beim Start der Headline auf großen Screens oft noch knapp
       unterhalb ihrer eigenen 20-%-Schwelle. Sie werden deshalb schon hier vorgemerkt,
       damit nach dem Headline-Ende keine zweite, scrollabhängige Wartephase entsteht.
       Die horizontale Prüfung lässt im mobilen Reel nur tatsächlich nahe Kacheln zu. */
    function armNearbyCards() {
      cards.forEach(function (card) {
        var rect = card.getBoundingClientRect();
        var nearVertically = rect.top < innerHeight * 1.8 && rect.bottom > -innerHeight * .2;
        var nearHorizontally = rect.left < innerWidth * 1.1 && rect.right > -innerWidth * .1;
        if (nearVertically && nearHorizontally && states.get(card) !== "visible") {
          pending.add(card);
        }
      });
      if (pending.size && !fallbackTimer) {
        fallbackTimer = setTimeout(releasePending, 1700);
      }
    }

    if (heading) {
      heading.addEventListener("animationstart", function (event) {
        if (event.animationName !== "headline-reveal") return;
        headlineReady = false;
        clearTimeout(headlineTimer);
        if (direction > 0) {
          armNearbyCards();
          /* Die hohen Rasterzellen tragen ihren Inhalt mittig. Ein Start erst am Ende
             der Headline wirkte deshalb trotz 0-ms-Gap räumlich verspätet. */
          releasePending();
        }
      });
      heading.addEventListener("animationend", function (event) {
        if (event.animationName === "headline-reveal") releaseShortlyAfterHeadline();
      });
    }

    root.classList.add("service-motion-ready");
    var thresholds = [0, .2, .75, 1];
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var card = entry.target;
        var rect = entry.boundingClientRect;
        var state = states.get(card) || "outside";

        if (entry.intersectionRatio >= .2 && state !== "visible") {
          if (direction > 0 && !headlineReady) {
            pending.add(card);
            if (!fallbackTimer) fallbackTimer = setTimeout(releasePending, 1700);
          } else {
            enter(card, direction);
          }
          return;
        }

        var leavesAtTop = direction > 0 && rect.top < 0;
        var leavesAtBottom = direction < 0 && rect.bottom > innerHeight;
        if (state === "visible" && entry.intersectionRatio <= .75 &&
            (leavesAtTop || leavesAtBottom)) {
          leave(card, direction);
        }
      });
    }, { threshold: thresholds });

    cards.forEach(function (card) { observer.observe(card); });
  }

  startServiceMotion();

  /* Im About-Akkordeon bewegen sich ausschließlich Titel und Subline. Das Plus/Minus
     bleibt als festes Bedienelement unangetastet. */
  function startAboutMotion() {
    var rows = [].slice.call(document.querySelectorAll("#about .me-row"));
    if (!rows.length || reduce.matches || !("IntersectionObserver" in window)) return;

    var heading = document.querySelector("#about .motion-heading");
    var rowGrid = document.querySelector("#about .me-text");
    var headlineReady = !heading;
    var headlineTimer = 0;
    var fallbackTimer = 0;
    var pending = new Set();
    var states = new WeakMap();
    var direction = 1;
    var previousY = window.scrollY;

    function setDirection() {
      var nextY = window.scrollY;
      if (Math.abs(nextY - previousY) > 1) direction = nextY > previousY ? 1 : -1;
      previousY = nextY;
    }
    addEventListener("scroll", setDirection, { passive: true });

    function orderFor(row, scrollDirection) {
      var index = rows.indexOf(row);
      return scrollDirection > 0 ? index : rows.length - 1 - index;
    }

    function enter(row, scrollDirection) {
      var order = orderFor(row, scrollDirection);
      row.style.setProperty(
        "--about-enter-y",
        scrollDirection > 0 ? "var(--about-travel)" : "calc(-1 * var(--about-travel))"
      );
      row.style.setProperty("--about-row-delay", order * 110 + "ms");
      row.classList.remove("is-about-leaving");
      row.classList.add("is-about-entering");
      states.set(row, "visible");
    }

    function leave(row, scrollDirection) {
      var order = orderFor(row, scrollDirection);
      pending.delete(row);
      row.style.setProperty(
        "--about-exit-y",
        scrollDirection > 0 ? "calc(-1 * var(--about-travel))" : "var(--about-travel)"
      );
      row.style.setProperty("--about-leave-delay", order * 70 + "ms");
      row.classList.remove("is-about-entering");
      row.classList.add("is-about-leaving");
      states.set(row, "outside");
      if (rowGrid) rowGrid.classList.remove("is-about-stretching");
    }

    function releasePending() {
      headlineReady = true;
      clearTimeout(fallbackTimer);
      fallbackTimer = 0;
      pending.forEach(function (row) { enter(row, 1); });
      pending.clear();
    }

    function armNearbyRows() {
      rows.forEach(function (row) {
        var rect = row.getBoundingClientRect();
        if (rect.top < innerHeight * 1.8 && rect.bottom > -innerHeight * .2 &&
            states.get(row) !== "visible") {
          pending.add(row);
        }
      });
      if (pending.size && !fallbackTimer) {
        fallbackTimer = setTimeout(releasePending, 1700);
      }
    }

    if (heading) {
      heading.addEventListener("animationstart", function (event) {
        if (event.animationName !== "headline-reveal") return;
        headlineReady = false;
        clearTimeout(headlineTimer);
        if (direction > 0) {
          armNearbyRows();
          if (rowGrid) rowGrid.classList.add("is-about-stretching");
          /* Die Textwelle setzt schon in der ruhigen Endphase der Headline ein. Dadurch
             liest sich die parallel mögliche Handschrift nicht als zusätzliche Pause. */
          headlineTimer = setTimeout(releasePending, 720);
        }
      });
      heading.addEventListener("animationend", function (event) {
        if (event.animationName !== "headline-reveal") return;
        clearTimeout(headlineTimer);
        headlineTimer = setTimeout(releasePending, 0);
      });
    }

    root.classList.add("about-motion-ready");
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var row = entry.target;
        var rect = entry.boundingClientRect;
        var state = states.get(row) || "outside";

        if (entry.intersectionRatio >= .2 && state !== "visible") {
          if (direction > 0 && !headlineReady) {
            pending.add(row);
            if (!fallbackTimer) fallbackTimer = setTimeout(releasePending, 1700);
          } else {
            enter(row, direction);
          }
          return;
        }

        var leavesAtBottom = direction < 0 && rect.bottom > innerHeight;
        /* Beim Hinunterscrollen bleibt der abgeschlossene Eintrittszustand bestehen.
           Ein `leave()` oberhalb des Viewports würde mobil das für die Textreise
           reservierte Padding wieder von 0 auf --about-travel animieren: drei bereits
           unter dem festen Header verborgene Zeilen vergrößerten das Dokument dadurch
           zusammen um 96 px, worauf Scroll Anchoring scrollY bildweise nachführte.
           Erst wenn die Zeile beim Hinaufscrollen UNTER dem Viewport austritt, wird sie
           für den nächsten Eintritt zurückgesetzt; dort kann ihre Höhenänderung den
           aktuellen Bildausschnitt nicht verschieben. */
        if (state === "visible" && entry.intersectionRatio <= .75 && leavesAtBottom) {
          leave(row, direction);
        }
      });
    }, { threshold: [0, .2, .75, 1] });

    rows.forEach(function (row) { observer.observe(row); });
  }

  startAboutMotion();

  /* Die sichtbare Ebene stammt aus dem bewährten CV-Composer: echte Font-Outlines,
     nicht erneut gerenderter SVG-Text. Ohne diese Daten bleibt das Original unangetastet. */
  if (window.PORTFOLIO_HANDWRITING) glyphs = window.PORTFOLIO_HANDWRITING;

  function handwritingGeometry(svg, element) {
    if (!element) return null;
    var reference = element.getAttribute("href");
    if (!reference) return element;
    if (reference.charAt(0) !== "#") return null;
    return svg.getElementById(reference.slice(1));
  }

  /* Astaginas Apostroph folgt im Rohfont unmittelbar auf den weit ausladenden zweiten
     t-Strich. Nur diese eine Glyphe bekommt etwas Luft; das anschließende „s me“ bleibt
     exakt an seiner originalen Position. Outline und Maskenpfad werden gemeinsam
     verschoben, damit Endbild und Schreibspur deckungsgleich bleiben. */
  function spaceThatsMeApostrophe(svg) {
    var shift = 320;
    var outlineIndex = 6;
    var penIndex = 4;

    /* Die generierten Astagina-Konturen beginnen jeden Teilpfad mit einem absoluten
       M-Punkt, alle weiteren Punkte sind relative l-Schritte. Nur die x-Koordinate des
       M-Punkts zu ändern verschiebt damit den ganzen Teilpfad und hält den originalen
       Compound-Path intakt; zusätzliche SVG-Elemente würden an Masken und Konturen
       sichtbare Kappen bzw. Nahtartefakte erzeugen. */
    var number = "(-?(?:\\d+\\.?\\d*|\\.\\d+))";
    var moveTo = new RegExp("M\\s*" + number + "\\s*" + number, "g");
    function shiftPathX(data) {
      return data.replace(moveTo, function (_, x, y) {
        return "M" + (parseFloat(x) + shift).toFixed(1) + " " + y;
      });
    }

    var shifted = new Set();
    svg.querySelectorAll(".hw-outline, .hw-ink, .hw-ink-edge").forEach(function (element) {
      var path = handwritingGeometry(svg, element);
      if (!path || shifted.has(path)) return;
      shifted.add(path);
      var parts = (path.getAttribute("d") || "").match(/M[^M]+/g);
      if (!parts || parts.length <= outlineIndex) return;
      parts[outlineIndex] = shiftPathX(parts[outlineIndex]);
      path.setAttribute("d", parts.join(" "));
    });

    svg.querySelectorAll("mask").forEach(function (mask) {
      var element = mask.querySelectorAll(".hw-pen, .hw-outline-pen")[penIndex];
      var pen = element && handwritingGeometry(svg, element);
      if (pen && !shifted.has(pen)) {
        shifted.add(pen);
        pen.setAttribute("d", shiftPathX(pen.getAttribute("d")));
      }
    });
  }

  function prepareScriptText() {
    var replaced = [];
    document.querySelectorAll("svg.scr > text").forEach(function (textNode) {
      var phrase = textNode.textContent.trim();
      if (!glyphs[phrase]) return;
      var old = textNode.parentElement;
      var shell = document.createElement("template");
      var startAligned = !!old.closest(".katha");
      shell.innerHTML = '<span class="scr hw-label' + (startAligned ? ' hw-start' : '') +
        '" aria-hidden="true">' + glyphs[phrase] + '</span>';
      var next = shell.content.firstElementChild;
      old.classList.add("hw-final");
      old.replaceWith(next);
      next.insertBefore(old, next.firstChild);
      var overlay = next.querySelector(".hw-svg");
      overlay._hwPhrase = phrase;
      if (phrase === "that's me") {
        overlay.classList.add("hw-clean-joins");
        spaceThatsMeApostrophe(overlay);
      }
      replaced.push(overlay);
    });
    return replaced;
  }

  function writeHandwriting(svgs) {
    if (!svgs.length) {
      root.classList.remove("js-hw");
      return;
    }
    svgs = svgs.filter(function (svg) {
      var pens = [].slice.call(svg.querySelectorAll(".hw-pen"));
      var outlinePens = [].slice.call(svg.querySelectorAll(".hw-outline-pen"));
      var geometries = pens.map(function (pen, penIndex) {
        return [handwritingGeometry(svg, pen), handwritingGeometry(svg, outlinePens[penIndex])];
      });
      var valid = pens.length === outlinePens.length && geometries.every(function (pair) {
        return pair[0] && pair[1];
      });
      if (!valid) {
        var label = svg.closest(".hw-label");
        if (label) label.classList.add("hw-fallback");
        return false;
      }
      pens.forEach(function (pen, penIndex) {
        var length = geometries[penIndex][0].getTotalLength();
        pen.style.setProperty("--L", length);
        outlinePens[penIndex].style.setProperty("--L", length);
      });
      return true;
    });
    svgs.forEach(function (svg, index) { svg._hwIndex = index; });

    if (reduce.matches) {
      root.classList.remove("js-hw");
      return;
    }

    var SPEED = 4800;
    var CAP = 1.7;
    var MIN = .55;
    var OVERLAP = .82;
    var GAP = .08;
    var queue = [];
    var playing = false;

    function enqueue(svgsToQueue) {
      Array.prototype.push.apply(queue, svgsToQueue);
      queue.sort(function (a, b) { return a._hwIndex - b._hwIndex; });
      pump();
    }

    function schedule(svg) {
      var pens = [].slice.call(svg.querySelectorAll(".hw-pen"));
      var outlinePens = [].slice.call(svg.querySelectorAll(".hw-outline-pen"));
      var lengths = pens.map(function (pen) {
        return parseFloat(pen.style.getPropertyValue("--L")) || 0;
      });
      var total = lengths.reduce(function (sum, length) { return sum + length; }, 0) || 1;
      var target = Math.min(CAP, Math.max(MIN, total / SPEED));
      var offset = 0;
      var end = 0;
      pens.forEach(function (pen, index) {
        var duration = (lengths[index] / total) * target / OVERLAP;
        pen.style.setProperty("--hw-duration", duration + "s");
        pen.style.setProperty("--hw-delay", offset + "s");
        if (outlinePens[index]) {
          outlinePens[index].style.setProperty("--hw-duration", duration + "s");
          outlinePens[index].style.setProperty("--hw-delay", offset + "s");
        }
        end = offset + duration;
        offset += duration * OVERLAP;
      });
      return end;
    }

    function pump() {
      if (playing || !queue.length) return;
      playing = true;
      var svg = queue.shift();
      if (svg._hwEligible && !svg._hwEligible()) {
        rearm(svg);
        playing = false;
        pump();
        return;
      }
      var duration = schedule(svg);
      svg.classList.add("hw-go");
      setTimeout(function () {
        playing = false;
        pump();
      }, (duration + GAP) * 1000);
    }

    var seen = new Set();
    var headingGroups = new Map();
    svgs.forEach(function (svg) {
      var heading = svg.closest(".motion-heading");
      if (!heading) {
        var section = svg.closest("section");
        heading = section ? section.querySelector(".motion-heading") : null;
      }
      if (!heading) {
        /* Ein später ergänzter freier Vermerk bleibt fail-open sichtbar. */
        svg.classList.add("hw-go");
        return;
      }
      svg._hwEligible = function () {
        return headingFullyVisible(heading);
      };
      if (!headingGroups.has(heading)) headingGroups.set(heading, []);
      headingGroups.get(heading).push(svg);
    });

    /* Ausschließlich die vollständig sichtbare Headline gibt ihre Vermerke frei. Die
       gemeinsame Queue hält mehrere gleichzeitig qualifizierte Headlines seriell. */
    var scanFrame = 0;
    var header = document.querySelector("header.site, .site-header");

    function headingFullyVisible(heading) {
      var headerHeight = header ? header.offsetHeight : 0;
      var viewTop = window.scrollY + headerHeight;
      var viewBottom = window.scrollY + window.innerHeight;
      var top = documentTop(heading);
      var bottom = top + heading.offsetHeight;
      var availableHeight = Math.max(0, viewBottom - viewTop);
      if (heading.offsetHeight > availableHeight) {
        return top <= viewTop && bottom >= viewBottom;
      }
      return top >= viewTop && bottom <= viewBottom;
    }

    function scanHeadings() {
      scanFrame = 0;
      headingGroups.forEach(function (group, heading) {
        var pending = group.filter(function (svg) { return !seen.has(svg); });
        if (!pending.length || !headingFullyVisible(heading)) return;
        pending.forEach(function (svg) { seen.add(svg); });
        enqueue(pending);
      });
    }

    function requestHeadingScan() {
      if (!scanFrame) scanFrame = requestAnimationFrame(scanHeadings);
    }
    function rearm(svg) {
      seen.delete(svg);
      requestHeadingScan();
    }
    addEventListener("scroll", requestHeadingScan, { passive: true });
    addEventListener("resize", requestHeadingScan, { passive: true });
    requestHeadingScan();
  }

  var handwritingStarted = false;
  function start() {
    if (reduce.matches || handwritingStarted || !window.PORTFOLIO_HANDWRITING) return;
    handwritingStarted = true;
    glyphs = window.PORTFOLIO_HANDWRITING;
    var ready = document.fonts && document.fonts.load
      ? document.fonts.load('400 40px "Astagina"')
      : Promise.resolve();
    Promise.resolve(ready).then(function () {
      var svgs = prepareScriptText();
      if (!svgs.length) return;
      root.classList.add("js-hw");
      writeHandwriting(svgs);
    }).catch(function () {
      root.classList.remove("js-hw");
    });
  }

  window.addEventListener("portfolio:handwriting-ready", start);
  if (window.PORTFOLIO_HANDWRITING) start();
  else if (handwritingSource) {
    /* Nur die optionale Schreibanimation braucht die großen Pfaddaten. Die vorhandenen
       SVG-Texte bleiben bis zum erfolgreichen Laden sichtbar, auch bei Netzfehlern. */
    var handwritingRequested = false;
    var handwritingObserver;
    function loadHandwriting() {
      if (reduce.matches || handwritingRequested) return;
      handwritingRequested = true;
      if (handwritingObserver) handwritingObserver.disconnect();
      var script = document.createElement("script");
      var phrases = [].map.call(document.querySelectorAll("svg.scr > text"), function (text) {
        return text.textContent.trim();
      });
      var contactOnly = phrases.length && phrases.every(function (phrase) { return phrase === "tell me more"; });
      var configuredSource = handwritingScript.getAttribute(contactOnly
        ? "data-handwriting-contact-src" : "data-handwriting-src");
      script.src = configuredSource || new URL(contactOnly
        ? "handwriting-contact.js" : "handwriting-glyphs.js", handwritingSource).href;
      script.async = true;
      script.onload = function () {
        window.dispatchEvent(new Event("portfolio:handwriting-ready"));
      };
      script.onerror = function () { root.classList.remove("js-hw"); };
      document.head.appendChild(script);
    }
    function observeHandwriting() {
      if (reduce.matches || handwritingRequested || handwritingObserver) return;
      var targets = document.querySelectorAll("svg.scr");
      if (!targets.length) return;
      if (!("IntersectionObserver" in window)) { loadHandwriting(); return; }
      handwritingObserver = new IntersectionObserver(function (entries) {
        if (entries.some(function (entry) { return entry.isIntersecting; })) loadHandwriting();
      }, { rootMargin: "100px" });
      targets.forEach(function (target) { handwritingObserver.observe(target); });
    }
    function syncHandwritingPreference() {
      if (reduce.matches) return;
      if (window.PORTFOLIO_HANDWRITING) start();
      else {
        if (handwritingObserver) handwritingObserver.disconnect();
        handwritingObserver = null;
        observeHandwriting();
      }
    }
    if (reduce.addEventListener) reduce.addEventListener("change", syncHandwritingPreference);
    else reduce.addListener(syncHandwritingPreference);
    observeHandwriting();
  }
})();

/* Der sichtbare Top-Anker bleibt ein echter Hash-Link und funktioniert deshalb auch ohne
   JavaScript. Mit JavaScript bekommt er eine verlässliche Scroll-up-Bewegung, unabhängig
   davon, wie der jeweilige Browser native Fragmentnavigation animiert. */
(function () {
  "use strict";

  var reduce = matchMedia("(prefers-reduced-motion: reduce)");
  document.addEventListener("click", function (event) {
    var link = event.target.closest && event.target.closest(".to-top");
    if (!link || event.defaultPrevented || event.button !== 0 ||
        event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

    var url = new URL(link.href, location.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname) return;

    event.preventDefault();
    if (location.hash !== url.hash) history.pushState(null, "", url.hash);
    window.scrollTo({ top: 0, behavior: reduce.matches ? "auto" : "smooth" });
  });
})();
