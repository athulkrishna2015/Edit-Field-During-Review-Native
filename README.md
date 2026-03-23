# Edit Field During Review (Native) [EFDRN]

This Anki add-on allows you to edit fields directly during review by embedding the native Anki editor into the review window.

## Features

- **Native Editor Support**: Use the full power of Anki's native editor (toolbars, clozes, MathJax, LaTeX, and more) directly in the review window.
- **No-Setup Mode**: By default, **all fields are editable**. You do not need to manually add `edit:` to your card templates, though `{{edit:FieldName}}` is still supported for explicit control.
- **Seamless Integration**: The editor appears above your card content without opening a new window, preserving your review context.
- **Granular Control**: Enable or disable editing for specific **Note Types**, **Templates (Card Types)**, or **Fields** via a simple tree-view configuration.
- **Customizable Triggers**: Choose your preferred trigger modifier (Ctrl, Shift, Alt, or None) and action (Click or DoubleClick).
- **Image Occlusion Support**: Image Occlusion cards can open the embedded editor through **Ctrl + Click** on the image, the review screen's **Edit** button, or the **E** shortcut, even when there is no clickable field on the card.
- **Separate Reviewer Preferences**: Keep the embedded reviewer editor's color memory, collapse state, paste behavior, and editor toggles separate from Anki's main editor.
- **Fast & Reliable**: Uses native components for maximum performance and compatibility with other add-ons.

## How to Use

1. **Trigger the Editor**: During review, use the default trigger: **Ctrl + Click** (or **Cmd + Click** on Mac) on the field content.
2. **Image Occlusion Cards**: On Image Occlusion notes, you can **Ctrl + Click** the image, use the review screen's **Edit** button, or press **E** to open the embedded editor.
3. **Visual Feedback**: When holding your trigger modifier, editable fields and Image Occlusion areas show a dashed outline on hover.
4. **Edit Your Content**: The native editor appears above your card. Standard Anki editor shortcuts and toolbar buttons are available.
5. **Undo While Editing**: Use **Ctrl + Z** while the embedded editor is open, or click the **Undo Edit** button beside **Done**. If another add-on or a global shortcut still grabs `Ctrl+Z`, set a dedicated fallback shortcut in the add-on config.
6. **Save and Close**: Click the **Done** button, press **Ctrl + Enter**, or press **Esc** to save your changes and return to review immediately.

## Configuration

Access the configuration via **Tools > Add-ons > EFDRN > Config**.

- **Auto-enable**: Toggle whether the add-on should automatically enable editing for all fields without the `edit:` filter.
- **Show outline**: Toggle the visual dashed outline on hover.
- **Trigger Modifier**: Choose between `Ctrl`, `Shift`, `Alt`, or `None`.
- **Trigger Action**: Choose between `Click` or `DoubleClick`.
- **Custom Undo Shortcut**: Set a dedicated embedded-editor undo shortcut such as `Ctrl+Alt+Z`. Leave it blank to disable the fallback shortcut.
- **Separate Reviewer Preferences**: When enabled, the embedded reviewer editor keeps its own colors, tag collapse state, MathJax/image/HTML toggle state, and paste behavior without changing Anki's main editor preferences.
- **Exclusions**: Use the tree view to disable editing for specific Note Types, Templates, or Fields. Use the **Enable All** and **Disable All** buttons for bulk management.
- **Support Tab**: The config dialog also includes a `Support` tab with large QR codes and copy buttons for UPI, BTC, and ETH.

## Recent Changes (23/03/2026)

- **Fixed Undo/Redo**: The "Undo Edit" button and shortcuts now reliably refocus the active field before executing, ensuring changes are reverted correctly.
- **Eliminated Flicker**: The review screen now remains visible during the save transition, removing the "blank screen" jump when finishing an edit.
- **Image Occlusion Support**: Added **Ctrl + Click** (or your custom modifier) support directly on Image Occlusion images to trigger the editor.
- **Architectural Cleanup**: Refactored the internal code into specialized modules (`editor`, `utils`, `config`) for better stability and faster loading on newer Anki versions.
- **Added to Tools Menu**: Quick access to configuration via `Tools > EFDRN Configuration`.

## Known Issues

- **Undo Reliability**: The "Undo Edit" button and the `Ctrl+Z` shortcut inside the embedded editor may still be inconsistent on some systems or Anki versions. We are investigating a more robust fix for the editor's internal undo stack.

## Credits & License

- Refactored version of "Edit Field During Review (Cloze)".
- Based on code from Anki and other contributors.
- Licensed under the **GNU AGPL v3**.
