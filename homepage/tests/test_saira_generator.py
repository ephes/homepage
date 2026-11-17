"""Exercise the real generator with tiny synthetic fonts and publication faults."""

import importlib.util
import json
import sys
from io import BytesIO
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def generator(tmp_path, monkeypatch):
    # fontTools is supplied by `just site-fonts`, not by the Django environment.
    fonttools = ModuleType("fontTools")
    fonttools.subset = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "fontTools", fonttools)
    monkeypatch.setitem(sys.modules, "fontTools.ttLib", SimpleNamespace(TTFont=None))
    varlib = SimpleNamespace(instancer=None)
    monkeypatch.setitem(sys.modules, "fontTools.varLib", varlib)
    script = Path(__file__).resolve().parents[2] / "scripts/subset_saira_fonts.py"
    spec = importlib.util.spec_from_file_location("saira_generator", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = tmp_path
    module.SOURCE_DIR = tmp_path / "source"
    module.TARGET_DIR = tmp_path / "static/fonts"
    module.CSS_FILE = tmp_path / "static/css/site.css"
    module.SOURCE_DIR.mkdir()
    module.TARGET_DIR.mkdir(parents=True)
    module.CSS_FILE.parent.mkdir()
    for name, _ in module.STYLES.values():
        (module.SOURCE_DIR / name).write_text("[65, 66, 256, 57344]")
    (module.SOURCE_DIR / "SAIRA-LICENSE.txt").write_bytes(b"synthetic license\n")
    module.CSS_FILE.write_bytes(
        b"/* outside before */\r\n"
        + module.CSS_START.encode()
        + b"\nold faces\n"
        + module.CSS_END.encode()
        + b"\r\n/* outside after */\r\n"
    )
    for prefix in module.STYLES:
        for suffix in ("latin", "latin-ext"):
            (module.TARGET_DIR / f"{prefix}-{suffix}.woff2").write_bytes(b"old font")
    (module.TARGET_DIR / "SAIRA-LICENSE.txt").write_bytes(b"old license")

    class Font:
        def __init__(self, source, **kwargs):
            if hasattr(source, "read"):
                data = source.read()
            else:
                data = Path(source).read_bytes()
            self.cmap = json.loads(data)

        def getBestCmap(self):
            return dict.fromkeys(self.cmap, "glyph")

        def close(self):
            pass

    def build(font, codepoints, target):
        target.write_text(json.dumps(sorted(codepoints)))

    monkeypatch.setattr(module, "TTFont", Font)
    instancer = SimpleNamespace(instantiateVariableFont=lambda source, axes: source)
    monkeypatch.setattr(module, "instancer", instancer)

    def copy_font(font):
        return BytesIO(json.dumps(font.cmap).encode())

    monkeypatch.setattr(module, "_copy", copy_font)
    monkeypatch.setattr(module, "build_subset", build)
    return module


def outputs(generator):
    paths = [*generator.TARGET_DIR.iterdir(), generator.CSS_FILE]
    return {path: path.read_bytes() for path in paths}


def assert_outputs(expected):
    assert {path: path.read_bytes() for path in expected} == expected


def test_later_font_failure_preserves_complete_set(generator, monkeypatch):
    before = outputs(generator)
    build = generator.build_subset
    calls = 0

    def fail(font, codepoints, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("second font failed")
        build(font, codepoints, target)

    monkeypatch.setattr(generator, "build_subset", fail)
    with pytest.raises(RuntimeError, match="second font failed"):
        generator.main()
    assert_outputs(before)


@pytest.mark.parametrize("markers", ["missing", "duplicate", "reversed"])
def test_marker_preflight(generator, monkeypatch, markers):
    start, end = generator.CSS_START, generator.CSS_END
    cases = {
        "missing": "no markers",
        "duplicate": start + end + start + end,
        "reversed": end + start,
    }
    text = cases[markers]
    generator.CSS_FILE.write_text(text)
    before = outputs(generator)
    builds = []
    monkeypatch.setattr(generator, "build_subset", lambda *args: builds.append(args))
    with pytest.raises((ValueError, SystemExit), match="[Mm]arker"):
        generator.main()
    assert not builds
    assert_outputs(before)


def test_success_installs_matching_ranges_and_preserves_outside_css_bytes(generator):
    before = generator.CSS_FILE.read_bytes()
    generator.main()
    css = generator.CSS_FILE.read_bytes()
    for marker, index in ((generator.CSS_START, 0), (generator.CSS_END, 1)):
        assert css.split(marker.encode())[index] == before.split(marker.encode())[index]
    assert b"unicode-range: U+0041-0042;" in css
    assert b"unicode-range: U+0100;" in css
    for prefix in generator.STYLES:
        core = generator.TARGET_DIR / f"{prefix}-latin.woff2"
        ext = generator.TARGET_DIR / f"{prefix}-latin-ext.woff2"
        assert json.loads(core.read_bytes()) == [65, 66]
        assert json.loads(ext.read_bytes()) == [256]
    license_file = generator.TARGET_DIR / "SAIRA-LICENSE.txt"
    assert license_file.read_bytes() == b"synthetic license\n"


def test_css_publication_failure_rolls_back_all_fonts(generator, monkeypatch):
    before = outputs(generator)
    replace = Path.replace

    def fail(source, target):
        if target == generator.CSS_FILE:
            raise OSError("CSS publication failed")
        return replace(source, target)

    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(OSError, match="CSS publication failed"):
        generator.main()
    assert_outputs(before)


@pytest.mark.parametrize("mutation", ["css", "source", "license", "font"])
def test_generation_conflict(generator, monkeypatch, mutation):
    paths = {
        "css": generator.CSS_FILE,
        "source": generator.SOURCE_DIR / "saira-variable.woff2",
        "license": generator.SOURCE_DIR / "SAIRA-LICENSE.txt",
        "font": generator.TARGET_DIR / "saira-latin.woff2",
    }
    changed = paths[mutation]
    before = outputs(generator)
    build = generator.build_subset
    calls = 0

    def edit(font, codepoints, target):
        nonlocal calls
        build(font, codepoints, target)
        calls += 1
        if calls == 2:
            changed.write_bytes(b"new manual generation")

    monkeypatch.setattr(generator, "build_subset", edit)
    with pytest.raises(RuntimeError, match="[Cc]hanged"):
        generator.main()
    if changed in before:
        before[changed] = b"new manual generation"
    assert_outputs(before)


def test_competing_generator_is_refused_and_lock_is_reusable(generator, monkeypatch):
    build = generator.build_subset
    calls = 0
    inode = None

    def compete(font, codepoints, target):
        nonlocal calls, inode
        build(font, codepoints, target)
        calls += 1
        if calls == 1:
            lock = generator.TARGET_DIR / ".saira-generation.lock"
            inode = lock.stat().st_ino
            before = outputs(generator)
            with pytest.raises(RuntimeError, match="Another font generator"):
                generator.main()
            assert_outputs(before)

    monkeypatch.setattr(generator, "build_subset", compete)
    generator.main()
    generator.main()
    assert (generator.TARGET_DIR / ".saira-generation.lock").stat().st_ino == inode
    assert calls == 8


def test_late_css_edit_rolls_back_fonts(generator, monkeypatch):
    before = outputs(generator)
    replace = Path.replace
    edited_css = before[generator.CSS_FILE] + b"\n/* manual edit */\n"
    calls = 0

    def edit(source, target):
        nonlocal calls
        result = replace(source, target)
        calls += 1
        if calls == 1:
            generator.CSS_FILE.write_bytes(edited_css)
        return result

    monkeypatch.setattr(Path, "replace", edit)
    with pytest.raises(RuntimeError, match="Changed during font generation"):
        generator.main()
    before[generator.CSS_FILE] = edited_css
    assert_outputs(before)


def test_rollback_failure_retains_recovery(generator, monkeypatch, capsys):
    replace = Path.replace
    before = outputs(generator)
    failed_target = generator.TARGET_DIR / "saira-latin.woff2"

    def fail(source, target):
        if target == generator.CSS_FILE:
            raise OSError("primary publication failure")
        if source.name.startswith("backup-") and target == failed_target:
            raise OSError("rollback failure")
        return replace(source, target)

    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(OSError, match="primary publication failure") as caught:
        generator.main()
    assert "Rollback failed" in " ".join(caught.value.__notes__)
    assert "visible files may be mixed" in capsys.readouterr().err
    (stage,) = generator.TARGET_DIR.parent.glob(".saira-stage-*")
    (backup,) = stage.glob("backup-*-saira-latin.woff2")
    assert backup.read_bytes() == before[failed_target]
    before.pop(failed_target)
    assert_outputs(before)


def test_interrupt_removes_new_outputs(generator, monkeypatch):
    for path in generator.TARGET_DIR.iterdir():
        path.unlink()
    css = generator.CSS_FILE.read_bytes()
    replace = Path.replace

    def interrupt(source, target):
        if target == generator.CSS_FILE:
            raise KeyboardInterrupt()
        return replace(source, target)

    monkeypatch.setattr(Path, "replace", interrupt)
    with pytest.raises(KeyboardInterrupt):
        generator.main()
    lock = generator.TARGET_DIR / ".saira-generation.lock"
    assert list(generator.TARGET_DIR.iterdir()) == [lock]
    assert generator.CSS_FILE.read_bytes() == css
    assert not list(generator.TARGET_DIR.parent.glob(".saira-stage-*"))


def test_missing_input_never_builds(generator, monkeypatch):
    (generator.SOURCE_DIR / "SAIRA-LICENSE.txt").unlink()
    before = outputs(generator)
    builds = []
    monkeypatch.setattr(generator, "build_subset", lambda *args: builds.append(args))
    with pytest.raises(FileNotFoundError, match="Missing input"):
        generator.main()
    assert not builds
    assert_outputs(before)


def test_validation_failure_preserves_complete_set(generator, monkeypatch):
    before = outputs(generator)

    def invalid(font, codepoints, target):
        target.write_text("[]")

    monkeypatch.setattr(generator, "build_subset", invalid)
    with pytest.raises(ValueError, match="unexpected character map"):
        generator.main()
    assert_outputs(before)


def test_newer_published_font_is_preserved(generator, monkeypatch, capsys):
    before = outputs(generator)
    changed = generator.TARGET_DIR / "saira-latin.woff2"
    replace = Path.replace

    def edit(source, target):
        result = replace(source, target)
        if target == changed:
            target.write_bytes(b"newer manual font")
        return result

    monkeypatch.setattr(Path, "replace", edit)
    with pytest.raises(RuntimeError, match="Changed after publication"):
        generator.main()
    assert changed.read_bytes() == b"newer manual font"
    assert "recovery files retained" in capsys.readouterr().err
    (stage,) = generator.TARGET_DIR.parent.glob(".saira-stage-*")
    (backup,) = stage.glob("backup-*-saira-latin.woff2")
    assert backup.read_bytes() == before[changed]
    assert_outputs({path: data for path, data in before.items() if path != changed})


@pytest.mark.parametrize("kind", ["symlink", "hardlink"])
def test_unsafe_lock_is_refused_without_changing_outputs(generator, kind):
    sentinel = generator.ROOT / "sentinel"
    sentinel.write_bytes(b"untouched")
    lock = generator.TARGET_DIR / ".saira-generation.lock"
    if kind == "symlink":
        lock.symlink_to(sentinel)
    else:
        lock.hardlink_to(sentinel)
    before = outputs(generator)
    with pytest.raises((OSError, RuntimeError)):
        generator.main()
    assert_outputs(before)
    assert sentinel.read_bytes() == b"untouched"


def test_interrupt_immediately_after_rename_still_rolls_back(generator, monkeypatch):
    before = outputs(generator)
    replace = Path.replace
    interrupted = False

    def interrupt(source, target):
        nonlocal interrupted
        result = replace(source, target)
        if not interrupted:
            interrupted = True
            raise KeyboardInterrupt()
        return result

    monkeypatch.setattr(Path, "replace", interrupt)
    with pytest.raises(KeyboardInterrupt):
        generator.main()
    assert_outputs(before)
