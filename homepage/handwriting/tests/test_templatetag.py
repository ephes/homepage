from django.template import Context, Template

def render(text):
    t = Template("{% load handwriting %}{% handwriting_label label %}")
    return t.render(Context({"label": text}))

def test_supported_renders_svg_plus_hidden_text():
    out = render("Contact")
    assert '<svg class="hw-svg"' in out
    assert 'class="hw-text"' in out          # real text kept for a11y
    assert "Contact" in out

def test_unsupported_renders_plain_text_only():
    out = render("Œuvre")
    assert "<svg" not in out
    assert "hw-fallback" in out
    assert "Œuvre" in out

def test_escapes_text():
    out = render("a<b")                       # '<' is punctuation -> unsupported -> fallback
    assert "<b" not in out
    assert "&lt;b" in out
