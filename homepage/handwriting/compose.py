"""Compose a CV label into an animated handwriting SVG (font-free, runtime-safe).

Rendering (verified pixel-identical to the real font via outline overlay):
  - ink = ONE combined outline <path> with fill-rule="nonzero" = the exact font
    glyph (counters open via opposite winding, cursive overlaps stay solid). A
    per-contour fill blobs the counters; an even-odd fill holes the overlaps.
  - a hair-thin same-colour stroke compensates text stem-darkening (the OS
    renders live text slightly bolder than a bare vector fill).
  - mask = one stroke per traced skeleton stroke, wide enough that the finished
    writing reveals the whole glyph (final state == font), animated via
    stroke-dashoffset.
  - height is emitted in `em` (viewBox units / em) so that at the label's
    font-size the glyph scale is font-size/em -> identical size to the font.
  - whole-label fallback (None) for empty/unsupported text.
"""
import os
import json
import hashlib
from functools import lru_cache

_DATA_PATH = os.path.join(os.path.dirname(__file__), "glyph_data.json")

# --- tunable rendering knobs -------------------------------------------------
# Mask pen width as a multiple of the font's global pen width. Must be wide
# enough that the union of skeleton strokes covers the whole glyph, so the
# fully-written state equals the font (not thin skeleton ribbons).
_MASK_COVER = 0.9
# Stem-darkening compensation: a same-colour stroke (font units) that thickens
# the glyph to match the OS-rendered (slightly bolder) font text. Counter-safe:
# the stroke is applied ONLY to the OUTER contours (classified by signed-area
# winding), so it grows the silhouette outward without closing narrow counters
# (the 'l' loop, the 'e' eye). 0 disables it. Fine-tune to taste.
_STEM_UNITS = 12.0


@lru_cache(maxsize=1)
def _data():
    with open(_DATA_PATH) as fh:
        return json.load(fh)


def _signed_area(poly):
    """Shoelace signed area; its sign is the contour's winding direction."""
    a = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        a += x1 * y2 - x2 * y1
    return a


def is_supported(text):
    """True only if the label is non-blank and every non-space char is traced."""
    if not text or not any(ch != " " for ch in text):
        return False
    glyphs = _data()["glyphs"]
    return all(ch == " " or ch in glyphs for ch in text)


@lru_cache(maxsize=512)
def compose_label(text):
    """Animated SVG markup for a fully-supported label, else None."""
    if not is_supported(text):
        return None
    d = _data()
    glyphs, units, GW, SPACE = d["glyphs"], d["units"], d["pen_width"], d["space"]
    ligatures, lig_order = d.get("ligatures", {}), d.get("lig_order", [])
    # Tokenize into glyph units, applying the default GSUB ligatures (a+l -> al,
    # a+t -> at, ...) the browser also applies -> matching spacing and shape.
    # Greedy longest-match (lig_order is longest-first) so 'alt'/'ath' beat 'al'/'at'.
    units_list = []     # each: glyph/ligature data dict, or None for a space
    i, n = 0, len(text)
    while i < n:
        if text[i] == " ":
            units_list.append(None); i += 1; continue
        seq = next((s for s in lig_order if text.startswith(s, i)), None)
        if seq is not None:
            units_list.append(ligatures[seq]); i += len(seq)
        else:
            units_list.append(glyphs[text[i]]); i += 1
    penx = 0.0
    contours = []   # each: list of (x, -y) points
    pens = []       # (path_d, stroke_width)
    for unit in units_list:
        if unit is None:
            penx += SPACE
            continue
        for cc in unit["outline"]:
            contours.append([(x + penx, -y) for x, y in cc])
        w = GW * _MASK_COVER
        for st in unit["strokes"]:
            dd = "M " + f"{st[0][0] + penx:.1f} {-st[0][1]:.1f} " + \
                 " ".join(f"L {x + penx:.1f} {-y:.1f}" for x, y in st[1:])
            pens.append((dd, w))
        penx += unit["adv"]
    if not contours:
        return None
    xs = [x for c in contours for x, y in c]
    ys = [y for c in contours for x, y in c]
    pad = units * 0.10
    vbx, vby = min(xs) - pad, min(ys) - pad
    vbw, vbh = (max(xs) - min(xs)) + 2 * pad, (max(ys) - min(ys)) + 2 * pad
    # ONE combined outline path, fill-rule="nonzero" = the exact font glyph
    # (counters open via opposite winding; cursive overlaps stay solid).
    od = " ".join("M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in c) + " Z" for c in contours)
    uid = "hw" + hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
    pp = "".join(f'<path class="hw-pen" d="{dd}" style="stroke-width:{w:.1f}"/>' for dd, w in pens)
    h_em = vbh / units
    ink = f'<path class="hw-ink" fill-rule="nonzero" d="{od}"/>'
    if _STEM_UNITS:
        # stroke only OUTER contours (same winding sign as the largest contour),
        # so the silhouette thickens but counters (opposite winding) stay open.
        areas = [_signed_area(c) for c in contours]
        ref = max(areas, key=abs)
        outer = [c for c, a in zip(contours, areas) if (a >= 0) == (ref >= 0)]
        ed = " ".join("M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in c) + " Z" for c in outer)
        ink += (f'<path class="hw-ink-edge" fill="none" stroke="currentColor" '
                f'stroke-width="{_STEM_UNITS:.1f}" stroke-linejoin="round" d="{ed}"/>')
    return (
        f'<svg class="hw-svg" viewBox="{vbx:.1f} {vby:.1f} {vbw:.1f} {vbh:.1f}" '
        f'preserveAspectRatio="xMinYMid meet" style="height:{h_em:.3f}em" '
        f'aria-hidden="true" focusable="false">'
        f'<defs><mask id="{uid}" maskUnits="userSpaceOnUse" x="{vbx:.1f}" y="{vby:.1f}" '
        f'width="{vbw:.1f}" height="{vbh:.1f}">{pp}</mask></defs>'
        f'<g class="hw-ink-group" mask="url(#{uid})">{ink}</g></svg>'
    )
