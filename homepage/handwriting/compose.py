"""Compose a CV label into an animated handwriting SVG (font-free, runtime-safe).

Ported verbatim in behaviour from the reviewed build_word.py:
  - one combined outline path with fill-rule="evenodd" (correct counters),
  - a stroke path per traced stroke as a reveal mask (stroke-dashoffset),
  - whole-label fallback (None) for empty/unsupported text.
"""
import os
import json
import hashlib
from functools import lru_cache

_DATA_PATH = os.path.join(os.path.dirname(__file__), "glyph_data.json")


@lru_cache(maxsize=1)
def _data():
    with open(_DATA_PATH) as fh:
        return json.load(fh)


def width_factor(ch):
    """Mask-width tier: letters+digits narrow (0.65), punctuation wide (1.0)."""
    return 0.65 if ch.isalnum() else 1.0


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
    penx = 0.0
    contours = []   # each: list of (x, -y) points
    pens = []       # (path_d, stroke_width)
    for ch in text:
        if ch == " ":
            penx += SPACE
            continue
        g = glyphs[ch]
        for cc in g["outline"]:
            contours.append([(x + penx, -y) for x, y in cc])
        w = GW * width_factor(ch)
        for st in g["strokes"]:
            dd = "M " + f"{st[0][0] + penx:.1f} {-st[0][1]:.1f} " + \
                 " ".join(f"L {x + penx:.1f} {-y:.1f}" for x, y in st[1:])
            pens.append((dd, w))
        penx += g["adv"]
    if not contours:
        return None
    xs = [x for c in contours for x, y in c]
    ys = [y for c in contours for x, y in c]
    pad = units * 0.10
    vbx, vby = min(xs) - pad, min(ys) - pad
    vbw, vbh = (max(xs) - min(xs)) + 2 * pad, (max(ys) - min(ys)) + 2 * pad
    od = " ".join("M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in c) + " Z" for c in contours)
    uid = "hw" + hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
    pp = "".join(f'<path class="hw-pen" d="{dd}" style="stroke-width:{w:.1f}"/>' for dd, w in pens)
    return (
        f'<svg class="hw-svg" viewBox="{vbx:.1f} {vby:.1f} {vbw:.1f} {vbh:.1f}" '
        f'preserveAspectRatio="xMinYMid meet" aria-hidden="true" focusable="false">'
        f'<defs><mask id="{uid}" maskUnits="userSpaceOnUse" x="{vbx:.1f}" y="{vby:.1f}" '
        f'width="{vbw:.1f}" height="{vbh:.1f}">{pp}</mask></defs>'
        f'<path class="hw-ink" d="{od}" fill-rule="evenodd" mask="url(#{uid})"/></svg>'
    )
