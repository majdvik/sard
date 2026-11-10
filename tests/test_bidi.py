import pytest

from sard.bidi import (
    LRI,
    PDI,
    RLM,
    analyze,
    first_strong,
    last_strong,
    paragraph_base,
    repair,
    strip_controls,
    strong_counts,
)


def test_direction_detection():
    assert paragraph_base("مرحباً بالعالم") == "rtl"
    assert paragraph_base("Hello world") == "ltr"
    assert paragraph_base("12345") == "ltr"
    assert first_strong("مرحبا") == "rtl"
    assert last_strong("مرحبا OpenAI") == "ltr"


def test_brand_led_arabic_line_is_rtl():
    assert paragraph_base("OpenAI شكراً") == "rtl"
    assert paragraph_base("شكراً OpenAI") == "rtl"
    assert paragraph_base("OpenAI is great") == "ltr"


def test_counts():
    rtl, ltr = strong_counts("مرحبا OpenAI")
    assert rtl == 5
    assert ltr == 6


def test_repair_pure_arabic_is_unchanged():
    result = repair("مرحباً بالعالم")
    assert result.text == "مرحباً بالعالم"
    assert result.base == "rtl"
    assert not result.changed


def test_repair_prepends_rlm_for_latin_led_arabic():
    result = repair("OpenAI شكراً")
    assert result.text.startswith(RLM)
    assert result.base == "rtl"
    assert result.changed
    assert any("prepended" in note for note in result.notes)


def test_repair_pins_trailing_latin():
    result = repair("شكراً OpenAI")
    assert result.text.endswith(RLM)
    assert any("appended" in note for note in result.notes)


def test_repair_removes_existing_controls_then_rebuilds():
    dirty = f"{RLM}مرحباً\u200e بالعالم\u202b"
    result = repair(dirty)
    assert "\u200e" not in result.text
    assert "\u202b" not in result.text
    assert result.text.endswith("العالم")


def test_repair_is_idempotent():
    once = repair("OpenAI شكراً")
    twice = repair(once.text)
    assert twice.text == once.text


def test_repair_off_only_normalises():
    result = repair("  مرحبا   بالعالم ", mode="off")
    assert result.text == "مرحبا بالعالم"
    assert RLM not in result.text


def test_isolates_wrap_latin_runs():
    result = repair("شكراً OpenAI على العمل", mode="isolates")
    assert LRI in result.text and PDI in result.text
    assert f"{LRI}OpenAI{PDI}" in result.text


def test_invalid_mode():
    with pytest.raises(ValueError):
        repair("نص", mode="bogus")


def test_analyze_mixed_direction():
    issues = analyze("مرحباً OpenAI", cue_index=7)
    codes = {issue.code for issue in issues}
    assert "mixed-direction" in codes
    assert all(issue.cue_index == 7 for issue in issues)


def test_analyze_unbalanced_punctuation():
    codes = {issue.code for issue in analyze("مرحباً (OpenAI")}
    assert "unbalanced-punctuation" in codes


def test_analyze_empty():
    issues = analyze("   ")
    assert issues[0].code == "empty-cue"
    assert issues[0].severity == "error"


def test_strip_controls():
    assert strip_controls(f"{RLM}نص\u200e") == "نص"
