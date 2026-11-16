const {test} = require('node:test');
const assert = require('node:assert/strict');
const {runtime} = require('./runtime.cjs');

test('framebuffer capability admission rejects incomplete targets and releases allocations', async () => {
  const r = runtime({incomplete: true});
  r.run('homepage.js'); await r.settle();
  assert(r.d.documentElement.classList.contains('no-webgl'));
  assert.equal(r.state.renders, 0);
  assert.equal(r.frames.size, 0);
  assert(r.state.deleted > 0);
  r.dom.window.close();
});

test('half float without linear filtering uses nearest; capable context renders', async () => {
  for (const noLinear of [true, false]) {
    const r = runtime({noLinear}); r.run('homepage.js'); await r.settle();
    assert.equal(r.state.renders, 1);
    assert.equal(r.frames.size, 1);
    assert(r.state.filters.includes(noLinear ? 7 : 6));
    r.dom.window.close();
  }
});

test('texture dimensions preserve tall and wide stage aspect within device and pixel limits', async () => {
  for (const [sizes, limit] of [[[100, 12000], 512], [[12000, 100], 512], [[3000, 3000], 4096]]) {
    const r = runtime({limit, sizes}); r.run('homepage.js'); await r.settle();
    assert.equal(r.state.renders, 1);
    assert(r.state.allocations.every(([w,h]) => w > 0 && h > 0 && w <= limit && h <= limit && w * h <= 4 * 1024 * 1024));
    const [w,h] = r.state.allocations.at(-1);
    assert(Math.abs(w / h - sizes[0] / sizes[1]) <= Math.max(1 / h, w / h / h));
    r.dom.window.close();
  }
  const r = runtime({limit: 0}); r.run('homepage.js'); await r.settle();
  assert(r.d.documentElement.classList.contains('no-webgl'));
  assert.equal(r.state.renders, 0);
  r.dom.window.close();
});

test('context loss is terminal during rendering and pending fonts', async () => {
  for (const pendingFonts of [false, true]) {
    const r = runtime({pendingFonts}); r.run('homepage.js'); await r.settle();
    assert.equal(r.state.renders, pendingFonts ? 0 : 1);
    assert(!r.d.documentElement.classList.contains('no-webgl'));
    r.event(r.d.querySelector('#fluid'), 'webglcontextlost');
    r.finishFont(); await r.settle();
    for (const {cb} of [...r.timers.values()]) cb();
    assert(r.d.documentElement.classList.contains('no-webgl'));
    assert.equal(r.frames.size, 0);
    const renders = r.state.renders;
    r.event(r.d.querySelector('#fluid'), 'webglcontextrestored');
    r.event(r.w, 'resize'); r.motion(true); r.motion(false); r.tick();
    assert.equal(r.state.renders, renders);
    assert.equal(r.frames.size, 0);
    r.dom.window.close();
  }
});


test('bounded reveal retains off-centre editorial focal placement', async () => {
  const r = runtime({limit: 512, sizes: [100, 12000], html:
    '<img id="hero-reveal-source" data-focal-portrait-x="0.25" data-focal-portrait-y="0.75">'});
  const source = r.d.querySelector('#hero-reveal-source');
  Object.defineProperties(source, {naturalWidth: {value: 1000}, naturalHeight: {value: 2000},
    complete: {value: true}});
  r.run('homepage.js'); await r.settle();
  const [width, height] = r.state.allocations.at(-1);
  assert(width <= 512 && height <= 512);
  const placed = r.state.imageDraws[0];
  assert.equal(placed.x + 0.25 * placed.width, width / 2);
  assert(placed.y <= 0 && placed.y + placed.height >= height);
  assert.equal(placed.width / placed.height, 0.5);
  r.dom.window.close();
});
