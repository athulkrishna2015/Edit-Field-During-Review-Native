# [Edit Field During Review (Native) [EFDRN]](https://github.com/athulkrishna2015/Edit-Field-During-Review-Native)

This Anki add-on lets you edit note fields directly during review by embedding Anki's native editor into the review window.
Install from [anki web](https://ankiweb.net/shared/info/2117554822)

## Features

- **Native Editor Support**: Use the full power of Anki's native editor (toolbars, clozes, MathJax, LaTeX, and more) directly in the review window.
- **No-Setup Mode**: By default, rendered note fields such as `{{Front}}` and `{{cloze:Text}}` are made editable automatically during review. You do not need to manually add `edit:` to your card templates, though `{{edit:FieldName}}` is still supported for explicit control.
- **Seamless Integration**: The editor appears above your card content without opening a new window, preserving your review context.
- **Granular Control**: Enable or disable editing for specific **Note Types**, **Templates (Card Types)**, or **Fields** via a simple tree-view configuration.
- **Customizable Triggers**: Choose your preferred trigger modifier (Ctrl, Shift, Alt, or None) and action (Click or DoubleClick).
- **Review Screen Native Button**: Optionally adds an **Edit (N)** button on the review screen to open the embedded editor directly. This button is disabled by default and can be enabled in config.
- **Image Occlusion Support**: Image Occlusion cards can open the embedded editor through the optional review screen **Edit (N)** button or the **N** shortcut, even when there is no clickable field on the card.
- **Separate Reviewer Preferences**: Keep the embedded reviewer editor's color memory, collapse state, paste behavior, and editor toggles separate from Anki's main editor.
- **Fast & Reliable**: Uses native components for maximum performance and compatibility with other add-ons.

## How to Use

1. **Trigger the Editor**: During review, use the default trigger: **Ctrl + Click** (or **Cmd + Click** on Mac) on the field content.
2. **Review Screen Native Button**: If enabled in config, click **Edit (N)** to open the embedded editor directly from the review screen. The **N** shortcut works regardless of button visibility.
3. **Image Occlusion Cards**: On Image Occlusion notes, use the optional **Edit (N)** button or press **N** to open the embedded editor.
4. **Visual Feedback**: When holding your trigger modifier, editable fields and Image Occlusion areas show a dashed outline on hover.
5. **Edit Your Content**: The native editor appears above your card. Standard Anki editor shortcuts and toolbar buttons are available.
6. **Undo Support**: Ctrl+Z behavior is configurable. Enable "Custom Undo" in config to choose a style: **Per-Field Revert** (reverts only the focused field, default), **Full Snapshot Revert** (reverts all fields), or **In-Editor Only** (standard Ctrl+Z). Ctrl+Y always works for redo.
7. **Save and Close**: Click the **Done** button, press **Ctrl + Enter**, or press **Esc** to save your changes and return to review immediately.

If you disable **Auto-enable**, add `{{edit:FieldName}}` only to the fields you want editable.

`Edit (N)` and `N` open EFDRN's embedded editor. The `Edit (N)` button is off by default and can be enabled in config. Anki's standard `Edit` button and `E` shortcut still open Anki's regular editor.

![demo](https://github.com/user-attachments/assets/1e27d7d1-4b82-44c3-a38e-00e8d62acbd3)

## Configuration

Access the configuration via either **Tools > Add-ons > EFDRN > Config** or **Tools > EFDRN Configuration**.

- **Auto-enable**: Toggle whether the add-on should automatically enable editing for rendered note fields without the `edit:` filter.
- **Explicit `edit:` support**: If Auto-enable is off, add `{{edit:FieldName}}` to any field you want clickable in review.
- **Show outline**: Toggle the visual dashed outline on hover.
- **Trigger Modifier**: Choose between `Ctrl`, `Shift`, `Alt`, or `None`.
- **Trigger Action**: Choose between `Click` or `DoubleClick`.
- **Show "Edit (N)" Button On Review Screen**: Toggle whether the extra review-screen button for the embedded editor is shown. Disabled by default.
- **Enable Custom Undo (Ctrl+Z)**: Toggle enhanced Ctrl+Z behavior on or off (disabled by default).
- **Undo Style**: Choose between `Per-Field Revert` (reverts only the focused field, default), `Full Snapshot Revert` (reverts all fields), or `In-Editor Only` (standard Ctrl+Z behavior).
- **Separate Reviewer Preferences**: When enabled, the embedded reviewer editor keeps its own colors, tag collapse state, MathJax/image/HTML toggle state, and paste behavior without changing Anki's main editor preferences.
- **Exclusions**: Use the tree view to disable editing for specific Note Types, Templates, or Fields. Exclusions apply to both auto-enabled fields and explicit `{{edit:...}}` fields. Use the **Enable All** and **Disable All** buttons for bulk management.
- **Support Tab**: The config dialog also includes a `Support` tab with large QR codes and copy buttons for UPI, BTC, and ETH.

## Troubleshooting

- **Can't edit during review**: Auto-enable is on by default. If you turned it off, add `{{edit:FieldName}}` to the fields you want clickable.
- **Image Occlusion cards**: Use the optional **Edit (N)** button or the **N** shortcut to open the embedded editor. `Ctrl+Click` is currently unreliable on Image Occlusion cards.
- **Editor shortcuts**: Standard native editor shortcuts such as `Ctrl+B` and `Ctrl+Shift+C` work inside the embedded editor.
- **Closing the editor**: Use **Done**, `Ctrl+Enter`, or `Esc` to save your changes and return to review.
- **Undo behavior**: By default, `Ctrl+Z` uses the embedded editor's normal undo. If **Custom Undo** is enabled, `Ctrl+Z` uses the selected undo style instead. `Ctrl+Y` continues to work for redo.

---
## Support

If you find this add-on useful, please consider supporting its development:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/D1D01W6NQT)

## Change Log

### 05/04/2026

- **Crash Fix**: Resolved a `RuntimeError` regarding C++ object deletion when interacting with the hidden editor widget (e.g., jumping between cards or using `N` shortcut).

### 02/04/2026

- **Cloze Bug Fix**: Fixed a critical issue where Anki would incorrectly default to displaying Cloze 1 deletions for Cloze 2 and above when using the embedded editor.
- **Native Config GUI**: Enabled standard HTML-based configuration from Anki's Add-on manager through a new `config.md` fallback, while safely maintaining the advanced Qt GUI dialog.
- **Crash Fix**: Resolved a `RuntimeError` that occurred when closing the profile, improving shutdown stability.

### 25/03/2026

- **Flicker Fix**: The embedded editor no longer causes the review screen to flicker or blank out while saving or redrawing the current card.
- **Review Screen Native Button**: Added an optional **Edit (N)** button and **N** shortcut on the review screen to open the embedded editor directly. The button is disabled by default and can be enabled in config.
- **Multiple Undo Styles**: Ctrl+Z now supports configurable undo behavior with three styles: Per-Field Revert (reverts only the focused field), Full Snapshot Revert (reverts all fields to when editing started), and In-Editor Only (standard Ctrl+Z behavior).
- **Enable/Disable Undo**: New "Enable Custom Undo" toggle in config (disabled by default). When enabled, Ctrl+Z uses the chosen undo style instead of in-editor undo.
- **Fixed No-Setup Editing**: Rendered reviewer fields are now auto-wrapped correctly, so Auto-enable works without manually adding `edit:` to templates.
- **Exclusions Hardened**: Disabled note types, templates, and fields now apply to explicit `{{edit:...}}` usage too, and exclusion settings survive renames by using stable internal IDs.
- **Toolbar Simplified**: The embedded editor now focuses on the native editing flow with **Done**, native undo/redo instead of a separate restore button.
- **Documentation Cleanup**: Updated the README, development notes, and config wording to match the current reviewer workflow.

### 24/03/2026

- **Eliminated Flicker**: The review screen now remains visible during the save transition, removing the "blank screen" jump when finishing an edit.
- **Image Occlusion Support**: Added review-screen support for opening the embedded editor on Image Occlusion cards.
- **Architectural Cleanup**: Refactored the internal code into specialized modules (`editor`, `utils`, `config`) for better stability and faster loading on newer Anki versions.
- **Added to Tools Menu**: Quick access to configuration via `Tools > EFDRN Configuration`.
- **README Refresh**: Updated installation info, screenshots, and repository links.

### 23/03/2026

- **Config Persistence Fix**: Configuration now resolves consistently through the base add-on name.
- **Empty Field Triggering**: Empty editable fields now expose a visible placeholder so they can still be clicked during review.
- **Undo/Redo Reliability**: Improved reviewer editing behavior and documentation around native undo/redo handling.

## Credits & License

- Refactored version of "Edit Field During Review (Cloze)".
- Based on code from Anki and other contributors.
- Licensed under the **GNU AGPL v3**.
