# Code Structure

This document describes the internal structure of the add-on: module responsibilities, the main controller class and its attributes/methods, module-level hooks, and key variables.

## Module Map

| Module | Responsibility |
| --- | --- |
| `__init__.py` | Entry point. Sets up file logging, checks for updates on startup, and auto-opens the Support tab after an update. |
| `reviewer.py` | The heart of the add-on. Defines the `EFDRC` controller class and installs runtime monkey-patches. |
| `editor.py` | `EmbeddedReviewerEditor(Editor)` — Anki editor subclass with tweaked shortcuts and bridge handling. |
| `config.py` | Builds the Qt config dialog; collects/applies editor preferences. |
| `config_settings.py` | "Settings" tab: checkboxes, combos, undo settings, and the note-type/template/field exclusion tree. |
| `config_support.py` | "Support" tab: Ko-fi widget, donation QR codes, supporter opt-out. |
| `config_log.py` | "Log" tab: live log viewer with refresh/copy/clear/auto-scroll. |
| `log_handler.py` | Logging setup: an in-memory `LogHandler` plus optional file handler writing `efdrn.log`. |
| `utils.py` | Pure helper functions: exclusion lookups, field/template checks, filter rewriting. |
| `web/efdrc.js` | Front-end trigger handling and "Edit (N)" button injection. |
| `web/efdrc.css` | Styling for editable-field outlines and empty-field placeholders. |

## Module: `__init__.py`

Functions:
- `check_for_update_and_show_support()` — reads `manifest.json` version and `meta.json` `last_version`; on change, updates `last_version` and (unless opted out) schedules opening the config dialog on the Support tab after 1 s.

Module side effects:
- Calls `setup_file_logging()` and logs `"EFDRN loaded"`.
- Registers `check_for_update_and_show_support` on `gui_hooks.main_window_did_init`.
- Imports `reviewer` (which instantiates `EFDRC`).

## Module: `reviewer.py`

### Class `EFDRC`

`EFDRC()` instantiates a singleton (`efdrc = EFDRC()`) at import time.

#### Attributes

| Attribute | Type / Default | Purpose |
| --- | --- | --- |
| `addon_name` | str | Add-on package name (`efdrn`). |
| `editor` | `Editor` \| `None` | The embedded editor instance. |
| `editor_widget` | `QWidget` \| `None` | Host widget inserted into the central layout. |
| `editor_container` | `QWidget` \| `None` | Inner container the editor is built into. |
| `done_btn` | `QPushButton` \| `None` | "Done (Ctrl+Enter)" button in the top bar. |
| `done_shortcut` | `QShortcut` | `Ctrl+Return` shortcut. |
| `done_shortcut_numpad` | `QShortcut` | `Ctrl+Enter` shortcut. |
| `cancel_shortcut` | `QShortcut` | `Escape` shortcut. |
| `undo_shortcut` | `QShortcut` | `QKeySequence.StandardKey.Undo`. |
| `redo_shortcut` | `QShortcut` | `QKeySequence.StandardKey.Redo`. |
| `redo_alt_shortcut` | `QShortcut` | `Ctrl+Y`. |
| `saved_main_undo_shortcuts` | list \| `None` | Saved main-window undo shortcuts while suspended. |
| `saved_main_redo_shortcuts` | list \| `None` | Saved main-window redo shortcuts while suspended. |
| `main_editor_pref_snapshot` | dict \| `None` | Snapshot of Anki's editor prefs before editing. |
| `note_snapshot` | dict \| `None` | Field values captured when the editor opened (used by custom undo). |
| `active_card_id` | int \| `None` | ID of the card currently being edited. |
| `is_saving` | bool | Whether a save is in progress. |
| `reload_after_save` | bool | Whether the reviewer should reload after save. |
| `pending_refocus_field_idx` | int \| `None` | Field to refocus after a refresh. |
| `pending_refocus_force` | bool | Force refocus even if focus is already in the editor. |
| `preload_delay_ms` | int | `150` — editor preload delay. |
| `preload_timer` | `QTimer` | Single-shot timer for deferred editor preload. |
| `refocus_timer` | `QTimer` | Single-shot timer for focus restoration. |
| `profile_is_closing` | bool | Guards against cleanup during profile close. |
| `add_window_last_deck_id` | int \| `None` | Last selected deck in the Add Cards dialog. |
| `config` | dict | The add-on configuration. |
| `_filter_cache` | dict | Cache of per-(model/template/field) edit-filter decisions. |

#### Methods (grouped)

**Setup / teardown**
- `load_config()` — loads config from Anki and applies defaults.
- `setup_ui()` — builds the editor widget + top bar and inserts it into the central layout.
- `_install_shortcuts()` / `_set_shortcuts_enabled()` — create/enable editor shortcuts.
- `_refresh_editor_controls()` / `_apply_shortcut_config()` — update button text from config.
- `on_profile_will_close()` / `on_profile_did_open()` — cleanup and re-preload on profile events.
- `_clear_editor_state()` — resets per-edit state.

