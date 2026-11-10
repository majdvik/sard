"""FFmpeg burn-in and frame rendering."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class MediaError(RuntimeError):
    """Raised when FFmpeg is missing or fails."""


def ffmpeg_path() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise MediaError("FFmpeg was not found on PATH")
    return binary


def _prepare(working_dir: Path, ass_text: str, font_path: str | None) -> str:
    (working_dir / "subs.ass").write_text(ass_text, encoding="utf-8")
    if font_path:
        fonts = working_dir / "fonts"
        fonts.mkdir(exist_ok=True)
        shutil.copyfile(font_path, fonts / Path(font_path).name)
        return "ass=subs.ass:fontsdir=fonts"
    return "ass=subs.ass"


def _run(cmd: list, cwd: Path) -> str:
    result = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        tail = (result.stderr or "").strip().splitlines()[-12:]
        raise MediaError("FFmpeg failed:\n" + "\n".join(tail))
    return (result.stderr or "").strip()


def burn_video(
    video: str | Path,
    ass_text: str,
    output: str | Path,
    font_path: str | None = None,
    crf: int = 18,
    preset: str = "medium",
) -> str:
    """Burn subtitles into ``video`` and write ``output``."""
    if not Path(video).is_file():
        raise MediaError(f"Video not found: {video}")
    with tempfile.TemporaryDirectory(prefix="sard_") as tmp:
        work = Path(tmp)
        video_filter = _prepare(work, ass_text, font_path)
        cmd = [
            ffmpeg_path(),
            "-y",
            "-i",
            str(Path(video).resolve()),
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(Path(output).resolve()),
        ]
        return _run(cmd, work)


def render_frame(
    video: str | Path,
    ass_text: str,
    output_png: str | Path,
    at: float = 1.0,
    font_path: str | None = None,
) -> str:
    """Render a single frame with burned subtitles, for visual QA."""
    if not Path(video).is_file():
        raise MediaError(f"Video not found: {video}")
    with tempfile.TemporaryDirectory(prefix="sard_") as tmp:
        work = Path(tmp)
        video_filter = _prepare(work, ass_text, font_path)
        cmd = [
            ffmpeg_path(),
            "-y",
            "-i",
            str(Path(video).resolve()),
            "-ss",
            f"{max(0.0, float(at)):.3f}",
            "-vf",
            video_filter,
            "-frames:v",
            "1",
            str(Path(output_png).resolve()),
        ]
        return _run(cmd, work)
