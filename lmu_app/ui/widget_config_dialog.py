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
    QFormLayout,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from lmu_app.config import AppConfig
    from lmu_app.widgets.base import BaseWidget

# Fusion + dark palette (set in main.py) handles spinbox/combobox arrows.
# We only need layout polish + button borders.
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
QLabel#section {
    color: #ffd700; font-weight: bold; font-size: 11px;
    padding-top: 6px;
}
QScrollArea { border: none; }
"""


class WidgetConfigDialog(QDialog):
    """Generic dialog: reads CONFIG_SCHEMA and applies changes live."""

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

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(14, 14, 14, 14)

        title = QLabel(self._widget.WIDGET_NAME)
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffd700; padding-bottom: 4px;")
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        inner = QWidget()
        form  = QFormLayout(inner)
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        saved = self._config.widget_params(self._key)

        for entry in self._schema:
            kind = entry["type"]

            # Section separator — visual only, not a control
            if kind == "separator":
                lbl = QLabel(entry.get("label", ""))
                lbl.setObjectName("section")
                sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
                form.addRow(lbl)
                form.addRow(sep)
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
                ctrl = QSpinBox()
                ctrl.setMinimum(entry.get("min", 0))
                ctrl.setMaximum(entry.get("max", 9999))
                ctrl.setSingleStep(entry.get("step", 1))
                ctrl.setValue(int(current) if current is not None else int(default))
                ctrl.valueChanged.connect(self._apply_live)

            elif kind == "float":
                ctrl = QDoubleSpinBox()
                ctrl.setMinimum(entry.get("min", 0.0))
                ctrl.setMaximum(entry.get("max", 9999.0))
                ctrl.setSingleStep(entry.get("step", 0.1))
                ctrl.setDecimals(entry.get("decimals", 2))
                ctrl.setValue(float(current) if current is not None else float(default))
                ctrl.valueChanged.connect(self._apply_live)

            elif kind == "choice":
                ctrl = QComboBox()
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

            else:
                continue

            self._controls[key] = ctrl
            lbl_w = QLabel(label)
            lbl_w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            form.addRow(lbl_w, ctrl)

        scroll.setWidget(inner)
        root.addWidget(scroll)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _apply_live(self) -> None:
        params = self._collect()
        self._config.set_widget_params(self._key, params)
        self._config.save()
        self._widget.apply_params(params)

    def _collect(self) -> dict:
        result: dict = {}
        for entry in self._schema:
            if entry["type"] == "separator":
                continue
            key  = entry["key"]
            kind = entry["type"]
            ctrl = self._controls.get(key)
            if ctrl is None:
                continue
            if kind == "bool":
                result[key] = ctrl.isChecked()
            elif kind == "int":
                result[key] = ctrl.value()
            elif kind == "float":
                result[key] = ctrl.value()
            elif kind == "choice":
                result[key] = ctrl.currentData()
            elif kind in ("multiselect", "ordered_multiselect"):
                result[key] = ctrl.selected_values()
            elif kind == "color":
                result[key] = ctrl.color_str()
        return result


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
    changed = Signal()
    def __init__(self, options, selected_ordered, parent=None):
        super().__init__(parent)
        self._all_opts = options
        sel_set        = set(selected_ordered)
        self._order    = list(selected_ordered) + [o["value"] for o in options if o["value"] not in sel_set]
        self._checked  = {v: (v in sel_set) for v in self._order}
        self._label    = {o["value"]: o["label"] for o in options}
        self._vl = QVBoxLayout(self); self._vl.setSpacing(2); self._vl.setContentsMargins(0,0,0,0)
        self._rebuild()

    def _rebuild(self):
        while self._vl.count():
            item = self._vl.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for i, v in enumerate(self._order):
            self._add_row(i, v)

    def _add_row(self, i, value):
        row = QWidget(); hl = QHBoxLayout(row)
        hl.setContentsMargins(0,0,0,0); hl.setSpacing(4)
        cb = QCheckBox(self._label.get(value, value))
        cb.setChecked(self._checked.get(value, False))
        cb.toggled.connect(lambda chk, v=value: self._on_check(v, chk))
        up = QPushButton("▲"); up.setObjectName("arrow"); up.setEnabled(i > 0)
        dn = QPushButton("▼"); dn.setObjectName("arrow"); dn.setEnabled(i < len(self._order)-1)
        up.clicked.connect(lambda _, idx=i: self._move(idx, -1))
        dn.clicked.connect(lambda _, idx=i: self._move(idx, +1))
        hl.addWidget(cb, 1); hl.addWidget(up); hl.addWidget(dn)
        self._vl.addWidget(row)

    def _on_check(self, value, checked):
        self._checked[value] = checked; self.changed.emit()

    def _move(self, idx, direction):
        j = idx + direction
        if 0 <= j < len(self._order):
            self._order[idx], self._order[j] = self._order[j], self._order[idx]
            self._rebuild(); self.changed.emit()

    def selected_values(self): return [v for v in self._order if self._checked.get(v, False)]


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
        c = QColorDialog.getColor(self._color, self);
        if c.isValid(): self._color=c; self._refresh(); self.color_changed.emit()
    def set_color(self, s):
        c = QColor(s)
        if c.isValid(): self._color=c; self._refresh()
    def color_str(self): return self._color.name()
