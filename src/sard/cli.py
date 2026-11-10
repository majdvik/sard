"""Command line interface for sard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .ass import AssOptions, build_ass
from .bidi import analyze, repair
from .burn import MediaError, burn_video, render_frame
from .fonts import find_font, font_info, missing_glyphs
from .layout import CharMeasurer, Measurer, PillowMeasurer, WrapOptions, wrap_text
from .subs import Cue, SubtitleError, load_cues, serialize_srt


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _text_width(args) -> float:
    return float(args.width - 2 * args.margin_lr)


def _measurer(args) -> tuple[Measurer, Path | None]:
    if args.font and not Path(args.font).is_file():
        raise SubtitleError(f"Font not found: {args.font}")
    font_path = find_font(args.font)
    size = args.font_size or max(12, round(args.height * 0.0482))
    if font_path:
        return PillowMeasurer(font_path, size), font_path
    if args.measure == "font":
        raise SubtitleError(
            "No font found. Pass --font PATH or set SARD_FONT, or use --measure heuristic."
        )
    print("warning: no font file found; using heuristic measurement", file=sys.stderr)
    return CharMeasurer(size), None


def _ass_options(args) -> AssOptions:
    return AssOptions(
        play_res_x=args.width,
        play_res_y=args.height,
        font_name=args.font_name or "Arial",
        bold=args.bold,
        font_size=args.font_size or 0,
        margin_lr=args.margin_lr,
        margin_v=args.margin_v,
        max_lines=args.max_lines,
        bidi=args.bidi,
        base=args.base,
    )


def _options_for(args, font_path: Path | None) -> AssOptions:
    options = _ass_options(args)
    if not font_path:
        return options
    info = font_info(font_path)
    return AssOptions(
        **{
            **options.__dict__,
            "font_name": args.font_name or info.family,
            "bold": args.bold or info.bold,
        }
    )


def _ensure_parent(path: Path) -> None:
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def _wrap_cues(cues: list[Cue], measurer: Measurer, args) -> list[Cue]:
    options = WrapOptions(max_width=_text_width(args), max_lines=args.max_lines)
    wrapped: list[Cue] = []
    for cue in cues:
        result = repair(cue.text, base=args.base, mode=args.bidi)
        lines = wrap_text(result.text, measurer, options)
        wrapped.append(
            Cue(index=cue.index, start=cue.start, end=cue.end, text="\n".join(lines))
        )
    return wrapped


def _target_for(args) -> str:
    if args.target:
        return args.target
    suffix = Path(args.output).suffix.lower()
    if suffix in (".srt", ".vtt"):
        return "srt"
    return "ass"


def cmd_convert(args) -> int:
    cues = load_cues(args.input)
    measurer, font_path = _measurer(args)
    target = _target_for(args)
    output = Path(args.output)
    fixed = 0
    issues = []
    for cue in cues:
        result = repair(cue.text, base=args.base, mode=args.bidi)
        fixed += int(result.changed)
        issues.extend(analyze(cue.text, cue.index))
    if target == "ass":
        document = build_ass(cues, measurer, _options_for(args, font_path))
        _ensure_parent(output)
        output.write_text(document, encoding="utf-8")
    else:
        wrapped = _wrap_cues(cues, measurer, args)
        newline = "\r\n" if args.crlf else "\n"
        _ensure_parent(output)
        output.write_text(serialize_srt(wrapped, newline=newline), encoding="utf-8-sig")
    warnings = [issue for issue in issues if issue.severity == "warning"]
    errors = [issue for issue in issues if issue.severity == "error"]
    print(f"cues: {len(cues)}  repaired: {fixed}  warnings: {len(warnings)}  errors: {len(errors)}")
    print(f"wrote: {output} ({target})")
    if args.strict and (warnings or errors):
        print("strict mode: issues found", file=sys.stderr)
        return 1
    return 0


def cmd_check(args) -> int:
    cues = load_cues(args.input)
    font_path = None
    if args.font:
        if not Path(args.font).is_file():
            raise SubtitleError(f"Font not found: {args.font}")
        font_path = Path(args.font)
    total = 0
    errors = 0
    for cue in cues:
        issues = analyze(cue.text, cue.index)
        for issue in issues:
            total += 1
            errors += int(issue.severity == "error")
            print(f"cue {cue.index:>3}  {issue.severity:<7}  {issue.code:<22} {issue.message}")
        if font_path and cue.text:
            missing = missing_glyphs(font_path, cue.text)
            if missing:
                total += 1
                print(
                    f"cue {cue.index:>3}  warning  missing-glyphs        "
                    f"{''.join(missing)!r} not in {font_path.name}"
                )
    print(f"\n{len(cues)} cues, {total} issue(s), {errors} error(s)")
    return 1 if errors else 0


def cmd_burn(args) -> int:
    cues = load_cues(args.subtitles)
    measurer, font_path = _measurer(args)
    document = build_ass(cues, measurer, _options_for(args, font_path))
    output = Path(args.output)
    _ensure_parent(output)
    burn_video(args.video, document, output, str(font_path) if font_path else None)
    print(f"wrote: {args.output}")
    return 0


def cmd_frame(args) -> int:
    cues = load_cues(args.subtitles)
    measurer, font_path = _measurer(args)
    document = build_ass(cues, measurer, _options_for(args, font_path))
    output = Path(args.output)
    _ensure_parent(output)
    render_frame(
        args.video, document, output, at=args.at, font_path=str(font_path) if font_path else None
    )
    print(f"wrote: {args.output}")
    return 0


def _add_layout_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--width", type=int, default=1920, help="frame width (default 1920)")
    parser.add_argument("--height", type=int, default=1080, help="frame height (default 1080)")
    parser.add_argument("--font", help="path to a font file (TTF/OTF)")
    parser.add_argument("--font-name", help="font family name written into the ASS style")
    parser.add_argument("--font-size", type=int, default=0, help="font size in pixels")
    parser.add_argument("--bold", action="store_true", help="force bold text")
    parser.add_argument("--margin-lr", type=int, default=60, help="left/right safety margin")
    parser.add_argument("--margin-v", type=int, default=54, help="vertical safety margin")
    parser.add_argument("--max-lines", type=int, default=2, help="maximum lines per cue")
    parser.add_argument("--bidi", choices=("marks", "isolates", "off"), default="marks")
    parser.add_argument("--base", choices=("auto", "rtl", "ltr"), default="auto")
    parser.add_argument(
        "--measure", choices=("auto", "font", "heuristic"), default="auto",
        help="line width measurement strategy",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sard", description="Bidi-safe Arabic/RTL subtitle toolkit"
    )
    parser.add_argument("--version", action="version", version=f"sard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    convert = sub.add_parser("convert", help="convert SRT/VTT to bidi-safe ASS or SRT")
    convert.add_argument("input")
    convert.add_argument("-o", "--output", required=True)
    convert.add_argument("--target", choices=("ass", "srt"), help="output format")
    convert.add_argument("--crlf", action="store_true", help="use CRLF line endings in SRT")
    convert.add_argument("--strict", action="store_true", help="fail on warnings")
    _add_layout_args(convert)
    convert.set_defaults(func=cmd_convert)

    check = sub.add_parser("check", help="report direction and punctuation issues")
    check.add_argument("input")
    check.add_argument("--font", help="also check glyph coverage with this font")
    check.set_defaults(func=cmd_check)

    burn = sub.add_parser("burn", help="burn subtitles into a video with FFmpeg")
    burn.add_argument("video")
    burn.add_argument("subtitles")
    burn.add_argument("-o", "--output", required=True)
    _add_layout_args(burn)
    burn.set_defaults(func=cmd_burn)

    frame = sub.add_parser("frame", help="render one frame with burned subtitles")
    frame.add_argument("video")
    frame.add_argument("subtitles")
    frame.add_argument("-o", "--output", required=True)
    frame.add_argument("--at", type=float, default=1.0, help="timestamp in seconds")
    _add_layout_args(frame)
    frame.set_defaults(func=cmd_frame)
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (SubtitleError, MediaError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
