# `homepage.handwriting` — self-writing CV section labels

Renders the django-resume **editorial** CV section labels (script font
*AstaginaSignature* / "Editorial Script") as a self-writing handwriting SVG that
animates on scroll, driven by a reusable Django template tag. Font-free at
runtime: the composer reads only a generated `glyph_data.json` (no `fonttools`,
no font file at request time).

## Pipeline

```
AstaginaSignature.woff2  +  hand-traced skeleton strokes        (~/gitprojects/handwriting-anim)
        │  export_glyph_data.py
        ▼
glyph_data.json   (outlines + strokes + advances + ligatures)   ← committed, copied into this app
        │  compose.compose_label(text)
        ▼
inline <svg>  +  visually-hidden real text                      ← {% handwriting_label %}
        │  handwriting.css (default = written) + handwriting.js (scroll-trigger)
        ▼
label writes itself on scroll; readable without JS / with reduced-motion
```

To regenerate the data after re-tracing or font changes, run the export in the
source repo and copy the artifact in:

```
cd ~/gitprojects/handwriting-anim
uv run --with fonttools --with brotli --with numpy --with pillow \
       --with scikit-image --with scipy --with svgpathtools python export_glyph_data.py
cp glyph_data.json ~/gitprojects/homepage/homepage/handwriting/glyph_data.json
```

## Rendering (the hard-won rules — do not regress)

The visual is built from two layers in one inline SVG:

1. **Ink = the exact font glyph.** ONE combined `<path>` with
   `fill-rule="nonzero"` over all glyph contours. This reproduces the font
   pixel-for-pixel (verified by outline overlay):
   - **Not `even-odd`** — even-odd turns the *overlaps* of cursive script
     (connections + self-overlaps) into holes → cut-outs and thinner strokes.
   - **Not one filled `<path>` per contour** — separate nonzero paths *blob* the
     counters (the 'o'/'a'/'e' holes fill in).
   `nonzero` keeps counters open (opposite winding) **and** keeps overlaps solid.

2. **Mask = the writing animation only.** One `<path class="hw-pen">` per
   hand-traced skeleton stroke, white, inside a `<mask>`. The ink group is
   masked by it; `handwriting.js` animates `stroke-dashoffset` so the ink is
   revealed stroke-by-stroke in writing order. The mask pen is wide enough
   (`_MASK_COVER`) that the finished state reveals the whole glyph.

**Stem-darkening compensation (counter-safe).** The OS renders live *text* a
touch bolder than a bare vector fill (font smoothing / stem darkening), so the
SVG would look slightly thinner than the surrounding font. A same-colour stroke
(`_STEM_UNITS`, font units) thickens the glyph to match — applied **only to the
outer contours** (classified by signed-area winding), so the silhouette grows
outward without the centred stroke closing narrow counters (the `l` loop, the
`e` eye).

**Size.** The SVG height is emitted in `em` (`viewBox height / units_per_em`),
so at the label's `font-size` the glyph scale is `font-size / em` — i.e. the SVG
letters are exactly the size of the font letters at that `font-size`.

**Ligatures.** The font's default GSUB ligatures (`af ah al alt at ath il ll lt
st`) are applied the way the browser does (`liga` is on by default), so spacing
and letterforms match the font — e.g. t**al**k → `al`, Educ**at**ion → `at`,
caf**é**… `af`. `compose_label` greedily longest-matches `lig_order` (3-char
ligatures beat their 2-char prefixes) and lays out the ligature glyph (its own
outline + traced strokes + advance) in place of the component letters.

### Tunable knobs (top of `compose.py`)

| knob | current | effect |
|------|---------|--------|
| `_MASK_COVER` | `0.9` | mask pen width = `pen_width × this`. Higher → fuller finished weight; lower → finer writing line (the stem edge keeps the silhouette so it stays font-clean down to ~0.9). |
| `_STEM_UNITS` | `12` | outer-contour stem-darkening stroke (font units). `0` disables. |

## Fallback & accessibility (progressive enhancement)

- `compose_label` returns **`None`** for empty / blank / unsupported labels
  (any non-space char without a traced glyph, e.g. `Œ`). The template tag then
  emits plain escaped text — no partial words, no crash.
- The tag always keeps the **real label text** in the DOM, visually hidden
  (`.hw-text`) for screen readers / print / selection; the SVG is
  `aria-hidden="true" focusable="false"`.
- **No JS:** CSS default is fully written (`stroke-dashoffset: 0`) — the label is
  always readable. JS *adds* a class to hide-then-animate on scroll.
- **`prefers-reduced-motion: reduce`:** no hide, no animation; final state shows
  immediately.
- **Replay:** returning to the page top or returning to the tab may replay the
  currently visible labels after a 30-second cooldown since the last writing run.
  No other replay trigger is registered. The default can be overridden with
  `data-hw-replay-cooldown="<milliseconds>"` on `<html>`.

## Files

- `compose.py` — `is_supported(text)`, `compose_label(text) -> str | None`
  (deterministic ids via `hashlib`, `lru_cache`d).
- `glyph_data.json` — generated artifact: `{units, pen_width, space,
  glyphs{char:{adv,outline,strokes}}, ligatures{seq:{…}}, lig_order[]}`.
- `templatetags/handwriting.py` — `{% handwriting_label text %}`: supported →
  hidden real text + animated SVG; unsupported → plain text.
- `static/handwriting/handwriting.css` / `.js` — default-written styling +
  IntersectionObserver scroll-trigger (reduced-motion / no-JS safe).
- `tests/` — composer, template-tag, and Playwright replay tests.

Markup classes: `hw-label`, `hw-text`, `hw-svg`, `hw-ink-group`, `hw-ink`,
`hw-ink-edge`, `hw-pen`.

## Source pipeline

The traced strokes, worksheets, and the `glyph_data.json` / ligature export live
in `~/gitprojects/handwriting-anim` (see its README). This app is the runtime
half and is self-contained once `glyph_data.json` is copied in.
