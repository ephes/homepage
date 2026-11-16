const {JSDOM} = require('jsdom');
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const assets = resolve(__dirname, '../../homepage/portfolio/static/portfolio/prototype');

function runtime(options = {}) {
  const dom = new JSDOM(`<!doctype html><html><body>
    <section id="stage"><canvas id="fluid"></canvas><div class="fallback">Readable</div></section>
    ${options.html || ''}</body></html>`, {url: 'https://example.invalid/', runScripts: 'outside-only'});
  const w = dom.window, d = w.document;
  const frames = new Map(), timers = new Map(), media = new Map(), observers = [];
  let sequence = 0;
  w.requestAnimationFrame = cb => { frames.set(++sequence, cb); return sequence; };
  w.cancelAnimationFrame = id => frames.delete(id);
  w.setTimeout = (cb, delay) => { timers.set(++sequence, {cb, delay}); return sequence; };
  w.clearTimeout = id => timers.delete(id);
  w.matchMedia = query => {
    if (!media.has(query)) {
      const mq = new w.EventTarget(); mq.matches = !!options.finePointer && query === '(hover: hover) and (pointer: fine)';
      mq.addListener = cb => mq.addEventListener('change', cb);
      media.set(query, mq);
    }
    return media.get(query);
  };
  w.ResizeObserver = class {
    constructor(cb) { this.cb = cb; this.targets = []; observers.push(this); }
    observe(target) { this.targets.push(target); }
    unobserve(target) { this.targets = this.targets.filter(t => t !== target); }
    disconnect() { this.targets = []; }
  };
  w.IntersectionObserver = class { observe() {} disconnect() {} };
  const sizes = options.sizes || [1000, 800];
  const stage = d.querySelector('#stage');
  Object.defineProperties(stage, {
    clientWidth: {get: () => sizes[0]}, clientHeight: {get: () => sizes[1]}
  });
  stage.getBoundingClientRect = () => ({top: 0, left: 0, right: sizes[0], bottom: sizes[1], width: sizes[0], height: sizes[1]});
  const state = {allocations: [], filters: [], deleted: 0, renders: 0, measures: 0, imageDraws: []};
  const gl = {COMPILE_STATUS: 1, LINK_STATUS: 2, ACTIVE_UNIFORMS: 3,
    FRAMEBUFFER_COMPLETE: 4, MAX_TEXTURE_SIZE: 5, LINEAR: 6, NEAREST: 7};
  gl.getExtension = name => options.noGL || (name.endsWith('_linear') && options.noLinear)
    ? null : {HALF_FLOAT_OES: 36193};
  gl.getParameter = () => options.limit ?? 4096;
  gl.checkFramebufferStatus = () => options.incomplete ? 0 : gl.FRAMEBUFFER_COMPLETE;
  gl.getShaderParameter = () => true;
  gl.getProgramParameter = (p, name) => name === gl.ACTIVE_UNIFORMS ? 0 : true;
  gl.getAttribLocation = () => 0;
  ['createShader', 'createProgram', 'createBuffer', 'createTexture', 'createFramebuffer']
    .forEach(name => { gl[name] = () => ({}); });
  ['shaderSource', 'compileShader', 'attachShader', 'linkProgram', 'bindBuffer', 'bufferData',
    'enableVertexAttribArray', 'vertexAttribPointer', 'bindTexture', 'framebufferTexture2D',
    'viewport', 'clear', 'pixelStorei', 'useProgram', 'uniform1f', 'uniform1i', 'uniform2f',
    'uniform3f', 'activeTexture'].forEach(name => { gl[name] = () => {}; });
  ['deleteTexture', 'deleteFramebuffer', 'deleteBuffer', 'deleteShader', 'deleteProgram']
    .forEach(name => { gl[name] = () => state.deleted++; });
  gl.texParameteri = (target, name, value) => state.filters.push(value);
  gl.texImage2D = (...args) => state.allocations.push(args.length === 6
    ? [args[5].width, args[5].height] : [args[3], args[4]]);
  let framebuffer;
  gl.bindFramebuffer = (target, value) => { framebuffer = value; };
  gl.drawArrays = () => { if (framebuffer === null) state.renders++; };
  w.HTMLCanvasElement.prototype.getContext = function (type) {
    if (type.includes('webgl')) return options.noGL ? null : gl;
    const ctx = {canvas: this, getImageData: () => ({data: [0, 0, 0, 255]}), measureText: () => ({actualBoundingBoxRight: 100,
      actualBoundingBoxLeft: 0, actualBoundingBoxAscent: 100}),
      createRadialGradient: () => ({addColorStop() {}})};
    ['clearRect', 'fillRect', 'fillText', 'strokeText', 'drawImage', 'beginPath', 'arc', 'fill', 'moveTo',
      'lineTo', 'stroke'].forEach(name => { ctx[name] = () => {}; });
    ctx.drawImage = (source, x, y, width, height) => {
      if (source.id === 'hero-reveal-source') state.imageDraws.push({x, y, width, height});
    };
    return ctx;
  };
  const fontResolvers = [];
  d.fonts = {load: () => options.pendingFonts ? new Promise(r => { fontResolvers.push(r); }) : Promise.resolve([]),
    ready: Promise.resolve()};
  Object.defineProperty(d, 'hidden', {value: false, writable: true});
  const api = {w, d, dom, state, frames, timers, sizes, observers,
    run: name => w.eval(readFileSync(resolve(assets, name), 'utf8')),
    tick() { for (const [id, cb] of [...frames]) if (frames.delete(id)) cb(16); },
    motion(reduce) { const mq = w.matchMedia('(prefers-reduced-motion: reduce)');
      mq.matches = reduce; mq.dispatchEvent(new w.Event('change')); },
    finishFont: (index = fontResolvers.length - 1) => fontResolvers[index]?.([]),
    async settle() { for (let i = 0; i < 8; i++) await Promise.resolve(); },
    event(target, type, values = {}) {
      const event = new w.Event(type, {bubbles: true, cancelable: true});
      Object.assign(event, values); target.dispatchEvent(event); return event;
    }
  };
  return api;
}
module.exports = {runtime};
