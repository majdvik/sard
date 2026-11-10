"""Width-aware, balanced line wrapping for subtitles."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class Measurer(Protocol):
    def measure(self, text: str) -> float:  # pragma: no cover - protocol
        ...


@dataclass(frozen=True)
class WrapOptions:
    max_width: float
    max_lines: int = 2
    ellipsis: str = "…"


class CharMeasurer:
    """Deterministic approximation, used when no font file is available."""

    def __init__(self, em: float = 52.0) -> None:
        self.em = em

    def _ratio(self, char: str) -> float:
        if char.isspace():
            return 0.30
        bidi = unicodedata.bidirectional(char)
        if bidi in ("NSM", "BN"):
            return 0.02
        if bidi in ("R", "AL"):
            return 0.60
        if char.isdigit():
            return 0.55
        return 0.52

    def measure(self, text: str) -> float:
        return sum(self._ratio(char) for char in text) * self.em


class PillowMeasurer:
    """Measure text with the exact font and pixel size used by the renderer."""

    def __init__(self, font_path: str | Path, size_px: int) -> None:
        try:
            from PIL import ImageFont
        except ImportError as exc:  # pragma: no cover - Pillow is a dependency
            raise RuntimeError("Pillow is required for font measurement") from exc
        self.font_path = str(font_path)
        self.size_px = int(size_px)
        self._font = ImageFont.truetype(self.font_path, self.size_px)

    def measure(self, text: str) -> float:
        return float(self._font.getlength(text))


def _partition(
    words: Sequence[str], measurer: Measurer, lines: int
) -> tuple[float, tuple[str, ...]] | None:
    n = len(words)
    if n < lines:
        return None
    widths: dict = {}

    def width(start: int, end: int) -> float:
        key = (start, end)
        if key not in widths:
            widths[key] = measurer.measure(" ".join(words[start:end]))
        return widths[key]

    # dp[line][end] = (max line width, sum of squared widths, cut positions)
    dp: list[list[tuple[float, float, tuple[int, ...]] | None]] = [
        [None] * (n + 1) for _ in range(lines + 1)
    ]
    dp[0][0] = (0.0, 0.0, ())
    for line in range(1, lines + 1):
        for end in range(line, n + 1):
            best: tuple[float, float, tuple[int, ...]] | None = None
            for start in range(line - 1, end):
                previous = dp[line - 1][start]
                if previous is None:
                    continue
                line_width = width(start, end)
                candidate = (
                    max(previous[0], line_width),
                    previous[1] + line_width * line_width,
                    previous[2] + (start,),
                )
                if best is None or (candidate[0], candidate[1]) < (best[0], best[1]):
                    best = candidate
            dp[line][end] = best
    if dp[lines][n] is None:
        return None
    cuts = dp[lines][n][2] + (n,)
    result = tuple(" ".join(words[cuts[i] : cuts[i + 1]]) for i in range(lines))
    return dp[lines][n][0], result


def _fit_line(line: str, measurer: Measurer, max_width: float, ellipsis: str) -> str:
    if measurer.measure(line) <= max_width:
        return line
    words = line.split()
    while words and measurer.measure(" ".join(words) + ellipsis) > max_width:
        words.pop()
    if not words:
        trimmed = ""
        for char in line:
            if measurer.measure(trimmed + char + ellipsis) > max_width:
                break
            trimmed += char
        return (trimmed.rstrip() + ellipsis) if trimmed else ellipsis
    return " ".join(words).rstrip("،,.;:") + ellipsis


def wrap_text(text: str, measurer: Measurer, options: WrapOptions) -> list[str]:
    """Wrap one paragraph into at most ``max_lines`` balanced lines."""
    text = " ".join(text.split())
    if not text:
        return []
    if options.max_lines < 1:
        raise ValueError("max_lines must be at least 1")
    if measurer.measure(text) <= options.max_width:
        return [text]
    words = text.split()
    if options.max_lines == 1 or len(words) == 1:
        return [_fit_line(text, measurer, options.max_width, options.ellipsis)]
    for count in range(2, options.max_lines + 1):
        partition = _partition(words, measurer, count)
        if partition and partition[0] <= options.max_width + 1e-6:
            return list(partition[1])
    partition = _partition(words, measurer, options.max_lines)
    if partition is None:
        return [_fit_line(text, measurer, options.max_width, options.ellipsis)]
    return [
        _fit_line(line, measurer, options.max_width, options.ellipsis)
        for line in partition[1]
    ]
