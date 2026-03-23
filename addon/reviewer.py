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


class EFDRC:
    def __init__(self) -> None:
        self.editor: Optional[Editor] = None
        self.editor_widget: Optional[QWidget] = None
        self.editor_container: Optional[QWidget] = None
        self.done_btn: Optional[QPushButton] = None
        self.done_shortcut: Optional[QShortcut] = None
        self.done_shortcut_numpad: Optional[QShortcut] = None
        self.cancel_shortcut: Optional[QShortcut] = None
        self.active_card_id: Optional[int] = None
        self.is_saving = False
        self.reload_after_save = False
        self.preload_delay_ms = 150
        self.preload_timer = QTimer(mw)
        self.preload_timer.setSingleShot(True)
        qconnect(self.preload_timer.timeout, self._run_deferred_preload)

        self.load_config()
        self._filter_cache: Dict[str, bool] = {}

        gui_hooks.webview_did_receive_js_message.append(self.on_js_message)
        gui_hooks.reviewer_did_show_question.append(self.on_reviewer_rendered)
        gui_hooks.reviewer_did_show_answer.append(self.on_reviewer_rendered)
        gui_hooks.state_did_change.append(self.on_state_did_change)
        gui_hooks.profile_will_close.append(self.on_profile_will_close)
        anki.hooks.field_filter.append(self.on_field_filter)
        gui_hooks.webview_will_set_content.append(self.on_webview_will_set_content)

        mw.addonManager.setConfigAction(__name__, self.on_config_action)

        if getattr(mw, "state", None) == "review":
            self.schedule_editor_preload()

    def load_config(self) -> None:
        self.config = mw.addonManager.getConfig(__name__) or {
            "auto_enable": True,
            "show_outline": True,
            "exclusions": {},
            "trigger_modifier": "Ctrl",
            "trigger_action": "Click",
        }

    def on_config_action(self) -> None:
        self.load_config()
        dialog = QDialog(mw)
        dialog.setWindowTitle("EFDRN Configuration")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(600)
        layout = QVBoxLayout(dialog)

        global_grp = QGroupBox("General Settings")
        grid = QGridLayout(global_grp)
        auto_cb = QCheckBox("Enable by default for all fields")
        auto_cb.setChecked(self.config.get("auto_enable", True))
        grid.addWidget(auto_cb, 0, 0, 1, 2)
        outline_cb = QCheckBox("Show visual outline on Hover")
        outline_cb.setChecked(self.config.get("show_outline", True))
        grid.addWidget(outline_cb, 1, 0, 1, 2)
        grid.addWidget(QLabel("Trigger Modifier:"), 2, 0)
        mod_combo = QComboBox()
        mod_combo.addItems(["Ctrl", "Shift", "Alt", "None"])
        mod_combo.setCurrentText(self.config.get("trigger_modifier", "Ctrl"))
        grid.addWidget(mod_combo, 2, 1)
        grid.addWidget(QLabel("Trigger Action:"), 3, 0)
        act_combo = QComboBox()
        act_combo.addItems(["Click", "DoubleClick"])
        act_combo.setCurrentText(self.config.get("trigger_action", "Click"))
        grid.addWidget(act_combo, 3, 1)
        layout.addWidget(global_grp)

        tree = QTreeWidget()
        tree.setHeaderLabels(["Note Type / Template / Field"])
        exclusions = self.config.get("exclusions", {})
        for model in mw.col.models.all():
            nt_item = QTreeWidgetItem(tree, [model["name"]])
            nt_item.setCheckState(
                0,
                Qt.CheckState.Unchecked
                if exclusions.get(model["name"], {}).get("disabled")
                else Qt.CheckState.Checked,
            )
            t_root = QTreeWidgetItem(nt_item, ["Templates"])
            for template in model["tmpls"]:
                t_item = QTreeWidgetItem(t_root, [template["name"]])
                t_item.setCheckState(
                    0,
                    Qt.CheckState.Unchecked
                    if template["name"]
                    in exclusions.get(model["name"], {}).get("templates", [])
                    else Qt.CheckState.Checked,
                )
            f_root = QTreeWidgetItem(nt_item, ["Fields"])
            for field in model["flds"]:
                f_item = QTreeWidgetItem(f_root, [field["name"]])
                f_item.setCheckState(
                    0,
                    Qt.CheckState.Unchecked
                    if field["name"]
                    in exclusions.get(model["name"], {}).get("fields", [])
                    else Qt.CheckState.Checked,
                )
        layout.addWidget(tree)

        bulk_row = QHBoxLayout()
        enable_all_btn = QPushButton("Enable All")
        disable_all_btn = QPushButton("Disable All")
        bulk_row.addWidget(enable_all_btn)
        bulk_row.addWidget(disable_all_btn)
        bulk_row.addStretch()
        layout.addLayout(bulk_row)

        def set_all_items(state: Qt.CheckState) -> None:
            def apply_to_item(item: QTreeWidgetItem) -> None:
                item.setCheckState(0, state)
                for idx in range(item.childCount()):
                    apply_to_item(item.child(idx))

            for idx in range(tree.topLevelItemCount()):
                apply_to_item(tree.topLevelItem(idx))

        enable_all_btn.clicked.connect(
            lambda: set_all_items(Qt.CheckState.Checked)
        )
        disable_all_btn.clicked.connect(
            lambda: set_all_items(Qt.CheckState.Unchecked)
        )

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)

        if dialog.exec():
            new_exclusions = {}
            for idx in range(tree.topLevelItemCount()):
                note_type_item = tree.topLevelItem(idx)
                disabled = note_type_item.checkState(0) == Qt.CheckState.Unchecked
                disabled_templates = [
                    note_type_item.child(0).child(child_idx).text(0)
                    for child_idx in range(note_type_item.child(0).childCount())
                    if note_type_item.child(0).child(child_idx).checkState(0)
                    == Qt.CheckState.Unchecked
                ]
                disabled_fields = [
                    note_type_item.child(1).child(child_idx).text(0)
                    for child_idx in range(note_type_item.child(1).childCount())
                    if note_type_item.child(1).child(child_idx).checkState(0)
                    == Qt.CheckState.Unchecked
                ]
                if disabled or disabled_templates or disabled_fields:
                    new_exclusions[note_type_item.text(0)] = {
                        "disabled": disabled,
                        "templates": disabled_templates,
                        "fields": disabled_fields,
                    }

            self.config.update(
                {
                    "auto_enable": auto_cb.isChecked(),
                    "show_outline": outline_cb.isChecked(),
                    "trigger_modifier": mod_combo.currentText(),
                    "trigger_action": act_combo.currentText(),
                    "exclusions": new_exclusions,
                }
            )
            mw.addonManager.writeConfig(__name__, self.config)
            self._filter_cache.clear()

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
        self.editor_widget.hide()

    def _install_shortcuts(self) -> None:
        if self.done_shortcut:
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

        self._set_shortcuts_enabled(False)

    def _set_shortcuts_enabled(self, enabled: bool) -> None:
        for shortcut in (
            self.done_shortcut,
            self.done_shortcut_numpad,
            self.cancel_shortcut,
        ):
            if shortcut:
                shortcut.setEnabled(enabled)

    def _on_done_shortcut(self) -> None:
        if self._editor_is_visible():
            self.hide_editor()

    def _on_cancel_shortcut(self) -> None:
        if self._editor_is_visible():
            self.hide_editor()

    def _editor_is_visible(self) -> bool:
        return bool(self.editor_widget and not self.editor_widget.isHidden())

    def _set_review_screen_visible(self, visible: bool) -> None:
        web = getattr(mw, "web", None)
        if web:
            web.setVisible(visible)

    def _clear_editor_state(self) -> None:
        self.active_card_id = None
        self.reload_after_save = False
        if self.done_btn:
            self.done_btn.setEnabled(True)

    def _wrap(self, txt: str, field: str, ctx: TemplateRenderContext) -> str:
        try:
            flds = ctx.note().model()["flds"]
            idx = next((i for i, fld in enumerate(flds) if fld["name"] == field), 0)
            return f'<span data-efdrc-idx="{idx}">{txt}</span>'
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
                template_name = card.template()["name"]
        except Exception:
            template_name = ""

        cache_key = (
            f"{ctx.note().model()['id']}::{template_name}::{field}::{filt or '_'}"
        )
        if cache_key in self._filter_cache:
            return self._wrap(txt, field, ctx) if self._filter_cache[cache_key] else txt

        try:
            model = ctx.note().model()
            exclusions = self.config.get("exclusions", {}).get(model["name"], {})
            if exclusions.get("disabled") or field in exclusions.get("fields", []):
                self._filter_cache[cache_key] = False
                return txt
            if template_name and template_name in exclusions.get("templates", []):
                self._filter_cache[cache_key] = False
                return txt
        except Exception:
            pass

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
        if message.startswith("EFDRC!edit#") and isinstance(context, Reviewer):
            try:
                self.show_editor(int(message.split("#")[1]))
            except Exception as exc:
                tooltip(f"Error: {exc}")
            return (True, None)
        return handled

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
            return Editor(mw, self.editor_container, mw, **kwargs)

        return Editor(mw, self.editor_container, note)

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

        note = mw.reviewer.card.note() if mw.reviewer.card else None
        self._ensure_editor_ready(note)
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
        self._ensure_editor_ready(note)
        if not self.editor or not self.editor_widget:
            tooltip("Editor could not be initialized.")
            return

        self.active_card_id = card.id
        self.reload_after_save = False
        self._set_shortcuts_enabled(True)
        self._set_review_screen_visible(False)
        self.editor_widget.show()
        self._set_editor_note(note, field_idx, card)
        if self.done_btn:
            self.done_btn.setEnabled(True)

    def hide_editor(self, reload: bool = True) -> None:
        self.reload_after_save = reload and getattr(mw, "state", None) == "review"

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

        if not self.reload_after_save:
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
        else:
            self._set_review_screen_visible(True)
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
        self._set_review_screen_visible(True)


efdrc = EFDRC()
mw.addonManager.setWebExports(__name__, r"web/.*")
