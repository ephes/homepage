import io
from pathlib import Path

import numpy as np
from PIL import Image

from homepage.handwriting.compose import compose_label

ROOT = Path(__file__).resolve().parents[2]


def _dark_px(shot):
    """Count near-black (revealed ink) pixels in a PNG screenshot."""
    return int((np.array(Image.open(io.BytesIO(shot)).convert("L")) < 128).sum())


def _reveal_pens(page, dashoffset):
    """Set every pen's --L = its length and freeze stroke-dashoffset.

    dashoffset 0 == fully written; "L - 1" == only just started (1 unit drawn).
    """
    page.eval_on_selector_all(
        ".hw-pen",
        "(els, off) => els.forEach(p => {"
        "  const L = p.getTotalLength();"
        "  p.style.setProperty('--L', L);"
        "  p.style.strokeDashoffset = off === 'start' ? (L - 1) : 0;"
        "})",
        dashoffset,
    )


def test_pens_reveal_no_ink_dot_when_a_stroke_just_starts(page):
    """Regression: a stroke that has only just begun must not reveal an ink blob.

    The reveal mask animates stroke-dashoffset from L to 0. With
    `stroke-linecap: round`, a stroke at the very start of its animation renders
    a round cap (a full dot, diameter = stroke-width) at its origin, which the
    mask exposes as a black dot floating ahead of the writing — most visible on
    mobile. `butt` caps draw nothing until the stroke has real length, so the
    just-started state reveals (almost) no ink. We assert the just-started state
    exposes a negligible fraction of the fully-written ink.
    """
    svg = compose_label("Work Experience")
    assert svg is not None
    page.set_viewport_size({"width": 2400, "height": 420})
    page.set_content(
        f"<!doctype html><meta charset=utf-8>"
        f"<style>body{{margin:20px;background:#fff;color:#000;font-size:140px}}</style>"
        f"<body>{svg}"
    )
    page.add_style_tag(path=str(ROOT / "static/handwriting/handwriting.css"))

    _reveal_pens(page, "start")
    just_started = _dark_px(page.locator(".hw-svg").screenshot())
    _reveal_pens(page, 0)
    written = _dark_px(page.locator(".hw-svg").screenshot())

    assert written > 5000, "fully-written label should reveal substantial ink"
    # round caps expose ~3.6% here (the dots); butt caps expose ~0%.
    assert just_started < 0.005 * written, (
        f"just-started strokes reveal too much ink ({just_started}px of "
        f"{written}px written) — round-cap dots are leaking through the mask"
    )


def _animation_durations(page):
    return page.evaluate(
        """
        Array.from(document.querySelectorAll(".hw-svg.hw-go .hw-pen")).map(function (pen) {
          return getComputedStyle(pen).animationDuration;
        })
        """
    )


def _label(text):
    return f"""
    <span class="hw-label" data-hw>
      <span class="hw-text">{text}</span>
      <svg class="hw-svg" viewBox="0 0 120 20" aria-hidden="true" focusable="false">
        <g class="hw-ink-group">
          <path class="hw-ink" d="M 0 0 H 100 V 20 H 0 Z"></path>
        </g>
        <path class="hw-pen" d="M 0 10 L 100 10" style="stroke-width:20"></path>
      </svg>
    </span>
    """


def _load_test_page(page):
    page.set_viewport_size({"width": 800, "height": 500})
    page.set_content(
        f"""
        <!doctype html>
        <html>
          <head>
            <script>
              window.__hwEvents = [];
              document.addEventListener("animationstart", function (event) {{
                var label = event.target.closest(".hw-label");
                if (label) {{
                  window.__hwEvents.push(label.querySelector(".hw-text").textContent);
                }}
              }}, true);
            </script>
          </head>
          <body>
            <main>
              <section style="height: 700px">{_label("First")}</section>
              <section style="height: 700px">{_label("Second")}</section>
            </main>
          </body>
        </html>
        """
    )
    page.evaluate("document.documentElement.setAttribute('data-hw-replay-cooldown', '2000')")
    page.add_style_tag(path=str(ROOT / "static/handwriting/handwriting.css"))
    page.add_script_tag(path=str(ROOT / "static/handwriting/handwriting.js"))


def test_handwriting_labels_replay_at_top_only_after_cooldown(page):
    _load_test_page(page)

    page.wait_for_function("window.__hwEvents.includes('First')")
    page.wait_for_timeout(900)
    assert page.evaluate("Array.from(new Set(window.__hwEvents))") == ["First"]
    assert any(duration != "0s" for duration in _animation_durations(page))

    page.evaluate("window.__hwEvents = []")
    page.evaluate("window.scrollTo(0, 700)")
    page.wait_for_function("window.__hwEvents.includes('Second')")
    page.wait_for_timeout(900)
    assert page.evaluate("Array.from(new Set(window.__hwEvents))") == ["Second"]

    page.evaluate("window.__hwEvents = []")
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(400)
    assert page.evaluate("window.__hwEvents") == []

    page.wait_for_timeout(2100)
    page.evaluate("window.scrollTo(0, 700)")
    page.wait_for_timeout(100)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_function("window.__hwEvents.includes('First')")
    page.wait_for_timeout(900)
    assert page.evaluate("Array.from(new Set(window.__hwEvents))") == ["First"]
    assert any(duration != "0s" for duration in _animation_durations(page))

    page.evaluate("window.__hwEvents = []")
    page.evaluate("window.scrollTo(0, 700)")
    page.wait_for_timeout(100)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(400)

    assert page.evaluate("window.__hwEvents") == []


def test_handwriting_labels_replay_when_returning_to_tab_after_cooldown(page):
    _load_test_page(page)

    page.wait_for_function("window.__hwEvents.includes('First')")
    page.wait_for_timeout(900)
    page.evaluate("window.__hwEvents = []")

    page.wait_for_timeout(2100)
    page.evaluate(
        """
        Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
        document.dispatchEvent(new Event("visibilitychange"));
        Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
        document.dispatchEvent(new Event("visibilitychange"));
        """
    )
    page.wait_for_function("window.__hwEvents.includes('First')")
    page.wait_for_timeout(900)
    assert page.evaluate("Array.from(new Set(window.__hwEvents))") == ["First"]
    assert any(duration != "0s" for duration in _animation_durations(page))

    page.evaluate("window.__hwEvents = []")
    page.evaluate(
        """
        Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
        document.dispatchEvent(new Event("visibilitychange"));
        Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
        document.dispatchEvent(new Event("visibilitychange"));
        """
    )
    page.wait_for_timeout(400)

    assert page.evaluate("window.__hwEvents") == []
