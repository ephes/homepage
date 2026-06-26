from homepage.handwriting import compose

def test_supported_label_uses_nonzero_font_outline():
    # The ink is ONE combined path with fill-rule="nonzero" = the exact font
    # glyph (counters open, overlaps solid). Even-odd would hole the cursive
    # overlaps; a per-contour fill would blob the counters.
    svg = compose.compose_label("Contact")
    assert svg is not None
    assert 'fill-rule="evenodd"' not in svg               # no even-odd anywhere
    assert 'fill-rule="nonzero"' in svg                   # exact font outline
    assert '<path class="hw-ink"' in svg                  # single combined ink path
    assert 'mask="url(#hw' in svg                         # ink masked for the writing animation
    assert 'class="hw-pen"' in svg                        # skeleton reveal mask present
    # horizontal label carries its em size as inline-size (width) with auto height,
    # so max-inline-size:100% can shrink it proportionally on narrow columns
    assert 'style="inline-size:' in svg and 'em"' in svg
    assert 'aria-hidden="true"' in svg

def test_vertical_label_keeps_em_height():
    # rotated rail labels size by em HEIGHT on the inner svg (the .hw-rot wrapper
    # reserves the rotated footprint), so the horizontal inline-size swap must not
    # touch them
    svg = compose.compose_label("Contact", "vertical")
    assert svg is not None
    assert 'class="hw-rot"' in svg
    assert 'height:' in svg and 'em' in svg

def test_unsupported_char_falls_back_to_none():
    assert compose.compose_label("Œuvre") is None          # Œ not in the font/library

def test_empty_and_space_only_fall_back_to_none():
    assert compose.compose_label("") is None
    assert compose.compose_label("   ") is None

def test_deterministic_mask_id():
    a = compose.compose_label("Education")
    b = compose.compose_label("Education")
    assert a == b                                          # stable id, no builtin hash()

def test_umlaut_label_supported():
    assert compose.compose_label("Über mich") is not None

def test_ligature_al_is_substituted():
    # "talk" must use the 'al' ligature glyph (one traced stroke), not base a+l,
    # so spacing/shape match the browser's default-liga rendering.
    d = compose._data()
    al_strokes = len(d["ligatures"]["al"]["strokes"])
    naive = len(d["glyphs"]["a"]["strokes"]) + len(d["glyphs"]["l"]["strokes"])
    assert al_strokes != naive                              # ligature genuinely differs
    assert compose.compose_label("al").count('class="hw-pen"') == al_strokes

def test_longest_ligature_wins():
    # 'alt' (3-char) must beat 'al'+'t' (lig_order is longest-first).
    d = compose._data()
    assert compose.compose_label("alt").count('class="hw-pen"') == len(d["ligatures"]["alt"]["strokes"])
