"""lmu_app/ui/main_window.py — Tabbed main control panel."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from lmu_app.utils.class_colors import CLASS_ENTRIES

if TYPE_CHECKING:
    from lmu_app.config import AppConfig
    from lmu_app.widgets.base import BaseWidget


# ---------------------------------------------------------------------------
# ON / OFF toggle button
# ---------------------------------------------------------------------------

_SS_ON  = ("QPushButton { background:#1a5c1a; color:#88ff88; "
           "border:1px solid #3a8a3a; border-radius:10px; "
           "font-weight:bold; font-size:10px; }"
           "QPushButton:hover { background:#1e6e1e; }")
_SS_OFF = ("QPushButton { background:#5c1a1a; color:#ff8888; "
           "border:1px solid #8a3a3a; border-radius:10px; "
           "font-weight:bold; font-size:10px; }"
           "QPushButton:hover { background:#6e1e1e; }")


class _OnOffBtn(QPushButton):
    """Pill-shaped ON / OFF toggle button."""

    def __init__(self, enabled: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(enabled)
        self.setFixedSize(46, 22)
        self._refresh(enabled)
        self.toggled.connect(self._refresh)

    def _refresh(self, checked: bool) -> None:
        self.setText("ON" if checked else "OFF")
        self.setStyleSheet(_SS_ON if checked else _SS_OFF)


# ---------------------------------------------------------------------------
# Sliding lock / unlock toggle
# ---------------------------------------------------------------------------

class _LockToggle(QWidget):
    """Animated pill toggle: FREE (left) ↔ LOCK (right)."""

    toggled = Signal(bool)   # True = locked

    _W, _H = 52, 28

    def __init__(self, locked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._locked = locked
        self._t = 1.0 if locked else 0.0   # animation progress 0=free, 1=locked
        self._timer = QTimer(self)
        self._timer.setInterval(14)
        self._timer.timeout.connect(self._step)
        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Lock / unlock overlay positions")

    def set_locked(self, locked: bool) -> None:
        if locked != self._locked:
            self._locked = locked
            self._timer.start()
        else:
            self._t = 1.0 if locked else 0.0
            self.update()

    def _step(self) -> None:
        target = 1.0 if self._locked else 0.0
        self._t += (target - self._t) * 0.20
        if abs(self._t - target) < 0.008:
            self._t = target
            self._timer.stop()
        self.update()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._locked = not self._locked
            self._timer.start()
            self.toggled.emit(self._locked)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H, t = self._W, self._H, self._t
        pad = 3
        knob_d = H - pad * 2
        travel = W - pad * 2 - knob_d

        # Track background: dark green (free) → dark gold (locked)
        r = int(22 + 46 * t)
        g = int(50 +  8 * t)
        b = int(22 - 14 * t)
        p.setBrush(QColor(r, g, b))
        p.setPen(QPen(QColor(70, 65, 40), 1))
        p.drawRoundedRect(0, 0, W, H, H // 2, H // 2)

        # Sliding knob
        knob_x = pad + int(travel * t)
        kr = int(195 + 25 * t)
        kg = int(215 - 35 * t)
        kb = int(175 - 80 * t)
        p.setBrush(QColor(kr, kg, kb))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(knob_x, pad, knob_d, knob_d)

        # Padlock icon on the knob
        self._draw_padlock(p, knob_x + knob_d // 2, pad + knob_d // 2, knob_d, t > 0.5)
        p.end()

    def _draw_padlock(self, p: QPainter, cx: int, cy: int,
                      size: int, locked: bool) -> None:
        s = max(1, size // 5)
        # Body
        bw = s * 2 + 2
        bh = s + s // 2 + 2
        bx = cx - bw // 2
        by = cy
        p.setBrush(QColor(35, 28, 18))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(bx, by, bw, bh, 1, 1)
        # Keyhole dot
        kr = max(1, s // 2)
        p.setBrush(QColor(190, 160, 60))
        p.drawEllipse(cx - kr, by + bh // 2 - kr, kr * 2, kr * 2)
        # Shackle arc
        arc_r = s + 1
        arc_rect = QRect(cx - arc_r, by - arc_r * 2 + 1, arc_r * 2, arc_r * 2)
        p.setPen(QPen(QColor(35, 28, 18), max(1, s // 2 + 1),
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        if locked:
            p.drawArc(arc_rect, 0, 180 * 16)
        else:
            p.drawArc(arc_rect, 40 * 16, 140 * 16)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QWidget):
    """Tabbed control panel."""

    def __init__(
        self,
        config: AppConfig,
        widget_entries: list[tuple[str, BaseWidget]],
    ) -> None:
        super().__init__()
        self._config  = config
        self._entries = widget_entries

        self.setWindowTitle("LMU App")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(290)

        self._toggles: dict[str, _OnOffBtn] = {}
        self._lock_toggle: _LockToggle | None = None
        self._merge_btn: _OnOffBtn | None = None

        self._setup_ui()
        self._apply_lock_state()
        self._broadcast_class_colors()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(8, 8, 8, 8)

        title = QLabel("LMU App")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffd700; padding: 2px 0;")
        root.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._make_overlays_tab(), "Overlays")
        tabs.addTab(self._make_class_colors_tab(), "Class Colors")
        root.addWidget(tabs)

    # ------------------------------------------------------------------ Tab 1

    def _make_overlays_tab(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setSpacing(4)
        vl.setContentsMargins(6, 8, 6, 8)

        for key, widget in self._entries:
            vl.addWidget(self._make_row(key, widget))

        # Merge button — only shown when both calc widgets are registered
        fc = self._find_widget("fuel_calc")
        vc = self._find_widget("ve_calc")
        if fc and vc:
            vl.addWidget(_sep())
            merge_row = QWidget()
            merge_hl  = QHBoxLayout(merge_row)
            merge_hl.setContentsMargins(0, 1, 0, 1)
            merge_hl.setSpacing(6)
            merge_hl.addWidget(QLabel("Merge Fuel & VE calc"), 1)
            self._merge_btn = _OnOffBtn(self._config.merge_calc)
            self._merge_btn.toggled.connect(self._on_merge_toggled)
            merge_hl.addWidget(self._merge_btn)
            vl.addWidget(merge_row)

        vl.addWidget(_sep())

        self._garage_cb = QCheckBox("Hide overlays in garage")
        self._garage_cb.setChecked(self._config.hide_in_garage)
        self._garage_cb.toggled.connect(self._toggle_garage_hide)
        vl.addWidget(self._garage_cb)

        vl.addWidget(_sep())

        self._lock_toggle = _LockToggle(self._config.locked)
        self._lock_toggle.toggled.connect(self._on_lock_toggled)
        vl.addWidget(self._lock_toggle, alignment=Qt.AlignmentFlag.AlignLeft)

        vl.addStretch()
        return w

    def _make_row(self, key: str, widget: BaseWidget) -> QWidget:
        row = QWidget()
        hl  = QHBoxLayout(row)
        hl.setContentsMargins(0, 1, 0, 1)
        hl.setSpacing(6)

        lbl = QLabel(widget.WIDGET_NAME)
        hl.addWidget(lbl, 1)

        if widget.CONFIG_SCHEMA:
            cfg_btn = QPushButton("⚙")
            cfg_btn.setFixedSize(22, 22)
            cfg_btn.setToolTip(f"Configure {widget.WIDGET_NAME}")
            cfg_btn.clicked.connect(lambda _, k=key, w=widget: self._open_config(k, w))
            hl.addWidget(cfg_btn)

        btn = _OnOffBtn(self._config.widget_enabled(key))
        btn.toggled.connect(lambda checked, k=key, w=widget: self._on_toggle(k, w, checked))
        self._toggles[key] = btn
        hl.addWidget(btn)

        return row

    # ------------------------------------------------------------------ Tab 2

    def _make_class_colors_tab(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setSpacing(6)
        vl.setContentsMargins(6, 8, 6, 8)

        info = QLabel("Background color per car class.\nApplied automatically from class name.")
        info.setStyleSheet("color: #888; font-size: 11px;")
        info.setWordWrap(True)
        vl.addWidget(info)

        self._class_btns: dict[str, _ClassColorBtn] = {}
        saved = self._config.class_colors()

        for entry in CLASS_ENTRIES:
            row = QWidget()
            hl  = QHBoxLayout(row)
            hl.setContentsMargins(0, 2, 0, 2)
            hl.setSpacing(8)

            lbl = QLabel(entry["label"])
            lbl.setMinimumWidth(120)
            btn = _ClassColorBtn(saved.get(entry["key"], entry["default"]))
            btn.color_changed.connect(
                lambda k=entry["key"]: self._on_class_color_change(k)
            )
            self._class_btns[entry["key"]] = btn
            hl.addWidget(lbl, 1)
            hl.addWidget(btn)
            vl.addWidget(row)

        vl.addWidget(_sep())

        reset_btn = QPushButton("Reset to defaults")
        reset_btn.clicked.connect(self._reset_class_colors)
        vl.addWidget(reset_btn)
        vl.addStretch()
        return w

    # ------------------------------------------------------------------ Handlers

    def _on_toggle(self, key: str, widget: BaseWidget, enabled: bool) -> None:
        self._config.set_widget_enabled(key, enabled)
        self._config.save()
        widget.start() if enabled else widget.stop()

    def closeEvent(self, event) -> None:
        QApplication.instance().quit()
        event.accept()

    def _open_config(self, key: str, widget: BaseWidget) -> None:
        from lmu_app.ui.widget_config_dialog import WidgetConfigDialog
        WidgetConfigDialog(self._config, key, widget, parent=self).exec()

    def _on_lock_toggled(self, locked: bool) -> None:
        self._config.locked = locked
        self._config.save()
        for _, widget in self._entries:
            widget.set_locked(locked)

    def _toggle_garage_hide(self, checked: bool) -> None:
        self._config.hide_in_garage = checked
        self._config.save()
        for _, widget in self._entries:
            widget.set_hide_in_garage(checked)

    def _apply_lock_state(self) -> None:
        locked = self._config.locked
        for _, widget in self._entries:
            widget.set_locked(locked)
        if self._lock_toggle is not None:
            self._lock_toggle.set_locked(locked)

    def _find_widget(self, key: str):
        return next((w for k, w in self._entries if k == key), None)

    def _on_merge_toggled(self, enabled: bool) -> None:
        self._config.merge_calc = enabled
        self._config.save()
        fc = self._find_widget("fuel_calc")
        vc = self._find_widget("ve_calc")
        if fc:
            fc.set_merge(enabled)
        if vc:
            vc.set_merge(enabled)

    def _on_class_color_change(self, key: str) -> None:
        colors = self._config.class_colors()
        colors[key] = self._class_btns[key].color_str()
        self._config.set_class_colors(colors)
        self._config.save()
        self._broadcast_class_colors()

    def _reset_class_colors(self) -> None:
        self._config.set_class_colors({})
        self._config.save()
        for entry in CLASS_ENTRIES:
            self._class_btns[entry["key"]].set_color(entry["default"])
        self._broadcast_class_colors()

    def _broadcast_class_colors(self) -> None:
        colors = self._config.class_colors()
        for _, widget in self._entries:
            try:
                widget.apply_class_colors(colors)
            except AttributeError:
                pass


# ---------------------------------------------------------------------------

class _ClassColorBtn(QPushButton):
    color_changed = Signal()

    def __init__(self, hex_color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        c = QColor(hex_color)
        self._color = c if c.isValid() else QColor("#404040")
        self.setFixedHeight(24)
        self._refresh()
        self.clicked.connect(self._pick)

    def _refresh(self) -> None:
        h = self._color.name()
        lum = (self._color.red()*299 + self._color.green()*587 + self._color.blue()*114) // 1000
        txt = "#000" if lum > 128 else "#fff"
        self.setStyleSheet(
            f"QPushButton {{ background:{h}; color:{txt}; border:1px solid #666; "
            f"padding:2px 8px; border-radius:3px; }}"
        )
        self.setText(h.upper())

    def _pick(self) -> None:
        c = QColorDialog.getColor(self._color, self)
        if c.isValid():
            self._color = c
            self._refresh()
            self.color_changed.emit()

    def set_color(self, hex_color: str) -> None:
        c = QColor(hex_color)
        if c.isValid():
            self._color = c
            self._refresh()

    def color_str(self) -> str:
        return self._color.name()


def _sep() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Plain)
    return line
