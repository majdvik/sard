from sard.ass import AssOptions, build_ass, sanitize_text
from sard.layout import CharMeasurer
from sard.subs import Cue

MEASURER = CharMeasurer(em=40)


def _cues():
    return [
        Cue(1, 0.5, 3.2, "مرحباً بالعالم"),
        Cue(2, 3.4, 6.8, "شكراً OpenAI"),
    ]


def test_header_and_style():
    document = build_ass(_cues(), MEASURER)
    assert "[Script Info]" in document
    assert "PlayResX: 1920" in document
    assert "PlayResY: 1080" in document
    assert "WrapStyle: 2" in document
    assert "Style: Default,Arial,52" in document
    assert "Dialogue: 0,0:00:00.50,0:00:03.20,Default" in document


def test_rtl_text_gets_rlm():
    document = build_ass(_cues(), MEASURER)
    dialogue = [line for line in document.splitlines() if line.startswith("Dialogue")]
    assert "\u200f" in dialogue[1]


def test_long_cue_wraps_with_ass_break():
    cue = Cue(1, 0.0, 5.0, " ".join(["كلمة"] * 14))
    document = build_ass([cue], MEASURER, AssOptions(play_res_x=600, margin_lr=50))
    dialogue = [line for line in document.splitlines() if line.startswith("Dialogue")][0]
    assert r"\N" in dialogue


def test_braces_and_backslashes_are_sanitised():
    cue = Cue(1, 0.0, 2.0, "مرحبا {OpenAI} C:\\path")
    document = build_ass([cue], MEASURER)
    dialogue = [line for line in document.splitlines() if line.startswith("Dialogue")][0]
    payload = dialogue.split(",,")[-1].replace("{\\q2}", "")
    assert "{" not in payload
    assert "}" not in payload
    assert "\\path" not in payload


def test_sanitize_text():
    assert sanitize_text("a{b}c\\d") == "a(b)c/d"


def test_default_font_size_scales_with_resolution():
    assert AssOptions(play_res_y=1080).resolved_font_size() == 52
    assert AssOptions(play_res_y=1920).resolved_font_size() == 93
    assert AssOptions(play_res_y=1080, font_size=64).resolved_font_size() == 64
