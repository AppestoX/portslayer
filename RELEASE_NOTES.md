# PortSlayer v1.1.1

Compatibility release — PortSlayer now supports **Python 3.9+** (previously 3.10+).

## Changes

- **Lowered minimum Python to 3.9** — the code never used 3.10-only features, so
  `requires-python` is now `>=3.9`; the full test suite passes on 3.9 (on 3.9,
  pip resolves Typer 0.23.x, the last line supporting it)
- **npm wrapper now checks the Python version** — if only an older Python is on
  `PATH` (e.g. 3.8), install and run print a clear
  "Python X.Y was found, but PortSlayer needs 3.9 or newer" message instead of
  pip's cryptic `No matching distribution found` error
- **CI now tests on Python 3.9 and 3.12** across Linux, Windows, and macOS
- README: accurate per-method minimum-version table (pip needs Python 3.9+;
  npm/npx need Node 14+ *and* Python 3.9+; `uvx` needs neither since uv
  downloads a compatible Python)

## Installation

```bash
pip install portslayer                    # Python 3.9+
npx @appestox/portslayer                  # Node 14+ and Python 3.9+
uvx portslayer                            # just uv — no Python setup needed
```

Full feature list: see the [v1.1.0 release notes](https://github.com/AppestoX/portslayer/releases/tag/v1.1.0). 
