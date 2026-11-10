# Using sard with DaVinci Resolve

Resolve's subtitle track (Timeline → Create Subtitle Track) imports **SRT**, and it does
not preserve ASS styling. That is why sard produces two outputs with different jobs.

## Subtitle track (editable, SRT)

```bash
sard convert interview.srt -o interview.rtl.srt --target srt --width 1920 --height 1080
```

1. Import `interview.rtl.srt` into the subtitle track.
2. Because sard already repaired the bidi boundaries and wrapped the lines, Resolve
   receives text with an explicit RTL base and line breaks that fit the measured font.
3. Style the track once in Resolve (font, size, outline, position). Avoid editing the
   text inside Resolve: retyping can drop the invisible RLM marks.

## Burn-in (ASS)

```bash
sard convert interview.srt -o interview.ass --font "assets/Tajawal-Bold.ttf"
sard burn interview.mp4 interview.ass -o interview_captioned.mp4 --font "assets/Tajawal-Bold.ttf"
```

Or bring the ASS file into any player/editor that supports ASS, and use `sard frame` to
inspect one frame before committing to a full render.

## Checking before import

```bash
sard check interview.srt --font "assets/Tajawal-Bold.ttf"
```

Warnings are advisory: mixed direction is normal in Arabic technical content. Errors
(empty cues) should be fixed first.

## Notes

- Keep the SRT encoding as UTF-8 with BOM (sard writes it that way). Some Resolve
  versions mis-detect plain UTF-8 Arabic.
- Tested exports use 1920×1080 landscape. For vertical reels, pass
  `--width 1080 --height 1920`; the font size, margins, and wrapping scale together.
- Fonts must be installed for Resolve's own text rendering. The `--font` path in sard is
  used for measurement and for FFmpeg burn-in; Resolve uses the installed family name.
