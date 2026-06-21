from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


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
