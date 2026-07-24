"""hypertrace/ui/main_window_controls.py — Small reusable widgets for MainWindow.

`_OnOffBtn`, `_CogBtn`, `_LockToggle`, `_sep()`, `_StreamConfigProxy` are moved
here verbatim from main_window.py (v1.0 redesign) — same behavior, same
pixels, just relocated so main_window.py stays focused on tab layout and
wiring. Colors that used to be hardcoded hex now read from `utils.theme.T`
(same values, just centralized).

`_SegmentedControl` and `_ExclusiveOnOffGroup` are new, added to deduplicate
logic that main_window.py used to hand-roll three times over (Broadcast
Battle/Driver/Sectors mutual exclusion) or reimplement ad hoc per use (Tower
mode buttons, Driver/Team name buttons).
"""
from __future__ import annotations

import math

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QWidget

from hypertrace.utils.theme import T

# ---------------------------------------------------------------------------
# Shared QSS snippets
# ---------------------------------------------------------------------------

_SS_ON = (
    f"QPushButton {{ background: {T.TOGGLE_ON}; color: #FFFFFF; "
    f"border: 1px solid {T.TOGGLE_ON}; border-radius: 2px; "
    f"font-weight: bold; font-size: 10px; font-family: '{T.F_TEXT}'; }}"
    f"QPushButton:hover {{ background: {T.TOGGLE_ON_HOVER}; border-color: {T.TOGGLE_ON_HOVER}; }}"
)
_SS_OFF = (
    f"QPushButton {{ background: {T.TOGGLE_OFF}; color: #FFFFFF; "
    f"border: 1px solid {T.TOGGLE_OFF}; border-radius: 2px; "
    f"font-weight: bold; font-size: 10px; font-family: '{T.F_TEXT}'; }}"
    f"QPushButton:hover {{ background: {T.TOGGLE_OFF_HOVER}; border-color: {T.TOGGLE_OFF_HOVER}; }}"
)
_SS_SEG_ON = (
    f"QPushButton {{ background: {T.ACCENT}; color: #000000; "
    f"border: 1px solid {T.ACCENT}; border-radius: 2px; "
    f"font-weight: bold; font-size: 9px; font-family: '{T.F_TEXT}'; padding: 0 4px; }}"
)
_SS_SEG_OFF = (
    f"QPushButton {{ background: rgba(255,255,255,0.06); color: {T.DIM}; "
    f"border: 1px solid rgba(255,255,255,0.12); border-radius: 2px; "
    f"font-size: 9px; font-family: '{T.F_TEXT}'; padding: 0 4px; }}"
    f"QPushButton:hover {{ color: {T.TEXT}; border-color: rgba(255,255,255,0.25); }}"
)
_SS_BTN = (
    f"QPushButton {{ color: {T.DIM}; background: rgba(255,255,255,0.06); "
    f"border: 1px solid rgba(255,255,255,0.12); border-radius: 4px; "
    f"padding: 3px 8px; font-size: 11px; }}"
    f"QPushButton:hover {{ background: rgba(255,255,255,0.12); color: {T.TEXT}; }}"
)
_SS_BTN_DANGER = (
    f"QPushButton {{ color: {T.DANGER}; background: rgba(255,50,50,0.08); "
    f"border: 1px solid rgba(255,80,80,0.20); border-radius: 3px; "
    f"padding: 2px 5px; font-size: 10px; }}"
    f"QPushButton:hover {{ background: rgba(255,50,50,0.20); }}"
)
_SS_BTN_DANGER_ARMED = (
    f"QPushButton {{ color: #FFFFFF; background: {T.DANGER}; "
    f"border: 1px solid {T.DANGER}; border-radius: 3px; "
    f"padding: 2px 5px; font-size: 10px; font-weight: bold; }}"
)


def _sep() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Plain)
    line.setStyleSheet("color: rgba(255,255,255,0.08);")
    return line


# ---------------------------------------------------------------------------
# ON / OFF toggle button
# ---------------------------------------------------------------------------

class _OnOffBtn(QPushButton):
    """Pill-shaped ON / OFF toggle."""

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
# Gear cog icon button
# ---------------------------------------------------------------------------

