const {test} = require('node:test');
const assert = require('node:assert/strict');
const {runtime} = require('./runtime.cjs');

function reelRuntime() {
  const r = runtime({noGL: true, html: `<div class="reel"><div class="card"><img></div></div>
    <div class="reelbar"><div class="reelbar-track"><div class="reelbar-thumb"></div></div></div>`});
  r.reel = r.d.querySelector('.reel'); r.thumb = r.d.querySelector('.reelbar-thumb');
  r.bar = r.d.querySelector('.reelbar'); r.contentWidth = 100;
  Object.defineProperties(r.reel, {clientWidth: {value: 100}, scrollWidth: {get: () => r.contentWidth}});
  Object.defineProperty(r.d.querySelector('.reelbar-track'), 'clientWidth', {value: 100});
  Object.defineProperty(r.thumb, 'offsetWidth', {value: 20});
  r.captured = null;
  r.thumb.setPointerCapture = id => { r.captured = id; };
  r.thumb.hasPointerCapture = id => r.captured === id;
  r.thumb.releasePointerCapture = id => { if (r.captured === id) r.captured = null; };
  r.run('homepage.js');
  return r;
}

test('intrinsic image and content changes coalesce overflow and no-overflow state', async () => {
  const r = reelRuntime();
  assert.equal(r.reel.tabIndex, -1);
  r.contentWidth = 500;
  r.event(r.reel.querySelector('img'), 'load');
  r.event(r.reel.querySelector('img'), 'error');
  assert.equal(r.frames.size, 1);
  r.tick();
  assert(r.bar.classList.contains('is-scrollable')); assert.equal(r.reel.tabIndex, 0);
  assert.equal(r.thumb.style.getPropertyValue('--thumb-size'), '20%');
  r.reel.scrollLeft = 200; r.event(r.reel, 'scroll'); r.tick();
  assert.equal(r.thumb.getAttribute('aria-valuenow'), '50');
  r.contentWidth = 100;
  const observer = r.observers.find(o => o.targets.includes(r.reel.querySelector('.card')));
  assert(observer, 'content boxes must be observed, not just the fixed reel box');
  observer.cb(); r.tick();
  assert.equal(r.reel.tabIndex, -1); assert(!r.bar.classList.contains('is-scrollable'));
  assert.equal(r.thumb.getAttribute('aria-valuenow'), '0');
  assert.equal(r.thumb.style.getPropertyValue('--thumb-size'), '100%');
  const card = r.d.createElement('div'); r.reel.append(card); await r.settle(); r.tick();
  assert(observer.targets.includes(card));
  r.contentWidth = 700; observer.cb(); r.tick(); assert.equal(r.reel.tabIndex, 0);
  assert.equal(r.frames.size, 0);
  r.dom.window.close();
});

test('one admitted pointer owns drag until up, cancel, or capture loss', () => {
  const r = reelRuntime(); r.contentWidth = 500;
  const event = (type, pointerId, clientX, button = 0) => r.event(r.thumb, type, {pointerId, clientX, button});
  event('pointerdown', 1, 10, 2); event('pointermove', 1, 30);
  assert.equal(r.reel.scrollLeft, 0);
  event('pointerdown', 1, 10); event('pointerdown', 2, 50);
  event('pointermove', 2, 90); assert.equal(r.reel.scrollLeft, 0);
  event('pointermove', 1, 30); assert.equal(r.reel.scrollLeft, 100);
  event('pointercancel', 2, 30); event('pointermove', 1, 40);
  assert.equal(r.reel.scrollLeft, 150);
  event('lostpointercapture', 1, 40); event('pointermove', 1, 90);
  assert.equal(r.reel.scrollLeft, 150);
  event('pointerdown', 3, 20); event('pointermove', 3, 30);
  assert.equal(r.reel.scrollLeft, 200);
  event('pointerup', 3, 30); assert.equal(r.captured, null);
  event('pointermove', 3, 60); assert.equal(r.reel.scrollLeft, 200);
  event('pointerdown', 4, 20); event('pointercancel', 4, 20);
  event('pointermove', 4, 80); assert.equal(r.reel.scrollLeft, 200);
  r.event(r.thumb, 'keydown', {key: 'ArrowRight'}); assert.equal(r.reel.scrollLeft, 260);
  r.dom.window.close();
});
