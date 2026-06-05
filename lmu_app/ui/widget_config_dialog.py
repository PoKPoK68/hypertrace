"""lmu_app/ui/widget_config_dialog.py — Widget config dialog (live update)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from lmu_app.config import AppConfig
    from lmu_app.widgets.base import BaseWidget

_STYLE = """
QDialog, QWidget { font-family: "Segoe UI", sans-serif; font-size: 12px; }
QSpinBox, QDoubleSpinBox, QComboBox { min-height: 28px; }
QPushButton {
    padding: 4px 14px; border-radius: 4px;
    border: 1px solid #555;
}
QPushButton:hover { background: #3a3a3a; }
QPushButton#arrow {
    padding: 0px; min-width: 26px; max-width: 26px;
    min-height: 24px; max-height: 24px; font-size: 13px;
    font-weight: bold;
}
QPushButton#icon_btn {
    padding: 0px; min-width: 26px; max-width: 26px;
    min-height: 26px; max-height: 26px; font-size: 13px;
}
QScrollArea { border: none; }
"""


class WidgetConfigDialog(QDialog):
    """Generic dialog: reads CONFIG_SCHEMA and applies changes live.

    Separator entries create collapsible sections; spin/combo boxes
    ignore mouse-wheel to avoid accidental value changes while scrolling.
    """

    def __init__(
        self,
        config: AppConfig,
        key: str,
        widget: BaseWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config  = config
        self._key     = key
        self._widget  = widget
        self._schema  = widget.CONFIG_SCHEMA
        self._controls: dict[str, QWidget] = {}

        self.setWindowTitle(f"Configure — {widget.WIDGET_NAME}")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(_STYLE)
        self.setMinimumWidth(400)
        self._setup_ui()

    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(14, 14, 14, 14)

        title = QLabel(self._widget.WIDGET_NAME)
        title.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #ffd700; padding-bottom: 4px;"
        )
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        inner = QWidget()
        vl    = QVBoxLayout(inner)
        vl.setSpacing(2)
        vl.setContentsMargins(0, 0, 0, 0)

        saved = self._config.widget_params(self._key)

        # Entries before the first separator go into a plain pre-form
        pre_widget = QWidget()
        pre_form   = QFormLayout(pre_widget)
        pre_form.setSpacing(8)
        pre_form.setContentsMargins(0, 0, 0, 0)
        pre_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        vl.addWidget(pre_widget)
        current_form: QFormLayout = pre_form

        for entry in self._schema:
            kind = entry.get("type")

            if kind == "separator":
                section      = _CollapsibleSection(entry.get("label", ""))
                current_form = section.form()
                vl.addWidget(section)
                continue

            if "key" not in entry:
                continue

            key     = entry["key"]
            label   = entry["label"]
            default = entry.get("default")
            current = saved.get(key, default)
            ctrl: QWidget

            if kind == "bool":
                ctrl = QCheckBox()
                ctrl.setChecked(bool(current) if current is not None else bool(default))
                ctrl.toggled.connect(self._apply_live)

            elif kind == "int":
                ctrl = _NoScrollSpin()
                ctrl.setMinimum(entry.get("min", 0))
                ctrl.setMaximum(entry.get("max", 9999))
                ctrl.setSingleStep(entry.get("step", 1))
                ctrl.setValue(int(current) if current is not None else int(default))
                ctrl.valueChanged.connect(self._apply_live)

            elif kind == "float":
                ctrl = _NoScrollDoubleSpin()
                ctrl.setMinimum(entry.get("min", 0.0))
                ctrl.setMaximum(entry.get("max", 9999.0))
                ctrl.setSingleStep(entry.get("step", 0.1))
                ctrl.setDecimals(entry.get("decimals", 2))
                ctrl.setValue(float(current) if current is not None else float(default))
                ctrl.valueChanged.connect(self._apply_live)

            elif kind == "choice":
                ctrl    = _NoScrollCombo()
                cur_val = current if current is not None else default
                for i, opt in enumerate(entry.get("options", [])):
                    ctrl.addItem(opt["label"], opt["value"])
                    if opt["value"] == cur_val:
                        ctrl.setCurrentIndex(i)
                ctrl.currentIndexChanged.connect(self._apply_live)

            elif kind == "multiselect":
                ctrl = _MultiSelectWidget(
                    entry["options"],
                    list(current) if current is not None else list(default),
                )
                ctrl.changed.connect(self._apply_live)

            elif kind == "ordered_multiselect":
                ctrl = _OrderedMultiSelectWidget(
                    entry["options"],
                    list(current) if current is not None else list(default),
                )
                ctrl.changed.connect(self._apply_live)

            elif kind == "color":
                ctrl = _ColorButton(
                    current if (current and QColor(current).isValid()) else default
                )
                ctrl.color_changed.connect(self._apply_live)

            elif kind == "filepath":
                ctrl = _FilePathWidget(current or "")
                ctrl.changed.connect(self._apply_live)

            else:
                continue

            self._controls[key] = ctrl
            if label:
                lbl_w = QLabel(label)
                lbl_w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                current_form.addRow(lbl_w, ctrl)
            else:
                current_form.addRow(ctrl)

        # Hide the pre-form area if nothing was added there
        if pre_form.rowCount() == 0:
            pre_widget.hide()

        # Link show_keys visibility controls to their ordered_multiselect widget
        for entry in self._schema:
            if entry.get("type") != "ordered_multiselect":
                continue
            show_keys = entry.get("show_keys", {})
            if not show_keys:
                continue
            ctrl = self._controls.get(entry["key"])
            if ctrl is None:
                continue
            value_to_ctrl: dict[str, QCheckBox] = {}
            for col_value, show_key in show_keys.items():
                bool_ctrl = self._controls.get(show_key)
                if isinstance(bool_ctrl, QCheckBox):
                    value_to_ctrl[col_value] = bool_ctrl
            if value_to_ctrl:
                ctrl.set_visibility_controls(value_to_ctrl)

        vl.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    # ------------------------------------------------------------------

    def _apply_live(self) -> None:
        params = self._collect()
        self._config.set_widget_params(self._key, params)
        self._config.save()
        self._widget.apply_params(params)

    def _collect(self) -> dict:
        result: dict = {}
        for entry in self._schema:
            if "key" not in entry:
                continue
            key  = entry["key"]
            kind = entry["type"]
            ctrl = self._controls.get(key)
            if ctrl is None:
                continue
            if kind == "bool":
                result[key] = ctrl.isChecked()
            elif kind in ("int", "float"):
                result[key] = ctrl.value()
            elif kind == "choice":
                result[key] = ctrl.currentData()
            elif kind in ("multiselect", "ordered_multiselect"):
                result[key] = ctrl.selected_values()
            elif kind == "color":
                result[key] = ctrl.color_str()
            elif kind == "filepath":
                result[key] = ctrl.path()
        return result


# ---------------------------------------------------------------------------
# No-scroll wrappers (prevent scroll from changing values while navigating)

class _NoScrollSpin(QSpinBox):
    def wheelEvent(self, e): e.ignore()

class _NoScrollDoubleSpin(QDoubleSpinBox):
    def wheelEvent(self, e): e.ignore()

class _NoScrollCombo(QComboBox):
    def wheelEvent(self, e): e.ignore()


# ---------------------------------------------------------------------------
# Collapsible section header

class _CollapsibleSection(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title

        vl = QVBoxLayout(self)
        vl.setSpacing(0)
        vl.setContentsMargins(0, 6, 0, 0)

        self._btn = QPushButton(f"▾  {title}")
        self._btn.setCheckable(True)
        self._btn.setChecked(True)
        self._btn.setStyleSheet(
            "QPushButton { text-align: left; padding: 3px 8px; font-weight: bold; "
            "font-size: 11px; color: #ffd700; background: #252525; "
            "border: none; border-bottom: 1px solid #3a3a3a; }"
            "QPushButton:hover { background: #2e2e2e; }"
        )
        self._btn.toggled.connect(self._on_toggle)
        vl.addWidget(self._btn)

        self._body = QWidget()
        self._form = QFormLayout(self._body)
        self._form.setSpacing(8)
        self._form.setContentsMargins(4, 6, 0, 6)
        self._form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        vl.addWidget(self._body)

    def _on_toggle(self, checked: bool) -> None:
        self._body.setVisible(checked)
        self._btn.setText(f"{'▾' if checked else '▸'}  {self._title}")

    def form(self) -> QFormLayout:
        return self._form


# ---------------------------------------------------------------------------

class _MultiSelectWidget(QWidget):
    changed = Signal()
    def __init__(self, options, selected, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self); layout.setSpacing(3); layout.setContentsMargins(0,0,0,0)
        self._checks: list[tuple[str, QCheckBox]] = []
        for opt in options:
            cb = QCheckBox(opt["label"]); cb.setChecked(opt["value"] in selected)
            cb.toggled.connect(self.changed); layout.addWidget(cb)
            self._checks.append((opt["value"], cb))
    def selected_values(self): return [v for v, cb in self._checks if cb.isChecked()]


class _OrderedMultiSelectWidget(QWidget):
    """Vertical ordered list — arrow buttons only, no checkboxes.
    Column visibility is controlled by separate bool keys linked via set_visibility_controls().
    selected_values() returns ALL items in their current order (filtering done by widget).
    """
    changed = Signal()

    def __init__(self, options, selected_ordered, parent=None):
        super().__init__(parent)
        valid         = {o["value"] for o in options}
        sel_filtered  = [v for v in selected_ordered if v in valid]
        sel_set       = set(sel_filtered)
        self._order   = sel_filtered + [o["value"] for o in options if o["value"] not in sel_set]
        self._label   = {o["value"]: o["label"] for o in options}
        self._vis_ctrls: dict[str, QCheckBox] = {}
        self._vl = QVBoxLayout(self)
        self._vl.setSpacing(2)
        self._vl.setContentsMargins(0, 0, 0, 0)
        self._rebuild()

    def set_visibility_controls(self, value_to_ctrl: dict) -> None:
        """Link each column value to its show/hide QCheckBox; rebuilds on toggle."""
        self._vis_ctrls = value_to_ctrl
        for ctrl in value_to_ctrl.values():
            ctrl.toggled.connect(lambda _: self._rebuild())
        self._rebuild()

    def _is_visible(self, value: str) -> bool:
        ctrl = self._vis_ctrls.get(value)
        return ctrl is None or ctrl.isChecked()

    def _rebuild(self):
        while self._vl.count():
            item = self._vl.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        visible = [v for v in self._order if self._is_visible(v)]
        for i, v in enumerate(visible):
            self._add_row(v, i == 0, i == len(visible) - 1)

    def _add_row(self, value: str, is_first: bool, is_last: bool):
        row = QWidget()
        hl  = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)
        lbl = QLabel(self._label.get(value, value))
        lbl.setMinimumWidth(80)
        up = QPushButton("▲"); up.setObjectName("arrow"); up.setEnabled(not is_first)
        dn = QPushButton("▼"); dn.setObjectName("arrow"); dn.setEnabled(not is_last)
        up.clicked.connect(lambda _, v=value: self._move_value(v, -1))
        dn.clicked.connect(lambda _, v=value: self._move_value(v, +1))
        hl.addWidget(lbl, 1)
        hl.addWidget(up)
        hl.addWidget(dn)
        self._vl.addWidget(row)

    def _move_value(self, value: str, direction: int) -> None:
        visible = [v for v in self._order if self._is_visible(v)]
        if value not in visible:
            return
        idx = visible.index(value)
        j   = idx + direction
        if 0 <= j < len(visible):
            i_full = self._order.index(value)
            j_full = self._order.index(visible[j])
            self._order[i_full], self._order[j_full] = self._order[j_full], self._order[i_full]
            self._rebuild()
            self.changed.emit()

    def selected_values(self):
        return list(self._order)


class _FilePathWidget(QWidget):
    changed = Signal()

    def __init__(self, path: str = "", parent=None):
        super().__init__(parent)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(4)
        self._edit = QLineEdit(path)
        self._edit.setReadOnly(True)
        self._edit.setPlaceholderText("Default (built-in)")
        browse = QPushButton("Browse")
        browse.setFixedHeight(26)
        browse.clicked.connect(self._browse)
        clear = QPushButton("✕")
        clear.setObjectName("icon_btn")
        clear.setFixedSize(26, 26)
        clear.setToolTip("Clear — revert to default wheel image")
        clear.clicked.connect(self._clear)
        hl.addWidget(self._edit, 1)
        hl.addWidget(browse)
        hl.addWidget(clear)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select wheel image", "",
            "Images (*.png *.jpg *.bmp *.svg)"
        )
        if path:
            self._edit.setText(path)
            self.changed.emit()

    def _clear(self):
        self._edit.clear()
        self.changed.emit()

    def path(self) -> str:
        return self._edit.text()


class _ColorButton(QPushButton):
    color_changed = Signal()
    def __init__(self, color_str="#333333", parent=None):
        super().__init__(parent)
        c = QColor(color_str); self._color = c if c.isValid() else QColor("#333333")
        self._refresh(); self.clicked.connect(self._pick)
    def _refresh(self):
        h = self._color.name()
        lum = (self._color.red()*299+self._color.green()*587+self._color.blue()*114)//1000
        txt = "#000" if lum > 128 else "#fff"
        self.setStyleSheet(f"QPushButton{{background:{h};color:{txt};border:1px solid #666;padding:3px 8px;border-radius:3px;}}")
        self.setText(h.upper())
    def _pick(self):
        c = QColorDialog.getColor(self._color, self)
        if c.isValid(): self._color=c; self._refresh(); self.color_changed.emit()
    def set_color(self, s):
        c = QColor(s)
        if c.isValid(): self._color=c; self._refresh()
    def color_str(self): return self._color.name()
