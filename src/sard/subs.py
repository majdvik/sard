"""Subtitle parsing and serialisation for SRT and WebVTT."""

from __future__ import annotations

import html
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

_ENCODINGS = ("utf-8-sig", "utf-8", "cp1256", "latin-1")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_TIMING_RE = re.compile(
    r"^\s*(?P<start>(?:\d{1,3}:)?\d{1,2}:\d{2}[.,]\d{1,3})"
    r"\s*-->\s*"
    r"(?P<end>(?:\d{1,3}:)?\d{1,2}:\d{2}[.,]\d{1,3})"
    r"(?:\s+(?P<settings>.*))?$"
)
_VTT_SKIP = ("NOTE", "STYLE", "REGION")


class SubtitleError(ValueError):
    """Raised when a subtitle file cannot be parsed."""


@dataclass(frozen=True)
class Cue:
    """A single subtitle cue. ``text`` is a single normalised paragraph."""

    index: int
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def parse_time(value: str) -> float:
    """Parse ``hh:mm:ss,mmm``, ``hh:mm:ss.mmm`` or ``mm:ss.mmm`` into seconds."""
    value = value.strip().replace(",", ".")
    clock, _, millis = value.rpartition(".")
    if not clock:
        raise SubtitleError(f"Invalid timestamp: {value!r}")
    parts = clock.split(":")
    if len(parts) not in (2, 3):
        raise SubtitleError(f"Invalid timestamp: {value!r}")
    try:
        numbers = [int(p) for p in parts]
        ms = int(millis)
    except ValueError as exc:
        raise SubtitleError(f"Invalid timestamp: {value!r}") from exc
    if len(numbers) == 3:
        hours, minutes, seconds = numbers
    else:
        hours, (minutes, seconds) = 0, numbers
    if minutes > 59 or seconds > 59 or ms > 999:
        raise SubtitleError(f"Invalid timestamp: {value!r}")
    return hours * 3600 + minutes * 60 + seconds + ms / 1000.0


def format_srt_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    total_ms = int(round(seconds * 1000))
    hours, total_ms = divmod(total_ms, 3_600_000)
    minutes, total_ms = divmod(total_ms, 60_000)
    secs, ms = divmod(total_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def clean_text(lines: Iterable[str]) -> str:
    """Join cue lines into one paragraph, strip markup and collapse whitespace."""
    raw = " ".join(lines)
    raw = _TAG_RE.sub("", raw)
    raw = html.unescape(raw)
    raw = raw.replace("\u200b", "").replace("\ufeff", "")
    return _WS_RE.sub(" ", raw).strip()


def _parse_blocks(text: str, *, vtt: bool) -> list[Cue]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", text.strip())
    cues: list[Cue] = []
    for block in blocks:
        lines = [line.rstrip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        if lines[0].strip().upper().startswith("WEBVTT"):
            lines = lines[1:]
            if not lines:
                continue
        if vtt and lines[0].split()[0].upper() in _VTT_SKIP:
            continue
        timing_at = None
        for pos, line in enumerate(lines):
            if "-->" in line:
                timing_at = pos
                break
        if timing_at is None:
            continue
        match = _TIMING_RE.match(lines[timing_at])
        if not match:
            raise SubtitleError(f"Invalid timing line: {lines[timing_at]!r}")
        start = parse_time(match.group("start"))
        end = parse_time(match.group("end"))
        if end < start:
            raise SubtitleError(f"Cue ends before it starts: {lines[timing_at]!r}")
        body = lines[timing_at + 1 :]
        if not body:
            continue
        label = lines[0].strip() if timing_at > 0 else ""
        index = int(label) if label.isdigit() else len(cues) + 1
        cues.append(Cue(index=index, start=start, end=end, text=clean_text(body)))
    if not cues:
        raise SubtitleError("No cues found in file")
    return cues


def parse_srt(text: str) -> list[Cue]:
    """Parse SRT content."""
    return _parse_blocks(text, vtt=False)


def parse_vtt(text: str) -> list[Cue]:
    """Parse WebVTT content (cue identifiers and settings are accepted)."""
    if not text.lstrip("\ufeff").lstrip().upper().startswith("WEBVTT"):
        raise SubtitleError("Not a WebVTT file (missing WEBVTT header)")
    return _parse_blocks(text, vtt=True)


def _read_text(path: Path) -> str:
    last_error: Exception | None = None
    for encoding in _ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, LookupError) as exc:
            last_error = exc
    raise SubtitleError(f"Cannot decode {path}: {last_error}")


def load_cues(path: str | Path) -> list[Cue]:
    """Load cues from an SRT or VTT file, detecting the format."""
    p = Path(path)
    if not p.is_file():
        raise SubtitleError(f"File not found: {p}")
    text = _read_text(p)
    if text.lstrip("\ufeff").lstrip().upper().startswith("WEBVTT"):
        return parse_vtt(text)
    return parse_srt(text)


def serialize_srt(cues: Sequence[Cue], newline: str = "\n") -> str:
    """Serialise cues as SRT with sequential numbering."""
    chunks = []
    for number, cue in enumerate(cues, 1):
        body = cue.text.replace("\r", "").replace("\n", newline)
        chunks.append(
            f"{number}{newline}{format_srt_time(cue.start)} --> "
            f"{format_srt_time(cue.end)}{newline}{body}{newline}"
        )
    return newline.join(chunks)


def split_lines(text: str) -> tuple[str, ...]:
    """Split cue text into display lines."""
    return tuple(line for line in text.split("\n") if line.strip())
