"""Inputs overlay — throttle/brake/clutch bars + rotating steering wheel."""
from __future__ import annotations
import math
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget

BASE_W, BASE_H = 162, 105

_BAR_W, _BAR_H, _BAR_X0, _BAR_Y0, _BAR_GAP = 20, 72, 10, 14, 6
# Wheel closer to bars (bars end at x≈82, wheel starts at x≈88)
_WHEEL_CX, _WHEEL_CY, _WHEEL_R              = 120, 50, 30
_WHEEL_MAX                                   = 270


class InputsWidget(BaseWidget):
    WIDGET_NAME = "Inputs"
    CONFIG_SCHEMA = [
        {"key": "scale", "label": "Size (%)", "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 100},
    ]

    C_BG    = QColor(10, 10, 10, 210)
    C_BDR   = QColor(55, 55, 55, 180)
    C_TRACK = QColor(35, 35, 35)
    C_LBL   = QColor(110, 110, 110)
    C_T     = QColor(60, 210, 90)
    C_B     = QColor(220, 55, 55)
    C_C     = QColor(70, 140, 220)
    C_RIM   = QColor(190, 190, 190)
    C_SPOKE = QColor(150, 150, 150)
    C_HUB   = QColor(120, 120, 120)

    def __init__(self, reader: DataReader, **kw):
        self._t = self._b = self._c = self._s = 0.0
        self._scale = 1.0
        super().__init__(reader, update_hz=60, **kw)
        self.setFixedSize(BASE_W, BASE_H)

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_params(self, params: dict) -> None:
        self._scale = int(params.get("scale", 100)) / 100.0
        self.setFixedSize(int(BASE_W * self._scale), int(BASE_H * self._scale))
        self.update()

    def on_data(self, snap: LMUSnapshot):
        v = snap.vehicle
        self._t = max(0., min(1., v.throttle))
        self._b = max(0., min(1., v.brake))
        self._c = max(0., min(1., v.clutch))
        self._s = max(-1., min(1., v.steering))
        self.update()

    def paintEvent(self, _):
        s = self._scale
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(s, s)
        p.setBrush(self.C_BG); p.setPen(QPen(self.C_BDR, 1))
        p.drawRoundedRect(0, 0, BASE_W, BASE_H, 8, 8)
        self._draw_bars(p)
        self._draw_wheel(p)
        p.end()

    def _draw_bars(self, p: QPainter):
        items = [("T", self._t, self.C_T), ("B", self._b, self.C_B), ("C", self._c, self.C_C)]
        p.setFont(QFont("Monospace", 8, QFont.Weight.Bold))
        for i, (lbl, val, col) in enumerate(items):
            x = _BAR_X0 + i * (_BAR_W + _BAR_GAP)
            y, bw, bh = _BAR_Y0, _BAR_W, _BAR_H
            p.setBrush(self.C_TRACK); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, bw, bh, 3, 3)
            fh = int(bh * val)
            if fh > 0:
                g = QLinearGradient(x, y + bh - fh, x, y + bh)
                g.setColorAt(0., col.lighter(130)); g.setColorAt(1., col)
                p.setBrush(g); p.drawRoundedRect(x, y + bh - fh, bw, fh, 3, 3)
            p.setPen(self.C_LBL if val == 0 else col.lighter(150))
            p.drawText(x-2, y - 13, bw+4, 12, Qt.AlignmentFlag.AlignHCenter,
                       f"{int(val*100)}")
            p.setPen(self.C_LBL)
            p.drawText(x, y + bh + 3, bw, 12, Qt.AlignmentFlag.AlignHCenter, lbl)

    def _draw_wheel(self, p: QPainter):
        cx, cy, r = _WHEEL_CX, _WHEEL_CY, _WHEEL_R
        deg = self._s * _WHEEL_MAX

        p.save()
        p.translate(cx, cy)
        p.rotate(deg)

        # Outer rim
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(self.C_RIM, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(-r, -r, r * 2, r * 2)

        # 2 butterfly spokes at ~30° below horizontal (4 o'clock & 8 o'clock)
        # avoids the "Mercedes logo" look of 3 equal spokes
        hub_r    = max(4, r // 5)
        spoke_r  = r - 3
        for deg_spoke in (30, 150):     # 30° from 3 o'clock = 4 o'clock; 150° = 8 o'clock
            rad = math.radians(deg_spoke)
            xe  = int(spoke_r * math.cos(rad))
            ye  = int(spoke_r * math.sin(rad))  # Qt y-axis down, so positive = downward
            xh  = int(hub_r   * math.cos(rad))
            yh  = int(hub_r   * math.sin(rad))
            p.setPen(QPen(self.C_SPOKE, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(xh, yh, xe, ye)

        # Center hub
        p.setBrush(self.C_HUB); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(-hub_r, -hub_r, hub_r * 2, hub_r * 2)

        p.restore()

        # Angle text below wheel (unrotated)
        p.setFont(QFont("Monospace", 8)); p.setPen(self.C_LBL)
        p.drawText(cx - 26, cy + r + 4, 52, 14, Qt.AlignmentFlag.AlignHCenter,
                   f"{int(deg):+.0f}°" if abs(deg) > 1 else "0°")
