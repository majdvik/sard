"""sard — bidi-safe Arabic/RTL subtitle toolkit."""

__version__ = "0.1.0"

from .ass import AssOptions, build_ass
from .bidi import analyze, repair
from .layout import PillowMeasurer, WrapOptions, wrap_text
from .subs import Cue, SubtitleError, load_cues, parse_srt, parse_vtt, serialize_srt

__all__ = [
    "AssOptions",
    "Cue",
    "PillowMeasurer",
    "SubtitleError",
    "WrapOptions",
    "__version__",
    "analyze",
    "build_ass",
    "load_cues",
    "parse_srt",
    "parse_vtt",
    "repair",
    "serialize_srt",
    "wrap_text",
]
