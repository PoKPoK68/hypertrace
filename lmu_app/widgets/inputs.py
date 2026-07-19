"""Pedals overlay — throttle/brake/clutch bars + history trace."""
from __future__ import annotations
import time
from collections import deque

from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy

from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.utils.theme import T, label_font, num_font
from lmu_app.widgets.base import BaseWidget, DEFAULT_SCALE

_BAR_W   = 16
_BAR_H   = 52
_BAR_Y0  = 19
_BAR_GAP = 6
_PAD     = 10

_TRACE_W   = 72
_TRACE_GAP = 8

BASE_H = 88

_TRACE_COLORS = [QColor(T.THROTTLE), QColor(T.BRAKE), QColor(T.CLUTCH)]


class InputsWidget(BaseWidget):
    WIDGET_NAME = "Pedals"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Appearance"},
        {"key": "opacity",        "label": "Opacity (%)",        "type": "int",
         "min": 0,  "max": 100, "step": 5,  "default": 85},
        {"key": "scale",          "label": "Size (%)",           "type": "int",
         "min": 50, "max": 250, "step": 5,  "default": 100},
        {"type": "separator", "label": "Pedals"},
        {"key": "show_throttle",  "label": "Throttle",           "type": "bool", "default": True},
        {"key": "show_brake",     "label": "Brake",              "type": "bool", "default": True},
        {"key": "show_clutch",    "label": "Clutch",             "type": "bool", "default": True},
        {"type": "separator", "label": "Trace"},
        {"key": "show_trace",         "label": "Show trace",         "type": "bool", "default": True},
        {"key": "trace_throttle",     "label": "  Throttle trace",   "type": "bool", "default": True,
         "show_if": ("show_trace", True)},
        {"key": "trace_brake",        "label": "  Brake trace",      "type": "bool", "default": True,
         "show_if": ("show_trace", True)},
        {"key": "trace_clutch",       "label": "  Clutch trace",     "type": "bool", "default": True,
         "show_if": ("show_trace", True)},
        {"key": "trace_seconds",      "label": "Trace duration (s)", "type": "int",
         "min": 2,  "max": 30,  "step": 1,  "default": 5,
         "show_if": ("show_trace", True)},
    ]

    stream_hz = 30   # render at 30 fps in stream mode

    def __init__(self, reader: DataReader, **kw):
        self._t = self._b = self._c = 0.0
        self._scale          = DEFAULT_SCALE / 100.0
        self._show_trace      = True
        self._trace_throttle  = True
        self._trace_brake     = True
        self._trace_clutch    = True
        self._trace_secs      = 5.0
        self._show_throttle   = True
        self._show_brake      = True
        self._show_clutch     = True
        self._trace_buf: deque[tuple[float, float, float, float]] = deque()
        super().__init__(reader, update_hz=60, **kw)
        # Steady 60 fps repaint, decoupled from the 50 Hz data feed: the trace
        # scrolls by wall-clock time so motion stays smooth even when no new
        # sample arrived this frame (avoids the 60/50 Hz beat stutter).
        self._render_timer = QTimer(self)
        self._render_timer.setInterval(16)
        self._render_timer.timeout.connect(self.update)
        self._apply_size()

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def start(self) -> None:
        super().start()
        self._render_timer.start()

    def stop(self) -> None:
        self._render_timer.stop()
        super().stop()

    def _n_bars(self) -> int:
        return sum([self._show_throttle, self._show_brake, self._show_clutch])

    def _bars_w(self) -> int:
        n = self._n_bars()
        if n == 0:
            return 0
        return n * (_BAR_W + _BAR_GAP) - _BAR_GAP

    def _base_w(self) -> int:
        n = self._n_bars()
        has_bars = n > 0
        if self._show_trace and not has_bars:
            return _PAD + _TRACE_W + _PAD
        if self._show_trace and has_bars:
            return _PAD + _TRACE_W + _TRACE_GAP + self._bars_w() + _PAD
        return _PAD + self._bars_w() + _PAD

    def _bar_x0(self) -> int:
        if self._show_trace:
            return _PAD + _TRACE_W + _TRACE_GAP
        return _PAD

    def _apply_size(self) -> None:
        self.setFixedSize(int(self._base_w() * self._scale),
                          int(BASE_H * self._scale))

    def apply_params(self, params: dict) -> None:
        self._scale          = int(params.get("scale",          DEFAULT_SCALE)) / 100.0
        self._opacity        = max(0, min(100, int(params.get("opacity", 85))))
        self._show_trace     = bool(params.get("show_trace",     True))
        self._trace_throttle = bool(params.get("trace_throttle", True))
        self._trace_brake    = bool(params.get("trace_brake",    True))
        self._trace_clutch   = bool(params.get("trace_clutch",   True))
        self._trace_secs     = max(2, min(30, int(params.get("trace_seconds", 5))))
        self._show_throttle  = bool(params.get("show_throttle",  True))
        self._show_brake     = bool(params.get("show_brake",     True))
        self._show_clutch    = bool(params.get("show_clutch",    True))
        self._apply_size()
        self.update()

    def on_data(self, snap: LMUSnapshot):
        v = snap.vehicle
        t = max(0., min(1., v.throttle))
        b = max(0., min(1., v.brake))
        c = max(0., min(1., v.clutch))
        now = time.monotonic()
        self._trace_buf.append((now, t, b, c))
        cutoff = now - self._trace_secs - 1.0
        while self._trace_buf and self._trace_buf[0][0] < cutoff:
            self._trace_buf.popleft()
        if t != self._t or b != self._b or c != self._c:
            self._t, self._b, self._c = t, b, c
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)
        self._draw_panel(p, self._base_w(), BASE_H)
        if self._show_trace:
            self._draw_trace(p)
        self._draw_bars(p)
        p.end()

    def _draw_trace(self, p: QPainter):
        tx = _PAD
        ty = _BAR_Y0
        tw = _TRACE_W
        th = _BAR_H

        p.setBrush(T.TRACK)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(tx, ty, tw, th, 3, 3)

        if len(self._trace_buf) < 2:
            return

        now    = time.monotonic()
        cutoff = now - self._trace_secs
        samples = [(ts, t, b, c) for ts, t, b, c in self._trace_buf if ts >= cutoff]
        if len(samples) < 2:
            return

        active_channels = []
        if self._trace_clutch:
            active_channels.append((2, _TRACE_COLORS[2]))
        if self._trace_throttle:
            active_channels.append((0, _TRACE_COLORS[0]))
        if self._trace_brake:
            active_channels.append((1, _TRACE_COLORS[1]))

        p.setClipRect(QRectF(tx, ty, tw, th))
        for ch, color in active_channels:
            pen = QPen(color, 1.5, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            pts = []
            for ts, t, b, c in samples:
                val = (t, b, c)[ch]
                x = tx + tw * (ts - cutoff) / self._trace_secs
                y = ty + th * (1.0 - val)
                pts.append(QPointF(x, y))
            for i in range(len(pts) - 1):
                p.drawLine(pts[i], pts[i + 1])
        p.setClipping(False)

    def _draw_bars(self, p: QPainter):
        items = []
        if self._show_throttle:
            items.append(("T", self._t, QColor(T.THROTTLE)))
        if self._show_brake:
            items.append(("B", self._b, QColor(T.BRAKE)))
        if self._show_clutch:
            items.append(("C", self._c, QColor(T.CLUTCH)))

        bar_x0 = self._bar_x0()
        for i, (lbl, val, col) in enumerate(items):
            x = bar_x0 + i * (_BAR_W + _BAR_GAP)
            y, bw, bh = _BAR_Y0, _BAR_W, _BAR_H

            p.setBrush(T.TRACK)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, bw, bh, 3, 3)

            fh = int(bh * val)
            if fh > 0:
                p.setBrush(col)
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(x, y + bh - fh, bw, fh, 3, 3)

            val_col = QColor(T.DIM) if val == 0 else col.lighter(150)
            p.setFont(num_font(7))
            p.setPen(val_col)
            p.drawText(QRectF(x - 2, y - 15, bw + 4, 14),
                       Qt.AlignmentFlag.AlignCenter, str(int(val * 100)))

            p.setFont(label_font(6))
            p.setPen(QColor(T.DIM))
            p.drawText(QRectF(x, y + bh + 2, bw, 10),
                       Qt.AlignmentFlag.AlignCenter, lbl)
