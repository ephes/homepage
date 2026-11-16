const {test} = require('node:test');
const assert = require('node:assert/strict');
const {runtime} = require('./runtime.cjs');

function aboutRuntime(text = 'Synthetic text with several readable lines.') {
  const r = runtime({noGL: true, html: `<section class="about"><details class="me-row">
    <summary>About</summary><p>${text}</p></details></section>`});
  r.d.createRange = () => {
    let start = 0, end = text.length;
    return {selectNodeContents() {}, setStart(node, i) { start = i; }, setEnd(node, i) { end = i; },
      getClientRects() { r.state.measures++; return end - start > 1
        ? Array.from({length: Math.ceil(text.length / 15)}, (_, i) => ({top: i * 20, height: 20}))
        : [{top: Math.floor(start / 15) * 20, height: 20}]; }};
  };
  r.run('homepage.js');
  r.row = r.d.querySelector('.me-row'); r.p = r.row.querySelector('p');
  return r;
}

test('stationary cursor retires frames and movement rearms one owner', () => {
  const r = runtime({noGL: true, finePointer: true, html: '<div class="cursor"></div>'});
  r.run('homepage.js'); const stage = r.d.querySelector('#stage');
  r.event(stage, 'pointerenter', {clientX: 10, clientY: 20});
  for (let i=0; i<100; i++) r.tick();
  assert.equal(r.frames.size, 0);
  r.event(r.w, 'pointermove', {clientX: 100, clientY: 200});
  assert.equal(r.frames.size, 1);
  r.event(r.w, 'pointermove', {clientX: 120, clientY: 200});
  assert.equal(r.frames.size, 1);
  r.tick(); const cur = r.d.querySelector('.cursor');
  assert(cur.style.transform.includes('32px'));
  r.motion(true); assert.equal(r.frames.size, 0);
  r.event(r.w, 'pointermove', {clientX: 180, clientY: 200});
  assert.equal(r.frames.size, 0);
  assert(cur.style.transform.includes('180px'));
  r.motion(false); r.event(r.w, 'pointermove', {clientX: 220, clientY: 200});
  assert.equal(r.frames.size, 1);
  r.d.hidden = true; r.event(r.d, 'visibilitychange');
  assert.equal(r.frames.size, 0);
  r.d.hidden = false; r.event(r.d, 'visibilitychange');
  r.event(stage, 'pointerleave');
  r.event(r.w, 'pointermove', {clientX: 250, clientY: 200});
  assert.equal(r.frames.size, 0);
  r.dom.window.close();
});

test('font completion requires current permitted handwriting generation', async () => {
  const r = runtime({pendingFonts: true, html: '<svg class="scr"><text>Example</text></svg>'});
  r.w.PORTFOLIO_HANDWRITING = {Example: '<svg class="hw-svg"></svg>'};
  r.run('motion.js'); await r.settle();
  r.motion(true); r.finishFont(0); await r.settle();
  assert.equal(r.d.querySelectorAll('.hw-label').length, 0);
  assert.equal(r.d.querySelector('svg.scr text').textContent, 'Example');
  r.motion(false); r.finishFont(1); await r.settle();
  assert.equal(r.d.querySelectorAll('.hw-label').length, 1);
  r.motion(true); r.motion(false);
  r.event(r.w, 'portfolio:handwriting-ready'); await r.settle();
  assert.equal(r.d.querySelectorAll('.hw-label').length, 1);
  r.dom.window.close();
});

test('obsolete font completion cannot prepare DOM after a newer start', async () => {
  const r = runtime({pendingFonts: true, html: '<svg class="scr"><text>Example</text></svg>'});
  r.w.PORTFOLIO_HANDWRITING = {Example: '<svg class="hw-svg"></svg>'};
  r.run('motion.js'); r.motion(true); r.motion(false);
  r.finishFont(0); await r.settle();
  assert.equal(r.d.querySelectorAll('.hw-label').length, 0);
  r.finishFont(1); await r.settle();
  assert.equal(r.d.querySelectorAll('.hw-label').length, 1);
  r.dom.window.close();
});

test('about live reduced motion retires queued frames and running lines', () => {
  for (const duringLines of [false, true]) {
    const r = aboutRuntime(); const text = r.p.textContent;
    r.row.open = true; r.event(r.row, 'toggle');
    if (duringLines) { r.tick(); assert(r.p.querySelector('.ln')); }
    r.motion(true);
    assert.equal(r.frames.size, 0); assert.equal(r.timers.size, 0);
    assert.equal(r.p.textContent, text); assert.equal(r.p.children.length, 0);
    r.tick(); r.event(r.row, 'toggle'); assert.equal(r.frames.size, 0);
    r.motion(false); r.event(r.row, 'toggle'); r.tick();
    assert(r.p.querySelector('.ln'));
    r.dom.window.close();
  }
});

test('long about copy stays complete without optional layout or delayed visibility', () => {
  const text = 'Synthetic editorial text. '.repeat(500);
  const r = aboutRuntime(text);
  r.row.open = true; r.event(r.row, 'toggle'); r.tick();
  assert.equal(r.state.measures, 0);
  assert.equal(r.frames.size, 0); assert.equal(r.timers.size, 0);
  assert.equal(r.p.textContent, text); assert.equal(r.p.children.length, 0);
  r.dom.window.close();
});

test('about line and duration envelope skips excessive wrapping but retains short animation', () => {
  const r = aboutRuntime('word '.repeat(120));
  r.row.open = true; r.event(r.row, 'toggle'); r.tick();
  assert.equal(r.state.measures, 1);
  assert.equal(r.p.children.length, 0); assert.equal(r.frames.size, 0);
  assert.equal(r.timers.size, 0); r.dom.window.close();
  const short = aboutRuntime(); const text = short.p.textContent;
  short.row.open = true; short.event(short.row, 'toggle'); short.tick();
  assert(short.p.querySelector('.ln'));
  const [timer] = short.timers.values(); assert(timer.delay <= 2700);
  timer.cb(); assert.equal(short.p.textContent, text);
  short.dom.window.close();
});