**Editor preferences**
- `_should_separate_editor_preferences()`
- `_reviewer_editor_preferences()`
- `_activate_reviewer_editor_preferences()` / `_deactivate_reviewer_editor_preferences()`

**Opening / closing the editor**
- `open_editor_for_current_card()`
- `open_image_occlusion_editor()`
- `_open_native_reviewer_editor()`
- `show_editor(field_idx)` — hides reviewer, shows editor, loads the note, snapshots fields.
- `hide_editor(reload=True)` — hides editor, saves note, reloads reviewer.
- `_on_save_done()` — callback after `saveNow` completes.
- `reload_reviewer()` — reloads the current card (handles deleted-card case).
- `_editor_is_visible()`, `_set_review_screen_visible(visible)`, `_set_editor_note(note, idx, card)`

**Undo / redo**
- `_on_editor_undo()` — dispatches to custom undo or in-editor undo.
- `_on_editor_redo()`
- `_on_card_restore_undo()` — snapshot-based revert (per-field or full).
- `_run_editor_history_action(action)`
- `_suspend_main_window_undo_shortcuts()` / `_restore_main_window_undo_shortcuts()`
- `_field_name_for_index(note, idx)` (static)
- `_active_editor_field_idx()`

**Focus**
- `schedule_editor_refocus(field_idx=None, delay_ms=75, force=False)`
- `_restore_editor_focus()`

**Preload**
- `schedule_editor_preload()` / `cancel_editor_preload()` / `_run_deferred_preload()` / `preload_editor()`
- `_ensure_editor_ready(note)`, `_create_editor(note)`, `_editor_uses_parent_window()`

**Rendering / templates**
- `_wrap(txt, field, ctx)` — wraps a field in `<span data-efdrc-idx="N">`.
- `on_field_filter(txt, field, filt, ctx)` — field-filter hook (adds the `edit` behaviour).
- `editable_template_for_card(card)` — returns a template rewritten with `edit:` filters.
- `should_auto_wrap_card(card)`, `should_defer_reviewer_refresh(reviewer, changes)`

**Hooks / message handling**
- `on_webview_will_set_content(web_content, context)` — injects `efdrc.js`/`efdrc.css` and config.
- `on_js_message(handled, message, context)` — handles `edit`, `EFDRC!edit_native`, `EFDRC!edit#N`.
- `on_reviewer_rendered(_card)` — keeps editor open on redraw; syncs Add Cards deck.
- `on_state_shortcuts_will_change(state, shortcuts)` — binds `e`/`n`/`ㄷ`/`ㅜ`.
- `on_state_did_change(new_state, old_state)`
- `_on_review_edit_shortcut()`, `_on_review_native_edit_shortcut()`

**Add Cards integration**
- `_patch_dialogs_open()` — wraps `aqt.dialogs.open`/`markClosed`.
- `schedule_add_window_preload(delay_ms)` / `_preload_add_window()`
- `on_add_cards_did_init(add_cards)` — custom `_close` that hides instead of destroying.

**Config**
- `on_config_action()` — opens the config dialog and refreshes on save.

#### Module-level hooks (installed after class definition)

- `gui_hooks.webview_did_receive_js_message`
- `gui_hooks.reviewer_did_show_question` / `reviewer_did_show_answer`
- `gui_hooks.state_shortcuts_will_change` / `state_did_change`
- `gui_hooks.profile_will_close` / `profile_did_open`
- `gui_hooks.add_cards_did_init`
- `anki.hooks.field_filter`
- `gui_hooks.webview_will_set_content`
- `mw.addonManager.setConfigAction(...)`, Tools-menu action
- `mw.addonManager.setWebExports(__name__, r"web/.*")`

#### Runtime monkey-patches (at import time)

1. **`Reviewer.op_executed`** → wraps to call `EFDRC.should_defer_reviewer_refresh`; returns `False` (skip refresh) while the editor is open to keep focus.
2. **`TemplateRenderContext._partially_render`** → calls `editable_template_for_card`; if a rewritten template exists, forces `template["ord"] = card.ord` and renders with the backend to fix the Cloze 1 bug.
3. **`aqt.addcards.AddCards.on_notetype_change`** → forces `update_deck=False` during review so changing note type doesn't reset the deck.
4. **`aqt.dialogs.open` / `aqt.dialogs.markClosed`** (via `_patch_dialogs_open`) → preload Add Cards and select the active deck.

## Module: `editor.py`

Class `EmbeddedReviewerEditor(Editor)`:
- `setupShortcuts()` — disables `Ctrl+Z`, `Ctrl+Y`, `Ctrl+Shift+Z`, `Meta+Z`, `Meta+Shift+Z` (the add-on manages undo/redo).
- `onBridgeCmd(cmd)` — handles `key:<ord>:<nid>:<text>` messages to update the note field and fire the typing timer.

