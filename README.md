# PortSlayer ⚡

> Cross-platform CLI + interactive TUI to list active ports and safely kill processes by port number.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)](#)

---

## Features

- **Interactive TUI dashboard** — just run `pk` (or `portslayer`): arrow keys to navigate, `/` to search, `k` to kill, live auto-refresh
- **Short alias** — every command works as both `portslayer <cmd>` and the 2-letter `pk <cmd>`
- **List all active ports** — port, PID, process name, protocol, state, addresses
- **Filter** by port number, process name, or protocol (TCP/UDP)
- **Kill processes by port or by process name** — with mandatory confirmation before any destructive action
- **JSON output** (`--json`) for scripting, plus built-in shell completion (`--install-completion`)
- **Cross-platform** — Linux (via `ss`/`lsof`), Windows (via `netstat`/`taskkill`), macOS (via `lsof`)
- **Install however you like** — pip, npx/npm, or Homebrew/Scoop

---

## Tech Stack

| Layer     | Technology                  | Reason                                                  |
|-----------|-----------------------------|---------------------------------------------------------|
| TUI       | Python + Textual            | Full-screen keyboard-driven dashboard, no extra runtime for users |
| CLI       | Python + Typer + Rich       | Single language, beautiful tables, type-safe commands   |
| Core      | Pure Python stdlib          | No external dependencies for port scanning / killing    |
| Tests     | pytest                      | Simple, fast, widely adopted                            |
| Packaging | pyproject.toml (setuptools) | PEP 517/518 standard, pip-installable                   |

---

## Installation

Pick whichever package manager you already have — they all install the same
tool.

```bash
pip install portslayer              # Python / pip
npx @appestox/portslayer            # Node.js — try it with zero install
npm install -g @appestox/portslayer # Node.js — install permanently
uvx portslayer                      # zero-install, no Python setup needed
brew install AppestoX/PortSlayer/portslayer   # Homebrew (macOS/Linux)
scoop bucket add AppestoX https://github.com/AppestoX/scoop-bucket
scoop install portslayer                      # Scoop (Windows)
```

The npm, Homebrew, and Scoop packages are thin wrappers that install the
same `portslayer` PyPI package underneath — see
[`packaging/`](packaging/) for how each is built and published.

### Prerequisites

- Python 3.10 or later (the npm/Homebrew/Scoop wrappers install this
  dependency for you if it's missing)

### Install from source

```bash
git clone https://github.com/AppestoX/portslayer.git
cd portslayer
pip install -e ".[dev]"
```

### Linux — additional notes

No extra system packages required. `ss` is available by default on all modern
Linux distributions (`iproute2`). `lsof` is used as a fallback if `ss` is
not available.

To see processes owned by other users you must run with `sudo`:

```bash
sudo portslayer list
```

### Windows — additional notes

Run PowerShell or Command Prompt **as Administrator** to see all processes.
`netstat` and `taskkill` are built into every Windows installation.

---

## Usage

### Interactive TUI (recommended)

```bash
pk
```

(`pk` is the short alias for `portslayer` — both commands are identical and installed together; use whichever you prefer. The rest of this doc uses `portslayer` for clarity, but `pk` works everywhere it does.)

Launches a full-screen dashboard — no flags to remember:

| Key         | Action                          |
|-------------|----------------------------------|
| `↑` / `↓`   | Navigate the port list           |
| `/`         | Search/filter (port, process, protocol, state) |
| `k` / `Del` | Kill the selected process (asks to confirm)     |
| `r`         | Refresh now (auto-refreshes every 3s anyway)     |
| `Esc`       | Clear search                     |
| `q`         | Quit                             |

### CLI

#### List all active ports

```bash
portslayer list
```

Sample output:

```
╭────────────────────────────────────────────────────────────────────╮
│           Active Ports (24 entries)                                │
├──────┬──────────┬─────────────┬───────┬────────────┬──────────────┤
│ Port │ Protocol │ State       │   PID │ Process    │ Local Address│
├──────┼──────────┼─────────────┼───────┼────────────┼──────────────┤
│   22 │ TCP      │ LISTEN      │   783 │ sshd       │ 0.0.0.0:22  │
│   80 │ TCP      │ LISTEN      │  1042 │ nginx      │ 0.0.0.0:80  │
│ 5432 │ TCP      │ LISTEN      │  2103 │ postgres   │ 127.0.0.1:… │
╰──────┴──────────┴─────────────┴───────┴────────────┴──────────────╯
```

#### Filter ports

```bash
# By exact port number
portslayer list --port 443

# By partial port prefix — matches every port starting with these digits
portslayer list --port 808   # -> 8080, 8081, 8083, ...

# By process name (partial match)
portslayer list --process nginx

# By protocol
portslayer list --protocol tcp

# Only LISTENING ports
portslayer list --listening

# Combine filters
portslayer list --protocol tcp --listening
```

#### Inspect a specific port — or a partial prefix

```bash
portslayer find 8080   # exact port
portslayer find 808    # partial prefix -> matches 8080, 8081, 8083, ...
```

Typing fewer digits is a feature, not an error — no need to remember or
type the full number if you just want to see everything in that range.

#### Kill the process on a port

```bash
portslayer kill 3000
```

`kill` always requires an **exact** port number (not a prefix) — this is a
deliberate safety choice so a mistyped digit can't broaden which processes
get terminated. Use `find`/`list` with a prefix first to see what's there,
then `kill` the exact port you want.

```bash
# Kill by process name instead of port (kills every port that process owns)
portslayer kill --name node
```

PortSlayer will:
1. Show full process details
2. Ask for explicit confirmation
3. Kill the process only after `y` is entered

```bash
# Skip confirmation (use with care)
portslayer kill 3000 --force
```

#### Scripting with JSON output

`list` and `find` both accept `--json` for piping into `jq` or other tools
instead of printing a table:

```bash
portslayer list --json | jq '.[] | select(.protocol == "TCP")'
portslayer find 808 --json
```

#### Shell completion

Typer wires this up automatically — no extra setup needed:

```bash
portslayer --install-completion   # installs completion for your current shell
```

#### Version

```bash
portslayer --version
```

---

## Project Structure

```
portslayer/
├── portslayer/
│   ├── __init__.py          # Package version / metadata
│   ├── cli.py               # Typer CLI (list / find / kill) — bare invocation launches the TUI
│   ├── tui.py                # Textual interactive dashboard
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py        # PortInfo dataclass
│   │   ├── port_scanner.py  # Platform-specific scanning + parsers
│   │   └── process_killer.py# Safe process termination
│   └── utils/
│       ├── __init__.py
│       ├── platform_utils.py# OS detection, admin check
│       └── validators.py    # Port number validation
├── tests/
│   ├── test_validators.py
│   ├── test_port_scanner.py
│   └── test_process_killer.py
├── packaging/
│   ├── npm/                 # npm wrapper package (`npx @appestox/portslayer`)
│   ├── homebrew/            # Homebrew tap formula
│   └── scoop/                # Scoop bucket manifest
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── LICENSE
└── README.md
```

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

With coverage:

```bash
pytest --cov=portslayer --cov-report=term-missing
```

---

## Security

| Concern                    | Mitigation                                                             |
|----------------------------|------------------------------------------------------------------------|
| Command injection          | All subprocess calls use **explicit argument lists** — never `shell=True` |
| Input validation           | Port numbers are validated (regex + range check) before any system call |
| Confirmation requirement   | Every kill operation requires explicit user confirmation               |
| Privilege transparency     | Users are warned when not running as root/Administrator                |
| PID validation             | PID existence is verified before sending signals                       |

**PortSlayer never executes raw shell input from the user.**

---

## Platform-Specific Commands Used

| Platform | List ports                     | Get process names       | Kill process                |
|----------|--------------------------------|-------------------------|-----------------------------|
| Linux    | `ss -tulnp` → `lsof -i -n -P` | embedded in `ss` output | `os.kill(pid, SIGKILL)`     |
| Windows  | `netstat -ano`                 | `tasklist /FO CSV /NH`  | `taskkill /PID <pid> /F`    |
| macOS    | `lsof -i -n -P`                | embedded in `lsof`      | `os.kill(pid, SIGKILL)`     |

---

## Publishing (maintainers)

Order matters — the npm, Homebrew, and Scoop packages all install the PyPI
package under the hood, so PyPI goes first.

1. **PyPI** (source of truth):
   ```bash
   python -m pip install build twine
   python -m build
   twine upload dist/*
   ```
2. **npm wrapper** (`packaging/npm/`) — bump `version` in
   `packaging/npm/package.json` to match the PyPI release, then:
   ```bash
   cd packaging/npm && npm publish
   ```
3. **Homebrew tap** (`packaging/homebrew/`) — see
   [`packaging/homebrew/README.md`](packaging/homebrew/README.md) for
   generating dependency resource blocks and the sdist checksum, then push
   to your `homebrew-portslayer` tap repo.
4. **Scoop bucket** (`packaging/scoop/`) — see
   [`packaging/scoop/README.md`](packaging/scoop/README.md) for the
   checksum step, then push to your bucket repo. Winget requires a compiled
   installer and is documented as a follow-up in the same file.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Run tests: `pytest`
4. Open a pull request

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.
