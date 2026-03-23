# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Any, Dict

from anki.config import Config
from aqt import mw
from aqt.utils import tooltip
from aqt.editor import EditorMode
from aqt.qt import *


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
    prefs.update(
        {
            "last_text_color": profile.get("lastTextColor", prefs["last_text_color"]),
            "last_highlight_color": profile.get(
                "lastHighlightColor", prefs["last_highlight_color"]
            ),
            "tags_collapsed": mw.pm.tags_collapsed(EditorMode.EDIT_CURRENT),
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
            "paste_images_as_png": mw.col.get_config_bool(
                Config.Bool.PASTE_IMAGES_AS_PNG
            ),
            "paste_strips_formatting": mw.col.get_config_bool(
                Config.Bool.PASTE_STRIPS_FORMATTING
            ),
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

    mw.pm.set_tags_collapsed(
        EditorMode.EDIT_CURRENT, bool(prefs.get("tags_collapsed", False))
    )

    def set_collection_config(key: str, value: Any) -> None:
        if mw.col.get_config(key, None) != value:
            mw.col.set_config(key, value)

    def set_collection_bool_config(key: Config.Bool.V, value: bool) -> None:
        if mw.col.get_config_bool(key) != value:
            mw.col.set_config_bool(key, value)

    set_collection_config("renderMathjax", bool(prefs.get("render_mathjax", True)))
    set_collection_config("shrinkEditorImages", bool(prefs.get("shrink_images", True)))
    set_collection_config("closeHTMLTags", bool(prefs.get("close_html_tags", True)))
    set_collection_config(
        "customColorPickerPalette",
        list(prefs.get("custom_color_picker_palette", [])),
    )
    set_collection_bool_config(
        Config.Bool.PASTE_IMAGES_AS_PNG,
        bool(prefs.get("paste_images_as_png", False)),
    )
    set_collection_bool_config(
        Config.Bool.PASTE_STRIPS_FORMATTING,
        bool(prefs.get("paste_strips_formatting", False)),
    )

    if editor:
        editor.setupColourPalette()


def shortcut_to_text(shortcut: Any) -> str:
    if not shortcut:
        return ""
    return QKeySequence(str(shortcut).strip()).toString(
        QKeySequence.SequenceFormat.PortableText
    )


def support_entries() -> list[dict[str, str]]:
    support_dir = Path(__file__).resolve().parent / "Support"
    return [
        {
            "title": "UPI",
            "value": "athulkrishnasv2015-2@okhdfcbank",
            "image": str(support_dir / "UPI.jpg"),
        },
        {
            "title": "Bitcoin (BTC)",
            "value": "bc1qrrek3m7sr33qujjrktj949wav6mehdsk057cfx",
            "image": str(support_dir / "BTC.jpg"),
        },
        {
            "title": "Ethereum (ETH)",
            "value": "0xce6899e4903EcB08bE5Be65E44549fadC3F45D27",
            "image": str(support_dir / "ETH.jpg"),
        },
    ]


def copy_support_value(value: str, label: str) -> None:
    clipboard = QGuiApplication.clipboard()
    if clipboard:
        clipboard.setText(value)
        tooltip(f"Copied {label}")


def make_support_card(entry: dict[str, str]) -> QGroupBox:
    group = QGroupBox(entry["title"])
    layout = QVBoxLayout(group)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    value_row = QHBoxLayout()
    value_edit = QLineEdit(entry["value"])
    value_edit.setReadOnly(True)
    value_edit.setCursorPosition(0)
    copy_btn = QPushButton("Copy")
    copy_btn.clicked.connect(
        lambda _checked=False, value=entry["value"], label=entry["title"]: (
            copy_support_value(value, label)
        )
    )
    value_row.addWidget(value_edit, 1)
    value_row.addWidget(copy_btn)
    layout.addLayout(value_row)

    qr_label = QLabel()
    qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    qr_label.setMinimumWidth(380)
    qr_label.setMinimumHeight(420)
    qr_label.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
    )

    pixmap = QPixmap(entry["image"])
    if pixmap.isNull():
        qr_label.setText("QR image not found.")
    else:
        qr_label.setPixmap(
            pixmap.scaledToWidth(
                420, Qt.TransformationMode.SmoothTransformation
            )
        )

    layout.addWidget(qr_label, 0, Qt.AlignmentFlag.AlignCenter)
    return group


def build_support_tab() -> QWidget:
    page = QWidget()
    page_layout = QVBoxLayout(page)
    page_layout.setContentsMargins(0, 0, 0, 0)

    support_scroll = QScrollArea()
    support_scroll.setWidgetResizable(True)
    support_scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )

    content = QWidget()
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(12, 12, 12, 12)
    content_layout.setSpacing(12)

    intro = QLabel(
        "If this add-on helps your workflow, you can support its development "
        "with any of the options below. Each QR code is shown large for easy "
        "scanning, and the payment ID can be copied with one click."
    )
    intro.setWordWrap(True)
    content_layout.addWidget(intro)

    for entry in support_entries():
        content_layout.addWidget(make_support_card(entry))

    content_layout.addStretch()
    support_scroll.setWidget(content)
    page_layout.addWidget(support_scroll)
    return page


