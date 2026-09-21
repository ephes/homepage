/* Canonical current-prototype homepage behavior; shared by the prototype and Wagtail. */
(function () {
  "use strict";

  function disableWebGL() {
    document.documentElement.classList.add('no-webgl');
  }

  try {
    initWebGL();
  } catch (error) {
    disableWebGL();
  }

  function initWebGL() {
  var canvas = document.getElementById('fluid');
  var stage = document.getElementById('stage');
  if (!canvas || !stage) { disableWebGL(); return; }
  var gl = canvas.getContext('webgl', {alpha:true, premultipliedAlpha:false, antialias:false})
        || canvas.getContext('experimental-webgl', {alpha:true});
  if (!gl) { disableWebGL(); return; }

  // Half-float-Support (WebGL1)
  var halfFloat = gl.getExtension('OES_texture_half_float');
  gl.getExtension('OES_texture_half_float_linear');
  var HALF = halfFloat ? halfFloat.HALF_FLOAT_OES : null;
  if (!HALF) { disableWebGL(); return; }

  var motionPreference = matchMedia('(prefers-reduced-motion: reduce)');
  var reduce = motionPreference.matches;
  var HERO_INSET = 16; // Screen-px, in resize() aus Viewport berechnet + als CSS-Var gesetzt

  // ---- Konfiguration (Original-nahe Werte aus dem noth.in-Bundle) ----
  var SIM_RES = 128, DYE_RES = 512;
  var VEL_DISSIP = 0.982, DYE_DISSIP = 0.988, PRESSURE = 0.8, PRESS_ITER = 20;
  var SPLAT_FORCE = 5900, SPLAT_RADIUS = 0.0035; // Radius in UV
  var REVEAL_SIZE = 3.9, EDGE_SOFT = 0.5, EDGE_WIDTH = 0.06; // Kante noch etwas schärfer

  // ---- Shader-Helfer ----
  function compile(type, src){ var s=gl.createShader(type); gl.shaderSource(s,src); gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)+"\n"+src); return s; }
  function prog(vs, fs){ var p=gl.createProgram(); gl.attachShader(p,compile(gl.VERTEX_SHADER,vs)); gl.attachShader(p,compile(gl.FRAGMENT_SHADER,fs));
    gl.linkProgram(p); if(!gl.getProgramParameter(p,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    p.uni={}; var n=gl.getProgramParameter(p,gl.ACTIVE_UNIFORMS); for(var i=0;i<n;i++){var u=gl.getActiveUniform(p,i).name; p.uni[u]=gl.getUniformLocation(p,u);} return p; }

  var baseVS =
    "precision highp float; attribute vec2 aPos; varying vec2 vUv; varying vec2 vL; varying vec2 vR; varying vec2 vT; varying vec2 vB; uniform vec2 texel;"+
    "void main(){ vUv=aPos*0.5+0.5; vL=vUv-vec2(texel.x,0.0); vR=vUv+vec2(texel.x,0.0); vT=vUv+vec2(0.0,texel.y); vB=vUv-vec2(0.0,texel.y); gl_Position=vec4(aPos,0.0,1.0);}";
  var simpleVS =
    "precision highp float; attribute vec2 aPos; varying vec2 vUv; void main(){ vUv=aPos*0.5+0.5; gl_Position=vec4(aPos,0.0,1.0);}";

  var advectFS =
    "precision highp float; varying vec2 vUv; uniform sampler2D uVelocity; uniform sampler2D uSource; uniform vec2 texel; uniform float dt; uniform float dissipation;"+
    "void main(){ vec2 coord = vUv - dt * texture2D(uVelocity, vUv).xy * texel; gl_FragColor = dissipation * texture2D(uSource, coord); }";
  var divergenceFS =
    "precision highp float; varying vec2 vUv; varying vec2 vL; varying vec2 vR; varying vec2 vT; varying vec2 vB; uniform sampler2D uVelocity;"+
    "void main(){ float L=texture2D(uVelocity,vL).x; float R=texture2D(uVelocity,vR).x; float T=texture2D(uVelocity,vT).y; float B=texture2D(uVelocity,vB).y;"+
    " float div=0.5*(R-L+T-B); gl_FragColor=vec4(div,0.0,0.0,1.0); }";
  var pressureFS =
    "precision highp float; varying vec2 vUv; varying vec2 vL; varying vec2 vR; varying vec2 vT; varying vec2 vB; uniform sampler2D uPressure; uniform sampler2D uDivergence;"+
    "void main(){ float L=texture2D(uPressure,vL).x; float R=texture2D(uPressure,vR).x; float T=texture2D(uPressure,vT).x; float B=texture2D(uPressure,vB).x; float C=texture2D(uDivergence,vUv).x;"+
    " float p=(L+R+B+T-C)*0.25; gl_FragColor=vec4(p,0.0,0.0,1.0); }";
  var gradientFS =
    "precision highp float; varying vec2 vUv; varying vec2 vL; varying vec2 vR; varying vec2 vT; varying vec2 vB; uniform sampler2D uPressure; uniform sampler2D uVelocity;"+
    "void main(){ float L=texture2D(uPressure,vL).x; float R=texture2D(uPressure,vR).x; float T=texture2D(uPressure,vT).x; float B=texture2D(uPressure,vB).x;"+
    " vec2 v=texture2D(uVelocity,vUv).xy; v-=vec2(R-L,T-B); gl_FragColor=vec4(v,0.0,1.0); }";
  var splatFS =
    "precision highp float; varying vec2 vUv; uniform sampler2D uTarget; uniform float aspect; uniform vec3 color; uniform vec2 point; uniform float radius;"+
    "void main(){ vec2 p=vUv-point; p.x*=aspect; vec3 splat=exp(-dot(p,p)/radius)*color; vec3 base=texture2D(uTarget,vUv).xyz; gl_FragColor=vec4(base+splat,1.0); }";
  var clearFS =
    "precision highp float; varying vec2 vUv; uniform sampler2D uTexture; uniform float value; void main(){ gl_FragColor=value*texture2D(uTexture,vUv); }";
  var displayFS =
    "precision highp float; varying vec2 vUv; uniform sampler2D uBase; uniform sampler2D uReveal; uniform sampler2D uDye;"+
    "uniform float revealSize; uniform float edgeSoft; uniform float edgeWidth; uniform float baseAspect; uniform float revealAspect; uniform float planeAspect;"+
    "vec2 coverUv(vec2 uv,float ia,float pa){ vec2 r=vec2(min(pa/ia,1.0),min(ia/pa,1.0)); return vec2(uv.x*r.x+(1.0-r.x)*0.5, uv.y*r.y+(1.0-r.y)*0.5); }"+
    "void main(){ float dye=texture2D(uDye,vUv).r; vec2 bU=clamp(coverUv(vUv,baseAspect,planeAspect),0.001,0.999); vec4 bC=texture2D(uBase,bU);"+
    " vec2 rU=clamp(coverUv(vUv,revealAspect,planeAspect),0.001,0.999); vec4 rC=texture2D(uReveal,rU);"+
    " float m=clamp(smoothstep(edgeSoft,edgeSoft+edgeWidth,dye*revealSize),0.0,1.0); gl_FragColor=mix(bC,rC,m); }";

  var P = {
    advect: prog(baseVS, advectFS), diverg: prog(baseVS, divergenceFS), press: prog(baseVS, pressureFS),
    grad: prog(baseVS, gradientFS), splat: prog(simpleVS, splatFS), clear: prog(simpleVS, clearFS), disp: prog(simpleVS, displayFS)
  };

  // Fullscreen-Quad
  var quad = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, quad);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
  function bindQuad(p){ gl.bindBuffer(gl.ARRAY_BUFFER, quad); var a=gl.getAttribLocation(p,'aPos'); gl.enableVertexAttribArray(a); gl.vertexAttribPointer(a,2,gl.FLOAT,false,0,0); }
  function draw(fbo){ gl.bindFramebuffer(gl.FRAMEBUFFER, fbo?fbo.fbo:null); gl.drawArrays(gl.TRIANGLE_STRIP,0,4); }

  function makeFBO(w,h,internal){ var tex=gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D,tex);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,w,h,0,gl.RGBA,HALF,null);
    var fbo=gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER,fbo); gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,tex,0);
    gl.viewport(0,0,w,h); gl.clear(gl.COLOR_BUFFER_BIT);
    return {tex:tex,fbo:fbo,w:w,h:h,texel:[1/w,1/h]}; }
  function makeDouble(w,h){ var a=makeFBO(w,h),b=makeFBO(w,h); return {read:a,write:b,w:w,h:h,texel:a.texel,swap:function(){var t=this.read;this.read=this.write;this.write=t;}}; }

  var velocity, dye, divergence, pressure;
  function initFBOs(){ velocity=makeDouble(SIM_RES,SIM_RES); dye=makeDouble(DYE_RES,DYE_RES); divergence=makeFBO(SIM_RES,SIM_RES); pressure=makeDouble(SIM_RES,SIM_RES); }
  initFBOs();

  // ---- Texturen: Base (clean) + Reveal (Illustration), Text eingebrannt ----
  var baseTex=gl.createTexture(), revealTex=gl.createTexture();
  var baseAspect=1, revealAspect=1;
  function uploadTex(tex, cnv){ gl.bindTexture(gl.TEXTURE_2D,tex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true); // Canvas oben-links → WebGL unten-links: vertikal flippen
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,cnv);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false); }

  var CSS = getComputedStyle(document.documentElement);
  function col(name,fb){ var v=CSS.getPropertyValue(name).trim(); return v||fb; }

  // Solid und Outline werden mit IDENTISCHER Geometrie (gleiche fs/x/y) gerendert,
  // damit die Buchstaben deckungsgleich sind — es wird nur das Bild dahinter freigelegt.
  // MOIN wird INK-GENAU am Grid verankert: die schwarzen Buchstaben-Ränder liegen exakt
  // mit dem Gap --hero-inset innerhalb der Zelle — links, rechts und oben identisch.
  function moinGeom(ctx, W, H){
    var clientW = stage.clientWidth, clientH = stage.clientHeight;
    var sx = W / clientW, sy = H / clientH;
    var padPx = Math.max(20, Math.min(0.04 * clientW, 64));       // = CSS var(--pad)
    var inset = HERO_INSET;                                       // Screen-px, synchron mit CSS
    // Ziel-Ink-Box in Canvas-px:
    var inkLeft = (padPx + inset) * sx;
    var inkW    = (clientW - 2 * padPx - 2 * inset) * sx;
    var inkTop  = (0.25 * clientH + inset) * sy;                  // ab der 25%-Gridlinie
    ctx.font = '800 300px Saira';
    var m0 = ctx.measureText('MOIN');
    var ink0 = m0.actualBoundingBoxRight + m0.actualBoundingBoxLeft;
    var fs = 300 * inkW / ink0;
    ctx.font = '800 ' + fs + 'px Saira';
    var m = ctx.measureText('MOIN');
    var penX = inkLeft + m.actualBoundingBoxLeft;                 // inkLeft = penX − abbLeft
    var penY = inkTop + m.actualBoundingBoxAscent;               // inkTop  = penY − ascent
    return { fs: fs, x: penX, y: penY };
  }
  function drawMoin(ctx, g, mode){
    var ink = col('--ink', '#171410');
    ctx.font = '800 ' + g.fs + 'px Saira';
    ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    if (mode === 'solid') { ctx.fillStyle = ink; ctx.fillText('MOIN', g.x, g.y); return; }
    // Outline INNEN: gedoppelter, mittiger Stroke, dann per destination-in auf die Glyphe
    // beschnitten → nur die innere Hälfte bleibt. Außenkante == Kante des soliden Buchstabens.
    var W = ctx.canvas.width, H = ctx.canvas.height;
    var t = document.createElement('canvas'); t.width = W; t.height = H; var tc = t.getContext('2d');
    tc.font = '800 ' + g.fs + 'px Saira'; tc.textAlign = 'left'; tc.textBaseline = 'alphabetic';
    tc.lineWidth = Math.max(2, g.fs * 0.022); tc.strokeStyle = ink; tc.lineJoin = 'round'; tc.miterLimit = 2;
    tc.strokeText('MOIN', g.x, g.y);
    tc.globalCompositeOperation = 'destination-in';
    tc.fillStyle = '#000'; tc.fillText('MOIN', g.x, g.y);
    ctx.drawImage(t, 0, 0);
  }
  function buildTextures(){
    // Texturbreite = Canvas-Breite. Alles darunter wird beim Zeichnen hochskaliert und
    // die Kanten des eingebrannten MOIN fransen sichtbar aus (vorher fix auf 2048 gedeckelt
    // → auf großen Screens Faktor 2 Upscaling).
    var W = Math.max(1024, canvas.width);
    var H = Math.round(W * stage.clientHeight/stage.clientWidth);
    // Base = Creme + solides MOIN
    var b=document.createElement('canvas'); b.width=W; b.height=H; var bx=b.getContext('2d');
    var g = moinGeom(bx, W, H);
    bx.fillStyle=col('--bg','#F0ECE2'); bx.fillRect(0,0,W,H); drawMoin(bx, g, 'solid');
    uploadTex(baseTex,b); baseAspect=W/H;
    // Reveal = bunte Illustration + MOIN-Outline (identische Geometrie g)
    var r=document.createElement('canvas'); r.width=W; r.height=H; var rx=r.getContext('2d');
    paintIllustration(rx,W,H); drawMoin(rx, g, 'outline');
    uploadTex(revealTex,r); revealAspect=W/H;
  }
  function paintIllustration(ctx,W,H){
    var cols=['#ff5ea8','#ffd23f','#23c9a7','#5b8cff','#b06bff','#ff7a1a'];
    ctx.fillStyle='#12100e'; ctx.fillRect(0,0,W,H);
    for(var i=0;i<70;i++){ // deterministische bunte Blobs (kein Math.random-Seed nötig fürs Gefühl)
      var gx=(i*97%100)/100*W, gy=(i*53%100)/100*H, rad=(0.12+0.2*((i*29%100)/100))*Math.min(W,H);
      var g=ctx.createRadialGradient(gx,gy,0,gx,gy,rad); var c=cols[i%cols.length];
      g.addColorStop(0,c); g.addColorStop(1,'rgba(0,0,0,0)'); ctx.globalCompositeOperation='screen'; ctx.fillStyle=g;
      ctx.beginPath(); ctx.arc(gx,gy,rad,0,7); ctx.fill();
    }
    ctx.globalCompositeOperation='source-over';
    // ein paar weiße Doodles
    ctx.strokeStyle='rgba(255,255,255,0.55)'; ctx.lineWidth=Math.max(2,W*0.002);
    for(var j=0;j<28;j++){ var x=(j*137%100)/100*W, y=(j*61%100)/100*H, s=Math.min(W,H)*0.03;
      ctx.beginPath(); if(j%3===0){ctx.arc(x,y,s,0,7);} else if(j%3===1){ctx.moveTo(x-s,y);ctx.lineTo(x+s,y);ctx.moveTo(x,y-s);ctx.lineTo(x,y+s);} else {ctx.moveTo(x-s,y-s);ctx.lineTo(x+s,y+s);ctx.moveTo(x+s,y-s);ctx.lineTo(x-s,y+s);} ctx.stroke(); }
  }

  // ---- Größe ----
  function resize(){ var dpr=Math.min(2,window.devicePixelRatio||1);
    var MAXD=4096, cw=stage.clientWidth, ch=stage.clientHeight;
    // Den MASSSTAB deckeln, nicht die Kanten einzeln: würde nur die Breite gekappt
    // (großer Screen: 2560×2 = 5120 → 4096, Höhe bleibt ungekappt), stimmte das
    // Seitenverhältnis des Canvas nicht mehr mit dem der Textur überein — der
    // Composite-Shader macht einen cover-Fit und zoomt die Textur seitlich aus dem Bild.
    var scale=Math.min(dpr, MAXD/cw, MAXD/ch);
    canvas.width=Math.round(cw*scale); canvas.height=Math.round(ch*scale);
    // Einheitlicher Gap Wort↔Gridzelle: einmal berechnen, für Canvas (MOIN) UND DOM (Subline) nutzen.
    HERO_INSET = Math.max(8, Math.min(0.012*stage.clientWidth, 20));
    document.documentElement.style.setProperty('--hero-inset', HERO_INSET+'px');
    buildTextures(); updateGridVars(); }
  function pageGridDocumentTop(){
    var pg = document.querySelector('.pagegrid');
    return pg ? pg.getBoundingClientRect().top + window.scrollY : 0;
  }
  // Unterkante der Subline-Zelle messen → Position von Unter-Linie + fortgesetzter 1/4-Linie.
  function updateGridVars(){
    var r = document.documentElement.style;
    var s = document.querySelector('.sub');
    if (s) {
      var st = stage.getBoundingClientRect();
      // Der Lead gehört immer vollständig in EINE Rasterzeile. Passt er ins untere
      // Viertel, beginnt er an der 75-%-Linie. Ist er höher, endet er stattdessen exakt
      // dort und sitzt geschlossen in der Zeile darüber — niemals mit einer Linie im Text.
      // getBoundingClientRect statt offsetHeight vermeidet einen Sub-Pixel-Überstand.
      var subHeight = s.getBoundingClientRect().height;
      var isAbsoluteSub = getComputedStyle(s).position === 'absolute';
      var lowerLine = 0.75 * stage.clientHeight;
      var subIsUpper = isAbsoluteSub && subHeight > stage.clientHeight - lowerLine;
      stage.classList.toggle('sub-is-upper', subIsUpper);
      r.setProperty('--sub-top', (subIsUpper ? lowerLine - subHeight : lowerLine) + 'px');
      var sb = s.getBoundingClientRect();
      var relBottom = sb.bottom - st.top;          // stage-relativ, für die Hero-Unterlinie
      var docTop = st.top + window.scrollY;        // Stage-Oberkante dokument-absolut
      var gridTop = pageGridDocumentTop();         // Ursprung des absoluten Linien-Layers
      r.setProperty('--sub-bottom', relBottom + 'px');
      // Grenzen der Lücke, die die durchgehende 1/4-Linie um die Subline-Zelle macht.
      // Beide Werte gehören zur lokalen y-Achse des Linien-Layers. Das ist auch dann
      // korrekt, wenn dessen absoluter Body-Ursprung nicht bei Dokument-y=0 liegt.
      r.setProperty('--gap-start', (docTop + 0.75 * stage.clientHeight - gridTop) + 'px');
      r.setProperty('--gap-end',   (docTop + relBottom - gridTop) + 'px');
    }
    buildLineGradients();
  }
  // Die Linienfarbe ist eine Funktion von y: über jeder .on-dark-Section hell, sonst dunkel.
  // Statt eines fest verdrahteten Bandes werden die Verläufe aus den gemessenen Kanten
  // gebaut — beliebig viele dunkle Sections, eine Stelle.
  function buildLineGradients(){
    var pg = document.querySelector('.pagegrid'); if (!pg) return;
    // Alle Stopps müssen relativ zum Linien-Layer sein. Auf Telefonen kann der Abstand
    // vor der Verfügbarkeitszeile den Body (und damit .pagegrid) per Margin-Collapse um
    // die Headerhöhe verschieben; Dokumentkoordinaten wechselten dort entsprechend zu spät.
    var gridTop = pageGridDocumentTop();
    var bands = [].map.call(document.querySelectorAll('.on-dark'), function(el){
      var r = el.getBoundingClientRect();
      return [r.top + window.scrollY - gridTop, r.bottom + window.scrollY - gridTop];
    }).sort(function(a,b){ return a[0]-b[0]; });

    // offset = lokaler Abstand der jeweiligen Linienoberkante vom .pagegrid-Ursprung;
    // nur .vsplit2 beginnt nicht bei 0.
    function grad(onLight, onDark, offset){
      var stops = [], y = 0;
      bands.forEach(function(b){
        stops.push(onLight+' '+(y-offset)+'px '+(b[0]-offset)+'px');
        stops.push(onDark +' '+(b[0]-offset)+'px '+(b[1]-offset)+'px');
        y = b[1];
      });
      stops.push(onLight+' '+(y-offset)+'px 100%');
      return 'linear-gradient(to bottom,'+stops.join(',')+')';
    }
    pg.style.setProperty('--line-strong', grad('var(--rule-strong)','var(--dark-ink)',0));
    pg.style.setProperty('--line-soft',   grad('var(--rule)','var(--dark-rule)',0));
    // Das untere Segment der 1/4-Linie beginnt erst bei --gap-end; seine eigene y-Achse
    // ist um diesen Betrag verschoben.
    var v2 = pg.querySelector('.vsplit2');
    if (v2) v2.style.backgroundImage =
      grad('var(--rule)','var(--dark-rule)', parseFloat(getComputedStyle(v2).top) || 0);
  }
  // About-Akkordeons und Reveal-Wellen verändern die Dokumenthöhe animiert. Damit die
  // eine globale Linienebene ihre Farbkanten dabei nicht an der alten Position behält,
  // folgt sie jeder echten Größenänderung des Hauptinhalts. requestAnimationFrame fasst
  // mehrere ResizeObserver-Signale desselben Frames zu genau einer Neuberechnung zusammen.
  var lineGradientFrame = 0;
  function requestLineGradients(){
    if (lineGradientFrame) return;
    lineGradientFrame = requestAnimationFrame(function(){
      lineGradientFrame = 0;
      buildLineGradients();
    });
  }
  if ('ResizeObserver' in window) {
    var lineLayoutObserver = new ResizeObserver(requestLineGradients);
    var mainContent = document.querySelector('main');
    if (mainContent) lineLayoutObserver.observe(mainContent);
    [].forEach.call(document.querySelectorAll('.on-dark'), function(section){
      lineLayoutObserver.observe(section);
    });
  }
  addEventListener('resize', updateGridVars, { passive: true });

  // ---- Splat: Geschwindigkeit + Dye eintragen ----
  function splat(x, y, dx, dy){
    var aspect=canvas.width/canvas.height;
    gl.viewport(0,0,velocity.w,velocity.h); gl.useProgram(P.splat); bindQuad(P.splat);
    gl.uniform1i(P.splat.uni.uTarget,0); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,velocity.read.tex);
    gl.uniform1f(P.splat.uni.aspect,aspect); gl.uniform2f(P.splat.uni.point,x,y);
    gl.uniform3f(P.splat.uni.color,dx,dy,0.0); gl.uniform1f(P.splat.uni.radius,SPLAT_RADIUS);
    draw(velocity.write); velocity.swap();
    gl.viewport(0,0,dye.w,dye.h); gl.bindTexture(gl.TEXTURE_2D,dye.read.tex);
    gl.uniform3f(P.splat.uni.color,1.0,1.0,1.0); // Dye = weiß = Maske
    draw(dye.write); dye.swap();
  }

  // ---- Pointer + scrollfreundliche Touch-Gestenerkennung ----
  var pointer={x:0,y:0,px:0,py:0,down:false,moved:false,force:1};
  var mouseSeeded=false, queue=[];
  var TOUCH_INTENT_DISTANCE=6, TOUCH_HORIZONTAL_RATIO=1.2;
  var touchGesture=null;
  var touchIdleDevice=navigator.maxTouchPoints>0||matchMedia('(pointer:coarse)').matches;
  var IDLE_INITIAL_DELAY=700, IDLE_RESUME_DELAY=3200, IDLE_FORCE_SCALE=0.28;
  var idleResumeAt=performance.now()+IDLE_INITIAL_DELAY;
  var idleVisible=true, idleWasRunning=false, idleAccumulator=0, idleT=0;
  var idlePhase=[Math.random()*6.283,Math.random()*6.283,Math.random()*6.283,
    Math.random()*6.283,Math.random()*6.283];
  var idleSpeed=0.88+Math.random()*0.24;
  var idleMenu=document.querySelector('.site-nav');

  function postponeIdle(delay){
    idleResumeAt=performance.now()+(delay==null?IDLE_RESUME_DELAY:delay);
    idleWasRunning=false; idleAccumulator=0;
  }
  function updateIdleVisibility(){
    var r=stage.getBoundingClientRect();
    idleVisible=r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth;
    syncSimulation();
  }
  updateIdleVisibility();
  if('IntersectionObserver' in window){
    new IntersectionObserver(function(entries){
      var wasVisible=idleVisible;
      idleVisible=!!(entries[0]&&entries[0].isIntersecting);
      if(!idleVisible)idleWasRunning=false;
      else if(!wasVisible)postponeIdle(IDLE_INITIAL_DELAY);
      syncSimulation();
    }).observe(stage);
  }else{
    addEventListener('scroll',updateIdleVisibility,{passive:true});
  }
  document.addEventListener('visibilitychange',function(){
    idleWasRunning=false; idleAccumulator=0;
    if(!document.hidden)postponeIdle(IDLE_INITIAL_DELAY);
    syncSimulation();
  });
  if(idleMenu)idleMenu.addEventListener('toggle',function(){
    postponeIdle(idleMenu.open?IDLE_RESUME_DELAY:IDLE_INITIAL_DELAY);
  });

  function toUV(clientX,clientY){ var r=canvas.getBoundingClientRect();
    return {x:(clientX-r.left)/r.width,y:1.0-(clientY-r.top)/r.height}; }
  function seedPointer(clientX,clientY){ var u=toUV(clientX,clientY);
    pointer.x=pointer.px=u.x; pointer.y=pointer.py=u.y; pointer.moved=false; }
  function movePointer(clientX,clientY){ var u=toUV(clientX,clientY);
    postponeIdle(); pointer.force=1;
    pointer.px=pointer.x; pointer.py=pointer.y; pointer.x=u.x; pointer.y=u.y; pointer.moved=true; }
  function moveMousePointer(clientX,clientY){
    if(!mouseSeeded){mouseSeeded=true;postponeIdle();pointer.force=1;seedPointer(clientX,clientY);return;}
    movePointer(clientX,clientY);
  }
  function beginTouch(id,clientX,clientY){
    mouseSeeded=false; postponeIdle(); pointer.force=1; seedPointer(clientX,clientY);
    touchGesture={id:id,startX:clientX,startY:clientY,intent:'pending'};
  }
  function moveTouch(id,clientX,clientY){
    if(!touchGesture||touchGesture.id!==id||touchGesture.intent==='scroll') return false;
    if(touchGesture.intent==='pending'){
      var dx=clientX-touchGesture.startX,dy=clientY-touchGesture.startY;
      if(dx*dx+dy*dy<TOUCH_INTENT_DISTANCE*TOUCH_INTENT_DISTANCE) return false;
      // Im Zweifel scrollen: Nur eine deutlich horizontalere Bewegung darf revealen.
      touchGesture.intent=Math.abs(dx)>Math.abs(dy)*TOUCH_HORIZONTAL_RATIO?'horizontal':'scroll';
      if(touchGesture.intent!=='horizontal') return false;
    }
    movePointer(clientX,clientY); return true;
  }

  // Maus und Stift behalten die direkte Desktopsteuerung. Touch wird hier bewusst
  // ignoriert, sobald echte Touch Events verfügbar sind, damit Safari nicht denselben
  // Kontakt als Pointer- und Touch-Stream doppelt in die Simulation einspeist.
  if('PointerEvent' in window){
    stage.addEventListener('pointermove',function(e){
      if(e.pointerType==='touch') return;
      moveMousePointer(e.clientX,e.clientY);
    },{passive:true});
  }

  var useTouchEvents=('ontouchstart' in window||navigator.maxTouchPoints>0)&&typeof TouchEvent!=='undefined';
  if(useTouchEvents){
    stage.classList.add('uses-touch-events');
    function findTouch(list,id){
      for(var i=0;i<list.length;i++)if(list[i].identifier===id)return list[i];
      return null;
    }
    // Der Listener existiert vor Gestenbeginn und touchmove ist nicht passiv. So kann iOS
    // nach der frühen horizontalen Klassifikation noch rechtzeitig vom Scrollen absehen.
    addEventListener('touchstart',function(e){
      mouseSeeded=false;
      if(e.touches.length===1&&stage.contains(e.target)){
        var t=e.touches[0];beginTouch(t.identifier,t.clientX,t.clientY);
      }else if(touchGesture){
        postponeIdle();
        touchGesture.intent='scroll'; // Mehrfinger- und außerhalb begonnene Gesten nie revealen.
      }
    },{passive:true,capture:true});
    stage.addEventListener('touchmove',function(e){
      if(e.touches.length!==1||!touchGesture){
        if(touchGesture)touchGesture.intent='scroll';
        return;
      }
      var t=findTouch(e.touches,touchGesture.id);
      if(t&&moveTouch(t.identifier,t.clientX,t.clientY)&&e.cancelable)e.preventDefault();
    },{passive:false});
    function finishTouch(e){
      if(!touchGesture)return;
      if(!findTouch(e.touches,touchGesture.id)){touchGesture=null;postponeIdle();}
      else if(e.touches.length!==1)touchGesture.intent='scroll';
    }
    addEventListener('touchend',finishTouch,{passive:true,capture:true});
    addEventListener('touchcancel',finishTouch,{passive:true,capture:true});
  }else if('PointerEvent' in window){
    // Touch-Fallback für Pointer-Event-Browser, die keine Touch Events bereitstellen.
    var touchContacts={},touchContactCount=0;
    // Kontakte global mitzählen: Auch ein zweiter Finger außerhalb des Heros muss eine
    // bereits horizontale Reveal-Geste beenden, damit native Zoomgesten Vorrang behalten.
    addEventListener('pointerdown',function(e){
      if(e.pointerType!=='touch') return;
      mouseSeeded=false;
      if(!touchContacts[e.pointerId]){touchContacts[e.pointerId]=true;touchContactCount++;}
      if(touchContactCount===1&&stage.contains(e.target)) beginTouch(e.pointerId,e.clientX,e.clientY);
      else if(touchGesture){postponeIdle();touchGesture.intent='scroll';} // Nie per Mehrfinger-Geste revealen.
    },{passive:true,capture:true});
    stage.addEventListener('pointermove',function(e){
      if(e.pointerType!=='touch')return;
      if(touchContactCount!==1||!moveTouch(e.pointerId,e.clientX,e.clientY)) return;
      // touch-action:pan-y trifft die Browserentscheidung; preventDefault ist erst nach
      // eindeutig horizontalem Intent ein zusätzlicher Schutz für Implementierungen,
      // die trotz der CSS-Deklaration noch eine Standardaktion vorsehen.
      if(e.cancelable) e.preventDefault();
      if(stage.setPointerCapture&&!stage.hasPointerCapture(e.pointerId)){
        try{stage.setPointerCapture(e.pointerId);}catch(ignore){}
      }
    },{passive:false});
    function finishPointerTouch(e){
      if(e.pointerType!=='touch') return;
      if(touchContacts[e.pointerId]){delete touchContacts[e.pointerId];touchContactCount--;}
      if(touchGesture&&touchGesture.id===e.pointerId){touchGesture=null;postponeIdle();}
      if(touchContactCount===0){touchContacts={};touchGesture=null;}
    }
    addEventListener('pointerup',finishPointerTouch,{passive:true,capture:true});
    addEventListener('pointercancel',finishPointerTouch,{passive:true,capture:true});
  }

  function idlePoint(){
    var t=idleT*idleSpeed;
    return {
      x:0.5+0.14*Math.sin(t*0.24+idlePhase[0])+0.055*Math.sin(t*0.53+idlePhase[1])+0.025*Math.sin(t*0.91+idlePhase[2]),
      y:0.52+0.095*Math.sin(t*0.19+idlePhase[3])+0.04*Math.cos(t*0.47+idlePhase[4])
    };
  }
  function updateTouchIdle(dt,now){
    var allowed=touchIdleDevice&&!reduce&&!document.hidden&&idleVisible&&!touchGesture&&
      (!idleMenu||!idleMenu.open)&&now>=idleResumeAt;
    if(!allowed){idleWasRunning=false;idleAccumulator=0;return;}
    idleT+=dt; idleAccumulator+=dt;
    var p=idlePoint();
    if(!idleWasRunning){
      pointer.x=pointer.px=p.x;pointer.y=pointer.py=p.y;pointer.moved=false;
      idleWasRunning=true;idleAccumulator=0;return;
    }
    // 30 Hz reichen für die langsame Einladung und halbieren ihre Splat-Last auf Mobile.
    if(idleAccumulator<1/30)return;
    idleAccumulator-=1/30;pointer.px=pointer.x;pointer.py=pointer.y;
    pointer.x=p.x;pointer.y=p.y;pointer.force=IDLE_FORCE_SCALE;pointer.moved=true;
  }

  function step(dt){
    updateTouchIdle(dt,performance.now());
    if(pointer.moved){ var dx=(pointer.x-pointer.px)*SPLAT_FORCE*pointer.force, dy=(pointer.y-pointer.py)*SPLAT_FORCE*pointer.force;
      if(Math.abs(dx)>0.0001||Math.abs(dy)>0.0001) splat(pointer.x,pointer.y,dx,dy); pointer.moved=false; }

    // 1) Advektion Geschwindigkeit
    gl.viewport(0,0,velocity.w,velocity.h);
    gl.useProgram(P.advect); bindQuad(P.advect);
    gl.uniform2f(P.advect.uni.texel,velocity.texel[0],velocity.texel[1]);
    gl.uniform1f(P.advect.uni.dt,dt); gl.uniform1f(P.advect.uni.dissipation,VEL_DISSIP);
    gl.uniform1i(P.advect.uni.uVelocity,0); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,velocity.read.tex);
    gl.uniform1i(P.advect.uni.uSource,0);
    draw(velocity.write); velocity.swap();

    // 2) Divergenz
    gl.useProgram(P.diverg); bindQuad(P.diverg);
    gl.uniform2f(P.diverg.uni.texel,velocity.texel[0],velocity.texel[1]);
    gl.uniform1i(P.diverg.uni.uVelocity,0); gl.bindTexture(gl.TEXTURE_2D,velocity.read.tex);
    draw(divergence);

    // 3) Druck (Jacobi ×N), mit leichter Dissipation via clear
    gl.useProgram(P.clear); bindQuad(P.clear);
    gl.uniform1i(P.clear.uni.uTexture,0); gl.bindTexture(gl.TEXTURE_2D,pressure.read.tex); gl.uniform1f(P.clear.uni.value,PRESSURE);
    draw(pressure.write); pressure.swap();
    gl.useProgram(P.press); bindQuad(P.press);
    gl.uniform2f(P.press.uni.texel,velocity.texel[0],velocity.texel[1]);
    gl.uniform1i(P.press.uni.uDivergence,1); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D,divergence.tex);
    for(var i=0;i<PRESS_ITER;i++){ gl.uniform1i(P.press.uni.uPressure,0); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,pressure.read.tex); draw(pressure.write); pressure.swap(); }

    // 4) Gradient subtrahieren
    gl.useProgram(P.grad); bindQuad(P.grad);
    gl.uniform2f(P.grad.uni.texel,velocity.texel[0],velocity.texel[1]);
    gl.uniform1i(P.grad.uni.uPressure,0); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,pressure.read.tex);
    gl.uniform1i(P.grad.uni.uVelocity,1); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D,velocity.read.tex);
    draw(velocity.write); velocity.swap();

    // 5) Advektion Dye
    gl.viewport(0,0,dye.w,dye.h);
    gl.useProgram(P.advect); bindQuad(P.advect);
    gl.uniform2f(P.advect.uni.texel,dye.texel[0],dye.texel[1]);
    gl.uniform1f(P.advect.uni.dt,dt); gl.uniform1f(P.advect.uni.dissipation,DYE_DISSIP);
    gl.uniform1i(P.advect.uni.uVelocity,0); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,velocity.read.tex);
    gl.uniform1i(P.advect.uni.uSource,1); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D,dye.read.tex);
    draw(dye.write); dye.swap();

    render();
  }

  function render(){
    // Anzeige: base/reveal per Dye mischen (auch ohne laufende Simulation).
    gl.viewport(0,0,canvas.width,canvas.height);
    gl.bindFramebuffer(gl.FRAMEBUFFER,null);
    gl.useProgram(P.disp); bindQuad(P.disp);
    gl.uniform1i(P.disp.uni.uBase,0); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,baseTex);
    gl.uniform1i(P.disp.uni.uReveal,1); gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D,revealTex);
    gl.uniform1i(P.disp.uni.uDye,2); gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D,dye.read.tex);
    gl.uniform1f(P.disp.uni.revealSize,REVEAL_SIZE); gl.uniform1f(P.disp.uni.edgeSoft,EDGE_SOFT); gl.uniform1f(P.disp.uni.edgeWidth,EDGE_WIDTH);
    gl.uniform1f(P.disp.uni.baseAspect,baseAspect); gl.uniform1f(P.disp.uni.revealAspect,revealAspect); gl.uniform1f(P.disp.uni.planeAspect,canvas.width/canvas.height);
    draw(null);
  }

  var last=0, simulationFrame=0, simulationReady=false;
  function disableSimulation(){
    simulationReady=false;
    if(simulationFrame)cancelAnimationFrame(simulationFrame);
    simulationFrame=0; pointer.moved=false; mouseSeeded=false;
    removeEventListener('resize',resizeSimulation);
    disableWebGL();
  }
  function frame(t){
    simulationFrame=0;
    if(!simulationReady||reduce||document.hidden||!idleVisible)return;
    var dt=Math.min(0.016,(t-last)/1000)||0.016;
    last=t;
    try {
      step(dt);
    } catch (error) {
      disableSimulation();
      return;
    }
    if(simulationReady)simulationFrame=requestAnimationFrame(frame);
  }
  function syncSimulation(){
    if(!simulationReady)return;
    if(reduce||document.hidden||!idleVisible){
      if(simulationFrame)cancelAnimationFrame(simulationFrame);
      simulationFrame=0; pointer.moved=false; mouseSeeded=false;
      return;
    }
    if(!simulationFrame){last=performance.now();simulationFrame=requestAnimationFrame(frame);}
  }
  function resizeSimulation(){
    if(!simulationReady)return;
    try {
      resize(); render();
    } catch (error) {
      disableSimulation();
      return;
    }
    syncSimulation();
  }
  function syncMotionPreference(){
    reduce=motionPreference.matches;
    idleWasRunning=false; idleAccumulator=0; pointer.moved=false;
    syncSimulation();
  }
  if(motionPreference.addEventListener)motionPreference.addEventListener('change',syncMotionPreference);
  else motionPreference.addListener(syncMotionPreference);
  var startAttempted=false;
  function start(){
    if(startAttempted)return;
    startAttempted=true;
    try {
      resize(); render();
      simulationReady=true;
      addEventListener('resize',resizeSimulation,{passive:true});
      syncSimulation();
    } catch (error) {
      disableSimulation();
    }
  }
  if(document.fonts && document.fonts.ready){
    try {
      Promise.resolve(document.fonts.load('800 40px Saira'))
        .then(function(){return document.fonts.ready;})
        .then(start, start);
    } catch (error) {
      start();
    }
  } else start();
  }

