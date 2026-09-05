/* Shared portfolio motion: headline reveal + traced Astagina writing. */
(function () {
  "use strict";

  var root = document.documentElement;
  var reduce = matchMedia("(prefers-reduced-motion: reduce)");
  var glyphs = {};

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
    var headings = [].slice.call(document.querySelectorAll(".motion-heading"));
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
        var entered = bottom >= viewTop + ENTER && top <= viewBottom - ENTER;
        if (entered) {
          if (!heading.classList.contains("is-visible")) {
            heading.style.setProperty(
              "--headline-enter-y",
              top < viewTop ? "-.42em" : ".42em"
            );
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

  /* Die sichtbare Ebene stammt aus dem bewährten CV-Composer: echte Font-Outlines,
     nicht erneut gerenderter SVG-Text. Ohne diese Daten bleibt das Original unangetastet. */
  if (window.PORTFOLIO_HANDWRITING) glyphs = window.PORTFOLIO_HANDWRITING;

  /* Astaginas Apostroph folgt im Rohfont unmittelbar auf den weit ausladenden zweiten
     t-Strich. Nur diese eine Glyphe bekommt etwas Luft; das anschließende „s me“ bleibt
     exakt an seiner originalen Position. Outline und Maskenpfad werden gemeinsam
     verschoben, damit Endbild und Schreibspur deckungsgleich bleiben. */
  function spaceThatsMeApostrophe(svg) {
    var shift = 320;
    var outlineIndex = 6;
    var penIndex = 4;

    /* Die generierten Astagina-Konturen bestehen hier ausschließlich aus absoluten
       M-/L-Punkten. Die x-Koordinate direkt im Teilpfad zu ändern hält den originalen
       Compound-Path intakt; zusätzliche SVG-Elemente würden an Masken und Konturen
       sichtbare Kappen bzw. Nahtartefakte erzeugen. */
    function shiftPathX(data) {
      return data.replace(/([ML])\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)/g,
        function (_, command, x, y) {
          return command + " " + (parseFloat(x) + shift).toFixed(1) + " " + y;
        });
    }

    svg.querySelectorAll(".hw-outline, .hw-ink, .hw-ink-edge").forEach(function (path) {
      var parts = (path.getAttribute("d") || "").match(/M\s[^M]+/g);
      if (!parts || parts.length <= outlineIndex) return;
      parts[outlineIndex] = shiftPathX(parts[outlineIndex]);
      path.setAttribute("d", parts.join(" "));
    });

    svg.querySelectorAll("mask").forEach(function (mask) {
      var pen = mask.querySelectorAll("path")[penIndex];
      if (pen) pen.setAttribute("d", shiftPathX(pen.getAttribute("d")));
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
    svgs.forEach(function (svg, index) {
      svg._hwIndex = index;
      var outlinePens = svg.querySelectorAll(".hw-outline-pen");
      svg.querySelectorAll(".hw-pen").forEach(function (pen, penIndex) {
        var length = pen.getTotalLength();
        pen.style.setProperty("--L", length);
        if (outlinePens[penIndex]) outlinePens[penIndex].style.setProperty("--L", length);
      });
    });

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

  function start() {
    if (reduce.matches) return;
    var ready = document.fonts && document.fonts.load
      ? document.fonts.load('400 40px "Astagina"')
      : Promise.resolve();
    Promise.resolve(ready).then(function () {
      var svgs = prepareScriptText();
      if (!svgs.length) return;
      root.classList.add("js-hw");
      writeHandwriting(svgs);
    });
  }

  if (window.PORTFOLIO_HANDWRITING) start();
})();
