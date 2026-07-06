# PortSlayer v1.1.0

First public release of the PortSlayer CLI — a cross-platform command-line tool and interactive terminal dashboard to inspect and kill processes by port.

## Highlights

- **Interactive TUI dashboard** — run `pk` (or `portslayer`) with no arguments for a full-screen, keyboard-driven view: `↑`/`↓` to navigate, `/` to search, `k`/`Del` to kill (with confirmation), `r` to refresh, auto-refreshes every 3s
- **Short alias `pk`** — every command works as both `portslayer <cmd>` and `pk <cmd>`
- **Partial port search** — `pk find 808` matches 8080, 8081, 8083, ... ; same for `list --port`. `kill` intentionally stays exact-only for safety
- **Kill by process name** — `pk kill --name node` kills every port that process owns, no need to look up the port first
- **JSON output** — `--json` on `list`/`find` for scripting (`pk list --json | jq ...`)
- **Shell completion** — `pk --install-completion` (built into Typer, zero extra code)
- **Install anywhere** — `pip install portslayer`, `npx @appestox/portslayer` / `npm install -g @appestox/portslayer`, or via Homebrew/Scoop (see [`packaging/`](packaging/)); all wrap the same PyPI package

## Design decisions

- Every subprocess call uses explicit argument lists — never `shell=True` — to prevent command injection
- `kill` always requires explicit confirmation (unless `--force`) before acting
- Users are warned when not running with admin/root privileges, since some processes will be hidden

## Installation

```bash
pip install portslayer
```

See the [README](README.md) for npm, Homebrew, and Scoop instructions.
