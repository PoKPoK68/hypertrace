"""lmu_app/ui/widget_config_dialog.py — Widget config dialog (live update)."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter
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

from lmu_app.utils.theme import T, label_font, panel_brush, border_pen

if TYPE_CHECKING:
    from lmu_app.config import AppConfig
    from lmu_app.widgets.base import BaseWidget

_check_svg      = (Path(__file__).parent.parent / "assets" / "check.svg").as_posix()
_chevron_svg    = (Path(__file__).parent.parent / "assets" / "chevron-down.svg").as_posix()
_chevron_up_svg = (Path(__file__).parent.parent / "assets" / "chevron-up.svg").as_posix()
_copy_svg       = (Path(__file__).parent.parent / "assets" / "copy.svg").as_posix()
_paste_svg      = (Path(__file__).parent.parent / "assets" / "paste.svg").as_posix()

_STYLE = f"""
QDialog {{
    background: rgb({T.PANEL_TOP[0]}, {T.PANEL_TOP[1]}, {T.PANEL_TOP[2]});
}}
QWidget {{
    color: {T.TEXT};
    font-family: '{T.F_TEXT}';
    font-size: 12px;
    background: transparent;
}}
QSpinBox, QDoubleSpinBox {{
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 4px;
    color: {T.TEXT};
    min-height: 24px;
    padding: 0 4px;
}}
QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: rgba(255,255,255,0.25);
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    width: 16px;
    border: none;
    border-left: 1px solid rgba(255,255,255,0.12);
    background: rgba(255,255,255,0.06);
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    border-top-right-radius: 3px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    border-bottom-right-radius: 3px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: rgba(255,255,255,0.14);
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({_chevron_up_svg}); width: 8px; height: 6px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({_chevron_svg}); width: 8px; height: 6px;
}}
QLineEdit {{
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 4px;
    color: {T.TEXT};
    min-height: 24px;
    padding: 0 6px;
}}
QLineEdit:hover {{ border-color: rgba(255,255,255,0.25); }}
QComboBox {{
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 4px;
    padding: 2px 6px;
    color: {T.TEXT};
    min-height: 24px;
}}
QComboBox:hover {{ border-color: rgba(255,255,255,0.25); }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{ image: url({_chevron_svg}); width: 10px; height: 6px; }}
QComboBox QAbstractItemView {{
    background: #2A2C30;
    border: 1px solid rgba(255,255,255,0.15);
    selection-background-color: rgba(236,170,67,0.2);
    color: {T.TEXT}; outline: none; padding: 2px;
}}
QCheckBox {{ spacing: 6px; color: {T.DIM}; }}
QCheckBox::indicator {{
    width: 14px; height: 14px; border-radius: 3px;
    border: 1px solid rgba(255,255,255,0.20);
    background: rgba(255,255,255,0.05);
}}
QCheckBox::indicator:checked {{
    background: {T.ACCENT}; border-color: {T.ACCENT};
    image: url({_check_svg});
}}
QPushButton {{
    color: {T.DIM};
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 4px;
    padding: 4px 14px;
    font-size: 11px;
}}
QPushButton:hover {{ background: rgba(255,255,255,0.12); color: {T.TEXT}; }}
QPushButton:disabled {{
    color: rgba(255,255,255,0.18);
    background: rgba(255,255,255,0.02);
    border-color: rgba(255,255,255,0.05);
}}
QPushButton#arrow {{
    padding: 0px; min-width: 26px; max-width: 26px;
    min-height: 24px; max-height: 24px;
}}
QPushButton#icon_btn {{
    padding: 0px; min-width: 26px; max-width: 26px;
    min-height: 26px; max-height: 26px;
    font-size: 13px;
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 6px; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.15); border-radius: 3px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


