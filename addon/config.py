# -*- coding: utf-8 -*-

from typing import Any, Dict

from aqt import mw
from aqt.qt import *

from .config_settings import SettingsTab
from .config_support import SupportTab
from .config_log import LogTab


def default_editor_preferences() -> Dict[str, Any]:
    return {
        "last_text_color": "#0000ff",
        "last_highlight_color": "#ffff00",
        "tags_collapsed": False,
        "render_mathjax": True,
        "shrink_images": True,
        "close_html_tags": True,
        "custom_color_picker_palette": [],
        "paste_images_as_png": False,
        "paste_strips_formatting": False,
    }


def collection_available() -> bool:
    return bool(getattr(mw, "col", None) and getattr(mw, "pm", None))


def collect_editor_preferences() -> Dict[str, Any]:
    prefs = default_editor_preferences()
    if not collection_available():
        return prefs

    profile = mw.pm.profile or {}
    
    tags_collapsed = False
    try:
        from aqt.editor import EditorMode
        tags_collapsed = mw.pm.tags_collapsed(EditorMode.EDIT_CURRENT)
    except Exception:
        try:
            tags_collapsed = mw.pm.tags_collapsed()
        except Exception:
            pass

    paste_png = False
    paste_strips = False
    try:
        from anki.config import Config
        paste_png = mw.col.get_config_bool(Config.Bool.PASTE_IMAGES_AS_PNG)
        paste_strips = mw.col.get_config_bool(Config.Bool.PASTE_STRIPS_FORMATTING)
    except Exception:
        if hasattr(mw.col, "conf") and isinstance(mw.col.conf, dict):
            paste_png = mw.col.conf.get("pastePNG", paste_png)
            paste_strips = mw.col.conf.get("pasteStripsFormatting", paste_strips)
        else:
            try:
                paste_png = mw.col.get_config("pastePNG", paste_png)
                paste_strips = mw.col.get_config("pasteStripsFormatting", paste_strips)
            except Exception:
                pass

    prefs.update(
        {
            "last_text_color": profile.get("lastTextColor", prefs["last_text_color"]),
            "last_highlight_color": profile.get(
                "lastHighlightColor", prefs["last_highlight_color"]
            ),
            "tags_collapsed": tags_collapsed,
            "render_mathjax": mw.col.get_config(
                "renderMathjax", prefs["render_mathjax"]
            ),
            "shrink_images": mw.col.get_config(
                "shrinkEditorImages", prefs["shrink_images"]
            ),
            "close_html_tags": mw.col.get_config(
                "closeHTMLTags", prefs["close_html_tags"]
            ),
            "custom_color_picker_palette": list(
                mw.col.get_config("customColorPickerPalette", [])
            ),
            "paste_images_as_png": paste_png,
            "paste_strips_formatting": paste_strips,
        }
    )
    return prefs


def apply_editor_preferences(prefs: Dict[str, Any], editor: Any = None) -> None:
    if not collection_available():
        return

    profile = mw.pm.profile
    if profile is not None:
        profile["lastTextColor"] = prefs.get("last_text_color", "#0000ff")
        profile["lastHighlightColor"] = prefs.get(
            "last_highlight_color", "#ffff00"
        )

    try:
        from aqt.editor import EditorMode
        mw.pm.set_tags_collapsed(
            EditorMode.EDIT_CURRENT, bool(prefs.get("tags_collapsed", False))
        )
    except Exception:
        try:
            mw.pm.set_tags_collapsed(bool(prefs.get("tags_collapsed", False)))
        except Exception:
            pass

    def set_collection_config(key: str, value: Any) -> None:
        if mw.col.get_config(key, None) != value:
            mw.col.set_config(key, value)

    def set_collection_bool_config(enum_attr: str, dict_key: str, value: bool) -> None:
        try:
            from anki.config import Config
            if hasattr(Config, "Bool") and hasattr(Config.Bool, enum_attr):
                key = getattr(Config.Bool, enum_attr)
                if mw.col.get_config_bool(key) != value:
                    mw.col.set_config_bool(key, value)
                return
        except Exception:
            pass
            
        if hasattr(mw.col, "conf") and isinstance(mw.col.conf, dict):
            if dict_key in mw.col.conf:
                mw.col.conf[dict_key] = value
                mw.col.setMod()
                return
        try:
            if mw.col.get_config(dict_key, None) != value:
                mw.col.set_config(dict_key, value)
        except Exception:
            pass

    set_collection_config("renderMathjax", bool(prefs.get("render_mathjax", True)))
    set_collection_config("shrinkEditorImages", bool(prefs.get("shrink_images", True)))
    set_collection_config("closeHTMLTags", bool(prefs.get("close_html_tags", True)))
    set_collection_config(
        "customColorPickerPalette",
        list(prefs.get("custom_color_picker_palette", [])),
    )
    set_collection_bool_config(
        "PASTE_IMAGES_AS_PNG", "pastePNG",
        bool(prefs.get("paste_images_as_png", False)),
    )
    set_collection_bool_config(
        "PASTE_STRIPS_FORMATTING", "pasteStripsFormatting",
        bool(prefs.get("paste_strips_formatting", False)),
    )

    if editor:
        editor.setupColourPalette()


def on_config_action(
    addon_manager: Any, module_name: str, on_save: Any, initial_tab: int = 0
) -> None:
    config = addon_manager.getConfig(module_name)
    dialog = QDialog(mw)
    dialog.setWindowTitle("EFDRN Configuration")
    dialog.setMinimumWidth(600)
    dialog.setMinimumHeight(600)
    layout = QVBoxLayout(dialog)
    tabs = QTabWidget()
    layout.addWidget(tabs)

    settings_tab = SettingsTab(config, mw)
    support_tab = SupportTab()
    log_tab = LogTab()

    tabs.addTab(settings_tab, "Settings")
    tabs.addTab(support_tab, "Support")
    tabs.addTab(log_tab, "Log")

    tabs.setCurrentIndex(initial_tab)

    btns = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    btns.accepted.connect(dialog.accept)
    btns.rejected.connect(dialog.reject)
    layout.addWidget(btns)

    if dialog.exec():
        settings_tab.update_config(config)
        addon_manager.writeConfig(module_name, config)
        if on_save:
            on_save()
