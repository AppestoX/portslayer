# @appestox/portslayer (npm wrapper)

This package lets Node.js users run PortSlayer via `npx @appestox/portslayer`
or `npm install -g @appestox/portslayer` without knowing it's built in Python.

On install, it locates a Python 3.10+ interpreter on your `PATH` and installs
the [`portslayer`](https://pypi.org/project/portslayer/) PyPI package via
`pip`. Both the `portslayer` and short `pk` commands it exposes simply
forward your arguments to `python -m portslayer.cli`.

## Requirements

Python 3.10+ must be installed and on your `PATH`. If it isn't, install it
from [python.org](https://python.org/downloads) and re-run:

```bash
npm install -g @appestox/portslayer
```

## Usage

```bash
npx pk                  # launch the interactive TUI dashboard
npx pk list              # list all active ports
npx pk find 3000         # inspect port 3000
npx pk kill 3000         # kill the process on port 3000
```

See the [main README](https://github.com/AppestoX/portslayer#readme) for
full documentation.
