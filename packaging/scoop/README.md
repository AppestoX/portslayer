# Scoop distribution

Scoop apps live in a **bucket** (your own manifest repo), not the main
`scoop-extras`/`scoop-main` bucket, until the project is popular enough to
be accepted there. Steps:

1. Publish `portslayer` to PyPI first.
2. Create a repo named `scoop-bucket` (or similar) with a `bucket/` folder.
3. Copy `portslayer.json` into `bucket/portslayer.json`.
4. Fill in the real `hash` (sha256 of the PyPI sdist tarball — shown on the
   PyPI project's "Download files" page).
5. Commit and push. Users install with:
   ```powershell
   scoop bucket add AppestoX https://github.com/AppestoX/scoop-bucket
   scoop install portslayer
   ```
6. Test locally first: `scoop install ./portslayer.json`.

This manifest depends on Scoop's `python` app (`scoop install python`), then
runs `pip install portslayer` as a post-install step — the `portslayer`
command is provided by pip's own console-script shim, which Scoop's Python
already puts on `PATH`.

## Winget

Winget's manifest format expects a real installer (MSI/EXE/MSIX), which a
pure `pip`-based tool doesn't have — submitting a passthrough manifest like
the Scoop one above would be rejected by Microsoft's validation. To support
`winget install portslayer` properly, build a standalone binary first (e.g.
via `pyinstaller --onefile`) and attach it to GitHub Releases, then generate
the manifest with `wingetcreate submit <release-asset-url>`. Treat this as a
follow-up once you're ready to maintain compiled release binaries.
