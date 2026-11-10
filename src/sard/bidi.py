"""BiDi analysis and conservative repair for Arabic/Hebrew subtitle text.

The functions here do not shape Arabic (that is the renderer's job). They make
the *logical* text unambiguous for renderers that infer direction from the
first strong character, which is the common failure mode in subtitle engines.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

RLM = "\u200f"
LRM = "\u200e"
ALM = "\u061c"
LRI = "\u2066"
PDI = "\u2069"

_CONTROLS = (
    RLM
    + LRM
    + ALM
    + LRI
    + PDI
    + "\u2067\u2068"
    + "".join(chr(code) for code in range(0x202A, 0x202F))
    + "\ufeff"
)
_CONTROL_RE = re.compile("[" + re.escape(_CONTROLS) + "]")
_WS_RE = re.compile(r"\s+")
_LTR_RUN_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9 .,:/_@#'\-]*[A-Za-z0-9])?")
_PAIRS = (("(", ")"), ("[", "]"), ("{", "}"), ("«", "»"), ("“", "”"))

RTL_CLASSES = {"R", "AL"}
LTR_CLASSES = {"L", "EN"}


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    message: str
    cue_index: int | None = None


@dataclass(frozen=True)
class RepairResult:
    text: str
    base: str
    changed: bool
    notes: tuple[str, ...] = ()


def strip_controls(text: str) -> str:
    """Remove bidi control characters so repair is deterministic."""
    return _CONTROL_RE.sub("", text)


def strong_counts(text: str) -> tuple[int, int]:
    """Return ``(rtl_strong, ltr_strong)`` character counts."""
    rtl = ltr = 0
    for char in text:
        bidi = unicodedata.bidirectional(char)
        if bidi in RTL_CLASSES:
            rtl += 1
        elif bidi == "L":
            ltr += 1
    return rtl, ltr


def _strong_classes(text: str) -> list[str]:
    return [
        unicodedata.bidirectional(char)
        for char in text
        if unicodedata.bidirectional(char) in RTL_CLASSES | LTR_CLASSES
    ]


def first_strong(text: str) -> str | None:
    """Return the bidi class of the first strong character, if any."""
    for char in text:
        bidi = unicodedata.bidirectional(char)
        if bidi in RTL_CLASSES:
            return "rtl"
        if bidi == "L":
            return "ltr"
    return None


def last_strong(text: str) -> str | None:
    for char in reversed(text):
        bidi = unicodedata.bidirectional(char)
        if bidi in RTL_CLASSES:
            return "rtl"
        if bidi in LTR_CLASSES:
            return "ltr"
    return None


def paragraph_base(text: str, default: str = "ltr") -> str:
    """Infer a paragraph direction from the strong characters.

    The first strong character decides, like the Unicode paragraph rule. One
    exception is made for Arabic subtitles: a line that starts with a Latin
    brand but ends in Arabic is treated as RTL, so trailing punctuation lands
    on the correct side.
    """
    first = first_strong(text)
    if first == "rtl":
        return "rtl"
    if first == "ltr":
        rtl, _ = strong_counts(text)
        if rtl and last_strong(text) == "rtl":
            return "rtl"
        return "ltr"
    return default if default in ("rtl", "ltr") else "ltr"


def _ensure_rtl_base(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if first_strong(text) != "rtl":
        text = RLM + text
        notes.append("prepended RLM to make the paragraph right-to-left")
    if last_strong(text) != "rtl":
        text = text + RLM
        notes.append("appended RLM to pin trailing neutrals to the RTL run")
    return text, notes


def _isolate_ltr_runs(text: str) -> tuple[str, int]:
    count = 0

    def wrap(match: re.Match) -> str:
        nonlocal count
        value = match.group(0)
        if not any(char.isalpha() or char.isdigit() for char in value):
            return value
        count += 1
        return LRI + value + PDI

    return _LTR_RUN_RE.sub(wrap, text), count


def repair(text: str, base: str = "auto", mode: str = "marks") -> RepairResult:
    """Normalise and make the direction of ``text`` explicit.

    ``mode``:
      - ``marks``   insert RLM only where the base direction is at risk (default)
      - ``isolates`` additionally wrap Latin/number runs in LRI/PDI
      - ``off``     normalise only
    """
    if mode not in ("marks", "isolates", "off"):
        raise ValueError(f"Unknown bidi mode: {mode}")
    original = text
    text = unicodedata.normalize("NFC", text)
    text = strip_controls(text)
    text = _WS_RE.sub(" ", text).strip()
    if not text:
        return RepairResult("", "ltr", text != original)
    resolved = paragraph_base(text) if base == "auto" else base
    if resolved not in ("rtl", "ltr"):
        raise ValueError(f"Unknown base direction: {base}")
    notes: list[str] = []
    if resolved == "rtl" and mode != "off":
        text, notes = _ensure_rtl_base(text)
        if mode == "isolates":
            text, isolated = _isolate_ltr_runs(text)
            if isolated:
                notes.append(f"isolated {isolated} left-to-right run(s)")
    return RepairResult(
        text=text,
        base=resolved,
        changed=text != unicodedata.normalize("NFC", original),
        notes=tuple(notes),
    )


def analyze(text: str, cue_index: int | None = None) -> list[Issue]:
    """Return direction-related issues for one cue."""
    issues: list[Issue] = []
    clean = _WS_RE.sub(" ", text).strip()
    if not clean:
        issues.append(Issue("empty-cue", "error", "Cue text is empty", cue_index))
        return issues
    rtl, ltr = strong_counts(clean)
    if rtl and ltr:
        issues.append(
            Issue(
                "mixed-direction",
                "info",
                f"Mixed direction ({rtl} RTL / {ltr} LTR strong characters)",
                cue_index,
            )
        )
    if not rtl and not ltr:
        issues.append(
            Issue("no-strong", "warning", "No letters or digits to determine direction", cue_index)
        )
    if _CONTROL_RE.search(text):
        issues.append(
            Issue("bidi-controls", "info", "Text already contains bidi control characters", cue_index)
        )
    if rtl and ltr and first_strong(clean) == "ltr" and rtl > ltr:
        issues.append(
            Issue(
                "latin-leading",
                "warning",
                "Latin word leads an otherwise Arabic cue; a renderer may pick LTR",
                cue_index,
            )
        )
    for opening, closing in _PAIRS:
        if clean.count(opening) != clean.count(closing):
            issues.append(
                Issue(
                    "unbalanced-punctuation",
                    "warning",
                    f"Unbalanced {opening}{closing} pair",
                    cue_index,
                )
            )
    return issues