class _CogBtn(QPushButton):
    """Round button that draws a proper gear cog via QPainterPath."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(22, 22)
        self.setFlat(True)
        self.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 11px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.09); }"
        )

    def paintEvent(self, _) -> None:
        super().paintEvent(_)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_cog(p, 11.0, 11.0, 13.0)
        p.end()

    @staticmethod
    def _draw_cog(p: QPainter, cx: float, cy: float, size: float) -> None:
        n       = 8
        r_out   = size / 2
        r_in    = size * 0.68 / 2
        r_hole  = size * 0.30 / 2
        step    = math.pi / n          # half tooth angular width
        tooth_w = step * 0.55          # flat-top fraction

        path = QPainterPath()
        first = True
        for i in range(n):
            base = 2 * math.pi * i / n
            for ang, r in (
                (base - step + tooth_w, r_in),
                (base - tooth_w,        r_out),
                (base + tooth_w,        r_out),
                (base + step - tooth_w, r_in),
            ):
                x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
                if first:
                    path.moveTo(x, y); first = False
                else:
                    path.lineTo(x, y)
        path.closeSubpath()

        hole = QPainterPath()
        hole.addEllipse(cx - r_hole, cy - r_hole, r_hole * 2, r_hole * 2)
        p.fillPath(path.subtracted(hole), QColor(T.DIM))


# ---------------------------------------------------------------------------
# Sliding lock / unlock toggle
# ---------------------------------------------------------------------------

class _LockToggle(QWidget):
    """Animated pill toggle: FREE (left) ↔ LOCK (right)."""

    toggled = Signal(bool)

    _W, _H = 52, 28
    _M = 2  # dead-space margin around the visible pill, on every side. The
    # widget's own bounding box is _W+2*_M by _H+2*_M — bigger than the pill
    # actually drawn — so the shape never sits flush against the widget's own
    # edge. Whatever exact pixel the pill's outline lands on after display
    # scaling/rounding, there are 2 full pixels of empty space to absorb it
    # before it could ever reach — and get clipped by — the widget boundary.

    def __init__(self, locked: bool = False, parent: QWidget | None = None,
                 tooltip: str = "Lock / unlock overlay positions") -> None:
        super().__init__(parent)
        self._locked = locked
        self._t = 1.0 if locked else 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(14)
        self._timer.timeout.connect(self._step)
        self.setFixedSize(self._W + 2 * self._M, self._H + 2 * self._M)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)

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
        M = self._M
        p.translate(M, M)  # draw the whole pill in its own W x H space; the
        # M-pixel margin around it is handled here once, not smeared through
        # every coordinate below.
        W, H, t = self._W, self._H, self._t
        pad = 3; knob_d = H - pad * 2; travel = W - pad * 2 - knob_d

        def lerp(a, b): return round(a + (b - a) * t)
        lock_rgb = QColor(T.ACCENT)
        track = QColor(
            lerp(T.LOCK_TRACK_OFF[0], lock_rgb.red()),
            lerp(T.LOCK_TRACK_OFF[1], lock_rgb.green()),
            lerp(T.LOCK_TRACK_OFF[2], lock_rgb.blue()),
            lerp(40, 255),
        )
        # Border drawn as two stacked fills (outer ring color, then the
        # track color inset by 1px) instead of a stroked outline — a pen's
        # stroke straddles the path it's drawn on, so half its width has to
        # be clipped or inset just right to stay inside the widget, and that
        # math rendered inconsistently across displays/scaling no matter how
        # it was adjusted. Two plain fills have no such ambiguity: each
        # shape's edge is exactly where it's drawn, pen or no pen.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(*T.LOCK_TRACK_BORDER))
        p.drawRoundedRect(0, 0, W, H, H / 2, H / 2)
        p.setBrush(track)
        p.drawRoundedRect(1, 1, W - 2, H - 2, (H - 2) / 2, (H - 2) / 2)

        knob_x = pad + int(travel * t)
        p.setBrush(QColor(T.ACCENT_INK) if t > 0.5 else QColor(T.TEXT))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(knob_x, pad, knob_d, knob_d)
        p.end()


# ---------------------------------------------------------------------------
# Stream config proxy
# ---------------------------------------------------------------------------

class _StreamConfigProxy:
    """Thin proxy so WidgetConfigDialog can read/write stream widget params."""

    def __init__(self, config, key: str) -> None:
        self._cfg = config
        self._key = key

    def widget_params(self, key: str) -> dict:
        return self._cfg.stream_widget_params(key)

    def set_widget_params(self, key: str, params: dict) -> None:
        self._cfg.set_stream_widget_params(key, params)

    def save(self) -> None:
        self._cfg.save()


# ---------------------------------------------------------------------------
# Segmented control — replaces hand-restyled QPushButton groups
# ---------------------------------------------------------------------------

class _SegmentedControl(QWidget):
    """Row of mutually-exclusive buttons, one active at a time.

    Works for both the 2-way (Driver/Team name, value=bool) and 3-way
    (Tower mode, value=int) cases that main_window.py used to hand-roll with
    manual setStyleSheet() calls scattered across 2 different handlers.
    """

    currentChanged = Signal(object)   # emits the newly-selected value

    def __init__(self, options: list[tuple[str, object]], current: object,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)
        self._buttons: list[tuple[object, QPushButton]] = []
        for label, value in options:
            btn = QPushButton(label)
            btn.setFixedHeight(22)
            btn.clicked.connect(lambda _, v=value: self._select(v, emit=True))
            hl.addWidget(btn)
            self._buttons.append((value, btn))
        self._current = current
        self._restyle()

    def _select(self, value: object, emit: bool) -> None:
        self._current = value
        self._restyle()
        if emit:
            self.currentChanged.emit(value)

    def setCurrent(self, value: object) -> None:
        """Programmatic sync (e.g. loading a preset) — does not emit."""
        self._select(value, emit=False)

    def _restyle(self) -> None:
        for value, btn in self._buttons:
            btn.setStyleSheet(_SS_SEG_ON if value == self._current else _SS_SEG_OFF)


# ---------------------------------------------------------------------------
# Exclusive on/off group — replaces the 3x-duplicated Battle/Driver/Sectors logic
# ---------------------------------------------------------------------------

class _ExclusiveOnOffGroup:
    """Turning one `_OnOffBtn` on turns every other one in the group off.

    Attached *after* each button already has its own toggled->handler
    connection (config write + stream_manager.set_widget_enabled) — forcing a
    sibling off here re-triggers its own toggled signal, so that handler still
    runs and persists the change exactly as it did when this was hand-coded
    into each of the 3 on_toggle methods.
    """

    def __init__(self, buttons: list[_OnOffBtn]) -> None:
        self._buttons = list(buttons)
        for b in self._buttons:
            b.toggled.connect(lambda checked, b=b: self._on_toggled(b, checked))

    def _on_toggled(self, source: _OnOffBtn, checked: bool) -> None:
        if not checked:
            return
        for b in self._buttons:
            if b is not source and b.isChecked():
                b.setChecked(False)
