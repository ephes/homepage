const {test} = require('node:test');
const assert = require('node:assert/strict');
const {runtime} = require('./runtime.cjs');

for (const script of ['homepage.js', 'site-shell.js']) {
  function setup() {
    const r = runtime({noGL: true, html: `<header class="site site-header">
      <details class="site-nav"><summary>Menu</summary><nav>
      <a href="#first">First</a><a href="#second">Second</a></nav></details></header>
      <main><section id="first">First</section><section id="second">Second</section></main>`});
    r.scrolled = [];
    r.w.HTMLElement.prototype.scrollIntoView = function () { r.scrolled.push(this.id); };
    r.menu = r.d.querySelector('.site-nav');
    r.toggle = r.menu.querySelector('summary');
    r.links = r.menu.querySelectorAll('a');
    r.run(script);
    r.menu.open = true; r.event(r.menu, 'toggle');
    return r;
  }
  const click = (r, index = 0, values = {}) => r.event(r.links[index], 'click', {button: 0, ...values});

  test(`${script}: reopening or Escape invalidates queued navigation even if callbacks were dispatched`, () => {
    for (const escape of [false, true]) {
      const r = setup(); click(r);
      const staleFrame = [...r.frames.values()][0];
      const staleTimer = [...r.timers.values()][0].cb;
      r.menu.open = true; r.event(r.menu, 'toggle');
      if (escape) r.event(r.d, 'keydown', {key: 'Escape'});
      staleFrame(); staleTimer(); r.tick();
      assert.deepEqual(r.scrolled, []);
      assert.notEqual(r.d.activeElement.id, 'first');
      assert.equal(r.frames.size, 0); assert.equal(r.timers.size, 0);
      assert.equal(r.d.querySelector('main').inert, !escape);
      r.dom.window.close();
    }
  });

  test(`${script}: Escape after deliberate close cancels still pending navigation`, () => {
    const r = setup(); click(r);
    r.event(r.d, 'keydown', {key: 'Escape'}); r.tick();
    assert.deepEqual(r.scrolled, []); assert.equal(r.frames.size, 0);
    assert.equal(r.timers.size, 0); assert.equal(r.d.activeElement, r.toggle);
    r.dom.window.close();
  });

  test(`${script}: own close preserves flight, latest navigation supersedes old focus/scroll`, () => {
    const r = setup(); click(r);
    const stale = [...r.frames.values()][0];
    r.event(r.menu, 'toggle'); // asynchronously delivered close from the deliberate link click
    click(r, 1); stale(); r.tick();
    assert.deepEqual(r.scrolled, ['second']); assert.equal(r.d.activeElement.id, 'second');
    assert.equal(r.d.querySelector('main').inert, false);
    r.dom.window.close();
  });

  test(`${script}: hover preview scrolls without focus and modified links stay native`, () => {
    const r = setup();
    r.w.matchMedia('(min-width: 52.001rem) and (hover: hover) and (pointer: fine)').matches = true;
    const event = click(r, 0, {ctrlKey: true}); assert.equal(event.defaultPrevented, false);
    assert.equal(r.frames.size, 0); assert.equal(r.menu.open, true);
    r.event(r.links[0], 'pointerenter'); r.tick();
    assert.deepEqual(r.scrolled, ['first']); assert.notEqual(r.d.activeElement.id, 'first');
    assert.equal(r.menu.open, true); r.dom.window.close();
  });
}
