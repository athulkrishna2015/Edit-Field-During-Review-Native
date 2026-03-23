# -*- coding: utf-8 -*-

import inspect
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import anki
import aqt
from anki.cards import Card
from anki.config import Config
from anki.notes import Note
from anki.template import TemplateRenderContext
from aqt import gui_hooks, mw
from aqt.editor import Editor, EditorMode
from aqt.qt import *
from aqt.reviewer import Reviewer
from aqt.utils import tooltip


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


class EFDRC:
    def __init__(self) -> None:
        self.editor: Optional[Editor] = None
        self.editor_widget: Optional[QWidget] = None
        self.editor_container: Optional[QWidget] = None
        self.undo_btn: Optional[QPushButton] = None
        self.done_btn: Optional[QPushButton] = None
        self.done_shortcut: Optional[QShortcut] = None
        self.done_shortcut_numpad: Optional[QShortcut] = None
        self.cancel_shortcut: Optional[QShortcut] = None
        self.undo_shortcut: Optional[QShortcut] = None
        self.custom_undo_shortcut: Optional[QShortcut] = None
        self.redo_shortcut: Optional[QShortcut] = None
        self.redo_alt_shortcut: Optional[QShortcut] = None
        self.saved_main_undo_shortcuts: Optional[list[QKeySequence]] = None
        self.saved_main_redo_shortcuts: Optional[list[QKeySequence]] = None
        self.main_editor_pref_snapshot: Optional[Dict[str, Any]] = None
        self.active_card_id: Optional[int] = None
        self.is_saving = False
        self.reload_after_save = False
        self.pending_refocus_field_idx: Optional[int] = None
        self.preload_delay_ms = 150
        self.preload_timer = QTimer(mw)
        self.preload_timer.setSingleShot(True)
        qconnect(self.preload_timer.timeout, self._run_deferred_preload)
        self.refocus_timer = QTimer(mw)
        self.refocus_timer.setSingleShot(True)
        qconnect(self.refocus_timer.timeout, self._restore_editor_focus)

        self.load_config()
        self._filter_cache: Dict[str, bool] = {}

        gui_hooks.webview_did_receive_js_message.append(self.on_js_message)
        gui_hooks.reviewer_did_show_question.append(self.on_reviewer_rendered)
        gui_hooks.reviewer_did_show_answer.append(self.on_reviewer_rendered)
        gui_hooks.state_shortcuts_will_change.append(self.on_state_shortcuts_will_change)
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
            "custom_undo_shortcut": "Ctrl+Alt+Z",
            "separate_editor_preferences": True,
            "reviewer_editor_preferences": {},
        }
        self.config.setdefault("custom_undo_shortcut", "Ctrl+Alt+Z")
        self.config.setdefault("separate_editor_preferences", True)
        reviewer_prefs = self.config.setdefault("reviewer_editor_preferences", {})
        for key, value in self._default_editor_preferences().items():
            reviewer_prefs.setdefault(key, value)

    def _default_editor_preferences(self) -> Dict[str, Any]:
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

    def _collection_available(self) -> bool:
        return bool(getattr(mw, "col", None) and getattr(mw, "pm", None))

    def _should_separate_editor_preferences(self) -> bool:
        return bool(self.config.get("separate_editor_preferences", True))

    def _collect_editor_preferences(self) -> Dict[str, Any]:
        prefs = self._default_editor_preferences()
        if not self._collection_available():
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

    def _reviewer_editor_preferences(self) -> Dict[str, Any]:
        prefs = dict(self._default_editor_preferences())
        prefs.update(self.config.get("reviewer_editor_preferences", {}))
        return prefs

    def _set_collection_config(self, key: str, value: Any) -> None:
        if not self._collection_available():
            return
        if mw.col.get_config(key, None) != value:
            mw.col.set_config(key, value)

    def _set_collection_bool_config(self, key: Config.Bool.V, value: bool) -> None:
        if not self._collection_available():
            return
        if mw.col.get_config_bool(key) != value:
            mw.col.set_config_bool(key, value)

    def _apply_editor_preferences(self, prefs: Dict[str, Any]) -> None:
        if not self._collection_available():
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
        self._set_collection_config(
            "renderMathjax", bool(prefs.get("render_mathjax", True))
        )
        self._set_collection_config(
            "shrinkEditorImages", bool(prefs.get("shrink_images", True))
        )
        self._set_collection_config(
            "closeHTMLTags", bool(prefs.get("close_html_tags", True))
        )
        self._set_collection_config(
            "customColorPickerPalette",
            list(prefs.get("custom_color_picker_palette", [])),
        )
        self._set_collection_bool_config(
            Config.Bool.PASTE_IMAGES_AS_PNG,
            bool(prefs.get("paste_images_as_png", False)),
        )
        self._set_collection_bool_config(
            Config.Bool.PASTE_STRIPS_FORMATTING,
            bool(prefs.get("paste_strips_formatting", False)),
        )

        if self.editor:
            self.editor.setupColourPalette()

    def _activate_reviewer_editor_preferences(self) -> None:
        if not self._should_separate_editor_preferences():
            return
        if self.main_editor_pref_snapshot is None:
            self.main_editor_pref_snapshot = self._collect_editor_preferences()
        self._apply_editor_preferences(self._reviewer_editor_preferences())

    def _deactivate_reviewer_editor_preferences(self) -> None:
        if self.main_editor_pref_snapshot is None:
            return

        if self._should_separate_editor_preferences():
            self.config["reviewer_editor_preferences"] = self._collect_editor_preferences()
            mw.addonManager.writeConfig(__name__, self.config)

        snapshot = self.main_editor_pref_snapshot
        self.main_editor_pref_snapshot = None
        self._apply_editor_preferences(snapshot)

    def _shortcut_to_text(self, shortcut: Any) -> str:
        if not shortcut:
            return ""
        return QKeySequence(str(shortcut).strip()).toString(
            QKeySequence.SequenceFormat.PortableText
        )

    def _configured_custom_undo_shortcut(self) -> str:
        return self._shortcut_to_text(self.config.get("custom_undo_shortcut"))

    def _undo_button_tooltip(self) -> str:
        shortcuts = ["Ctrl+Z"]
        custom_shortcut = self._configured_custom_undo_shortcut()
        if custom_shortcut:
            shortcuts.append(custom_shortcut)
        shortcut_list = ", ".join(shortcuts)
        return f"Undo the last embedded editor change ({shortcut_list})"

    def _refresh_editor_controls(self) -> None:
        if self.undo_btn:
            self.undo_btn.setText("Undo Edit")
            self.undo_btn.setToolTip(self._undo_button_tooltip())
        if self.done_btn:
            self.done_btn.setText("Done (Ctrl+Enter)")

    def _apply_shortcut_config(self) -> None:
        if self.custom_undo_shortcut:
            custom_shortcut = self._configured_custom_undo_shortcut()
            self.custom_undo_shortcut.setKey(QKeySequence(custom_shortcut))
        self._refresh_editor_controls()

    def _support_entries(self) -> list[dict[str, str]]:
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

    def _copy_support_value(self, value: str, label: str) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(value)
            tooltip(f"Copied {label}")

    def _make_support_card(self, entry: dict[str, str]) -> QGroupBox:
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
                self._copy_support_value(value, label)
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

    def _build_support_tab(self) -> QWidget:
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

        for entry in self._support_entries():
            content_layout.addWidget(self._make_support_card(entry))

        content_layout.addStretch()
        support_scroll.setWidget(content)
        page_layout.addWidget(support_scroll)
        return page

    def on_config_action(self) -> None:
        self.load_config()
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
        grid.addWidget(QLabel("Custom Undo Shortcut:"), 4, 0)
        undo_shortcut_edit = QKeySequenceEdit()
        configured_custom_undo = self._configured_custom_undo_shortcut()
        if configured_custom_undo:
            undo_shortcut_edit.setKeySequence(QKeySequence(configured_custom_undo))
        undo_shortcut_edit.setClearButtonEnabled(True)
        grid.addWidget(undo_shortcut_edit, 4, 1)
        separate_prefs_cb = QCheckBox(
            "Keep reviewer editor preferences separate from Anki's main editor"
        )
        separate_prefs_cb.setChecked(self._should_separate_editor_preferences())
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
        tabs.addTab(self._build_support_tab(), "Support")

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
                    "custom_undo_shortcut": self._shortcut_to_text(
                        undo_shortcut_edit.keySequence().toString(
                            QKeySequence.SequenceFormat.PortableText
                        )
                    ),
                    "separate_editor_preferences": separate_prefs_cb.isChecked(),
                    "exclusions": new_exclusions,
                }
            )
            mw.addonManager.writeConfig(__name__, self.config)
            self._filter_cache.clear()
            self._apply_shortcut_config()

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
        self.undo_btn = QPushButton("Undo Edit")
        self.undo_btn.clicked.connect(self._on_editor_undo)
        top_layout.addWidget(self.undo_btn)
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
        self._refresh_editor_controls()
        self.editor_widget.hide()

    def _install_shortcuts(self) -> None:
        if self.done_shortcut:
            self._apply_shortcut_config()
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

        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, mw)
        self.undo_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        qconnect(self.undo_shortcut.activated, self._on_editor_undo)

        self.custom_undo_shortcut = QShortcut(QKeySequence(), mw)
        self.custom_undo_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        qconnect(self.custom_undo_shortcut.activated, self._on_editor_undo)

        self.redo_shortcut = QShortcut(QKeySequence.StandardKey.Redo, mw)
        self.redo_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        qconnect(self.redo_shortcut.activated, self._on_editor_redo)

        self.redo_alt_shortcut = QShortcut(QKeySequence("Ctrl+Y"), mw)
        self.redo_alt_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        qconnect(self.redo_alt_shortcut.activated, self._on_editor_redo)

        self._apply_shortcut_config()
        self._set_shortcuts_enabled(False)

    def _set_shortcuts_enabled(self, enabled: bool) -> None:
        for shortcut in (
            self.done_shortcut,
            self.done_shortcut_numpad,
            self.cancel_shortcut,
            self.undo_shortcut,
            self.custom_undo_shortcut,
            self.redo_shortcut,
            self.redo_alt_shortcut,
        ):
            if shortcut:
                shortcut.setEnabled(enabled)

    def _active_editor_field_idx(self) -> Optional[int]:
        if not self.editor:
            return None
        current_idx = getattr(self.editor, "currentField", None)
        if current_idx is not None:
            return current_idx
        return getattr(self.editor, "last_field_index", None)

    def schedule_editor_refocus(
        self, field_idx: Optional[int] = None, delay_ms: int = 75
    ) -> None:
        if field_idx is None:
            field_idx = self._active_editor_field_idx()
        self.pending_refocus_field_idx = field_idx
        if self.refocus_timer.isActive():
            self.refocus_timer.stop()
        self.refocus_timer.start(delay_ms)

    def _restore_editor_focus(self) -> None:
        if (
            not self._editor_is_visible()
            or not self.editor
            or not getattr(self.editor, "web", None)
            or getattr(mw, "state", None) != "review"
        ):
            return

        field_idx = self.pending_refocus_field_idx
        if field_idx is None:
            field_idx = self._active_editor_field_idx()
        self.pending_refocus_field_idx = None

        self.editor.web.setFocus()
        if field_idx is None:
            return

        self.editor.web.eval(
            f'require("anki/ui").loaded.then(() => {{ focusField({field_idx}); }});'
        )

    def _main_window_undo_actions(self) -> tuple[Optional[QAction], Optional[QAction]]:
        form = getattr(mw, "form", None)
        if not form:
            return (None, None)
        return (getattr(form, "actionUndo", None), getattr(form, "actionRedo", None))

    def _suspend_main_window_undo_shortcuts(self) -> None:
        undo_action, redo_action = self._main_window_undo_actions()
        if undo_action and self.saved_main_undo_shortcuts is None:
            self.saved_main_undo_shortcuts = list(undo_action.shortcuts())
            undo_action.setShortcuts([])
        if redo_action and self.saved_main_redo_shortcuts is None:
            self.saved_main_redo_shortcuts = list(redo_action.shortcuts())
            redo_action.setShortcuts([])

    def _restore_main_window_undo_shortcuts(self) -> None:
        undo_action, redo_action = self._main_window_undo_actions()
        if undo_action and self.saved_main_undo_shortcuts is not None:
            undo_action.setShortcuts(self.saved_main_undo_shortcuts)
            self.saved_main_undo_shortcuts = None
        if redo_action and self.saved_main_redo_shortcuts is not None:
            redo_action.setShortcuts(self.saved_main_redo_shortcuts)
            self.saved_main_redo_shortcuts = None

    def _on_done_shortcut(self) -> None:
        if self._editor_is_visible():
            self.hide_editor()

    def _on_cancel_shortcut(self) -> None:
        if self._editor_is_visible():
            self.hide_editor()

    def _on_editor_undo(self) -> None:
        if not self._editor_is_visible() or not self.editor or not getattr(self.editor, "web", None):
            return
        self.editor.web.setFocus()
        self.editor.web.triggerPageAction(QWebEnginePage.WebAction.Undo)
        self.editor.web.eval("document.execCommand('undo');")

    def _on_editor_redo(self) -> None:
        if not self._editor_is_visible() or not self.editor or not getattr(self.editor, "web", None):
            return
        self.editor.web.setFocus()
        self.editor.web.triggerPageAction(QWebEnginePage.WebAction.Redo)
        self.editor.web.eval("document.execCommand('redo');")

    def _editor_is_visible(self) -> bool:
        return bool(self.editor_widget and not self.editor_widget.isHidden())

    def _set_review_screen_visible(self, visible: bool) -> None:
        web = getattr(mw, "web", None)
        if web:
            web.setVisible(visible)

    def _clear_editor_state(self) -> None:
        self.active_card_id = None
        self.reload_after_save = False
        self.pending_refocus_field_idx = None
        if self.refocus_timer.isActive():
            self.refocus_timer.stop()
        if self.undo_btn:
            self.undo_btn.setEnabled(False)
        if self.done_btn:
            self.done_btn.setEnabled(True)

    def _template_name_for_card(self, card: Card) -> str:
        try:
            template = card.template()
            return template["name"] if template else ""
        except Exception:
            return ""

    def _note_is_image_occlusion(self, note: Note) -> bool:
        kind = note.model().get("originalStockKind")
        if hasattr(kind, "name"):
            kind = kind.name
        if kind == "ORIGINAL_STOCK_KIND_IMAGE_OCCLUSION":
            return True
        try:
            return int(kind) == 6
        except (TypeError, ValueError):
            return False

    def _field_allowed_for_card(self, card: Card, field_name: str) -> bool:
        try:
            model = card.note().model()
            exclusions = self.config.get("exclusions", {}).get(model["name"], {})
            if exclusions.get("disabled"):
                return False
            if field_name in exclusions.get("fields", []):
                return False
            template_name = self._template_name_for_card(card)
            if template_name and template_name in exclusions.get("templates", []):
                return False
        except Exception:
            return True
        return True

    def _field_index_by_name(self, note: Note, field_name: str) -> Optional[int]:
        for idx, field in enumerate(note.model()["flds"]):
            if field["name"] == field_name:
                return idx
        return None

    def _card_has_any_allowed_field(self, card: Card) -> bool:
        for field in card.note().model()["flds"]:
            if self._field_allowed_for_card(card, field["name"]):
                return True
        return False

    def _fallback_field_index_for_card(self, card: Card) -> int:
        note = card.note()
        model_fields = note.model()["flds"]

        if self._note_is_image_occlusion(note):
            io_fields = None
            try:
                io_fields = mw.backend.get_image_occlusion_fields(note.mid)
            except Exception:
                io_fields = None

            preferred_indices = []
            if io_fields is not None:
                for attr in ("header", "back_extra", "comments"):
                    idx = getattr(io_fields, attr, None)
                    if idx is not None:
                        preferred_indices.append(int(idx))

            if not preferred_indices:
                for field_name in ("Header", "Back Extra", "Comments"):
                    idx = self._field_index_by_name(note, field_name)
                    if idx is not None:
                        preferred_indices.append(idx)

            skipped_indices = set()
            if io_fields is not None:
                for attr in ("occlusions", "image"):
                    idx = getattr(io_fields, attr, None)
                    if idx is not None:
                        skipped_indices.add(int(idx))

            for idx in preferred_indices:
                if 0 <= idx < len(model_fields):
                    field_name = model_fields[idx]["name"]
                    if self._field_allowed_for_card(card, field_name):
                        return idx

            for idx, field in enumerate(model_fields):
                if idx in skipped_indices:
                    continue
                if self._field_allowed_for_card(card, field["name"]):
                    return idx

        for idx, field in enumerate(model_fields):
            if self._field_allowed_for_card(card, field["name"]):
                return idx

        return 0

    def open_editor_for_current_card(self) -> bool:
        reviewer = getattr(mw, "reviewer", None)
        card = reviewer.card if reviewer and reviewer.card else None
        if not card:
            return False
        self.show_editor(self._fallback_field_index_for_card(card))
        return True

    def open_image_occlusion_editor(self) -> bool:
        reviewer = getattr(mw, "reviewer", None)
        card = reviewer.card if reviewer and reviewer.card else None
        if not card:
            return False
        if not self._note_is_image_occlusion(card.note()):
            return False
        if self._editor_is_visible():
            self.schedule_editor_refocus(delay_ms=30)
            return True
        if not self._card_has_any_allowed_field(card):
            return False
        self.show_editor(self._fallback_field_index_for_card(card))
        return True

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
        if (
            message == "edit"
            and isinstance(context, Reviewer)
            and self.open_image_occlusion_editor()
        ):
            return (True, None)
        if message.startswith("EFDRC!edit#") and isinstance(context, Reviewer):
            try:
                self.show_editor(int(message.split("#")[1]))
            except Exception as exc:
                tooltip(f"Error: {exc}")
            return (True, None)
        return handled

    def on_state_shortcuts_will_change(
        self, state: str, shortcuts: list[tuple[str, Any]]
    ) -> None:
        if state != "review":
            return
        shortcuts.append(("e", self._on_review_edit_shortcut))
        shortcuts.append(("ㄷ", self._on_review_edit_shortcut))

    def _on_review_edit_shortcut(self) -> None:
        if self.open_image_occlusion_editor():
            return
        mw.onEditCurrent()

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
        self._deactivate_reviewer_editor_preferences()
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
        self.schedule_editor_refocus()

    def should_defer_reviewer_refresh(self, reviewer: Reviewer, changes: Any) -> bool:
        current_card = getattr(reviewer, "card", None)
        current_card_id = current_card.id if current_card else None
        return bool(
            self._editor_is_visible()
            and not self.is_saving
            and current_card_id
            and current_card_id == self.active_card_id
            and getattr(changes, "note_text", False)
        )

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
            return EmbeddedReviewerEditor(mw, self.editor_container, mw, **kwargs)

        return EmbeddedReviewerEditor(mw, self.editor_container, note)

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

        self._activate_reviewer_editor_preferences()
        note = mw.reviewer.card.note() if mw.reviewer.card else None
        try:
            self._ensure_editor_ready(note)
        finally:
            if not self._editor_is_visible():
                self._deactivate_reviewer_editor_preferences()
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
        self._activate_reviewer_editor_preferences()
        self._ensure_editor_ready(note)
        if not self.editor or not self.editor_widget:
            tooltip("Editor could not be initialized.")
            self._deactivate_reviewer_editor_preferences()
            return

        self.active_card_id = card.id
        self.reload_after_save = False
        self._suspend_main_window_undo_shortcuts()
        self._set_shortcuts_enabled(True)
        self._set_review_screen_visible(False)
        self.editor_widget.show()
        self._set_editor_note(note, field_idx, card)
        self.schedule_editor_refocus(field_idx, delay_ms=120)
        if self.undo_btn:
            self.undo_btn.setEnabled(True)
        if self.done_btn:
            self.done_btn.setEnabled(True)

    def hide_editor(self, reload: bool = True) -> None:
        self.reload_after_save = reload and getattr(mw, "state", None) == "review"
        self._restore_main_window_undo_shortcuts()
        self._deactivate_reviewer_editor_preferences()

        if not self._editor_is_visible():
            if not self.reload_after_save:
                self._set_review_screen_visible(True)
                if not self.is_saving:
                    self._clear_editor_state()
            return

        self._set_shortcuts_enabled(False)
        if self.undo_btn:
            self.undo_btn.setEnabled(False)
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

if not getattr(Reviewer.op_executed, "_efdrn_wrapped", False):
    _efdrn_original_op_executed = Reviewer.op_executed

    def _efdrn_reviewer_op_executed(
        reviewer: Reviewer, changes: Any, handler: object | None, focused: bool
    ) -> bool:
        controller = globals().get("efdrc")
        if controller and controller.should_defer_reviewer_refresh(reviewer, changes):
            result = _efdrn_original_op_executed(reviewer, changes, handler, False)
            controller.schedule_editor_refocus(delay_ms=120)
            return result
        return _efdrn_original_op_executed(reviewer, changes, handler, focused)

    _efdrn_reviewer_op_executed._efdrn_wrapped = True  # type: ignore[attr-defined]
    Reviewer.op_executed = _efdrn_reviewer_op_executed

mw.addonManager.setWebExports(__name__, r"web/.*")
