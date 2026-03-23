# Edit Field During Review (Native) - Developer Notes

This repository contains the source for the **Edit Field During Review (Native)** (EFDRN) Anki add-on.

## Project Structure

- `addon/`: Add-on package contents.
  - `__init__.py`: Entry point.
  - `reviewer.py`: Main implementation (Reviewer hooks, Editor embedding).
  - `web/`: Web assets (CSS/JS for visual feedback).
  - `manifest.json`: Add-on metadata.
  - `VERSION`: Local development version file (semantic version string).
- `bump.py`: Version helpers (`validate_version`, `sync_version`) and configurable semantic bumping (`major`/`minor`/`patch`, default `patch`).
- `make_ankiaddon.py`: Creates `.ankiaddon`; auto-bumps patch only when no explicit version is provided.

## Features Wired Into Anki

- Reviewer field filter: converts `{{edit:Field}}` into a span with data attributes.
- Reviewer WebView: injected JS/CSS to handle Ctrl+Click and visual feedback.
- Native Editor: When a field is Ctrl-clicked, a native Anki `Editor` is initialized and embedded above the card.
- Done button: Saves changes via `editor.saveNow()` and refreshes the reviewer.

## Versioning Scheme

Version format is strictly:

```text
major.minor.patch
```

Behavior:

- `bump.py` validates semantic version format and syncs:
  - `manifest.json` keys: `version`, `human_version`
  - `addon/VERSION`
- `bump.py` can read current version and increment:
  - `patch`: `x.y.z` -> `x.y.(z+1)` (default)
  - `minor`: `x.y.z` -> `x.(y+1).0`
  - `major`: `x.y.z` -> `(x+1).0.0`
- `make_ankiaddon.py` behavior:
  - Without args: auto-bumps patch via `bump.py`, then packages.
  - With `<major.minor.patch>` arg: writes that version via `bump.py` sync helpers, then packages without bumping.

## Common Commands

Bump patch version:

```shell
python bump.py
```

Bump minor version:

```shell
python bump.py minor
```

Bump major version:

```shell
python bump.py major
```

Build `.ankiaddon` locally:

```shell
python make_ankiaddon.py
```

Build `.ankiaddon` with explicit version (no auto-bump):

```shell
python make_ankiaddon.py 1.5.0
```

Output naming format:

```text
Edit_Field_During_Review_Native_v<major.minor.patch>_<YYYYMMDDHHMM>.ankiaddon
```

## Local Testing With Symlink

Linux:

```shell
ln -s "$(pwd)/addon" ~/.local/share/Anki2/addons21/efdrn_dev
```

Windows (PowerShell as admin):

```powershell
New-Item -ItemType SymbolicLink -Path "$env:APPDATA\Anki2\addons21\efdrn_dev" -Target "$pwd\addon"
```
