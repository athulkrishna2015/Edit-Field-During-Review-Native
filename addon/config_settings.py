# -*- coding: utf-8 -*-

from typing import Any, Dict
from aqt.qt import *
from . import utils

MODEL_ID_ROLE = int(Qt.ItemDataRole.UserRole)
ENTRY_KIND_ROLE = int(Qt.ItemDataRole.UserRole) + 1
ENTRY_ORD_ROLE = int(Qt.ItemDataRole.UserRole) + 2

UNDO_STYLE_MAP = {
    "Full Snapshot Revert": "full_snapshot",
    "Per-Field Revert": "per_field",
    "In-Editor Only": "editor_only",
}

class SettingsTab(QWidget):
    def __init__(self, config: Dict[str, Any], mw: Any):
        super().__init__()
        self.config = config
        self.mw = mw
        self._setup_ui()

    def _setup_ui(self):
        # Wrap entire settings in a scroll area so the tab works on small windows
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        global_grp = QGroupBox("General Settings")
        grid = QGridLayout(global_grp)

        self.auto_cb = QCheckBox("Enable by default for all fields")
        self.auto_cb.setChecked(self.config.get("auto_enable", True))
        self.auto_cb.setToolTip(
            "When enabled, all rendered fields are made editable automatically without "
            "needing explicit edit: filters in templates.\n\n"
            "When disabled, only fields explicitly marked with {{edit:Field}} are editable."
        )
        grid.addWidget(self.auto_cb, 0, 0, 1, 2)

        self.outline_cb = QCheckBox("Show visual outline on hover")
        self.outline_cb.setChecked(self.config.get("show_outline", True))
        self.outline_cb.setToolTip(
            "Show a dashed outline around editable fields when the configured trigger "
            "modifier is held down (or always when modifier is 'None').\n\n"
            "Helps you identify which fields can be clicked to open the editor."
        )
        grid.addWidget(self.outline_cb, 1, 0, 1, 2)

        trigger_mod_label = QLabel("Trigger modifier:")
        trigger_mod_label.setToolTip(
            "Key modifier that must be held down to activate editing."
        )
        grid.addWidget(trigger_mod_label, 2, 0)
        self.mod_combo = QComboBox()
        self.mod_combo.addItems(["Ctrl", "Shift", "Alt", "None"])
        self.mod_combo.setCurrentText(self.config.get("trigger_modifier", "Ctrl"))
        self.mod_combo.setToolTip(
            "Key modifier required to show the outline and enable editing.\n\n"
            "• Ctrl — hold the Control key (default)\n"
            "• Shift — hold the Shift key\n"
            "• Alt — hold the Alt/Option key\n"
            "• None — editing is always active when hovering over editable fields"
        )
        grid.addWidget(self.mod_combo, 2, 1)

        trigger_act_label = QLabel("Trigger action:")
        trigger_act_label.setToolTip(
            "Mouse action that opens the editor on an editable field."
        )
        grid.addWidget(trigger_act_label, 3, 0)
        self.act_combo = QComboBox()
        self.act_combo.addItems(["Click", "DoubleClick"])
        self.act_combo.setCurrentText(self.config.get("trigger_action", "Click"))
        self.act_combo.setToolTip(
            "How to open the editor on an editable field.\n\n"
            "• Click — single click opens the editor\n"
            "• DoubleClick — double click required to open the editor"
        )
        grid.addWidget(self.act_combo, 3, 1)

        self.show_review_button_cb = QCheckBox('Show "Edit (N)" button on the review screen')
        self.show_review_button_cb.setChecked(self.config.get("show_review_button", False))
        self.show_review_button_cb.setToolTip(
            "When enabled, a visible 'Edit (N)' button appears on the review screen.\n\n"
            "You can click this button or use the N keyboard shortcut to open the "
            "embedded editor directly without using the configured trigger modifier."
        )
        grid.addWidget(self.show_review_button_cb, 4, 0, 1, 2)

        # --- Undo settings ---
        self.enable_undo_cb = QCheckBox("Enable Custom Undo (Ctrl+Z)")
        self.enable_undo_cb.setChecked(self.config.get("enable_undo", False))
        self.enable_undo_cb.setToolTip(
            "When enabled, Ctrl+Z performs custom undo instead of the standard in-editor undo.\n\n"
            "The exact behavior is controlled by the 'Undo Style' setting below."
        )
        grid.addWidget(self.enable_undo_cb, 5, 0, 1, 2)

        undo_style_label = QLabel("Undo Style:")
        undo_style_label.setToolTip("How Ctrl+Z behaves when custom undo is enabled.")
        grid.addWidget(undo_style_label, 6, 0)
        self.undo_style_combo = QComboBox()
        self.undo_style_combo.addItems(list(UNDO_STYLE_MAP.keys()))
        current_style = self.config.get("undo_style", "per_field")
        for label, value in UNDO_STYLE_MAP.items():
            if value == current_style:
                self.undo_style_combo.setCurrentText(label)
                break
        self.undo_style_combo.setToolTip(
            "Choose how Ctrl+Z behaves when custom undo is enabled.\n\n"
            "• Full Snapshot Revert — reverts ALL fields to the state when the editor opened\n"
            "• Per-Field Revert (default) — reverts only the currently focused field\n"
            "• In-Editor Only — standard in-editor undo (no snapshot-based revert)"
        )
        grid.addWidget(self.undo_style_combo, 6, 1)

        def _update_undo_controls(checked: bool) -> None:
            self.undo_style_combo.setEnabled(checked)

        self.enable_undo_cb.toggled.connect(_update_undo_controls)
        _update_undo_controls(self.enable_undo_cb.isChecked())

        # --- Other settings ---
        self.separate_prefs_cb = QCheckBox(
            "Keep reviewer editor preferences separate from Anki's main editor"
        )
        self.separate_prefs_cb.setChecked(
            self.config.get("separate_editor_preferences", False)
        )
        self.separate_prefs_cb.setToolTip(
            "When enabled, the embedded editor maintains its own independent preferences "
            "for text color, highlight color, tag collapse state, MathJax rendering, "
            "image shrink, HTML auto-close, and paste settings.\n\n"
            "These stay separate from Anki's main editor settings."
        )
        grid.addWidget(self.separate_prefs_cb, 8, 0, 1, 2)

        self.preload_add_cb = QCheckBox("Preload Add Cards window for faster opening")
        self.preload_add_cb.setChecked(self.config.get("preload_add_window", True))
        self.preload_add_cb.setToolTip(
            "When enabled, the Add Cards dialog is constructed in the background while "
            "you're in review mode.\n\n"
            "This makes the Add Cards window open almost instantly when you need it, "
            "while preserving your currently selected deck."
        )
        grid.addWidget(self.preload_add_cb, 10, 0, 1, 2)

        layout.addWidget(global_grp)

        # Exclusions section
        excl_grp = QGroupBox("Exclusions")
        excl_layout = QVBoxLayout(excl_grp)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Note Type / Template / Field"])
        self.tree.setToolTip(
            "Tree of note types, their templates, and fields.\n\n"
            "Uncheck a Note Type to disable editing for all its cards.\n"
            "Uncheck a Template (card type) to disable editing for that card type only.\n"
            "Uncheck a Field to disable editing for that field across all cards in the note type."
        )
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._populate_tree()
        excl_layout.addWidget(self.tree)

        bulk_row = QHBoxLayout()
        enable_all_btn = QPushButton("Enable All")
        enable_all_btn.setToolTip(
            "Check every Note Type, Template, and Field — makes everything editable."
        )
        disable_all_btn = QPushButton("Disable All")
        disable_all_btn.setToolTip(
            "Uncheck every Note Type, Template, and Field — disables editing for everything."
        )
        bulk_row.addWidget(enable_all_btn)
        bulk_row.addWidget(disable_all_btn)
        bulk_row.addStretch()
        excl_layout.addLayout(bulk_row)

        enable_all_btn.clicked.connect(
            lambda: self._set_all_items(Qt.CheckState.Checked)
        )
        disable_all_btn.clicked.connect(
            lambda: self._set_all_items(Qt.CheckState.Unchecked)
        )

        layout.addWidget(excl_grp)
        layout.addStretch()

        scroll_area.setWidget(content_widget)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_area)

    def _populate_tree(self):
        try:
            models = self.mw.col.models.all()
        except Exception:
            return
        for model in models:
            nt_item = QTreeWidgetItem(self.tree, [model["name"]])
            model_id = str(model["id"])
            nt_item.setData(0, MODEL_ID_ROLE, model_id)
            nt_item.setData(0, ENTRY_KIND_ROLE, "model")
            nt_item.setCheckState(
                0,
                Qt.CheckState.Unchecked
                if utils.note_type_disabled(model, self.config)
                else Qt.CheckState.Checked,
            )
            t_root = QTreeWidgetItem(nt_item, ["Templates"])
            t_root.setData(0, MODEL_ID_ROLE, model_id)
            t_root.setData(0, ENTRY_KIND_ROLE, "templates_root")
            for template in model["tmpls"]:
                t_item = QTreeWidgetItem(t_root, [template["name"]])
                t_item.setData(0, MODEL_ID_ROLE, model_id)
                t_item.setData(0, ENTRY_KIND_ROLE, "template")
                t_item.setData(0, ENTRY_ORD_ROLE, int(template.get("ord", -1)))
                t_item.setCheckState(
                    0,
                    Qt.CheckState.Unchecked
                    if utils.template_disabled(model, template, self.config)
                    else Qt.CheckState.Checked,
                )
            f_root = QTreeWidgetItem(nt_item, ["Fields"])
            f_root.setData(0, MODEL_ID_ROLE, model_id)
            f_root.setData(0, ENTRY_KIND_ROLE, "fields_root")
            for field in model["flds"]:
                f_item = QTreeWidgetItem(f_root, [field["name"]])
                f_item.setData(0, MODEL_ID_ROLE, model_id)
                f_item.setData(0, ENTRY_KIND_ROLE, "field")
                f_item.setData(0, ENTRY_ORD_ROLE, int(field.get("ord", -1)))
                f_item.setCheckState(
                    0,
                    Qt.CheckState.Unchecked
                    if utils.field_disabled(model, field, self.config)
                    else Qt.CheckState.Checked,
                )

    def _set_all_items(self, state: Qt.CheckState) -> None:
        def apply_to_item(item: QTreeWidgetItem) -> None:
            item.setCheckState(0, state)
            for idx in range(item.childCount()):
                apply_to_item(item.child(idx))

        for idx in range(self.tree.topLevelItemCount()):
            apply_to_item(self.tree.topLevelItem(idx))

    def update_config(self, config: Dict[str, Any]):
        new_exclusions = {}
        new_exclusions_v2 = {}
        for idx in range(self.tree.topLevelItemCount()):
            note_type_item = self.tree.topLevelItem(idx)
            model_id = str(note_type_item.data(0, MODEL_ID_ROLE) or "")
            disabled = note_type_item.checkState(0) == Qt.CheckState.Unchecked
            
            # Helper to get unchecked children from a root item
            def get_unchecked_data(root_item_idx, data_role=None):
                root = note_type_item.child(root_item_idx)
                results = []
                for i in range(root.childCount()):
                    child = root.child(i)
                    if child.checkState(0) == Qt.CheckState.Unchecked:
                        if data_role is not None:
                            val = child.data(0, data_role)
                            if val is not None:
                                results.append(val)
                        else:
                            results.append(child.text(0))
                return results

            disabled_templates = get_unchecked_data(0)
            disabled_template_ords = get_unchecked_data(0, ENTRY_ORD_ROLE)
            disabled_fields = get_unchecked_data(1)
            disabled_field_ords = get_unchecked_data(1, ENTRY_ORD_ROLE)

            if disabled or disabled_templates or disabled_fields:
                new_exclusions[note_type_item.text(0)] = {
                    "disabled": disabled,
                    "templates": disabled_templates,
                    "fields": disabled_fields,
                }
            if model_id and (disabled or disabled_template_ords or disabled_field_ords):
                new_exclusions_v2[model_id] = {
                    "disabled": disabled,
                    "templates": disabled_template_ords,
                    "fields": disabled_field_ords,
                }

        config.update({
            "auto_enable": self.auto_cb.isChecked(),
            "show_outline": self.outline_cb.isChecked(),
            "trigger_modifier": self.mod_combo.currentText(),
            "trigger_action": self.act_combo.currentText(),
            "show_review_button": self.show_review_button_cb.isChecked(),
            "enable_undo": self.enable_undo_cb.isChecked(),
            "undo_style": UNDO_STYLE_MAP.get(self.undo_style_combo.currentText(), "per_field"),
            "separate_editor_preferences": self.separate_prefs_cb.isChecked(),
            "preload_add_window": self.preload_add_cb.isChecked(),
            "exclusions": new_exclusions,
            "exclusions_v2": new_exclusions_v2,
        })