// Jede nachfolgende Verfeinerung bleibt ein eigenständiges Progressive-Enhancement.
// Ein Defekt in einer optionalen Funktion darf deshalb weder die nativen Inhalte noch
// spätere Verfeinerungen (zum Beispiel Reel, Akkordeon oder Cursor) abschalten.
function runPortfolioEnhancement(name, initialize) {
  try {
    initialize();
  } catch (error) {
    // Die Diagnose ist hilfreich, aber selbst eine exotische/ersetzte Console darf die
    // Fehlergrenze nicht wieder durchbrechen.
    try {
      if (typeof console !== 'undefined' && typeof console.error === 'function') {
        console.error('Portfolio enhancement failed: ' + name, error);
      }
    } catch (reportingError) {
      // Progressive Enhancement bleibt auch ohne nutzbare Entwicklerkonsole intakt.
    }
  }
}

// Navigation und Scroll-Lock arbeiten zusammen: normale Scrollversuche bleiben bei
// offenem Panel gesperrt, nur der bewusst ausgelöste Ankerflug darf die Seite bewegen.
runPortfolioEnhancement('navigation', function () {
  var menu = document.querySelector('.site-nav');
  if (!menu) return;
  var lockedY = null;
  var anchorFlight = false;
  var flightTimer = 0;
  var desktopHover = matchMedia('(min-width: 52.001rem) and (hover: hover) and (pointer: fine)');
  var motionReduce = matchMedia('(prefers-reduced-motion: reduce)');
  var toggle = menu.querySelector('summary');
  var menuLinks = [].slice.call(menu.querySelectorAll('nav a'));
  var menuStops = [].slice.call(menu.querySelectorAll('nav a, nav summary'));
  var inertTargets = [].slice.call(document.querySelectorAll(
    'main, body > footer, header.site > .brand, header.site > .avail, header.site > .header-actions > .pill'
  ));

  function localTarget(link) {
    var url = new URL(link.href, location.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname || !url.hash) return null;
    return document.getElementById(decodeURIComponent(url.hash.slice(1)));
  }
  function flyTo(link, keepOpen) {
    var target = localTarget(link);
    if (!target) return false;
    clearTimeout(flightTimer);
    anchorFlight = true;
    if (!keepOpen) {
      lockedY = null;
      menu.removeAttribute('open');
      history.pushState(null, '', link.hash);
    }
    requestAnimationFrame(function () {
      target.scrollIntoView({ behavior: motionReduce.matches ? 'auto' : 'smooth', block: 'start' });
    });
    flightTimer = setTimeout(function () {
      anchorFlight = false;
      if (menu.open) lockedY = window.scrollY;
    }, 850);
    return true;
  }

  menu.addEventListener('toggle', function () {
    lockedY = menu.open ? window.scrollY : null;
    toggle.setAttribute('aria-label', menu.open ? 'Menü schließen' : 'Menü');
    inertTargets.forEach(function (node) { node.inert = menu.open; });
    if (!menu.open) anchorFlight = false;
  });
  menuLinks.forEach(function (link) {
    link.addEventListener('click', function (event) {
      if (flyTo(link, false)) event.preventDefault();
      else menu.removeAttribute('open');
    });
    link.addEventListener('pointerenter', function () {
      if (desktopHover.matches) flyTo(link, true);
    });
  });
  function insidePanel(target) {
    return target instanceof Element && !!target.closest('.site-nav nav');
  }
  var panelTouchY = null;
  addEventListener('touchstart', function (event) {
    panelTouchY = lockedY !== null && event.touches.length === 1 && insidePanel(event.target)
      ? event.touches[0].clientY
      : null;
  }, { passive: true });
  function stopOutsidePanel(event) {
    if (lockedY === null) return;
    if (!insidePanel(event.target)) {
      if (event.type === 'touchmove' && event.touches.length !== 1) return;
      event.preventDefault();
      return;
    }
    if (event.type !== 'touchmove') return;
    // iOS darf eine Bewegung an der oberen/unteren Panelkante nicht an den
    // Root-Scroller weiterreichen. Innerhalb des Panels bleibt natives Scrollen erhalten.
    if (event.touches.length !== 1 || panelTouchY === null) return;
    var panel = event.target.closest('.site-nav nav');
    var nextY = event.touches[0].clientY;
    var deltaY = nextY - panelTouchY;
    panelTouchY = nextY;
    var atTop = panel.scrollTop <= 0.5;
    var atBottom = panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 0.5;
    if ((deltaY > 0 && atTop) || (deltaY < 0 && atBottom)) event.preventDefault();
  }
  addEventListener('wheel', stopOutsidePanel, { passive: false });
  addEventListener('touchmove', stopOutsidePanel, { passive: false });
  addEventListener('touchend', function () { panelTouchY = null; }, { passive: true });
  addEventListener('touchcancel', function () { panelTouchY = null; }, { passive: true });
  addEventListener('scroll', function () {
    if (lockedY !== null && !anchorFlight && window.scrollY !== lockedY) window.scrollTo(0, lockedY);
  }, { passive: true });
  document.addEventListener('keydown', function (event) {
    if (!menu.open) return;
    if (event.key === 'Escape') {
      menu.removeAttribute('open');
      toggle.focus();
      event.preventDefault();
      return;
    }
    if (event.key === 'Tab') {
      var stops = [toggle].concat(menuStops);
      var first = stops[0], last = stops[stops.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        last.focus(); event.preventDefault();
      } else if (!event.shiftKey && document.activeElement === last) {
        first.focus(); event.preventDefault();
      }
      return;
    }
    if (lockedY === null || insidePanel(event.target)) return;
    if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '].includes(event.key)) {
      event.preventDefault();
    }
  });
  document.addEventListener('click', function (event) {
    if (menu.open && !menu.contains(event.target)) menu.removeAttribute('open');
  });
});
// Höhe der Navigation als CSS-Variable. Eigener Block, damit er auch ohne WebGL läuft.
// ResizeObserver statt Media Query: der Header wächst je nach Inhalt und Textgröße
// (auf schmalen Breiten bricht die Wortmarke um) — die Hero-Höhe folgt dem fluide.
runPortfolioEnhancement('header', function () {
  var head = document.querySelector('header.site');
  if (!head) return;
  function sync() {
    document.documentElement.style.setProperty(
      '--header-h', head.getBoundingClientRect().height + 'px');
  }
  sync();
  if ('ResizeObserver' in window) new ResizeObserver(sync).observe(head);
  addEventListener('resize', sync, { passive: true });

  // Scroll-Hinweis ausblenden, sobald er befolgt wurde.
  var root = document.documentElement;
  function scrolled() {
    root.classList.toggle('is-scrolled', window.scrollY > 40);
  }
  scrolled();
  addEventListener('scroll', scrolled, { passive: true });
});
// Slide-Indicator für die Reels. Eigener Block, damit er auch ohne WebGL läuft —
// das Hero-Skript steigt bei fehlendem Kontext früh aus.
runPortfolioEnhancement('reels', function () {
  var bars = document.querySelectorAll('.reelbar');
  Array.prototype.forEach.call(bars, function (bar) {
    var reel = bar.previousElementSibling;
    var track = bar.querySelector('.reelbar-track');
    var thumb = bar.querySelector('.reelbar-thumb');
    if (!reel || !track || !thumb) return;

    // Breite des Anfassers = sichtbarer Anteil, Position = Scrollfortschritt.
    function sync() {
      var max = reel.scrollWidth - reel.clientWidth;
      var isScrollable = max > 1;
      bar.classList.toggle('is-scrollable', isScrollable);
      reel.tabIndex = isScrollable ? 0 : -1;
      if (max <= 1) return;
      var frac = reel.clientWidth / reel.scrollWidth;
      var pos = reel.scrollLeft / max;
      thumb.style.setProperty('--thumb-size', (frac * 100) + '%');
      thumb.style.setProperty('--thumb-pos', (pos * (100 - frac * 100)) + '%');
      thumb.setAttribute('aria-valuenow', Math.round(pos * 100));
    }
    reel.addEventListener('scroll', sync, { passive: true });
    if ('ResizeObserver' in window) new ResizeObserver(sync).observe(reel);
    addEventListener('resize', sync, { passive: true });
    sync();

    // Ziehen: zurückgelegte Strecke auf der Spur → Scrollstrecke im Reel.
    var dragging = false, startX = 0, startScroll = 0;
    thumb.addEventListener('pointerdown', function (e) {
      dragging = true; startX = e.clientX; startScroll = reel.scrollLeft;
      thumb.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    thumb.addEventListener('pointermove', function (e) {
      if (!dragging) return;
      var travel = track.clientWidth - thumb.offsetWidth;
      var max = reel.scrollWidth - reel.clientWidth;
      if (travel > 0) reel.scrollLeft = startScroll + (e.clientX - startX) * (max / travel);
    });
    ['pointerup', 'pointercancel'].forEach(function (t) {
      thumb.addEventListener(t, function () { dragging = false; });
    });

    // Tastatur: der Anfasser bildet den horizontalen Scrollstand semantisch ab.
    thumb.addEventListener('keydown', function (e) {
      var step = reel.clientWidth * 0.6;
      if (e.key === 'ArrowRight') { reel.scrollLeft += step; e.preventDefault(); }
      else if (e.key === 'ArrowLeft') { reel.scrollLeft -= step; e.preventDefault(); }
      else if (e.key === 'Home') { reel.scrollLeft = 0; e.preventDefault(); }
      else if (e.key === 'End') { reel.scrollLeft = reel.scrollWidth; e.preventDefault(); }
    });
  });
});
// Zerlegt den Fließtext einer Kachel beim Öffnen in seine gesetzten ZEILEN, damit jede
// einzeln von unten hereinfahren kann — CSS kann Zeilen eines umbrochenen Absatzes nicht
// ansprechen. Nach dem Lauf wird der Absatz wieder zu reinem Text: so bleibt er für die
// Seitensuche und für Screenreader ein zusammenhängender Satz und nicht eine Kette von
// Bruchstücken. Ohne JavaScript oder bei `prefers-reduced-motion` steht der Text
// unverändert da.
runPortfolioEnhancement('about-lines', function () {
  var reduce = matchMedia("(prefers-reduced-motion: reduce)");

  document.querySelectorAll(".about .me-row").forEach(function (row) {
    var p = row.querySelector("p");
    if (!p) return;
    var text = p.textContent;

    function zurueck() { p.textContent = text; }

    // Sucht die Zeichenpositionen, an denen der Browser umbrochen hat, und baut daraus
    // je Zeile ein <span class="ln"><span>…</span></span>.
    function zerlegen() {
      p.textContent = text;
      var node = p.firstChild;
      var rng = document.createRange();
      rng.selectNodeContents(p);

      // Oberkanten der gesetzten Zeilen
      var tops = [];
      [].forEach.call(rng.getClientRects(), function (r) {
        if (!r.height) return;
        if (!tops.length || r.top > tops[tops.length - 1] + 1) tops.push(r.top);
      });
      if (tops.length < 2) return false;

      // Das erste Zeichen nach einem GETRENNTEN Umbruch meldet ZWEI Rechtecke: eines am
      // Ende der alten Zeile (dort sitzt der erzeugte Trennstrich) und eines am Anfang
      // der neuen. `getBoundingClientRect()` bildet daraus die Vereinigung und liefert
      // die OBERE — das Zeichen sähe damit aus, als gehörte es noch zur alten Zeile, und
      // die Umbruchstelle läge ein Zeichen zu spät („ausm-" statt „aus-", nachgemessen
      // 18px zu breit). Das unterste Rechteck ist die richtige Antwort.
      function topBei(i) {
        rng.setStart(node, i); rng.setEnd(node, i + 1);
        var rs = rng.getClientRects(), t = -Infinity;
        for (var k = 0; k < rs.length; k++) if (rs[k].height) t = Math.max(t, rs[k].top);
        return t === -Infinity ? rng.getBoundingClientRect().top : t;
      }
      // Binäre Suche statt Zeichen für Zeichen: ~9 Messungen je Zeile statt ~380.
      var stellen = [], vorher = 0;
      for (var l = 1; l < tops.length; l++) {
        var lo = vorher, hi = text.length - 1;
        while (lo < hi) {
          var mid = (lo + hi) >> 1;
          if (topBei(mid) >= tops[l] - 1) hi = mid; else lo = mid + 1;
        }
        stellen.push(lo); vorher = lo;
      }

      var zeilen = [], start = 0;
      stellen.concat([text.length]).forEach(function (b) {
        // Liegt der Umbruch mitten im Wort, hat der Browser getrennt — der Trennstrich
        // wird beim Setzen erzeugt und steht NICHT im Text. Hier muss er zurück, sonst
        // verschwände er beim Zerlegen.
        var stueck = text.slice(start, b);
        if (b < text.length && text.charAt(b - 1) !== " " && text.charAt(b) !== " ") stueck += "-";
        // Leerzeichen am Zeilenende bleiben stehen: ohne sie klebten beim Auslesen die
        // Wörter aneinander („schon denganzen Weg") — für Screenreader, Kopieren und
        // die Seitensuche.
        zeilen.push(stueck);
        start = b;
      });

      p.textContent = "";
      zeilen.forEach(function (t, i) {
        var aussen = document.createElement("span");
        aussen.className = "ln";
        aussen.style.setProperty("--i", i);
        var innen = document.createElement("span");
        innen.textContent = t;
        aussen.appendChild(innen);
        p.appendChild(aussen);
      });
      return true;
    }

    // Zurückgesetzt wird, sobald die Animation durch ist. Das ist inzwischen gefahrlos:
    // Weil diese Absätze ohne Silbentrennung gesetzt sind, liegen die Umbrüche nur auf
    // Leerzeichen — die Zerlegung bildet den natürlichen Umbruch also exakt ab und das
    // Zurücksetzen ändert nichts Sichtbares. (Mit Trennung sprang der Absatz an dieser
    // Stelle sichtbar um, deshalb lag das Zurücksetzen vorher beim Schließen.)
    // Es löst zugleich das Resize-Problem: Zeilen-Spans tragen festen Inhalt und
    // `nowrap`, sie brechen bei einer Fensteränderung nicht neu um. Als reiner Text
    // tut der Absatz das von selbst.
    var timer = 0, frame = 0;
    var DAUER = 640, VERSATZ = 105;   // muss zu den Werten im CSS passen

    // Gemessen wird NICHT im `toggle`-Ereignis selbst: Dort ist der Inhalt teilweise noch
    // `content-visibility: hidden` mit Höhe 0, die Zerlegung findet dann keine Zeilen und
    // die Animation fällt ersatzlos aus. Deshalb ein Frame später — und wenn es dann immer
    // noch nicht klappt, bis zu drei weitere Male. Der Aufwand ist gering (ein Frame
    // Verzögerung ist unsichtbar), aber ein sporadisch ausfallender Effekt fühlt sich
    // kaputt an, und die Ursache ließ sich in 96 Öffnungen nicht reproduzieren.
    function versuchen(rest) {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(function () {
        if (!row.open) { zurueck(); return; }
        if (!zerlegen()) {
          if (rest > 0) { versuchen(rest - 1); return; }
          zurueck(); return;
        }
        var zeilen = p.querySelectorAll(".ln").length;
        var letzte = p.querySelector(".ln:last-child > span");
        // Zurücksetzen, wenn die LETZTE Zeile fertig ist — verlässlicher als eine
        // gerechnete Wartezeit, die bei jeder Änderung an Dauer oder Versatz nachgezogen
        // werden müsste. Der Zeitgeber bleibt als Netz, falls das Ereignis ausbleibt
        // (etwa weil die Kachel zwischendurch geschlossen wurde).
        if (letzte) letzte.addEventListener("animationend", zurueck, { once: true });
        timer = setTimeout(zurueck, DAUER + (zeilen - 1) * VERSATZ + 400);
      });
    }

    function zeigen() {
      clearTimeout(timer);
      cancelAnimationFrame(frame);
      if (!row.open || reduce.matches) { zurueck(); return; }
      versuchen(3);
    }
    row.addEventListener("toggle", zeigen);
    // Sicherheitsnetz: Wird während der Animation die Breite geändert, sofort zurück
    // auf reinen Text — sonst stünden dort Zeilen, die zur neuen Breite nicht passen.
    addEventListener("resize", function () {
      clearTimeout(timer); cancelAnimationFrame(frame); zurueck();
    }, { passive: true });
  });
});
// Die ganze Kachel schließt, nicht nur ihre Kopfzeile. Eigener Block, damit er auch
// ohne WebGL läuft. Die Kopfzeile bleibt die eigentliche Bedienung — sie ist ein
// <summary> und damit fokussierbar, per Tastatur schaltbar und für Screenreader als
// aufklappbar angekündigt. Das hier ist eine reine Mausbequemlichkeit obendrauf.
runPortfolioEnhancement('about-tiles', function () {
  document.querySelectorAll(".about .me-row").forEach(function (row) {
    row.addEventListener("click", function (e) {
      if (e.target.closest("summary")) return;          // schaltet schon selbst
      // Wer im Text etwas markiert hat, wollte nicht klappen, sondern lesen.
      var sel = window.getSelection();
      if (sel && !sel.isCollapsed) return;
      row.open = false;
    });
  });
});
// Custom Cursor über dem Hero. Eigener Block, damit er auch ohne WebGL läuft.
runPortfolioEnhancement('custom-cursor', function () {
  var stage = document.getElementById('stage');
  var cur = document.querySelector('.cursor');
  if (!stage || !cur) return;
  var finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;
  var touchPointer = navigator.maxTouchPoints > 0 || matchMedia('(pointer: coarse)').matches;
  if (!finePointer) {
    if (touchPointer) {
      stage.appendChild(cur);
      cur.classList.add('touch-hint');
      addEventListener('touchmove', function () {
        cur.classList.add('is-dismissed');
      }, { passive: true, once: true });
    }
    return;
  }

  var tx = 0, ty = 0, x = 0, y = 0, raf = 0;
  // Nachlaufen mit Lerp: der Ring hängt dem Zeiger eine Spur hinterher, das nimmt ihm
  // die Härte und passt zur trägen Bewegung der Flüssigkeitssimulation darunter.
  function loop() {
    x += (tx - x) * 0.2; y += (ty - y) * 0.2;
    cur.style.transform = 'translate3d(' + x + 'px,' + y + 'px,0)';
    raf = requestAnimationFrame(loop);
  }
  addEventListener('pointermove', function (e) { tx = e.clientX; ty = e.clientY; }, { passive: true });
  stage.addEventListener('pointerenter', function (e) {
    tx = x = e.clientX; ty = y = e.clientY;      // ohne Sprung einsetzen
    cur.style.transform = 'translate3d(' + x + 'px,' + y + 'px,0)';
    document.documentElement.classList.add('stage-hover');
    if (!raf) raf = requestAnimationFrame(loop);
  });
  stage.addEventListener('pointerleave', function () {
    document.documentElement.classList.remove('stage-hover');
    cancelAnimationFrame(raf); raf = 0;
  });
});
// SMIL kennt prefers-reduced-motion nicht, und display:none auf dem <animate> stoppt es
// nicht zuverlässig. pauseAnimations() ist der dafür vorgesehene Weg — es friert die
// Form in ihrer Ausgangslage ein.
runPortfolioEnhancement('reduced-motion-shapes', function () {
  var svg = document.querySelector('.shapes');
  if (!svg || !svg.pauseAnimations) return;
  var mq = matchMedia('(prefers-reduced-motion: reduce)');
  var apply = function () { mq.matches ? svg.pauseAnimations() : svg.unpauseAnimations(); };
  apply();
  mq.addEventListener ? mq.addEventListener('change', apply) : mq.addListener(apply);
});
})();
