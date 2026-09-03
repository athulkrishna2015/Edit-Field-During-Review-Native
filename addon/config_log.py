# -*- coding: utf-8 -*-

from aqt.qt import *
from aqt.qt import QApplication
from .log_handler import get_log_content, clear_logs, connect_log_signal

class LogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        connect_log_signal(self._refresh_logs)

    def _setup_ui(self):
        # Wrap in a scroll area so the tab works on small windows
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        btn_row = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setToolTip("Refresh the log display to show latest entries")
        refresh_btn.clicked.connect(self._refresh_logs)
        btn_row.addWidget(refresh_btn)

        copy_btn = QPushButton("Copy")
        copy_btn.setToolTip("Copy log content to clipboard")
        copy_btn.clicked.connect(self._on_copy)
        btn_row.addWidget(copy_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setToolTip("Clear all log entries")
        clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()

        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.setToolTip("When enabled, the log view automatically scrolls to the bottom after each refresh")
        btn_row.addWidget(self.auto_scroll_cb)

        layout.addLayout(btn_row)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        layout.addWidget(self.log_display, 1)

        scroll_area.setWidget(content_widget)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_area)
    
    def _refresh_logs(self):
        content = get_log_content()
        if content != self.log_display.toPlainText():
            self.log_display.setPlainText(content)
            
            if self.auto_scroll_cb.isChecked():
                self.log_display.moveCursor(QTextCursor.MoveOperation.End)
    
    def _on_clear(self):
        clear_logs()
        self.log_display.clear()
    
    def _on_copy(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.log_display.toPlainText())
            from aqt.utils import tooltip
            tooltip("Logs copied to clipboard")

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_logs()
