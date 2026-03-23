# -*- coding: utf-8 -*-

from typing import Any

from aqt import gui_hooks
from aqt.editor import Editor


class EmbeddedReviewerEditor(Editor):
    def onBridgeCmd(self, cmd: str) -> Any:
        if not self.note:
            return

        if cmd.startswith("key"):
            (_type, ord_str, nid_str, txt) = cmd.split(":", 3)
            ord_idx = int(ord_str)
            try:
                nid = int(nid_str)
            except ValueError:
                nid = 0
            if nid != self.note.id:
                return

            try:
                self.note.fields[ord_idx] = self.mungeHTML(txt)
            except IndexError:
                return

            gui_hooks.editor_did_fire_typing_timer(self.note)
            self._check_and_update_duplicate_display_async()
            return

        return super().onBridgeCmd(cmd)
