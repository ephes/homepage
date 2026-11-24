const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const {JSDOM} = require('jsdom');

test('switching to a note excludes the title and switching back restores the draft', async (t) => {
  const template = readFileSync(resolve(__dirname, '../../homepage/templates/micropub/form.html'), 'utf8');
  const script = template.match(/<script>[\s\S]*?<\/script>/)[0];
  const {window} = new JSDOM(`
    <form>
      <input type="radio" name="post_type" value="article" checked>
      <input type="radio" name="post_type" value="note">
      <div id="title-field"><input id="id_name" name="name"></div>
      <textarea id="id_content" name="content"></textarea>
    </form>
    ${script}
  `, {runScripts: 'dangerously'});
  t.after(() => window.close());
  const {document, FormData} = window;
  await new Promise(resolve => document.addEventListener('DOMContentLoaded', resolve, {once: true}));

  const form = document.querySelector('form');
  const titleField = document.getElementById('title-field');
  const title = document.getElementById('id_name');
  const draft = '  A draft with café & 猫  ';
  title.value = draft;

  document.querySelector('[value="note"]').click();
  assert(titleField.classList.contains('d-none'));
  assert(title.disabled);
  assert(!new FormData(form).has('name'));

  document.querySelector('[value="article"]').click();
  assert(!titleField.classList.contains('d-none'));
  assert.equal(new FormData(form).get('name'), draft);
});
