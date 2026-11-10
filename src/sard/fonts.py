"""Font discovery and metadata."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_COMMON_FONTS = (
    "arial.ttf",
    "tahoma.ttf",
    "segoeui.ttf",
    "NotoNaskhArabic-Regular.ttf",
    "NotoNaskhArabic-Bold.ttf",
    "NotoSansArabic-Regular.ttf",
    "Tajawal-Bold.ttf",
)


@dataclass(frozen=True)
class FontInfo:
    path: Path
    family: str
    bold: bool


def _guess_from_filename(path: Path) -> FontInfo:
    stem = path.stem
    family = stem.split("-")[0].replace("_", " ").strip() or stem
    bold = any(token in stem.lower() for token in ("bold", "heavy", "black"))
    return FontInfo(path=path, family=family, bold=bold)


def font_info(path: str | Path) -> FontInfo:
    """Read the family name and weight of a font file."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Font not found: {p}")
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return _guess_from_filename(p)
    try:
        font = TTFont(str(p), fontNumber=0, lazy=True)
        names = font["name"]
        family = None
        for record in names.names:
            if record.nameID in (16, 1) and record.platformID == 3:
                family = record.toUnicode().strip()
                if record.nameID == 1:
                    break
        bold = False
        try:
            bold = bool(font["OS/2"].fsSelection & (1 << 5))
        except Exception:
            bold = "bold" in p.stem.lower()
        font.close()
        if family:
            return FontInfo(path=p, family=family, bold=bold)
    except Exception:
        pass
    return _guess_from_filename(p)


def _candidate_dirs() -> Iterable[Path]:
    env = os.environ.get("SARD_FONT_DIR")
    if env:
        yield Path(env)
    yield Path("C:/Windows/Fonts")
    yield Path("/usr/share/fonts")
    yield Path("/usr/local/share/fonts")
    yield Path.home() / ".local/share/fonts"
    yield Path.home() / "Library/Fonts"


def find_font(explicit: str | None = None, extra_dirs: Iterable[str] = ()) -> Path | None:
    """Find an Arabic-capable font file. Returns ``None`` if nothing is found."""
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    env = os.environ.get("SARD_FONT")
    if env and Path(env).is_file():
        return Path(env)
    for directory in list(extra_dirs) + list(_candidate_dirs()):
        base = Path(directory)
        if not base.is_dir():
            continue
        for name in _COMMON_FONTS:
            p = base / name
            if p.is_file():
                return p
    for directory in list(extra_dirs) + list(_candidate_dirs()):
        base = Path(directory)
        if base.is_dir():
            for pattern in ("*Arabic*.ttf", "*Tajawal*.ttf", "*Naskh*.ttf"):
                for p in base.rglob(pattern):
                    return p
    return None


def missing_glyphs(font_path: str | Path, text: str) -> list:
    """Return characters absent from the font's cmap (best effort)."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return []
    try:
        font = TTFont(str(font_path), fontNumber=0, lazy=True)
        cmap = font.getBestCmap() or {}
        font.close()
    except Exception:
        return []
    return sorted({char for char in text if char.isprintable() and ord(char) not in cmap})
