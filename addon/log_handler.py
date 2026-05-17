# -*- coding: utf-8 -*-

import os
import time
import logging
from typing import List, Optional

from aqt import mw
from aqt.qt import QObject, pyqtSignal

LOG_FILE_NAME = "efdrn.log"

class LogSignal(QObject):
    new_record = pyqtSignal()

_log_signal = LogSignal()

class LogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: List[str] = []
        self.max_records = 1000

    def emit(self, record):
        try:
            msg = self.format(record)
            self.records.append(msg)
            if len(self.records) > self.max_records:
                self.records.pop(0)
            _log_signal.new_record.emit()
        except Exception:
            self.handleError(record)

_log_handler = LogHandler()
_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger("efdrn")
logger.setLevel(logging.DEBUG)
logger.addHandler(_log_handler)

def get_log_content() -> str:
    return "\n".join(_log_handler.records)

def clear_logs():
    _log_handler.records.clear()

def setup_file_logging():
    try:
        addon_package = mw.addonManager.addonFromModule(__name__)
        addon_path = mw.addonManager.addon_path(addon_package)
        log_path = os.path.join(addon_path, LOG_FILE_NAME)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    except Exception:
        pass

def connect_log_signal(slot):
    _log_signal.new_record.connect(slot)
