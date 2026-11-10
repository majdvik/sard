from pathlib import Path

import pytest

from sard.subs import (
    Cue,
    SubtitleError,
    format_srt_time,
    load_cues,
    parse_srt,
    parse_time,
    parse_vtt,
    serialize_srt,
)

SAMPLE = """1
00:00:00,500 --> 00:00:03,200
مرحباً، هذا اختبار.

2
00:00:03,400 --> 00:00:06,800
سطر أول
سطر ثانٍ
"""


def test_parse_srt_basic():
    cues = parse_srt(SAMPLE)
    assert len(cues) == 2
    assert cues[0].start == 0.5
    assert cues[0].end == 3.2
    assert cues[1].text == "سطر أول سطر ثانٍ"


def test_parse_bom_and_crlf():
    text = "\ufeff" + SAMPLE.replace("\n", "\r\n")
    cues = parse_srt(text)
    assert len(cues) == 2
    assert cues[0].text == "مرحباً، هذا اختبار."


def test_parse_strips_tags_and_entities():
    text = "1\n00:00:01,000 --> 00:00:02,000\n<i>OpenAI</i> &amp; شركاء\n"
    cues = parse_srt(text)
    assert cues[0].text == "OpenAI & شركاء"


def test_parse_vtt_with_identifier_and_settings():
    text = (
        "WEBVTT\n\n"
        "NOTE this is a comment\n\n"
        "intro\n"
        "00:00:01.000 --> 00:00:02.500 align:start position:10%\n"
        "مرحباً\n"
    )
    cues = parse_vtt(text)
    assert len(cues) == 1
    assert cues[0].start == 1.0
    assert cues[0].end == 2.5
    assert cues[0].text == "مرحباً"


def test_parse_vtt_requires_header():
    with pytest.raises(SubtitleError):
        parse_vtt(SAMPLE)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("00:00:01,500", 1.5),
        ("00:00:01.500", 1.5),
        ("01:02.250", 62.25),
        ("1:00:00,000", 3600.0),
    ],
)
def test_parse_time(value, expected):
    assert parse_time(value) == pytest.approx(expected)


@pytest.mark.parametrize("value", ["", "12:99:00,000", "abc", "00:00:00,9999"])
def test_parse_time_invalid(value):
    with pytest.raises(SubtitleError):
        parse_time(value)


def test_reversed_timing_is_rejected():
    with pytest.raises(SubtitleError):
        parse_srt("1\n00:00:05,000 --> 00:00:01,000\nنص\n")


def test_no_cues_raises():
    with pytest.raises(SubtitleError):
        parse_srt("just text\n")


def test_serialize_roundtrip():
    cues = [Cue(1, 0.5, 3.2, "سطر\nثانٍ"), Cue(2, 61.0, 62.5, "OpenAI")]
    text = serialize_srt(cues)
    reparsed = parse_srt(text)
    assert [cue.text for cue in reparsed] == ["سطر ثانٍ", "OpenAI"]
    assert reparsed[1].start == 61.0


def test_format_srt_time():
    assert format_srt_time(3725.456) == "01:02:05,456"


def test_load_cp1256(tmp_path: Path):
    path = tmp_path / "legacy.srt"
    path.write_bytes(SAMPLE.encode("cp1256"))
    cues = load_cues(path)
    assert cues[0].text.startswith("مرحباً")
