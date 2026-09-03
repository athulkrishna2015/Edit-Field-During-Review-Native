# Features

## Overview

**Edit Field During Review (Native)** lets you edit note fields directly during review by embedding **Anki's native editor** into the review window. Instead of opening a separate window, the full editor (toolbars, cloze, MathJax, LaTeX, formatting, image pasting) appears above your card content, and saving returns you straight to review.

It is a re-engineering of the classic "Edit Field During Review (Cloze)" add-on around Anki's native editor, so it stays compatible with modern Anki versions and other add-ons.

## How It Works

1. **Rendering**: When a card renders during review, the add-on's template filter wraps every allowed rendered field in a `<span data-efdrc-idx="N">…</span>` (with class `efdrc-empty` if the field is empty).
2. **Triggering**: A front-end script (`efdrc.js`) listens for the configured trigger (e.g. `Ctrl+Click`). Clicking a wrapped field sends `EFDRC!edit#<idx>` to Python.
3. **Embedding**: Python hides the reviewer webview, shows a widget containing a real `aqt.editor.Editor`, loads the card's note into it, and focuses the clicked field.
4. **Editing**: All native editor behaviour is available. Undo/redo can optionally be customised.
5. **Saving**: Clicking **Done**, pressing **Ctrl+Enter**, or **Esc** flushes the note via `saveNow`/`call_after_note_saved`, then reloads the reviewer (preserving the card timer) and returns to review.

## Feature List

### Native Editor
- Embeds Anki's real editor (toolbars, cloze, MathJax, LaTeX, HTML, image paste) inside the review window.
- No separate window; the editor appears in place above the card, preserving review context.
- A top bar shows **"Native Field Editor"** and a **"Done (Ctrl+Enter)"** button.

### No-Setup Auto-enable (default)
- Rendered fields such as `{{Front}}` and `{{cloze:Text}}` are made editable automatically — no need to add `edit:` to templates.
- `{{edit:FieldName}}` is still supported for explicit control when auto-enable is off.
- The backend hook rewrites the rendered template to inject the `edit` filter; the `cloze:` ord bug (showing Cloze 1 instead of the correct cloze) is handled by patching `TemplateRenderContext._partially_render`.

### Granular Exclusions
- Disable editing for specific **note types**, **templates (card types)**, or **fields** via a tree view in the Settings tab.
- Exclusions apply to both auto-enabled fields and explicit `{{edit:...}}` fields.
- Two storage formats are supported:
  - `exclusions` (legacy, keyed by note-type name)
  - `exclusions_v2` (stable, keyed by note-type ID, so settings survive renames)
- **Enable All / Disable All** buttons for bulk management.

### Customizable Triggers
- Modifier: `Ctrl`, `Shift`, `Alt`, or `None`.
- Action: `Click` or `DoubleClick`.
- While the modifier is held (or always, when `None`), editable fields and Image Occlusion areas show a dashed outline on hover.

### Review Screen Native Button / Shortcut
- Optional **Edit (N)** button on the review screen (off by default).
- The **N** shortcut always works to open the embedded editor.
- `E` still opens Anki's regular editor; `Edit (N)`/`N` open EFDRN's embedded editor.
- Korean keyboard shortcuts `ㄷ` (E) and `ㅜ` (N) are also bound.

### Image Occlusion Support
- On Image Occlusion cards, `Ctrl+Click` on an image/canvas area or the **Edit (N)** button / **N** shortcut opens the embedded editor.
- The add-on picks the first non-occlusion editable field (Header, Back Extra, Comments, etc.).

### Custom Undo (optional)
- `Ctrl+Z` behaviour is configurable via **Enable Custom Undo (Ctrl+Z)** (off by default) and **Undo Style**:
  - **Per-Field Revert** (default): reverts only the focused field.
  - **Full Snapshot Revert**: reverts all fields to their state when editing started.
  - **In-Editor Only**: standard in-editor undo.
- `Ctrl+Y` always performs redo.
- While custom undo is active, the main window undo/redo shortcuts are temporarily suspended and the editor's own `Ctrl+Z`/`Ctrl+Y` shortcuts are managed by the add-on.
- Undo uses a snapshot of all field values taken when the editor opens (`note_snapshot`).

### Separate Reviewer Editor Preferences
- When enabled (default), the embedded editor keeps its own preferences independent of Anki's main editor:
  - last text colour, last highlight colour
  - tags collapsed state
  - MathJax rendering, image shrink, HTML auto-close
  - custom colour picker palette
  - paste-as-PNG, paste-strips-formatting
- These are captured/restored around each edit session and stored under `reviewer_editor_preferences`.

### Performance & UX
- **Preloads** the embedded editor when entering review (deferred via timer) to open almost instantly.
- **Preload Add Cards window** option (default on): the Add Cards dialog is constructed in the background for near-instant opening, while preserving the user's selected deck.
- **Optimized card content loading (7.4.4)**: When a new question card is shown, the Add Cards window and card content are preloaded proactively with reduced delays (50ms for AddCards, 100ms for card content), making "Study Now" and card transitions feel snappier.
- **Throttled reviewer refresh (7.4.4)**: A defer counter limits consecutive deferrals (max 3) to prevent excessive refresh suppression while editing.
- **Flicker-free** save: the reviewer webview is shown immediately during the save transition.
- While editing, reviewer redraws are deferred so focus stays in the editor.

### Add Cards Integration
- Opening Add Cards during review selects the current card's deck.
- Changing the card/note type during review no longer resets the deck to the new type's default deck (preserves Anki default behaviour outside review).

### Configuration Dialog (Qt)
- Accessible via **Tools > Add-ons > EFDRN > Config** or **Tools > EFDRN Configuration**.
- Tabs: **Settings**, **Support**, **Log**.

### Support Tab
- Ko-fi widget, plus UPI / BTC / ETH QR codes with copyable addresses.
- "I have supported this addon" checkbox hides the automatic post-update welcome.
- Auto-opens once after an add-on update (unless opted out).

### Log Tab
- Live, real-time log viewer (last 1000 records in memory, also written to `efdrn.log`).
- Buttons: **Refresh**, **Copy**, **Clear**, and an **Auto-scroll** toggle.

## Compatibility

- Requires modern Anki (native editor embedding, `parentWindow`/`EditorMode` supported).
- Declares a conflict with the original add-on `1020366288`.
- Patches used at runtime:
  - `Reviewer.op_executed` — defer reviewer refresh while editing.
  - `TemplateRenderContext._partially_render` — inject `edit` filter and fix cloze ord.
  - `aqt.addcards.AddCards.on_notetype_change` — preserve deck during review.
  - `aqt.dialogs.open` / `aqt.dialogs.markClosed` — preload Add Cards.

### Reviewer Hooks (7.4.4)
- `gui_hooks.reviewer_did_show_question` now also fires `on_reviewer_did_show_question`, which cancels any pending editor preload and schedules:
  - `_preload_add_window_fast` (50 ms) — fast Add Cards preloading.
  - `_preload_card_content_fast` (100 ms) — fresh card fetch from the collection.
