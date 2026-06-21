// homepage/homepage/static/handwriting/handwriting.js
(function () {
  "use strict";
  var root = document.documentElement;
  root.classList.add("js-hw");
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SPEED = 4200; // font units per second (matches the validated words.html feel)

  var svgs = [].slice.call(document.querySelectorAll(".hw-svg"));
  svgs.forEach(function (svg) {
    svg.querySelectorAll(".hw-pen").forEach(function (p) {
      p.style.setProperty("--L", p.getTotalLength());
    });
    if (!reduce) svg.classList.add("hw-pending"); // hide until scrolled into view
  });
  if (reduce || !("IntersectionObserver" in window)) return; // final state stays visible

  function write(svg) {
    var off = 0;
    svg.querySelectorAll(".hw-pen").forEach(function (p) {
      var L = parseFloat(p.style.getPropertyValue("--L")) || 0;
      var dur = Math.max(0.22, L / SPEED);
      p.style.animationDuration = dur + "s";
      p.style.animationDelay = off + "s";
      off += dur * 0.82;
    });
    svg.classList.remove("hw-pending");
    svg.classList.add("hw-go");
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { write(e.target); io.unobserve(e.target); }
    });
  }, { threshold: 0.55 });
  svgs.forEach(function (s) { io.observe(s); });
})();