class WidgetConfigDialog(QDialog):
    """Generic dialog: reads CONFIG_SCHEMA and applies changes live.

    Entries with ``"side_panel": True`` in the schema are placed in a right
    column instead of the main scrollable form — reducing scroll length for
    widgets that have both many settings and a reorder panel (e.g. Standings).
    """

    def __init__(
        self,
        config: AppConfig,
        key: str,
        widget: BaseWidget,
        parent: QWidget | None = None,
        on_copy=None,
        on_paste=None,
    ) -> None:
        super().__init__(parent)
        self._config   = config
        self._key      = key
        self._widget   = widget
        self._schema   = widget.CONFIG_SCHEMA
        self._on_copy  = on_copy
        self._on_paste = on_paste
        self._controls: dict[str, QWidget] = {}
        self._labels:   dict[str, QWidget] = {}

        self.setWindowTitle(f"Configure — {widget.WIDGET_NAME}")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(_STYLE)

        has_side = any(e.get("side_panel") for e in self._schema)
        if has_side:
            self.setMinimumWidth(560)
        else:
            self.setFixedWidth(400)

        self._setup_ui()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setBrush(panel_brush(0, 0, h, 255))
        p.setPen(border_pen(100))
        p.drawRect(0, 0, w, h)
        p.end()

    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(14, 14, 14, 14)

        title = QLabel(self._widget.WIDGET_NAME)
        title.setFont(label_font(12))
        title.setStyleSheet(f"color: {T.ACCENT}; padding-bottom: 4px;")
        root.addWidget(title)

        saved    = self._config.widget_params(self._key)
        has_side = any(e.get("side_panel") for e in self._schema)

        if has_side:
            body    = QWidget()
            body_hl = QHBoxLayout(body)
            body_hl.setContentsMargins(0, 0, 0, 0)
            body_hl.setSpacing(20)
            root.addWidget(body, 1)

            # Left: scrollable main form (all entries without side_panel)
            left_scroll = QScrollArea()
            left_scroll.setWidgetResizable(True)
            left_scroll.setFrameShape(left_scroll.Shape.NoFrame)
            left_inner = QWidget()
            left_vl    = QVBoxLayout(left_inner)
            left_vl.setSpacing(2)
            left_vl.setContentsMargins(0, 0, 8, 0)
            pre_w, pre_form = self._make_pre_form()
            left_vl.addWidget(pre_w)
            current_form = pre_form

            for entry in self._schema:
                if entry.get("side_panel"):
                    continue
                current_form = self._add_entry_to_form(entry, left_vl, current_form, saved)

            if pre_form.rowCount() == 0:
                pre_w.hide()
            left_vl.addStretch()
            left_scroll.setWidget(left_inner)
            body_hl.addWidget(left_scroll, 1)

            # Right: side panel (side_panel entries)
            right_panel = QWidget()
            right_panel.setObjectName("sidePanel")
            right_panel.setStyleSheet(
                "#sidePanel { background: rgba(255,255,255,0.05); border-radius: 4px; }"
            )
            right_panel.setMinimumWidth(155)
            right_vl = QVBoxLayout(right_panel)
            right_vl.setContentsMargins(8, 6, 8, 6)
            right_vl.setSpacing(4)

            for entry in self._schema:
                if not entry.get("side_panel"):
                    continue
                kind = entry.get("type")
                if kind == "separator":
                    lbl = QLabel(entry.get("label", "").upper())
                    lbl.setStyleSheet(
                        f"color: {T.ACCENT}; font-size: 10px; "
                        f"letter-spacing: 1px; font-weight: bold; padding-bottom: 2px;"
                    )
                    right_vl.addWidget(lbl)
                    continue
                ctrl = self._make_ctrl(entry, saved)
                if ctrl is not None:
                    right_vl.addWidget(ctrl)

            right_vl.addStretch()
            body_hl.addWidget(right_panel, 0)

        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(scroll.Shape.NoFrame)
            inner = QWidget()
            vl    = QVBoxLayout(inner)
            vl.setSpacing(2)
            vl.setContentsMargins(0, 0, 8, 0)
            pre_w, pre_form = self._make_pre_form()
            vl.addWidget(pre_w)
            current_form = pre_form

            for entry in self._schema:
                current_form = self._add_entry_to_form(entry, vl, current_form, saved)

            if pre_form.rowCount() == 0:
                pre_w.hide()
            vl.addStretch()
            scroll.setWidget(inner)
            root.addWidget(scroll)

        self._link_show_keys()
        self._setup_show_if()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        _icon_btn_ss = (
            f"QPushButton {{ color: {T.DIM}; background: rgba(255,255,255,0.06); "
            f"border: 1px solid rgba(255,255,255,0.12); border-radius: 4px; "
            f"padding: 4px 8px; font-size: 11px; }}"
            f"QPushButton:hover {{ background: rgba(255,255,255,0.12); color: {T.TEXT}; }}"
        )

        if self._on_copy:
            copy_btn = QPushButton(" Copy")
            copy_btn.setIcon(QIcon(_copy_svg))
            copy_btn.setIconSize(QSize(14, 14))
            copy_btn.setStyleSheet(_icon_btn_ss)
            copy_btn.clicked.connect(self._do_copy)
            btn_row.addWidget(copy_btn)

        if self._on_paste:
            paste_btn = QPushButton(" Paste")
            paste_btn.setIcon(QIcon(_paste_svg))
            paste_btn.setIconSize(QSize(14, 14))
            paste_btn.setStyleSheet(_icon_btn_ss)
            paste_btn.clicked.connect(self._do_paste)
            btn_row.addWidget(paste_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.setStyleSheet(_icon_btn_ss)
        reset_btn.clicked.connect(self._do_reset)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            f"QPushButton {{ color: {T.ACCENT_INK}; background: {T.ACCENT}; "
            f"border: 1px solid {T.ACCENT}; border-radius: 4px; "
            f"padding: 5px 18px; font-weight: bold; font-size: 11px; }}"
            f"QPushButton:hover {{ background: #F0B54A; }}"
        )
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _do_copy(self) -> None:
        if not self._on_copy:
            return
        self._on_copy(dict(self._config.widget_params(self._key)))
        btn = self.sender()
        if isinstance(btn, QPushButton):
            orig_text = btn.text()
            orig_icon = btn.icon()
            btn.setText("✓ Copied!")
            btn.setIcon(QIcon())
            btn.setEnabled(False)
            QTimer.singleShot(1500, lambda b=btn, t=orig_text, i=orig_icon: (
                b.setText(t), b.setIcon(i), b.setEnabled(True)
            ))

    def _do_paste(self) -> None:
        if not self._on_paste:
            return
        self._on_paste()
        self._load_controls(self._config.widget_params(self._key))
        btn = self.sender()
        if isinstance(btn, QPushButton):
            orig_text = btn.text()
            orig_icon = btn.icon()
            btn.setText("✓ Applied!")
            btn.setIcon(QIcon())
            btn.setEnabled(False)
            QTimer.singleShot(1500, lambda b=btn, t=orig_text, i=orig_icon: (
                b.setText(t), b.setIcon(i), b.setEnabled(True)
            ))

    def _load_controls(self, params: dict) -> None:
        for entry in self._schema:
            key  = entry.get("key")
            kind = entry.get("type")
            if not key or key not in params:
                continue
            ctrl = self._controls.get(key)
            if ctrl is None:
                continue
            v = params[key]
            ctrl.blockSignals(True)
            try:
                if kind == "bool":
                    ctrl.setChecked(bool(v))
                elif kind in ("int", "float"):
                    ctrl.setValue(v)
                elif kind == "choice":
                    idx = ctrl.findData(v)
                    if idx >= 0:
                        ctrl.setCurrentIndex(idx)
                elif kind == "color":
                    ctrl.set_color(str(v))
            except Exception:
                pass
            finally:
                ctrl.blockSignals(False)
        self._apply_live()

    # ------------------------------------------------------------------

    @staticmethod
    def _make_pre_form() -> tuple[QWidget, QFormLayout]:
        w = QWidget()
        f = QFormLayout(w)
        f.setSpacing(8)
        f.setContentsMargins(0, 0, 0, 0)
        f.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return w, f

    def _add_entry_to_form(
        self,
        entry: dict,
        vl: QVBoxLayout,
        current_form: QFormLayout,
        saved: dict,
    ) -> QFormLayout:
        """Process one schema entry into the left-panel form. Returns the active form."""
        kind = entry.get("type")
        if kind == "separator":
            section      = _CollapsibleSection(entry.get("label", ""))
            current_form = section.form()
            vl.addWidget(section)
            return current_form

        if "key" not in entry:
            return current_form

        ctrl = self._make_ctrl(entry, saved)
        if ctrl is None:
            return current_form

        label = entry.get("label", "")
        key   = entry.get("key", "")
        if label:
            lbl_w = QLabel(label)
            lbl_w.setStyleSheet(f"color: {T.DIM}; font-size: 11px;")
            lbl_w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            current_form.addRow(lbl_w, ctrl)
            if key:
                self._labels[key] = lbl_w
        else:
            current_form.addRow(ctrl)

        return current_form

    def _make_ctrl(self, entry: dict, saved: dict) -> QWidget | None:
        """Build and register the control widget for one schema entry."""
        kind    = entry.get("type")
        key     = entry.get("key", "")
        default = entry.get("default")
        current = saved.get(key, default) if key else default

        ctrl: QWidget | None = None

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
            color_btn = _ColorButton(
                current if (current and QColor(current).isValid()) else default
            )
            color_btn.color_changed.connect(self._apply_live)
            if default:
                container = QWidget()
                hl = QHBoxLayout(container)
                hl.setContentsMargins(0, 0, 0, 0)
                hl.setSpacing(4)
                hl.addWidget(color_btn, 1)
                reset_btn = QPushButton("Default")
                reset_btn.setFixedHeight(26)
                _def = default
                reset_btn.clicked.connect(lambda _, b=color_btn, d=_def: (b.set_color(d), self._apply_live()))
                hl.addWidget(reset_btn)
                container.color_str = color_btn.color_str
                ctrl = container
            else:
                ctrl = color_btn

        elif kind == "filepath":
            ctrl = _FilePathWidget(current or "")
            ctrl.changed.connect(self._apply_live)

        if ctrl is not None and key:
            self._controls[key] = ctrl

        return ctrl

    def _link_show_keys(self) -> None:
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

    # ------------------------------------------------------------------

    def _setup_show_if(self) -> None:
        for entry in self._schema:
            show_if_key = entry.get("show_if")
            if not show_if_key:
                continue
            key = entry.get("key", "")
            ctrl   = self._controls.get(key)
            lbl    = self._labels.get(key)
            parent = self._controls.get(show_if_key)
            if not isinstance(parent, QCheckBox) or ctrl is None:
                continue

            def _update(checked, c=ctrl, l=lbl):
                c.setVisible(checked)
                if l:
                    l.setVisible(checked)

            parent.toggled.connect(_update)
            _update(parent.isChecked())

    def _do_reset(self) -> None:
        defaults = {
            e["key"]: e["default"]
            for e in self._schema
            if "key" in e and "default" in e
        }
        self._load_controls(defaults)

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
# No-scroll wrappers

