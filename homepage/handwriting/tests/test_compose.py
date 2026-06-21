from homepage.handwriting import compose

def test_supported_label_returns_svg_with_evenodd_and_mask():
    svg = compose.compose_label("Contact")
    assert svg is not None
    assert svg.count('fill-rule="evenodd"') == 1          # ONE combined outline path
    assert 'class="hw-pen"' in svg                         # stroke mask present
    assert 'aria-hidden="true"' in svg

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