## Module: `config.py`

- `default_editor_preferences()` → dict of default reviewer editor preferences.
- `collection_available()` → whether the collection is loaded.
- `collect_editor_preferences()` → reads current editor preferences from profile/collection.
- `apply_editor_preferences(prefs, editor=None)` → writes preferences to profile/collection and refreshes the palette.
- `on_config_action(addon_manager, module_name, on_save, initial_tab=0)` → builds the dialog with Settings/Support/Log tabs and saves config on OK.

## Module: `config_settings.py`

Constants:
- `MODEL_ID_ROLE = UserRole`
- `ENTRY_KIND_ROLE = UserRole + 1`
- `ENTRY_ORD_ROLE = UserRole + 2`
- `UNDO_STYLE_MAP` — UI label → `undo_style` value.

Class `SettingsTab(QWidget)`:
- `_setup_ui()` — builds controls (see configuration.md) and the exclusion tree.
- `_populate_tree()` — fills the tree from `mw.col.models.all()`.
- `_set_all_items(state)` — Enable All / Disable All.
- `update_config(config)` — writes the UI state back into the config dict (including `exclusions` / `exclusions_v2`).

## Module: `config_support.py`

Class `SupportTab(QWidget)`:
- `get_addon_package()`
- `_setup_ui()` — instruction label, supporter opt-out checkbox, Ko-fi webview, and three QR-code blocks (UPI/BTC/ETH) with copy buttons.
- `load_supporter_state()` / `on_supporter_check_toggled(checked)` — persist `supporter_opt_out` in meta.

## Module: `config_log.py`

Class `LogTab(QWidget)`:
- Live `QTextEdit` log view.
- `_refresh_logs()`, `_on_clear()`, `_on_copy()`; auto-scroll toggle; refresh on `showEvent`.

## Module: `log_handler.py`

- `LogSignal(QObject)` — `new_record` signal.
- `LogHandler(logging.Handler)` — in-memory ring buffer (`max_records=1000`).
- `logger` — named logger `"efdrn"` at `DEBUG`.
- `get_log_content()`, `clear_logs()`, `setup_file_logging()`, `connect_log_signal(slot)`.
- `LOG_FILE_NAME = "efdrn.log"`.

## Module: `utils.py`

- `_FIELD_REPLACEMENT_RE = re.compile(r"{{([^{}]+)}}")`
- `note_is_image_occlusion(note)` → bool.
- `field_index_by_name(note, field_name)` → int | None.
- `template_name_for_card(card)` → str.
- `_stable_model_exclusion(model, config)`, `_legacy_model_exclusion(model, config)` → dict.
- `note_type_disabled(model, config)`, `template_disabled(model, template, config)`, `field_disabled(model, field, config)` → bool.
- `field_allowed_for_card(card, field_name, config)` → bool.
- `card_has_any_allowed_field(card, config)` → bool.
- `fallback_field_index_for_card(card, config)` → int (chooses Image Occlusion fields first).
- `add_edit_filter_to_template(template_html, field_names)` → str (rewrites `{{Field}}` to `{{edit:Field}}`, skipping `edit:`/`type:` filters).

## Module: `web/efdrc.js`

`window.EFDRC` object:
- `config` — `{ modifier, action, mode, isImageOcclusion }`.
- `isImageOcclusionTarget(element)` → bool (walks up from an element looking for media/IO tags).
- `cloneBottomBarButton(button)`, `injectNativeButton()` — add the "Edit (N)" button to the bottom bar.
- `setup(conf)` — merges config; in `bottom` mode injects the button; otherwise installs click/dblclick trigger and modifier-key active-state handling. Sends `EFDRC!edit#<idx>` / `EFDRC!edit_native` via `window.pycmd`.

## Module: `web/efdrc.css`

- `span[data-efdrc-idx]` — no text-decoration override.
- `.efdrc-active [data-efdrc-idx], .efdrc-active #io-*` — dashed outline + pointer cursor.
- `.efdrc-active ...:hover` — soft blue highlight.
- `.efdrc-active [data-efdrc-idx].efdrc-empty` — placeholder sizing + `"[ empty field ]"` label.

## Key Variables / Constants Summary

| Variable | Module | Meaning |
| --- | --- | --- |
| `efdrc` | `reviewer.py` | Singleton `EFDRC` instance. |
| `logger` | `log_handler.py` | `logging.getLogger("efdrn")`. |
| `ADDON_NAME` | `make_ankiaddon.py` | `Edit_Field_During_Review_Native`. |
| `ADDON_DIR` | `make_ankiaddon.py` | `addon`. |
| `preload_delay_ms` | `reviewer.py` | `150`. |
| `max_records` | `log_handler.py` | `1000`. |
| `LOG_FILE_NAME` | `log_handler.py` | `efdrn.log`. |
