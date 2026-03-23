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
        
        gui_hooks.webview_did_receive_js_message.append(self.on_js_message)
        gui_hooks.reviewer_did_show_question.append(lambda reviewer: self.hide_editor())
        gui_hooks.reviewer_did_show_answer.append(lambda reviewer: self.hide_editor())
        anki.hooks.field_filter.append(self.on_field_filter)
        gui_hooks.webview_will_set_content.append(self.on_webview_will_set_content)

    def setup_ui(self):
        if self.editor_widget:
            return
        
        self.editor_widget = QWidget(mw.centralWidget())
        layout = QVBoxLayout(self.editor_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Done button and toolbar container
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
        
        # Editor parent widget
        self.editor_parent = QWidget()
        editor_parent_layout = QVBoxLayout(self.editor_parent)
        editor_parent_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor_parent)
        
        # Insert into main window layout above the webview
        mw.centralWidget().layout().insertWidget(1, self.editor_widget)
        self.editor_widget.hide()

    def on_field_filter(self, txt: str, field: str, filt: str, ctx: TemplateRenderContext) -> str:
        if filt == "edit":
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
                pass
        return txt

    def on_webview_will_set_content(self, web_content: aqt.webview.WebContent, context: Optional[Any]) -> None:
        if isinstance(context, aqt.reviewer.Reviewer):
            addon_package = mw.addonManager.addonFromModule(__name__)
            web_content.js.append(f"/_addons/{addon_package}/web/efdrc.js")
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
            
        # Re-fetch card to get updated note content
        reviewer.card = mw.col.getCard(reviewer.card.id)
        
        if reviewer.state == "question":
            reviewer._showQuestion()
        elif reviewer.state == "answer":
            reviewer._showAnswer()

efdrc = EFDRC()
mw.addonManager.setWebExports(__name__, r"web/.*")
