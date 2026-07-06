# Homebrew distribution

Homebrew formulas for non-trivial-dependency Python CLIs are published via a
**tap** (your own formula repo), not `homebrew-core`, until the project is
established enough to meet core's notability bar. Steps:

1. Publish `portslayer` to PyPI first (this formula installs from the PyPI
   sdist).
2. Create a repo named `homebrew-portslayer` under your GitHub org/user
   (the `homebrew-` prefix is required — Homebrew strips it automatically,
   so users type `brew tap AppestoX/PortSlayer`).
3. Copy `portslayer.rb` into that repo's root (or a `Formula/` subdir).
4. Generate real dependency resource blocks:
   ```bash
   pip install homebrew-pypi-poet
   pip install portslayer   # so poet can introspect its deps
   poet -f portslayer > resources.rb
   ```
   Paste the generated `resource "..." do ... end` blocks into
   `portslayer.rb`, replacing the placeholder comment.
5. Fill in the real sdist `sha256` (shown on the PyPI project's "Download
   files" page, or via `shasum -a 256 portslayer-1.0.0.tar.gz`).
6. Commit and push. Users install with:
   ```bash
   brew tap AppestoX/PortSlayer
   brew install portslayer
   ```
7. Test locally before pushing: `brew install --build-from-source ./portslayer.rb`.

Bump the `url`/`sha256` (and re-run `poet`) on every new PyPI release.
