# -*- coding: utf-8 -*-

import inspect
import json
from typing import Any, Dict, Optional, Tuple

import anki
import aqt
from anki.cards import Card
from anki.notes import Note
from anki.template import TemplateRenderContext
from aqt import gui_hooks, mw
from aqt.editor import Editor
from aqt.qt import *
from aqt.reviewer import Reviewer
from aqt.utils import tooltip

from . import config as cfg
from . import utils
from .editor import EmbeddedReviewerEditor


class EFDRC:
    def __init__(self) -> None:
        self.addon_name = mw.addonManager.addonFromModule(__name__)
        self.editor: Optional[Editor] = None
        self.editor_widget: Optional[QWidget] = None
        self.editor_container: Optional[QWidget] = None

        self.done_btn: Optional[QPushButton] = None
        self.done_shortcut: Optional[QShortcut] = None
        self.done_shortcut_numpad: Optional[QShortcut] = None
        self.cancel_shortcut: Optional[QShortcut] = None
        self.custom_undo_shortcut: Optional[QShortcut] = None
        self.saved_main_undo_shortcuts: Optional[list[QKeySequence]] = None
        self.saved_main_redo_shortcuts: Optional[list[QKeySequence]] = None
        self.main_editor_pref_snapshot: Optional[Dict[str, Any]] = None
        self.note_snapshot: Optional[Dict[str, str]] = None
        self.active_card_id: Optional[int] = None
        self.is_saving = False
        self.reload_after_save = False
        self.pending_refocus_field_idx: Optional[int] = None
        self.preload_delay_ms = 150
        self.preload_timer = QTimer(mw)
        self.preload_timer.setSingleShot(True)
        qconnect(self.preload_timer.timeout, self._run_deferred_preload)
        self.refocus_timer = QTimer(mw)
        self.refocus_timer.setSingleShot(True)
        qconnect(self.refocus_timer.timeout, self._restore_editor_focus)

        self.load_config()
        self._filter_cache: Dict[str, bool] = {}

        gui_hooks.webview_did_receive_js_message.append(self.on_js_message)
        gui_hooks.reviewer_did_show_question.append(self.on_reviewer_rendered)
        gui_hooks.reviewer_did_show_answer.append(self.on_reviewer_rendered)
        gui_hooks.state_shortcuts_will_change.append(self.on_state_shortcuts_will_change)
        gui_hooks.state_did_change.append(self.on_state_did_change)
        gui_hooks.profile_will_close.append(self.on_profile_will_close)
        anki.hooks.field_filter.append(self.on_field_filter)
        gui_hooks.webview_will_set_content.append(self.on_webview_will_set_content)

        mw.addonManager.setConfigAction(self.addon_name, self.on_config_action)

        # Add to Tools menu
        action = QAction("EFDRN Configuration", mw)
        qconnect(action.triggered, self.on_config_action)
        mw.form.menuTools.addAction(action)

        if getattr(mw, "state", None) == "review":
            self.schedule_editor_preload()

    def load_config(self) -> None:
        self.config = mw.addonManager.getConfig(self.addon_name) or {
            "auto_enable": True,
            "show_outline": True,
            "exclusions": {},
            "trigger_modifier": "Ctrl",
            "trigger_action": "Click",
            "custom_undo_shortcut": "Ctrl+Alt+Z",
            "separate_editor_preferences": True,
            "reviewer_editor_preferences": {},
        }
        self.config.setdefault("custom_undo_shortcut", "Ctrl+Alt+Z")
        self.config.setdefault("separate_editor_preferences", True)
        reviewer_prefs = self.config.setdefault("reviewer_editor_preferences", {})
        for key, value in cfg.default_editor_preferences().items():
            reviewer_prefs.setdefault(key, value)

    def _should_separate_editor_preferences(self) -> bool:
        return bool(self.config.get("separate_editor_preferences", False))

    def _reviewer_editor_preferences(self) -> Dict[str, Any]:
        prefs = dict(cfg.default_editor_preferences())
        prefs.update(self.config.get("reviewer_editor_preferences", {}))
        return prefs

    def _activate_reviewer_editor_preferences(self) -> None:
        if not self._should_separate_editor_preferences():
            return
        if self.main_editor_pref_snapshot is None:
            self.main_editor_pref_snapshot = cfg.collect_editor_preferences()
        cfg.apply_editor_preferences(self._reviewer_editor_preferences(), self.editor)

    def _deactivate_reviewer_editor_preferences(self) -> None:
        if self.main_editor_pref_snapshot is None:
            return

        if self._should_separate_editor_preferences():
            self.config["reviewer_editor_preferences"] = cfg.collect_editor_preferences()
            mw.addonManager.writeConfig(self.addon_name, self.config)

        snapshot = self.main_editor_pref_snapshot
        self.main_editor_pref_snapshot = None
        cfg.apply_editor_preferences(snapshot, self.editor)

    def _configured_custom_undo_shortcut(self) -> str:
        return cfg.shortcut_to_text(self.config.get("custom_undo_shortcut"))

    def _refresh_editor_controls(self) -> None:
        if self.done_btn:
            self.done_btn.setText("Done (Ctrl+Enter)")

    def _apply_shortcut_config(self) -> None:
        if self.custom_undo_shortcut:
            custom_shortcut = self._configured_custom_undo_shortcut()
            self.custom_undo_shortcut.setKey(QKeySequence(custom_shortcut))
        self._refresh_editor_controls()

    def on_config_action(self) -> None:
        def on_save():
            self.load_config()
            self._filter_cache.clear()
            self._apply_shortcut_config()

        cfg.on_config_action(mw.addonManager, self.addon_name, on_save)

    def setup_ui(self) -> None:
        if self.editor_widget:
            return

        central = mw.centralWidget()
        if not central:
            return

        self.editor_widget = QWidget(central)
        self.editor_widget.setMinimumHeight(0)
        self.editor_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout = QVBoxLayout(self.editor_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_bar = QWidget()
        top_bar.setStyleSheet(
            "background: palette(window); border-bottom: 1px solid #888;"
        )
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(10, 5, 10, 5)
        top_layout.addWidget(QLabel("<b>Native Field Editor</b>"))
        top_layout.addStretch()

        self.done_btn = QPushButton("Done (Ctrl+Enter)")
        self.done_btn.clicked.connect(self.hide_editor)
        top_layout.addWidget(self.done_btn)
        layout.addWidget(top_bar)

        # Anki's Editor expects to own the layout of the host widget.
        self.editor_container = QWidget()
        self.editor_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.editor_container, 1)

        cw_layout = central.layout()
        if cw_layout:
            insert_at = cw_layout.indexOf(mw.reviewer.web)
            if insert_at < 0:
                insert_at = cw_layout.count()
            cw_layout.insertWidget(insert_at, self.editor_widget, 1)

        self._install_shortcuts()
        self._refresh_editor_controls()
        self.editor_widget.hide()

    def _install_shortcuts(self) -> None:
        if self.done_shortcut:
            self._apply_shortcut_config()
            return

        self.done_shortcut = QShortcut(QKeySequence("Ctrl+Return"), mw)
        self.done_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        qconnect(self.done_shortcut.activated, self._on_done_shortcut)

        self.done_shortcut_numpad = QShortcut(QKeySequence("Ctrl+Enter"), mw)
        self.done_shortcut_numpad.setContext(Qt.ShortcutContext.WindowShortcut)
        qconnect(self.done_shortcut_numpad.activated, self._on_done_shortcut)

        self.cancel_shortcut = QShortcut(QKeySequence("Escape"), mw)
        self.cancel_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        qconnect(self.cancel_shortcut.activated, self._on_cancel_shortcut)

        # Ctrl+Alt+Z: full card restore (configured shortcut).
        # Ctrl+Z / Ctrl+Y are NOT intercepted — they flow to the webview so
        # the browser's native undo/redo handles text AND formatting changes.
        self.custom_undo_shortcut = QShortcut(QKeySequence(), mw)
        self.custom_undo_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        qconnect(self.custom_undo_shortcut.activated, self._on_card_restore_undo)

        self._apply_shortcut_config()
        self._set_shortcuts_enabled(False)

    def _set_shortcuts_enabled(self, enabled: bool) -> None:
        for shortcut in (
            self.done_shortcut,
            self.done_shortcut_numpad,
            self.cancel_shortcut,
            self.custom_undo_shortcut,
        ):
            if shortcut:
                shortcut.setEnabled(enabled)

    def _active_editor_field_idx(self) -> Optional[int]:
        if not self.editor:
            return None
        current_idx = getattr(self.editor, "currentField", None)
        if current_idx is not None:
            return current_idx
        return getattr(self.editor, "last_field_index", None)

    def schedule_editor_refocus(
        self, field_idx: Optional[int] = None, delay_ms: int = 75
    ) -> None:
        if field_idx is None:
            field_idx = self._active_editor_field_idx()
        self.pending_refocus_field_idx = field_idx
        if self.refocus_timer.isActive():
            self.refocus_timer.stop()
        self.refocus_timer.start(delay_ms)

    def _restore_editor_focus(self) -> None:
        if (
            not self._editor_is_visible()
            or not self.editor
            or not getattr(self.editor, "web", None)
            or getattr(mw, "state", None) != "review"
        ):
            return

        field_idx = self.pending_refocus_field_idx
        if field_idx is None:
            field_idx = self._active_editor_field_idx()
        self.pending_refocus_field_idx = None

        self.editor.web.setFocus()
        if field_idx is None:
            return

        self.editor.web.eval(
            f'require("anki/ui").loaded.then(() => {{ focusField({field_idx}); }});'
        )

    def _main_window_undo_actions(self) -> tuple[Optional[QAction], Optional[QAction]]:
        form = getattr(mw, "form", None)
        if not form:
            return (None, None)
        return (getattr(form, "actionUndo", None), getattr(form, "actionRedo", None))

    def _suspend_main_window_undo_shortcuts(self) -> None:
        undo_action, redo_action = self._main_window_undo_actions()
        if undo_action and self.saved_main_undo_shortcuts is None:
            self.saved_main_undo_shortcuts = list(undo_action.shortcuts())
            undo_action.setShortcuts([])
        if redo_action and self.saved_main_redo_shortcuts is None:
            self.saved_main_redo_shortcuts = list(redo_action.shortcuts())
            redo_action.setShortcuts([])

    def _restore_main_window_undo_shortcuts(self) -> None:
        undo_action, redo_action = self._main_window_undo_actions()
        if undo_action and self.saved_main_undo_shortcuts is not None:
            undo_action.setShortcuts(self.saved_main_undo_shortcuts)
            self.saved_main_undo_shortcuts = None
        if redo_action and self.saved_main_redo_shortcuts is not None:
            redo_action.setShortcuts(self.saved_main_redo_shortcuts)
            self.saved_main_redo_shortcuts = None

    def _on_done_shortcut(self) -> None:
        if self._editor_is_visible():
            self.hide_editor()

    def _on_cancel_shortcut(self) -> None:
        if self._editor_is_visible():
            self.hide_editor()

    def _on_card_restore_undo(self) -> None:
        """Ctrl+Alt+Z / Undo Edit button: restore the note to the snapshot
        taken when the editor was opened.  We must flush the editor first so
        that the Python note object reflects the latest webview content."""
        if not self._editor_is_visible() or not self.editor:
            return
        if self.note_snapshot is None:
            return

        def _do_restore() -> None:
            note = getattr(self.editor, "note", None)
            if note is None or self.note_snapshot is None:
                return
            changed = False
            for field_name, original_value in self.note_snapshot.items():
                if field_name in note and note[field_name] != original_value:
                    note[field_name] = original_value
                    changed = True
            if not changed:
                tooltip("Nothing to restore \u2013 note is unchanged from when editing started.")
                return
            # Reload the editor to reflect the restored values
            field_idx = self._active_editor_field_idx() or 0
            card = mw.reviewer.card if mw.reviewer else None
            if card:
                self._set_editor_note(note, field_idx, card)
                self.schedule_editor_refocus(field_idx, delay_ms=120)
            tooltip("Note restored to state before editing.")

        # Flush current webview content → Python note object, then restore.
        save_now = getattr(
            self.editor, "call_after_note_saved",
            getattr(self.editor, "saveNow", None),
        )
        if callable(save_now):
            save_now(_do_restore)
        else:
            _do_restore()

    def _editor_is_visible(self) -> bool:
        return bool(self.editor_widget and not self.editor_widget.isHidden())

    def _set_review_screen_visible(self, visible: bool) -> None:
        web = getattr(mw, "web", None)
        if web:
            web.setVisible(visible)

    def _clear_editor_state(self) -> None:
        self.active_card_id = None
        self.note_snapshot = None
        self.reload_after_save = False
        self.pending_refocus_field_idx = None
        if self.refocus_timer.isActive():
            self.refocus_timer.stop()
        if self.done_btn:
            self.done_btn.setEnabled(True)

    def open_editor_for_current_card(self) -> bool:
        reviewer = getattr(mw, "reviewer", None)
        card = reviewer.card if reviewer and reviewer.card else None
        if not card:
            return False
        self.show_editor(utils.fallback_field_index_for_card(card, self.config))
        return True

    def open_image_occlusion_editor(self) -> bool:
        reviewer = getattr(mw, "reviewer", None)
        card = reviewer.card if reviewer and reviewer.card else None
        if not card:
            return False
        if not utils.note_is_image_occlusion(card.note()):
            return False
        if self._editor_is_visible():
            self.schedule_editor_refocus(delay_ms=30)
            return True
        if not utils.card_has_any_allowed_field(card, self.config):
            return False
        self.show_editor(utils.fallback_field_index_for_card(card, self.config))
        return True

    def _wrap(self, txt: str, field: str, ctx: TemplateRenderContext) -> str:
        try:
            flds = ctx.note().model()["flds"]
            idx = next((i for i, fld in enumerate(flds) if fld["name"] == field), 0)
            # Add a class if the field is empty to help with selection
            cls = "efdrc-empty" if not txt.strip() else ""
            return f'<span data-efdrc-idx="{idx}" class="{cls}">{txt}</span>'
        except Exception:
            return txt

    def on_field_filter(
        self, txt: str, field: str, filt: str, ctx: TemplateRenderContext
    ) -> str:
        if filt == "edit":
            return self._wrap(txt, field, ctx)
        if not self.config.get("auto_enable", True) or filt:
            return txt

        template_name = ""
        try:
            card = ctx.card()
            if card:
                template_name = utils.template_name_for_card(card)
        except Exception:
            template_name = ""

        cache_key = (
            f"{ctx.note().model()['id']}::{template_name}::{field}::{filt or '_'}"
        )
        if cache_key in self._filter_cache:
            return self._wrap(txt, field, ctx) if self._filter_cache[cache_key] else txt

        if not utils.field_allowed_for_card(ctx.card(), field, self.config):
            self._filter_cache[cache_key] = False
            return txt

        self._filter_cache[cache_key] = True
        return self._wrap(txt, field, ctx)

    def on_webview_will_set_content(
        self, web_content: aqt.webview.WebContent, context: Optional[Any]
    ) -> None:
        if not isinstance(context, Reviewer):
            return

        self._filter_cache.clear()
        addon_package = mw.addonManager.addonFromModule(__name__)
        web_content.js.append(f"/_addons/{addon_package}/web/efdrc.js")
        if self.config.get("show_outline", True):
            web_content.css.append(f"/_addons/{addon_package}/web/efdrc.css")
        js_conf = {
            "modifier": self.config.get("trigger_modifier", "Ctrl"),
            "action": self.config.get("trigger_action", "Click"),
        }
        web_content.body += f"<script>EFDRC.setup({json.dumps(js_conf)});</script>"

    def on_js_message(
        self, handled: Tuple[bool, Any], message: str, context: Any
    ) -> Tuple[bool, Any]:
        if (
            message == "edit"
            and isinstance(context, Reviewer)
            and self.open_image_occlusion_editor()
        ):
            return (True, None)
        if message.startswith("EFDRC!edit#") and isinstance(context, Reviewer):
            try:
                self.show_editor(int(message.split("#")[1]))
            except Exception as exc:
                tooltip(f"Error: {exc}")
            return (True, None)
        return handled

    def on_state_shortcuts_will_change(
        self, state: str, shortcuts: list[tuple[str, Any]]
    ) -> None:
        if state != "review":
            return
        replaced_e = replaced_kr = False
        for i, (key, fn) in enumerate(shortcuts):
            if key == "e":
                shortcuts[i] = (key, self._on_review_edit_shortcut)
                replaced_e = True
            elif key == "ㄷ":
                shortcuts[i] = (key, self._on_review_edit_shortcut)
                replaced_kr = True
        
        if not replaced_e:
            shortcuts.append(("e", self._on_review_edit_shortcut))
        if not replaced_kr:
            shortcuts.append(("ㄷ", self._on_review_edit_shortcut))

    def _on_review_edit_shortcut(self) -> None:
        if self._editor_is_visible():
            self.schedule_editor_refocus()
            return
        if self.open_image_occlusion_editor():
            return
        mw.onEditCurrent()

    def on_state_did_change(self, new_state: str, old_state: str) -> None:
        if new_state == "review":
            self.schedule_editor_preload()
            return

        self.cancel_editor_preload()
        if old_state == "review" or self._editor_is_visible() or self.is_saving:
            self.hide_editor(reload=False)

    def on_profile_will_close(self) -> None:
        self.cancel_editor_preload()
        self.hide_editor(reload=False)
        self._deactivate_reviewer_editor_preferences()
        self._set_review_screen_visible(True)
        if self.editor:
            self.editor.cleanup()
            self.editor = None
        if self.editor_widget:
            self.editor_widget.deleteLater()
            self.editor_widget = None
            self.editor_container = None

    def on_reviewer_rendered(self, _card: Card) -> None:
        if not self._editor_is_visible():
            return

        reviewer = getattr(mw, "reviewer", None)
        current_card_id = reviewer.card.id if reviewer and reviewer.card else None
        if not current_card_id or current_card_id != self.active_card_id:
            self.hide_editor(reload=False)
            return

        # Reviewer redraws can happen while editing the same note; keep the
        # card hidden so the editor stays visually in control.
        self._set_review_screen_visible(False)
        self.schedule_editor_refocus()

    def should_defer_reviewer_refresh(self, reviewer: Reviewer, changes: Any) -> bool:
        current_card = getattr(reviewer, "card", None)
        current_card_id = current_card.id if current_card else None
        return bool(
            self._editor_is_visible()
            and not self.is_saving
            and current_card_id
            and current_card_id == self.active_card_id
            and getattr(changes, "note_text", False)
        )

    def _editor_uses_parent_window(self) -> bool:
        try:
            return "parentWindow" in inspect.signature(Editor.__init__).parameters
        except (TypeError, ValueError):
            return False

    def _create_editor(self, note: Note) -> Editor:
        assert self.editor_container is not None

        if self._editor_uses_parent_window():
            editor_mode = getattr(aqt.editor, "EditorMode", None)
            kwargs = {}
            if editor_mode is not None and hasattr(editor_mode, "EDIT_CURRENT"):
                kwargs["editor_mode"] = editor_mode.EDIT_CURRENT
            return EmbeddedReviewerEditor(mw, self.editor_container, mw, **kwargs)

        return EmbeddedReviewerEditor(mw, self.editor_container, note)

    def _ensure_editor_ready(self, note: Optional[Note] = None) -> None:
        self.setup_ui()
        if self.editor or not self.editor_container:
            return

        fallback_note = note or (mw.reviewer.card.note() if mw.reviewer.card else None)
        if fallback_note is None:
            return

        self.editor = self._create_editor(fallback_note)

    def cancel_editor_preload(self) -> None:
        if self.preload_timer.isActive():
            self.preload_timer.stop()

    def schedule_editor_preload(self) -> None:
        if getattr(mw, "state", None) != "review":
            return
        if self.editor or self._editor_is_visible() or self.is_saving:
            return
        if self.preload_timer.isActive():
            return
        self.preload_timer.start(self.preload_delay_ms)

    def _run_deferred_preload(self) -> None:
        if getattr(mw, "state", None) != "review":
            return
        if self.editor or self._editor_is_visible() or self.is_saving:
            return
        reviewer = getattr(mw, "reviewer", None)
        if not reviewer or not reviewer.card:
            return
        self.preload_editor()

    def preload_editor(self) -> None:
        if getattr(mw, "state", None) != "review":
            return

        self._activate_reviewer_editor_preferences()
        note = mw.reviewer.card.note() if mw.reviewer.card else None
        try:
            self._ensure_editor_ready(note)
        finally:
            if not self._editor_is_visible():
                self._deactivate_reviewer_editor_preferences()
        if self.editor_widget:
            self.editor_widget.hide()

    def _set_editor_note(self, note: Note, field_idx: int, card: Card) -> None:
        assert self.editor is not None

        self.editor.card = card

        set_note = getattr(self.editor, "set_note", getattr(self.editor, "setNote", None))
        if callable(set_note):
            try:
                set_note(note, focusTo=field_idx)
                return
            except TypeError:
                set_note(note)

        self.editor.loadNote(field_idx)

    def show_editor(self, field_idx: int) -> None:
        if self.is_saving:
            return
        if getattr(mw, "state", None) != "review":
            tooltip("Open the reviewer before editing fields.")
            return
        self.cancel_editor_preload()

        card = mw.reviewer.card
        if not card:
            tooltip("No active card to edit.")
            return

        note = card.note()
        self._activate_reviewer_editor_preferences()
        self._ensure_editor_ready(note)
        if not self.editor or not self.editor_widget:
            tooltip("Editor could not be initialized.")
            self._deactivate_reviewer_editor_preferences()
            return

        self.active_card_id = card.id
        self.reload_after_save = False
        # Capture a snapshot of all field values before editing begins so that
        # Ctrl+Alt+Z can restore the note to this exact state.
        self.note_snapshot = {name: value for name, value in note.items()}
        self._suspend_main_window_undo_shortcuts()
        self._set_shortcuts_enabled(True)
        self._set_review_screen_visible(False)
        self.editor_widget.show()
        self._set_editor_note(note, field_idx, card)
        self.schedule_editor_refocus(field_idx, delay_ms=120)
        if self.done_btn:
            self.done_btn.setEnabled(True)

    def hide_editor(self, reload: bool = True) -> None:
        self.reload_after_save = reload and getattr(mw, "state", None) == "review"
        self._restore_main_window_undo_shortcuts()
        self._deactivate_reviewer_editor_preferences()

        if not self._editor_is_visible():
            if not self.reload_after_save:
                self._set_review_screen_visible(True)
                if not self.is_saving:
                    self._clear_editor_state()
            return

        self._set_shortcuts_enabled(False)
        if self.done_btn:
            self.done_btn.setEnabled(False)
        if self.editor_widget:
            self.editor_widget.hide()

        # Show reviewer immediately to reduce flicker during the save process
        self._set_review_screen_visible(True)

        if not self.editor:
            self._clear_editor_state()
            return

        self.is_saving = True
        save_now = getattr(
            self.editor, "call_after_note_saved", getattr(self.editor, "saveNow", None)
        )
        if callable(save_now):
            save_now(self._on_save_done)
        else:
            self._on_save_done()

    def _on_save_done(self) -> None:
        self.is_saving = False
        if self.reload_after_save:
            self.reload_reviewer()
        self._clear_editor_state()

    def reload_reviewer(self) -> None:
        reviewer = mw.reviewer
        if reviewer and reviewer.card:
            timer_started = getattr(
                reviewer.card, "timer_started", getattr(reviewer.card, "timerStarted", None)
            )
            reviewer.card = mw.col.getCard(reviewer.card.id)
            if timer_started is not None:
                if hasattr(reviewer.card, "timer_started"):
                    reviewer.card.timer_started = timer_started
                else:
                    reviewer.card.timerStarted = timer_started
            if reviewer.state == "question":
                reviewer._showQuestion()
            elif reviewer.state == "answer":
                reviewer._showAnswer()


efdrc = EFDRC()

if hasattr(Reviewer, "op_executed"):
    if not getattr(Reviewer.op_executed, "_efdrn_wrapped", False):
        _efdrn_original_op_executed = Reviewer.op_executed

        def _efdrn_reviewer_op_executed(
            reviewer: Reviewer, changes: Any, handler: object | None, focused: bool
        ) -> bool:
            controller = globals().get("efdrc")
            if controller and controller.should_defer_reviewer_refresh(reviewer, changes):
                result = _efdrn_original_op_executed(reviewer, changes, handler, False)
                controller.schedule_editor_refocus(delay_ms=120)
                return result
            return _efdrn_original_op_executed(reviewer, changes, handler, focused)

        _efdrn_reviewer_op_executed._efdrn_wrapped = True  # type: ignore[attr-defined]
        Reviewer.op_executed = _efdrn_reviewer_op_executed

mw.addonManager.setWebExports(__name__, r"web/.*")
