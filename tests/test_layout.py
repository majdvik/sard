import pytest

from sard.layout import CharMeasurer, WrapOptions, wrap_text

MEASURER = CharMeasurer(em=40)


def test_short_text_stays_on_one_line():
    assert wrap_text("مرحبا", MEASURER, WrapOptions(max_width=300)) == ["مرحبا"]


def test_wraps_into_two_balanced_lines():
    text = "هذا نص عربي طويل يحتاج إلى تقسيم على سطرين"
    options = WrapOptions(max_width=480)
    lines = wrap_text(text, MEASURER, options)
    assert len(lines) == 2
    assert all(MEASURER.measure(line) <= 480 for line in lines)
    assert " ".join(lines) == text


def test_balance_prefers_similar_widths():
    text = "كلمات قصيرة ثم كلمة طويلة جدا هنا"
    lines = wrap_text(text, MEASURER, WrapOptions(max_width=500))
    widths = [MEASURER.measure(line) for line in lines]
    assert max(widths) - min(widths) < 140


def test_respects_max_lines_with_ellipsis():
    text = " ".join(["كلمة"] * 20)
    lines = wrap_text(text, MEASURER, WrapOptions(max_width=200, max_lines=2))
    assert len(lines) == 2
    assert lines[-1].endswith("…")


def test_single_long_word_is_truncated():
    lines = wrap_text("ا" * 40, MEASURER, WrapOptions(max_width=200))
    assert len(lines) == 1
    assert lines[0].endswith("…")
    assert MEASURER.measure(lines[0]) <= 200


def test_empty_text():
    assert wrap_text("   ", MEASURER, WrapOptions(max_width=100)) == []


def test_invalid_max_lines():
    with pytest.raises(ValueError):
        wrap_text("نص", MEASURER, WrapOptions(max_width=100, max_lines=0))
