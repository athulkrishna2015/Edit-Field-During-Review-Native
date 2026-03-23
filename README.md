# Edit Field During Review (Native) [EFDRN]

This Anki add-on allows you to edit fields directly during review by embedding the native Anki editor into the review window.

## ✨ Features

- **Native Editor Support**: Use the full power of Anki's native editor (toolbars, clozes, mathjax, LaTeX, etc.) directly in the review window.
- **No-Setup Mode**: By default, **all fields are editable**! No need to manually add `edit:` to your card templates (though `{{edit:FieldName}}` is still supported for explicit control).
- **Seamless Integration**: The editor appears above your card content without opening a new window, preserving your review context.
- **Granular Control**: Enable or disable editing for specific **Note Types**, **Templates (Card Types)**, or **Fields** via a simple tree-view configuration.
- **Customizable Triggers**: Choose your preferred trigger modifier (Ctrl, Shift, Alt, or None) and action (Click or DoubleClick).
- **Browser Preview Support**: Edit fields directly from the Browser's preview pane.
- **Fast & Reliable**: Uses native components for maximum performance and compatibility with other add-ons.

## 🚀 How to Use

1. **Trigger the Editor**: During review (or in the Browser Preview), use the default trigger: **Ctrl + Click** (or **Cmd + Click** on Mac) on the field content.
2. **Visual Feedback**: When holding your trigger modifier (e.g., Ctrl), editable fields will show a dashed outline on hover.
3. **Edit Your Content**: The native editor will appear above the card. All standard Anki editor shortcuts and toolbar buttons are available.
4. **Save and Close**: Click the **Done** button or press **Ctrl + Enter** to save your changes and return to the review immediately.

## ⚙️ Configuration

Access the configuration via **Tools > Add-ons > EFDRN > Config**.

- **Auto-enable**: Toggle whether the add-on should automatically enable editing for all fields without the `edit:` filter.
- **Show outline**: Toggle the visual dashed outline on hover.
- **Trigger Modifier**: Choose between `Ctrl`, `Shift`, `Alt`, or `None`.
- **Trigger Action**: Choose between `Click` or `DoubleClick`.
- **Exclusions**: Use the tree view to disable editing for specific Note Types, Templates, or Fields. Use the **Enable All** and **Disable All** buttons for bulk management.

## 🛠️ Development

This add-on is simplified to use native Anki components and requires no external build steps.

### Building
To create the `.ankiaddon` package:
```shell
python make_ankiaddon.py
```
This will automatically bump the patch version and generate a timestamped `.ankiaddon` file in the root directory.

## 📜 Credits & License
- Refactored version of "Edit Field During Review (Cloze)".
- Based on code from Anki and other contributors.
- Licensed under the **GNU AGPL v3**.