def on_config_action(addon_manager: Any, module_name: str, on_save: Any) -> None:
    config = addon_manager.getConfig(module_name)
    dialog = QDialog(mw)
    dialog.setWindowTitle("EFDRN Configuration")
    dialog.setMinimumWidth(600)
    dialog.setMinimumHeight(600)
    layout = QVBoxLayout(dialog)
    tabs = QTabWidget()
    layout.addWidget(tabs)

    settings_page = QWidget()
    settings_layout = QVBoxLayout(settings_page)

    global_grp = QGroupBox("General Settings")
    grid = QGridLayout(global_grp)
    auto_cb = QCheckBox("Enable by default for all fields")
    auto_cb.setChecked(config.get("auto_enable", True))
    grid.addWidget(auto_cb, 0, 0, 1, 2)
    outline_cb = QCheckBox("Show visual outline on Hover")
    outline_cb.setChecked(config.get("show_outline", True))
    grid.addWidget(outline_cb, 1, 0, 1, 2)
    grid.addWidget(QLabel("Trigger Modifier:"), 2, 0)
    mod_combo = QComboBox()
    mod_combo.addItems(["Ctrl", "Shift", "Alt", "None"])
    mod_combo.setCurrentText(config.get("trigger_modifier", "Ctrl"))
    grid.addWidget(mod_combo, 2, 1)
    grid.addWidget(QLabel("Trigger Action:"), 3, 0)
    act_combo = QComboBox()
    act_combo.addItems(["Click", "DoubleClick"])
    act_combo.setCurrentText(config.get("trigger_action", "Click"))
    grid.addWidget(act_combo, 3, 1)
    grid.addWidget(QLabel("Custom Undo Shortcut:"), 4, 0)
    undo_shortcut_edit = QKeySequenceEdit()
    configured_custom_undo = shortcut_to_text(config.get("custom_undo_shortcut"))
    if configured_custom_undo:
        undo_shortcut_edit.setKeySequence(QKeySequence(configured_custom_undo))
    undo_shortcut_edit.setClearButtonEnabled(True)
    grid.addWidget(undo_shortcut_edit, 4, 1)
    separate_prefs_cb = QCheckBox(
        "Keep reviewer editor preferences separate from Anki's main editor"
    )
    separate_prefs_cb.setChecked(config.get("separate_editor_preferences", False))
    grid.addWidget(separate_prefs_cb, 5, 0, 1, 2)
    undo_help = QLabel(
        "Used by the embedded reviewer editor. Leave blank to disable the "
        "fallback shortcut."
    )
    undo_help.setWordWrap(True)
    grid.addWidget(undo_help, 6, 0, 1, 2)
    prefs_help = QLabel(
        "When enabled, changes to color memory, tags collapse state, MathJax, "
        "image shrink, HTML closing, and paste options stay local to the "
        "embedded reviewer editor."
    )
    prefs_help.setWordWrap(True)
    grid.addWidget(prefs_help, 7, 0, 1, 2)
    settings_layout.addWidget(global_grp)

    tree = QTreeWidget()
    tree.setHeaderLabels(["Note Type / Template / Field"])
    exclusions = config.get("exclusions", {})
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
    settings_layout.addWidget(tree)

    bulk_row = QHBoxLayout()
    enable_all_btn = QPushButton("Enable All")
    disable_all_btn = QPushButton("Disable All")
    bulk_row.addWidget(enable_all_btn)
    bulk_row.addWidget(disable_all_btn)
    bulk_row.addStretch()
    settings_layout.addLayout(bulk_row)

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

    tabs.addTab(settings_page, "Settings")
    tabs.addTab(build_support_tab(), "Support")

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

        config.update(
            {
                "auto_enable": auto_cb.isChecked(),
                "show_outline": outline_cb.isChecked(),
                "trigger_modifier": mod_combo.currentText(),
                "trigger_action": act_combo.currentText(),
                "custom_undo_shortcut": shortcut_to_text(
                    undo_shortcut_edit.keySequence().toString(
                        QKeySequence.SequenceFormat.PortableText
                    )
                ),
                "separate_editor_preferences": separate_prefs_cb.isChecked(),
                "exclusions": new_exclusions,
            }
        )
        addon_manager.writeConfig(module_name, config)
        if on_save:
            on_save()
