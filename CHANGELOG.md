# Changelog

## 0.1.0 — 2026-11-10

First public release.

- SRT and WebVTT parsing with BOM, CRLF, cue identifiers, settings, and CP1256 fallback.
- Conservative bidi repair: RLM insertion at direction-risk boundaries, stale control
  removal, idempotent output, optional LRI/PDI isolation mode.
- Width-aware balanced wrapping using the measured font (Pillow) with heuristic fallback.
- ASS export with `WrapStyle: 2`, `{\q2}`, safe margins, override sanitation, and
  resolution-scaled font size.
- Resolve-ready SRT export with UTF-8 BOM.
- `check`, `convert`, `burn`, and `frame` commands.
- 51 tests, including an FFmpeg/libass render integration test.
