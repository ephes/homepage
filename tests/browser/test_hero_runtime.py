"""Run the shipped hero script with synthetic DOM and controlled browser boundaries."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

ASSETS = Path(__file__).resolve().parents[2] / "homepage/portfolio/static/portfolio/prototype"

# Only the WebGL calls used by the hero are substituted. Canvas2D, DOM, promises,
# CSS and event dispatch stay real; this gate makes no GPU/pixel accuracy claim.
CONTROLS = """(options) => {
  const state = window.heroTest = {renders: 0, failures: 0, stageObservers: 0, frames: new Map()};
  state.motionChanges = 0;
  matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', () => state.motionChanges++);
  state.enhancementFaults = 0;
  const querySelector = Element.prototype.querySelector;
  Element.prototype.querySelector = function (selector) {
    if (options.enhancementFailure === 'reels' && this.classList.contains('reelbar') &&
        selector === '.reelbar-track') {
      state.enhancementFaults++; throw new Error('Synthetic reel dependency failure');
    }
    return querySelector.call(this, selector);
  };
  let nextFrame = 0;
  window.requestAnimationFrame = callback => {
    state.frames.set(++nextFrame, callback); return nextFrame;
  };
  window.cancelAnimationFrame = id => state.frames.delete(id);
  state.tick = () => {
    const batch = [...state.frames];
    batch.forEach(([id, callback]) => {
      if (state.frames.delete(id)) callback(performance.now());
    });
  };
  // No asynchronous layout callbacks: tests explicitly control lifecycle inputs.
  window.ResizeObserver = class {
    observe(target) { if (target.id === 'stage') state.stageObservers++; }
    disconnect() {}
  };
  window.IntersectionObserver = class {
    constructor(callback) { state.intersect = visible => callback([{isIntersecting: visible}]); }
    observe() {} disconnect() {}
  };
  state.visibility = hidden => {
    Object.defineProperty(document, 'hidden', {configurable: true, value: hidden});
    document.dispatchEvent(new Event('visibilitychange'));
  };
  let resolveLoad, resolveReady, rejectLoad, rejectReady;
  const load = new Promise((resolve, reject) => { resolveLoad = resolve; rejectLoad = reject; });
  const ready = new Promise((resolve, reject) => { resolveReady = resolve; rejectReady = reject; });
  state.finishFonts = () => { resolveLoad([]); resolveReady(document.fonts); };
  state.rejectFonts = () => {
    const reject = options.fonts === 'pending-load' ? rejectLoad : rejectReady;
    reject(new Error('Synthetic late font rejection'));
  };
  document.fonts.load = () => {
    if (options.fonts === 'throw') throw new Error('Synthetic font load failure');
    if (options.fonts === 'rejected') return Promise.reject(new Error('Synthetic font rejection'));
    return options.fonts === 'pending-load' ? load : Promise.resolve([]);
  };
  Object.defineProperty(document.fonts, 'ready', {
    value: options.fonts === 'pending-ready' ? ready : Promise.resolve(document.fonts)
  });
  const gl = {COMPILE_STATUS: 1, LINK_STATUS: 2, ACTIVE_UNIFORMS: 3};
  gl.getExtension = () => ({HALF_FLOAT_OES: 36193});
  gl.getShaderParameter = () => {
    if (options.failure === 'shader') { state.failures++; return false; }
    return true;
  };
  gl.getShaderInfoLog = () => 'Synthetic shader failure';
  gl.getProgramParameter = (program, name) => name === gl.ACTIVE_UNIFORMS ? 0 : true;
  gl.getAttribLocation = () => 0;
  ['createShader', 'createProgram', 'createBuffer', 'createTexture', 'createFramebuffer']
    .forEach(name => { gl[name] = () => ({}); });
  ['shaderSource', 'compileShader', 'attachShader', 'linkProgram', 'bindBuffer', 'bufferData',
   'enableVertexAttribArray', 'vertexAttribPointer', 'bindTexture', 'texParameteri',
   'texImage2D', 'framebufferTexture2D', 'viewport', 'clear', 'pixelStorei', 'useProgram',
   'uniform1f', 'uniform1i', 'uniform2f', 'uniform3f', 'activeTexture']
    .forEach(name => { gl[name] = () => {}; });
  let framebuffer;
  gl.bindFramebuffer = (target, value) => { framebuffer = value; };
  gl.drawArrays = () => {
    if (framebuffer !== null) return;
    if (options.failure === 'startup' || state.failRender) {
      state.failures++; throw new Error('Synthetic render failure');
    }
    state.renders++;
  };
  const getContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (name, ...args) {
    if (name === 'webgl' || name === 'experimental-webgl') {
      if (options.failure === 'context') { state.failures++; return null; }
      return gl;
    }
    return getContext.call(this, name, ...args);
  };
}"""

HTML = """<!doctype html><html class="has-js"><head>
<link rel="stylesheet" href="/portfolio-startseite.css"></head><body>
<header class="site"><details class="site-nav"><summary>Menu</summary>
<nav><a href="#content">Content</a></nav></details></header>
<main><section id="stage" class="stage"><canvas id="fluid"></canvas>
<div class="fallback"><h1>Moin</h1></div><div class="sub">Synthetic introduction</div></section>
<section id="content"><h2>Synthetic content</h2></section>
<div class="reel">Synthetic project</div><div class="reelbar"><div class="reelbar-track">
<div class="reelbar-thumb"></div></div></div>
<section class="about"><details class="me-row"><summary>About</summary>
<p>Synthetic readable biography.</p></details></section></main>
<script src="/homepage.js"></script></body></html>"""


@pytest.fixture
def hero_page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        contexts = []
        errors = []
        unexpected = []

        def open_page(*, failure=None, fonts="fulfilled", enhancement_failure=None, reduced_motion="no-preference"):
            context = browser.new_context(viewport={"width": 1000, "height": 800}, reduced_motion=reduced_motion)
            contexts.append(context)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.clock.install(time=0)
            page.clock.pause_at(1)
            options = {"failure": failure, "fonts": fonts, "enhancementFailure": enhancement_failure}
            page.add_init_script(f"({CONTROLS})({json.dumps(options)})")

            html = HTML
            if enhancement_failure:
                html = html.replace(
                    '<script src="/homepage.js">',
                    '<div class="cursor"></div><svg class="shapes" width="20" height="20">'
                    '<circle r="5"><animate attributeName="r" values="5;8;5" dur="2s" '
                    'repeatCount="indefinite"/></circle></svg><script src="/homepage.js">',
                )

            def serve(route):
                resources = {
                    "http://hero.invalid/": (html, "text/html"),
                    "http://hero.invalid/homepage.js": ((ASSETS / "homepage.js").read_text(), "text/javascript"),
                    "http://hero.invalid/portfolio-startseite.css": (
                        (ASSETS / "portfolio-startseite.css").read_text(),
                        "text/css",
                    ),
                }
                resource = resources.get(route.request.url)
                if resource is None:
                    unexpected.append(route.request.url)
                    route.abort()
                else:
                    body, content_type = resource
                    route.fulfill(body=body, content_type=content_type)

            page.route("**/*", serve)
            page.goto("http://hero.invalid/")
            return page

        yield open_page
        for context in contexts:
            context.close()
        browser.close()
        assert not errors
        assert not unexpected


def assert_navigation_works(page):
    page.locator(".site-nav > summary").click()
    expect(page.locator(".site-nav")).to_have_attribute("open", "")
    page.locator(".site-nav a").click()
    page.evaluate("heroTest.tick()")
    expect(page.locator(".site-nav")).not_to_have_attribute("open", "")
    expect(page.locator("#content")).to_be_focused()
    expect(page.locator("main")).to_have_js_property("inert", False)


def assert_stopped_fallback(page):
    expect(page.locator(".fallback h1")).to_be_visible()
    expect(page.locator(".fallback h1")).to_have_text("Moin")
    expect(page.locator("#fluid")).to_be_hidden()
    page.evaluate("heroTest.tick()")
    assert page.evaluate("heroTest.frames.size") == 0
    assert_navigation_works(page)


@pytest.mark.parametrize("failure", ["context", "shader", "startup", "frame"])
def test_webgl_failure_has_readable_fallback_and_navigation(hero_page, failure):
    page = hero_page(failure=failure)
    if failure == "frame":
        assert page.evaluate("heroTest.renders") == 1
        assert page.evaluate("heroTest.frames.size") == 1
        page.evaluate("heroTest.failRender = true; heroTest.tick()")
    assert page.evaluate("heroTest.failures") > 0
    assert_stopped_fallback(page)
    # Failure is terminal even when normal resume signals arrive later.
    page.evaluate("heroTest.intersect?.(true); dispatchEvent(new Event('resize'))")
    page.emulate_media(reduced_motion="reduce")
    page.emulate_media(reduced_motion="no-preference")
    assert page.evaluate("heroTest.frames.size") == 0


@pytest.mark.parametrize("fonts", ["pending-load", "pending-ready", "rejected", "fulfilled", "throw"])
def test_font_readiness_reaches_one_start_within_deadline(hero_page, fonts):
    page = hero_page(fonts=fonts)
    if fonts.startswith("pending"):
        assert page.evaluate("heroTest.renders") == 0
        # Other page interaction must already work while fonts remain pending.
        assert_navigation_works(page)
    page.clock.run_for(1600)
    assert page.evaluate("heroTest.renders") == 1
    assert page.evaluate("heroTest.frames.size") == 1
    expect(page.locator("#fluid")).to_be_visible()
    expect(page.locator(".fallback")).to_be_hidden()
    page.evaluate("heroTest.finishFonts()")
    page.clock.run_for(2000)
    assert page.evaluate("heroTest.stageObservers") == 1
    assert page.evaluate("heroTest.renders") == (2 if fonts.startswith("pending") else 1)
    assert page.evaluate("heroTest.frames.size") == 1


@pytest.mark.parametrize("fonts", ["pending-load", "pending-ready"])
def test_late_font_rejection_does_not_restart_or_repaint(hero_page, fonts):
    page = hero_page(fonts=fonts)
    page.clock.run_for(1600)
    assert page.evaluate("heroTest.renders") == 1
    page.evaluate("heroTest.rejectFonts()")
    page.clock.run_for(2000)
    assert page.evaluate("heroTest.renders") == 1
    assert page.evaluate("heroTest.stageObservers") == 1
    assert page.evaluate("heroTest.frames.size") == 1


def test_failed_reel_initializer_leaves_later_enhancements_and_native_content(hero_page):
    page = hero_page(failure="context", enhancement_failure="reels")
    assert page.evaluate("heroTest.enhancementFaults") == 1
    row = page.locator(".about .me-row")
    row.locator("summary").click()
    expect(row).to_have_attribute("open", "")
    expect(row.locator("p")).to_have_text("Synthetic readable biography.")
    # This convenience is installed after the failed reel initializer.
    row.locator("p").click()
    expect(row).not_to_have_attribute("open", "")
    assert_navigation_works(page)
    expect(page.locator(".fallback h1")).to_be_visible()
    # These two independent effects are registered after both reel and tile setup.
    page.locator("#stage").dispatch_event("pointerenter", {"clientX": 80, "clientY": 90})
    assert page.evaluate("document.documentElement.classList.contains('stage-hover')")
    cursor = page.locator(".cursor")
    before = cursor.evaluate("node => node.style.transform")
    page.evaluate("dispatchEvent(new PointerEvent('pointermove', {clientX: 120, clientY: 130})); heroTest.tick()")
    assert cursor.evaluate("node => node.style.transform") != before
    page.locator("#stage").dispatch_event("pointerleave")
    assert not page.evaluate("document.documentElement.classList.contains('stage-hover')")
    assert page.evaluate("heroTest.frames.size") == 0
    shapes = page.locator(".shapes")
    assert not shapes.evaluate("svg => svg.animationsPaused()")
    set_motion(page, "reduce")
    assert shapes.evaluate("svg => svg.animationsPaused()")
    set_motion(page, "no-preference")
    assert not shapes.evaluate("svg => svg.animationsPaused()")


def set_motion(page, value):
    before = page.evaluate("heroTest.motionChanges")
    page.emulate_media(reduced_motion=value)
    page.wait_for_function("before => heroTest.motionChanges > before", arg=before)


@pytest.mark.parametrize("boundary", ["visibility", "intersection", "motion"])
def test_hero_pause_resume_keeps_one_frame_owner(hero_page, boundary):
    page = hero_page()
    assert page.evaluate("heroTest.renders") == 1
    assert page.evaluate("heroTest.frames.size") == 1
    for _ in range(3):
        before = page.evaluate("heroTest.renders")
        if boundary == "motion":
            set_motion(page, "reduce")
        elif boundary == "visibility":
            page.evaluate("heroTest.visibility(true); heroTest.visibility(true)")
        else:
            page.evaluate("heroTest.intersect(false); heroTest.intersect(false)")
        assert page.evaluate("heroTest.frames.size") == 0
        page.evaluate("heroTest.tick()")
        assert page.evaluate("heroTest.renders") == before
        if boundary == "motion":
            set_motion(page, "no-preference")
        elif boundary == "visibility":
            page.evaluate("heroTest.visibility(false); heroTest.visibility(false)")
        else:
            page.evaluate("heroTest.intersect(true); heroTest.intersect(true)")
        assert page.evaluate("heroTest.frames.size") == 1
        page.evaluate("heroTest.tick()")
        assert page.evaluate("heroTest.renders") == before + 1
        assert page.evaluate("heroTest.frames.size") == 1
    assert page.evaluate("heroTest.stageObservers") == 1


def test_hero_resumes_only_when_all_pause_reasons_clear(hero_page):
    page = hero_page(reduced_motion="reduce")
    assert page.evaluate("heroTest.renders") == 1
    assert page.evaluate("heroTest.frames.size") == 0
    page.evaluate("heroTest.visibility(true); heroTest.intersect(false)")
    set_motion(page, "no-preference")
    assert page.evaluate("heroTest.frames.size") == 0
    page.evaluate("heroTest.visibility(false)")
    assert page.evaluate("heroTest.frames.size") == 0
    page.evaluate("heroTest.intersect(true); heroTest.intersect(true)")
    assert page.evaluate("heroTest.frames.size") == 1
    page.evaluate("heroTest.tick()")
    assert page.evaluate("heroTest.renders") == 2
    assert page.evaluate("heroTest.frames.size") == 1
