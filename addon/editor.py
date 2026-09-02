# -*- coding: utf-8 -*-

from typing import Any

from aqt import gui_hooks
from aqt.editor import Editor
from aqt.qt import QKeySequence, QShortcut


class EmbeddedReviewerEditor(Editor):
    def setupShortcuts(self) -> None:
        super().setupShortcuts()
        # Disable built-in undo/redo shortcuts; the reviewer controller
        # handles them to support per-field/full-snapshot revert modes.
        disabled_sequences = {
            QKeySequence.StandardKey.Undo,
            QKeySequence.StandardKey.Redo,
        }
        disabled_strings = {"Ctrl+Z", "Ctrl+Y", "Ctrl+Shift+Z", "Meta+Z", "Meta+Shift+Z"}
        for child in self.widget.findChildren(QShortcut):
            try:
                seq = child.key()
                # Check by StandardKey
                if seq in disabled_sequences:
                    child.setEnabled(False)
                    continue
                key_str = seq.toString()
                if key_str in disabled_strings:
                    child.setEnabled(False)
            except Exception:
                continue

    def onBridgeCmd(self, cmd: str) -> Any:
        # Only intercept "key:" commands when a note is loaded; delegate everything else
        if cmd.startswith("key:"):
            if not self.note:
                return None
            try:
                (_type, ord_str, nid_str, txt) = cmd.split(":", 3)
                ord_idx = int(ord_str)
            except (ValueError, IndexError):
                return None
            try:
                nid = int(nid_str)
            except ValueError:
                nid = 0
            if nid != self.note.id:
                return None

            try:
                self.note.fields[ord_idx] = self.mungeHTML(txt)
            except IndexError:
                return None

            self.last_field_index = self.currentField = ord_idx
            try:
                gui_hooks.editor_did_fire_typing_timer(self.note)
            except Exception:
                pass
            try:
                self._check_and_update_duplicate_display_async()
            except Exception:
                pass
            return None

        return super().onBridgeCmd(cmd)
