const {test} = require('node:test');
const assert = require('node:assert/strict');
const {runtime} = require('./runtime.cjs');

const themeMenu = `
  <div data-theme-switch>
    <button class="theme-switch__toggle" data-label="Appearance" aria-expanded="false">Theme</button>
    <div class="theme-switch__menu" role="menu" hidden>
      <button role="menuitemradio" data-theme-value="system">System</button>
      <button role="menuitemradio" data-theme-value="light">Light</button>
      <button role="menuitemradio" data-theme-value="dark">Dark</button>
    </div>
  </div>`;

function assertChoice(document, choice, explicitTheme, label) {
  const root = document.documentElement;
  assert.equal(root.dataset.themeChoice, choice);
  assert.equal(root.getAttribute('data-theme'), explicitTheme);
  assert.deepEqual(
    [...document.querySelectorAll('[aria-checked="true"]')].map(option => option.dataset.themeValue),
    [choice],
  );
  assert.equal(document.querySelector('.theme-switch__toggle').getAttribute('aria-label'), `Appearance: ${label}`);
}

test('theme changes reach another same-origin document, including reset to system', {timeout: 2000}, async t => {
  const r = runtime({html: themeMenu + '<iframe></iframe>'});
  t.after(() => r.w.close());
  const peer = r.d.querySelector('iframe').contentWindow;
  peer.document.body.innerHTML = themeMenu;
  peer.matchMedia = r.w.matchMedia;
  r.run('theme-switch.js');
  r.run('theme-switch.js', peer);

  const update = async change => {
    const notification = new Promise(resolve => r.w.addEventListener('storage', resolve, {once: true}));
    change();
    await notification;
  };
  const choose = choice => {
    peer.document.querySelector('.theme-switch__toggle').click();
    peer.document.querySelector(`[data-theme-value="${choice}"]`).click();
  };

  await update(() => choose('dark'));
  assertChoice(r.d, 'dark', 'dark', 'Dark');
  await update(() => peer.localStorage.setItem('unrelated', 'light'));
  assertChoice(r.d, 'dark', 'dark', 'Dark');
  await update(() => choose('system'));
  assertChoice(r.d, 'system', null, 'System');
  assert.equal(peer.localStorage.getItem('portfolio-theme'), null);

  await update(() => choose('light'));
  assertChoice(r.d, 'light', 'light', 'Light');
  await update(() => peer.localStorage.setItem('portfolio-theme', 'unsupported'));
  assertChoice(r.d, 'system', null, 'System');
  assert.equal(peer.localStorage.getItem('portfolio-theme'), 'unsupported');
  await update(() => choose('dark'));
  await update(() => peer.localStorage.clear());
  assertChoice(r.d, 'system', null, 'System');
});
