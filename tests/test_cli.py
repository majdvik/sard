import shutil
from pathlib import Path

import pytest

from sard.cli import main
from sard.subs import load_cues

SAMPLE = """1
00:00:00,500 --> 00:00:03,200
مرحباً، هذا اختبار للترجمة العربية مع كلمة OpenAI.

2
00:00:03,400 --> 00:00:06,800
هذا سطر طويل نسبياً لازم يتقسم على سطرين مشان يضل داخل الإطار الآمن للشاشة.
"""


@pytest.fixture()
def sample(tmp_path: Path) -> Path:
    path = tmp_path / "sample.srt"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


def test_convert_to_ass(sample: Path, tmp_path: Path):
    output = tmp_path / "out.ass"
    code = main(["convert", str(sample), "-o", str(output), "--measure", "heuristic"])
    assert code == 0
    text = output.read_text(encoding="utf-8")
    assert "PlayResX: 1920" in text
    assert text.count("Dialogue:") == 2


def test_convert_to_srt_wraps(sample: Path, tmp_path: Path):
    output = tmp_path / "out.srt"
    code = main(
        [
            "convert",
            str(sample),
            "-o",
            str(output),
            "--width",
            "600",
            "--measure",
            "heuristic",
        ]
    )
    assert code == 0
    cues = load_cues(output)
    assert len(cues) == 2
    raw = output.read_text(encoding="utf-8-sig")
    first_body = raw.split("\n\n")[0].splitlines()[2:]
    assert len(first_body) >= 2


def test_check_reports_warnings_and_exits_zero(tmp_path: Path):
    path = tmp_path / "warn.srt"
    path.write_text("1\n00:00:01,000 --> 00:00:02,000\nمرحباً (OpenAI\n", encoding="utf-8")
    assert main(["check", str(path)]) == 0


def test_missing_file_returns_two(tmp_path: Path):
    assert main(["convert", str(tmp_path / "missing.srt"), "-o", str(tmp_path / "x.ass")]) == 2


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_render_frame_integration(sample: Path, tmp_path: Path):
    video = tmp_path / "clip.mp4"
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x101820:s=640x360:d=4",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        check=True,
        capture_output=True,
    )
    output = tmp_path / "frame.png"
    code = main(
        [
            "frame",
            str(video),
            str(sample),
            "-o",
            str(output),
            "--width",
            "640",
            "--height",
            "360",
            "--measure",
            "heuristic",
            "--at",
            "1",
        ]
    )
    assert code == 0
    assert output.is_file() and output.stat().st_size > 1000
