# Contributing to sard

Thanks for taking a look. This project is small on purpose: a subtitle safety layer,
not an editor.

## Development setup

```bash
git clone https://github.com/majdvik/sard.git
cd sard
python -m pip install -e ".[dev]"
pytest
ruff check .
```

FFmpeg is optional for the test suite; the render integration test skips itself when
`ffmpeg` is not on `PATH`.

## What makes a good change

- A failing test that describes a real subtitle problem, followed by the smallest fix.
- New bidi cases need a fixture with the exact characters (use escapes for controls such
  as `\u200f`) and a short explanation of the visual result.
- Keep the default `marks` mode conservative. New control characters need a documented
  reason and a renderer that handles them.
- Update `CHANGELOG.md` under "Unreleased".

## Style

- Python 3.10+, type hints on public functions.
- Ruff with the repository configuration.
- No network access in tests.
- Comments explain why, not what.

## Reporting a bad render

Include: input cue text (with escapes), font file, renderer and version, expected visual
order, actual screenshot, and the exact `sard` command.
