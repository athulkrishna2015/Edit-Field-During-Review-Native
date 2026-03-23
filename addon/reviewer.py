# -*- coding: utf-8 -*-

import base64
import time
import json
from typing import Any, Optional, Tuple, Union, Dict

import anki
from anki.template import TemplateRenderContext
from anki.notes import Note
from anki.cards import Card
import aqt
from aqt import mw, gui_hooks
from aqt.editor import Editor
from aqt.qt import *
from aqt.utils import tooltip
from aqt.reviewer import Reviewer
from aqt.browser.previewer import MultiCardPreviewer

class EFDRC:
    def __init__(self):
        self.editor: Optional[Editor] = None
        self.editor_widget: Optional[QWidget] = None
        self.editor_container: Optional[QWidget] = None
        self.current_note_id: Optional[int] = None
        self.done_btn: Optional[QPushButton] = None
        self.is_saving = False
        
        self.load_config()
        self._filter_cache: Dict[str, bool] = {}
        
        gui_hooks.webview_did_receive_js_message.append(self.on_js_message)
        gui_hooks.reviewer_did_show_question.append(lambda reviewer: self.hide_editor())
        gui_hooks.reviewer_did_show_answer.append(lambda reviewer: self.hide_editor())
        anki.hooks.field_filter.append(self.on_field_filter)
        gui_hooks.webview_will_set_content.append(self.on_webview_will_set_content)
        
        mw.addonManager.setConfigAction(__name__, self.on_config_action)

    def load_config(self):
        self.config = mw.addonManager.getConfig(__name__) or {
            "auto_enable": True,
            "show_outline": True,
            "exclusions": {},
            "trigger_modifier": "Ctrl",
            "trigger_action": "Click"
        }

    def on_config_action(self):
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
            nt_item = QTreeWidgetItem(tree, [model['name']])
            nt_item.setCheckState(0, Qt.CheckState.Unchecked if exclusions.get(model['name'], {}).get("disabled") else Qt.CheckState.Checked)
            t_root = QTreeWidgetItem(nt_item, ["Templates"])
            for t in model['tmpls']:
                t_item = QTreeWidgetItem(t_root, [t['name']])
                t_item.setCheckState(0, Qt.CheckState.Unchecked if t['name'] in exclusions.get(model['name'], {}).get("templates", []) else Qt.CheckState.Checked)
            f_root = QTreeWidgetItem(nt_item, ["Fields"])
            for f in model['flds']:
                f_item = QTreeWidgetItem(f_root, [f['name']])
                f_item.setCheckState(0, Qt.CheckState.Unchecked if f['name'] in exclusions.get(model['name'], {}).get("fields", []) else Qt.CheckState.Checked)
        layout.addWidget(tree)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)
        
        if dialog.exec():
            new_ex = {}
            for i in range(tree.topLevelItemCount()):
                nt = tree.topLevelItem(i)
                disabled = nt.checkState(0) == Qt.CheckState.Unchecked
                d_tmpls = [nt.child(0).child(j).text(0) for j in range(nt.child(0).childCount()) if nt.child(0).child(j).checkState(0) == Qt.CheckState.Unchecked]
                d_flds = [nt.child(1).child(j).text(0) for j in range(nt.child(1).childCount()) if nt.child(1).child(j).checkState(0) == Qt.CheckState.Unchecked]
                if disabled or d_tmpls or d_flds:
                    new_ex[nt.text(0)] = {"disabled": disabled, "templates": d_tmpls, "fields": d_flds}
            self.config.update({"auto_enable": auto_cb.isChecked(), "show_outline": outline_cb.isChecked(), "trigger_modifier": mod_combo.currentText(), "trigger_action": act_combo.currentText(), "exclusions": new_ex})
            mw.addonManager.writeConfig(__name__, self.config)
            self._filter_cache.clear()

    def setup_ui(self):
        if self.editor_widget: return
        
        # We attach to mw.centralWidget()
        self.editor_widget = QWidget(mw.centralWidget())
        self.editor_widget.setMinimumHeight(400)
        self.editor_widget.setMaximumHeight(600)
        layout = QVBoxLayout(self.editor_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        top_bar = QWidget()
        top_bar.setStyleSheet("background: palette(window); border-bottom: 1px solid #888;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(10, 5, 10, 5)
        top_layout.addWidget(QLabel("<b>Native Field Editor</b>"))
        top_layout.addStretch()
        self.done_btn = QPushButton("Done (Ctrl+Enter)")
        self.done_btn.clicked.connect(self.hide_editor)
        top_layout.addWidget(self.done_btn)
        layout.addWidget(top_bar)
        
        # This is where the Editor's own widget will be placed
        self.editor_container = QWidget()
        QVBoxLayout(self.editor_container).setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor_container)
        
        # Insert above the reviewer webview
        cw_layout = mw.centralWidget().layout()
        if cw_layout:
            idx = cw_layout.indexOf(mw.reviewer.web)
            cw_layout.insertWidget(max(0, idx), self.editor_widget)
        
        self.editor_widget.hide()

    def _wrap(self, txt: str, field: str, ctx: TemplateRenderContext) -> str:
        try:
            flds = ctx.note().model()['flds']
            idx = next((i for i, f in enumerate(flds) if f['name'] == field), 0)
            return f'<span data-efdrc-idx="{idx}">{txt}</span>'
        except: return txt

    def on_field_filter(self, txt: str, field: str, filt: str, ctx: TemplateRenderContext) -> str:
        if filt == "edit": return self._wrap(txt, field, ctx)
        if not self.config.get("auto_enable", True) or filt: return txt
        cache_key = f"{ctx.note().model()['name']}_{field}_{filt}"
        if cache_key in self._filter_cache:
            return self._wrap(txt, field, ctx) if self._filter_cache[cache_key] else txt
        try:
            model = ctx.note().model()
            ex = self.config.get("exclusions", {}).get(model['name'], {})
            if ex.get("disabled") or field in ex.get("fields", []):
                self._filter_cache[cache_key] = False
                return txt
            try:
                if ctx.card() and ctx.card().template()['name'] in ex.get("templates", []):
                    self._filter_cache[cache_key] = False
                    return txt
            except: pass
        except: pass
        self._filter_cache[cache_key] = True
        return self._wrap(txt, field, ctx)

    def on_webview_will_set_content(self, web_content: aqt.webview.WebContent, context: Optional[Any]) -> None:
        if isinstance(context, (Reviewer, MultiCardPreviewer)):
            self._filter_cache.clear()
            addon_package = mw.addonManager.addonFromModule(__name__)
            web_content.js.append(f"/_addons/{addon_package}/web/efdrc.js")
            if self.config.get("show_outline", True):
                web_content.css.append(f"/_addons/{addon_package}/web/efdrc.css")
            js_conf = {"modifier": self.config.get("trigger_modifier", "Ctrl"), "action": self.config.get("trigger_action", "Click")}
            web_content.body += f"<script>EFDRC.setup({json.dumps(js_conf)});</script>"

    def on_js_message(self, handled: Tuple[bool, Any], message: str, context: Any) -> Tuple[bool, Any]:
        if message.startswith("EFDRC!edit#") and isinstance(context, (Reviewer, MultiCardPreviewer)):
            try: self.show_editor(int(message.split("#")[1]))
            except Exception as e: tooltip(f"Error: {e}")
            return (True, None)
        return handled

    def show_editor(self, field_idx: int):
        if self.is_saving: return
        self.setup_ui()
        note = mw.reviewer.card.note()
        
        self.editor_widget.show()
        
        if self.editor and self.current_note_id != note.id:
            self.editor.cleanup()
            self.editor = None
            
        if not self.editor:
            # We must pass the container widget directly to Editor
            # In some Anki versions, Editor(mw, container, note) works,
            # but we should ensure Editor's widget is correctly managed.
            self.editor = Editor(mw, self.editor_container, note)
            self.current_note_id = note.id
            # Explicitly add the editor's widget to our layout if it's not already there
            if self.editor.widget:
                self.editor_container.layout().addWidget(self.editor.widget)
        
        self.editor.loadNote(field_idx)
        if self.done_btn: self.done_btn.setEnabled(True)

    def hide_editor(self):
        if self.editor_widget and not self.editor_widget.isHidden():
            self.is_saving = True
            if self.done_btn: self.done_btn.setEnabled(False)
            self.editor_widget.hide()
            if self.editor: self.editor.saveNow(self._on_save_done)
            else: self._on_save_done()

    def _on_save_done(self):
        self.is_saving = False
        self.reload_reviewer()

    def reload_reviewer(self):
        reviewer = mw.reviewer
        if reviewer and reviewer.card:
            t = getattr(reviewer.card, "timer_started", getattr(reviewer.card, "timerStarted", None))
            reviewer.card = mw.col.getCard(reviewer.card.id)
            if t is not None:
                if hasattr(reviewer.card, "timer_started"): reviewer.card.timer_started = t
                else: reviewer.card.timerStarted = t
            if reviewer.state == "question": reviewer._showQuestion()
            elif reviewer.state == "answer": reviewer._showAnswer()
        if hasattr(mw, "previewer") and mw.previewer: mw.previewer.render_card()

efdrc = EFDRC()
mw.addonManager.setWebExports(__name__, r"web/.*")
