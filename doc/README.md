# Edit Field During Review (Native) [EFDRN] — Documentation

This folder contains developer and user documentation for the **Edit Field During Review (Native)** add-on.

> Package ID: `efdrn` · Latest version: `7.4.4` · License: GNU AGPL v3

## Index

| Document | Description |
| --- | --- |
| [features.md](features.md) | Full add-on description, feature list, and how it works. |
| [configuration.md](configuration.md) | Every setting, its default value, allowed values, and the underlying JSON structures. |
| [code-structure.md](code-structure.md) | Module layout, classes, functions, variables, and inter-module flow. |
| [CHANGELOG.md](CHANGELOG.md) | All notable changes organized by version. |

## Quick Reference

- **Add-on name**: Edit Field During Review (Native)
- **Manifest package**: `efdrn`
- **Conflicts**: `1020366288` (the original "Edit Field During Review (Cloze)" add-on)
- **AnkiWeb ID**: `2117554822`
- **Repository**: https://github.com/athulkrishna2015/Edit-Field-During-Review-Native
- **Installed location**: Anki's `addons21/efdrn/` directory

## File Tree

```
addon/
├── __init__.py            Entry point; update check + auto-open Support tab
├── reviewer.py            Core controller (class EFDRC) + runtime monkey-patches
├── editor.py              EmbeddedReviewerEditor (subclass of aqt.editor.Editor)
├── config.py              Config dialog builder + editor-preferences helpers
├── config_settings.py     "Settings" tab UI + exclusion tree
├── config_support.py      "Support" tab (donations, QR codes, supporter opt-out)
├── config_log.py          "Log" tab (live log viewer)
├── config.md              Anki 23.10+ HTML fallback config schema
├── config.json            Default add-on configuration
├── manifest.json          Add-on metadata (package, name, version, conflicts)
├── VERSION                Plain-text version string
├── log_handler.py         File + in-memory logger ("efdrn")
├── utils.py               Exclusion helpers, field/template logic, filter rewriting
├── web/
│   ├── efdrc.js           Front-end: click/dblclick triggers, Edit (N) button injection
│   └── efdrc.css          Outline / hover / empty-field styling
└── Support/
    ├── UPI.jpg            Donation QR code
    ├── BTC.jpg            Donation QR code
    └── ETH.jpg            Donation QR code
```

## Distribution / Build

- `make_ankiaddon.py` builds a `.ankiaddon` package from the `addon/` directory.
- `bump.py` reads/bumps the version across `VERSION` and `manifest.json`.
- Runtime artifacts (`efdrn.log`, `meta.json`, `__pycache__`) are git-ignored and excluded from the package.
