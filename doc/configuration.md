# Configuration

This document lists every add-on setting, its default value, allowed values, and the exact JSON structures the add-on reads and writes.

## Where Settings Are Stored

| File | Purpose |
| --- | --- |
| `addon/config.json` | Default configuration shipped with the add-on. |
| `addon/config.md` | HTML schema used by Anki 23.10+ for the fallback config editor. |
| `addon/meta.json` | Runtime add-on state (managed by Anki + the add-on). Not shipped/committed. |
| `addon/manifest.json` | Static add-on metadata. |
| `addon/VERSION` | Plain-text current version. |

The live configuration is stored by Anki in the user profile (e.g. `meta.json` under the add-on's folder). When no config exists, `EFDRC.load_config()` applies the in-code defaults below.

---

## 1. Add-on Settings (`config`)

Defaults come from `addon/config.json` and are mirrored in `reviewer.py:EFDRC.load_config()` and `config_settings.py:SettingsTab`.

| Key | Type | Default | Allowed Values | Description |
| --- | --- | --- | --- | --- |
| `auto_enable` | bool | `true` | `true`, `false` | Auto-enable editing for all rendered fields without `edit:`. |
| `show_outline` | bool | `true` | `true`, `false` | Show the dashed outline on hover while the trigger modifier is held. |
| `exclusions` | object | `{}` | note-type-keyed object | Legacy exclusions (keyed by note-type name). |
| `exclusions_v2` | object | `{}` | note-type-ID-keyed object | Stable exclusions (keyed by note-type ID). |
| `trigger_modifier` | string | `"Ctrl"` | `Ctrl`, `Shift`, `Alt`, `None` | Modifier required to trigger editing. |
| `trigger_action` | string | `"Click"` | `Click`, `DoubleClick` | Mouse action that triggers editing. |
| `show_review_button` | bool | `false` | `true`, `false` | Show the extra **Edit (N)** button on the review screen. |
| `enable_undo` | bool | `false` | `true`, `false` | Enable custom `Ctrl+Z` undo behaviour. |
| `undo_style` | string | `"per_field"` | `per_field`, `full_snapshot`, `editor_only` | Which undo style custom `Ctrl+Z` uses. |
| `separate_editor_preferences` | bool | `true` | `true`, `false` | Keep the reviewer editor's preferences separate from Anki's main editor. |
| `reviewer_editor_preferences` | object | `{}` | editor-preference object | Saved separate preferences (see section 3). |
| `preload_add_window` | bool | `true` | `true`, `false` | Preload the Add Cards window in the background. |

> Note: `load_config()` uses default `separate_editor_preferences` and `preload_add_window` of `true`. Older `config.json` snapshots may have `false`; defaults are applied via `setdefault`.

### `exclusions` (legacy) value shape

```json
{
  "<NoteTypeName>": {
    "disabled": true,
    "templates": ["Card 1"],
    "fields": ["Front", "Back"]
  }
}
```

### `exclusions_v2` (stable) value shape

```json
{
  "<NoteTypeID>": {
    "disabled": true,
    "templates": [0, 1],
    "fields": [0, 2]
  }
}
```

- Templates and fields are referenced by **ordinal** (index) in `exclusions_v2`, and by **name** in the legacy `exclusions`.
- If `exclusions_v2` has an entry for a note type, it takes precedence over the legacy `exclusions` entry.

---

## 2. Undo Style Mapping

Mapping defined in `config_settings.py:UNDO_STYLE_MAP` (UI label → stored value):

| UI Label | Stored Value (`undo_style`) |
| --- | --- |
| Full Snapshot Revert | `full_snapshot` |
| Per-Field Revert | `per_field` |
| In-Editor Only | `editor_only` |

---

## 3. `reviewer_editor_preferences` (nested object)

The separate editor preferences object. Keys and defaults come from `config.py:default_editor_preferences()`.

| Key | Type | Default | Notes |
| --- | --- | --- | --- |
| `last_text_color` | string | `"#0000ff"` | Last used text colour. |
| `last_highlight_color` | string | `"#ffff00"` | Last used highlight colour. |
| `tags_collapsed` | bool | `false` | Whether the tags area is collapsed. |
| `render_mathjax` | bool | `true` | Render MathJax in the editor. |
| `shrink_images` | bool | `true` | Shrink large pasted images. |
| `close_html_tags` | bool | `true` | Auto-close HTML tags while typing. |
| `custom_color_picker_palette` | array | `[]` | Custom colour-picker palette (list of colour strings). |
| `paste_images_as_png` | bool | `false` | Convert pasted images to PNG. |
| `paste_strips_formatting` | bool | `false` | Strip formatting when pasting. |

When `separate_editor_preferences` is enabled, these are captured from Anki on activation (`config.py:collect_editor_preferences`) and restored on deactivation (`config.py:apply_editor_preferences`).

---

## 4. `config.md` (fallback schema)

`addon/config.md` lists the settings exposed through Anki 23.10+'s standard HTML config editor. It references the same keys as above:

- **General**: `auto_enable`, `show_outline`, `trigger_modifier`, `trigger_action`, `show_review_button`
- **Undo Behavior**: `enable_undo`, `undo_style`
- **Advanced**: `separate_editor_preferences`

(`preload_add_window` and the exclusion tree are only exposed through the custom Qt dialog.)

---

## 5. `manifest.json`

```json
{
  "package": "efdrn",
  "name": "Edit Field During Review (Native)",
  "version": "7.4.2",
  "human_version": "7.4.2",
  "conflicts": ["1020366288"]
}
```

| Key | Value | Description |
| --- | --- | --- |
| `package` | `efdrn` | Internal add-on package name. |
| `name` | Edit Field During Review (Native) | Display name. |
| `version` | `7.4.2` | Machine version (synced to `VERSION`). |
| `human_version` | `7.4.2` | Human-readable version. |
| `conflicts` | `["1020366288"]` | Conflicting add-on IDs (the original Cloze add-on). |

---

## 6. `VERSION`

A single line containing the version, e.g. `7.4.2`. Kept in sync with `manifest.json` by `bump.py`.

---

## 7. `meta.json` (runtime, generated)

Not committed or shipped. Anki writes this with the add-on's live config and state. Fields observed:

| Key | Type | Description |
| --- | --- | --- |
| `config` | object | Live copy of the add-on configuration (see section 1). |
| `disabled` | bool | Whether the add-on is disabled. |
| `mod` | number | Modification counter. |
| `conflicts` | array | Conflicts detected by Anki. |
| `max_point_version` / `min_point_version` | number | Anki API version bounds. |
| `branch_index` | number | Update branch index. |
| `update_enabled` | bool | Whether Anki Web updates are enabled. |
| `supporter_opt_out` | bool | Whether the Support tab auto-open is disabled. |
| `last_version` | string | Last version the add-on ran, used to detect updates. |

`supporter_opt_out` and `last_version` are written by the add-on itself (`config_support.py` and `__init__.py`).

---

## 8. Other Constants

| Constant | Location | Value |
| --- | --- | --- |
| `LOG_FILE_NAME` | `log_handler.py` | `efdrn.log` |
| `max_records` | `log_handler.py` | `1000` (in-memory log records) |
| `preload_delay_ms` | `reviewer.py:EFDRC` | `150` (editor preload delay) |
| Ko-fi URL / id | `config_support.py` | `D1D01W6NQT` |
| UPI address | `config_support.py` | `athulkrishnasv2015-2@okhdfcbank` |
| BTC address | `config_support.py` | `bc1qrrek3m7sr33qujjrktj949wav6mehdsk057cfx` |
| ETH address | `config_support.py` | `0xce6899e4903EcB08bE5Be65E44549fadC3F45D27` |