class _NoScrollSpin(QSpinBox):
    def wheelEvent(self, e): e.ignore()
    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.lineEdit().setFocus(Qt.FocusReason.OtherFocusReason)

class _NoScrollDoubleSpin(QDoubleSpinBox):
    def wheelEvent(self, e): e.ignore()
    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.lineEdit().setFocus(Qt.FocusReason.OtherFocusReason)

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
            f"QPushButton {{ text-align: left; padding: 4px 8px; font-weight: bold; "
            f"font-size: 11px; color: {T.ACCENT}; background: rgba(255,255,255,0.04); "
            f"border: none; border-bottom: 1px solid rgba(255,255,255,0.08); "
            f"border-radius: 0px; letter-spacing: 1px; }}"
            f"QPushButton:hover {{ background: rgba(255,255,255,0.08); }}"
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
            w = item.widget()
            if w is not None:
                # Unparent immediately: deleteLater() only destroys the row on the
                # next event-loop pass, until then it stays a child of self and
                # keeps painting over the newly built rows.
                w.setParent(None)
                w.deleteLater()
        visible = [v for v in self._order if self._is_visible(v)]
        for i, v in enumerate(visible):
            self._add_row(v, i == 0, i == len(visible) - 1)

    def _add_row(self, value: str, is_first: bool, is_last: bool):
        row = QWidget()
        hl  = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)
        lbl = QLabel(self._label.get(value, value))
        lbl.setStyleSheet(f"color: {T.TEXT}; font-size: 11px;")
        lbl.setMinimumWidth(80)
        up = QPushButton(); up.setObjectName("arrow"); up.setEnabled(not is_first)
        up.setIcon(QIcon(_chevron_up_svg)); up.setIconSize(QSize(8, 6))
        dn = QPushButton(); dn.setObjectName("arrow"); dn.setEnabled(not is_last)
        dn.setIcon(QIcon(_chevron_svg)); dn.setIconSize(QSize(8, 6))
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
        self.setStyleSheet(
            f"QPushButton {{ background:{h}; color:{txt}; "
            f"border: 1px solid rgba(255,255,255,0.20); "
            f"padding: 3px 8px; border-radius: 3px; }}"
        )
        self.setText(h.upper())
    def _pick(self):
        c = QColorDialog.getColor(self._color, self)
        if c.isValid(): self._color=c; self._refresh(); self.color_changed.emit()
    def set_color(self, s):
        c = QColor(s)
        if c.isValid(): self._color=c; self._refresh()
    def color_str(self): return self._color.name()
