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
<section id="content"><h2>Synthetic content</h2></section></main>
<script src="/homepage.js"></script></body></html>"""


@pytest.fixture
def hero_page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        contexts = []
        errors = []
        unexpected = []

        def open_page(*, failure=None, fonts="fulfilled"):
            context = browser.new_context(viewport={"width": 1000, "height": 800}, reduced_motion="no-preference")
            contexts.append(context)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.clock.install(time=0)
            page.clock.pause_at(1)
            page.add_init_script(f"({CONTROLS})({json.dumps({'failure': failure, 'fonts': fonts})})")

            def serve(route):
                resources = {
                    "http://hero.invalid/": (HTML, "text/html"),
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
