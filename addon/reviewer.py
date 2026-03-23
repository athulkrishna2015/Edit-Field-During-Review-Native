# -*- coding: utf-8 -*-

import base64
from typing import Any, Optional, Tuple, Union

import anki
from anki.template import TemplateRenderContext
from anki.notes import Note
from anki.cards import Card
import aqt
from aqt import mw, gui_hooks
from aqt.editor import Editor
from aqt.qt import *
from aqt.utils import tooltip

class EFDRCEditor(Editor):
    def onBridgeCmd(self, cmd: str) -> None:
        super().onBridgeCmd(cmd)

class EFDRC:
    def __init__(self):
        self.editor: Optional[EFDRCEditor] = None
        self.editor_widget: Optional[QWidget] = None
        self.editor_parent: Optional[QWidget] = None
        self.current_note_id: Optional[int] = None
        self.done_btn: Optional[QPushButton] = None
        
        self.load_config()
        
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
            "exclusions": {}
        }

    def on_config_action(self):
        self.load_config()
        dialog = QDialog(mw)
        dialog.setWindowTitle("EFDRN Configuration")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(600)
        layout = QVBoxLayout(dialog)
        
        # Global settings
        global_grp = QGroupBox("Global Settings")
        global_layout = QVBoxLayout(global_grp)
        
        auto_cb = QCheckBox("Enable by default for all fields")
        auto_cb.setChecked(self.config.get("auto_enable", True))
        global_layout.addWidget(auto_cb)
        
        outline_cb = QCheckBox("Show outline on Ctrl + Hover")
        outline_cb.setChecked(self.config.get("show_outline", True))
        global_layout.addWidget(outline_cb)
        
        layout.addWidget(global_grp)
        
        # Note types customization
        layout.addWidget(QLabel("<b>Enable/Disable Note Types, Templates, and Fields:</b>"))
        tree = QTreeWidget()
        tree.setHeaderLabels(["Name", "Type"])
        tree.setColumnCount(2)
        tree.setColumnWidth(0, 300)
        
        exclusions = self.config.get("exclusions", {})
        
        models = mw.col.models.all()
        for model in models:
            nt_name = model['name']
            nt_ex = exclusions.get(nt_name, {})
            
            nt_item = QTreeWidgetItem(tree, [nt_name, "Note Type"])
            nt_item.setCheckState(0, Qt.CheckState.Unchecked if nt_ex.get("disabled") else Qt.CheckState.Checked)
            nt_item.setExpanded(False)
            
            # Templates
            tmpl_root = QTreeWidgetItem(nt_item, ["Templates", ""])
            for tmpl in model['tmpls']:
                t_name = tmpl['name']
                t_item = QTreeWidgetItem(tmpl_root, [t_name, "Template"])
                t_item.setCheckState(0, Qt.CheckState.Unchecked if t_name in nt_ex.get("templates", []) else Qt.CheckState.Checked)
            
            # Fields
            fld_root = QTreeWidgetItem(nt_item, ["Fields", ""])
            for fld in model['flds']:
                f_name = fld['name']
                f_item = QTreeWidgetItem(fld_root, [f_name, "Field"])
                f_item.setCheckState(0, Qt.CheckState.Unchecked if f_name in nt_ex.get("fields", []) else Qt.CheckState.Checked)

        layout.addWidget(tree)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec():
            # Save configuration
            new_exclusions = {}
            for i in range(tree.topLevelItemCount()):
                nt_item = tree.topLevelItem(i)
                nt_name = nt_item.text(0)
                
                nt_disabled = nt_item.checkState(0) == Qt.CheckState.Unchecked
                
                tmpl_root = nt_item.child(0)
                disabled_tmpls = []
                for j in range(tmpl_root.childCount()):
                    t_item = tmpl_root.child(j)
                    if t_item.checkState(0) == Qt.CheckState.Unchecked:
                        disabled_tmpls.append(t_item.text(0))
                
                fld_root = nt_item.child(1)
                disabled_flds = []
                for j in range(fld_root.childCount()):
                    f_item = fld_root.child(j)
                    if f_item.checkState(0) == Qt.CheckState.Unchecked:
                        disabled_flds.append(f_item.text(0))
                
                if nt_disabled or disabled_tmpls or disabled_flds:
                    new_exclusions[nt_name] = {
                        "disabled": nt_disabled,
                        "templates": disabled_tmpls,
                        "fields": disabled_flds
                    }
            
            self.config["auto_enable"] = auto_cb.isChecked()
            self.config["show_outline"] = outline_cb.isChecked()
            self.config["exclusions"] = new_exclusions
            mw.addonManager.writeConfig(__name__, self.config)
            tooltip("Config saved. Please reload the reviewer to apply changes.")

    def setup_ui(self):
        if self.editor_widget:
            return
        
        self.editor_widget = QWidget(mw.centralWidget())
        layout = QVBoxLayout(self.editor_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(5, 5, 5, 5)
        
        title = QLabel("<b>Edit Field</b>")
        top_layout.addWidget(title)
        
        top_layout.addStretch()
        
        self.done_btn = QPushButton("Done")
        self.done_btn.setShortcut("Ctrl+Return")
        self.done_btn.clicked.connect(self.hide_editor)
        top_layout.addWidget(self.done_btn)
        
        layout.addWidget(top_bar)
        
        self.editor_parent = QWidget()
        editor_parent_layout = QVBoxLayout(self.editor_parent)
        editor_parent_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor_parent)
        
        mw.centralWidget().layout().insertWidget(1, self.editor_widget)
        self.editor_widget.hide()

    def wrap_field(self, txt: str, field: str, ctx: TemplateRenderContext) -> str:
        try:
            note = ctx.note()
            model = note.model()
            fld_idx = 0
            for i, f in enumerate(model['flds']):
                if f['name'] == field:
                    fld_idx = i
                    break
            return f'<span data-efdrc-idx="{fld_idx}">{txt}</span>'
        except:
            return txt

    def on_field_filter(self, txt: str, field: str, filt: str, ctx: TemplateRenderContext) -> str:
        # Explicit 'edit:' filter always enabled
        if filt == "edit":
            return self.wrap_field(txt, field, ctx)
            
        # If auto_enable is false, skip unless explicitly using 'edit:'
        if not self.config.get("auto_enable", True):
            return txt
            
        # Skip if any other filter is applied (e.g. {{cloze:Field}}, {{text:Field}}, etc.)
        if filt:
            return txt

        # Check for exclusions
        try:
            note = ctx.note()
            model = note.model()
            nt_name = model['name']
            
            exclusions = self.config.get("exclusions", {})
            if nt_name in exclusions:
                nt_ex = exclusions[nt_name]
                if nt_ex.get("disabled", False):
                    return txt
                if field in nt_ex.get("fields", []):
                    return txt
                
                # Check current card template
                # ctx.card() might not be available in all contexts, but is for Reviewer
                try:
                    card = ctx.card()
                    if card:
                        tmpl_name = card.template()['name']
                        if tmpl_name in nt_ex.get("templates", []):
                            return txt
                except:
                    pass
        except:
            pass
        
        return self.wrap_field(txt, field, ctx)

    def on_webview_will_set_content(self, web_content: aqt.webview.WebContent, context: Optional[Any]) -> None:
        if isinstance(context, aqt.reviewer.Reviewer):
            addon_package = mw.addonManager.addonFromModule(__name__)
            web_content.js.append(f"/_addons/{addon_package}/web/efdrc.js")
            if self.config.get("show_outline", True):
                web_content.css.append(f"/_addons/{addon_package}/web/efdrc.css")

    def on_js_message(self, handled: Tuple[bool, Any], message: str, context: Any) -> Tuple[bool, Any]:
        if message.startswith("EFDRC!edit#"):
            if not isinstance(context, aqt.reviewer.Reviewer):
                return handled
            try:
                idx = int(message.split("#")[1])
                self.show_editor(idx)
            except Exception as e:
                tooltip(f"Error opening editor: {e}")
            return (True, None)
        return handled

    def show_editor(self, field_idx: int):
        self.setup_ui()
        note = mw.reviewer.card.note()
        
        if self.editor and self.current_note_id != note.id:
            self.editor.cleanup()
            self.editor = None
            
        if not self.editor:
            self.editor = EFDRCEditor(mw, self.editor_parent, note)
            self.current_note_id = note.id
        
        self.editor.loadNote(field_idx)
        self.editor_widget.show()
        if self.done_btn:
            self.done_btn.setEnabled(True)

    def hide_editor(self):
        if self.editor_widget and not self.editor_widget.isHidden():
            if self.done_btn:
                self.done_btn.setEnabled(False)
            self.editor_widget.hide()
            if self.editor:
                self.editor.saveNow(self.reload_reviewer)
            else:
                self.reload_reviewer()

    def reload_reviewer(self):
        reviewer = mw.reviewer
        if not reviewer or not reviewer.card:
            return
            
        reviewer.card = mw.col.getCard(reviewer.card.id)
        
        if reviewer.state == "question":
            reviewer._showQuestion()
        elif reviewer.state == "answer":
            reviewer._showAnswer()

efdrc = EFDRC()
mw.addonManager.setWebExports(__name__, r"web/.*")
