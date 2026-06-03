"""Widget Inputs : throttle, brake, clutch (barres verticales) + angle volant."""
from __future__ import annotations
import math
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget


class InputsWidget(BaseWidget):
    WIDGET_NAME = "Inputs"
    W, H = 280, 160
    BAR_W, BAR_H, BAR_X0, BAR_Y0, BAR_GAP = 36, 110, 16, 22, 14
    WHEEL_CX, WHEEL_CY, WHEEL_R, WHEEL_MAX = 210, 75, 52, 270

    C_BG     = QColor(10, 10, 10, 210)
    C_BORDER = QColor(55, 55, 55, 180)
    C_TRACK  = QColor(35, 35, 35)
    C_LABEL  = QColor(120, 120, 120)
    C_T      = QColor(60, 210, 90)
    C_B      = QColor(220, 55, 55)
    C_C      = QColor(70, 140, 220)

    def __init__(self, reader: DataReader, **kw):
        self._t = self._b = self._c = self._s = 0.0
        super().__init__(reader, update_hz=60, **kw)
        self.setFixedSize(self.W, self.H)

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def on_data(self, snap: LMUSnapshot):
        v = snap.vehicle
        self._t = max(0., min(1., v.throttle))
        self._b = max(0., min(1., v.brake))
        self._c = max(0., min(1., v.clutch))
        self._s = max(-1., min(1., v.steering))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(self.C_BG)
        p.setPen(QPen(self.C_BORDER, 1))
        p.drawRoundedRect(0, 0, self.W, self.H, 10, 10)
        self._bars(p)
        self._wheel(p)
        p.end()

    def _bars(self, p: QPainter):
        items = [("T", self._t, self.C_T), ("B", self._b, self.C_B), ("C", self._c, self.C_C)]
        p.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
        for i, (lbl, val, col) in enumerate(items):
            x = self.BAR_X0 + i * (self.BAR_W + self.BAR_GAP)
            y, bw, bh = self.BAR_Y0, self.BAR_W, self.BAR_H
            p.setBrush(self.C_TRACK); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, bw, bh, 4, 4)
            fh = int(bh * val)
            if fh > 0:
                g = QLinearGradient(x, y + bh - fh, x, y + bh)
                g.setColorAt(0., col.lighter(130)); g.setColorAt(1., col)
                p.setBrush(g); p.drawRoundedRect(x, y + bh - fh, bw, fh, 4, 4)
            p.setPen(self.C_LABEL if val == 0 else col.lighter(160))
            p.drawText(x, y - 16, bw, 14, Qt.AlignmentFlag.AlignHCenter, f"{int(val*100)}")
            p.setPen(self.C_LABEL)
            p.drawText(x, y + bh + 4, bw, 14, Qt.AlignmentFlag.AlignHCenter, lbl)

    def _wheel(self, p: QPainter):
        cx, cy, r = self.WHEEL_CX, self.WHEEL_CY, self.WHEEL_R
        deg = self._s * self.WHEEL_MAX
        rr = r - 3
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(50, 50, 50), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(cx-rr, cy-rr, rr*2, rr*2, int((90+self.WHEEL_MAX)*16), -int(self.WHEEL_MAX*2*16))
        if abs(deg) > 1:
            col = QColor(100, 180, 255) if deg < 0 else QColor(255, 160, 60)
            p.setPen(QPen(col, 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(cx-rr, cy-rr, rr*2, rr*2, int(90*16), -int(deg*16))
        a = math.radians(90 + deg)
        p.setFont(QFont("Monospace", 9)); p.setPen(self.C_LABEL)
        p.drawText(cx-30, cy+r-4, 60, 16, Qt.AlignmentFlag.AlignHCenter,
                   f"{int(deg):+.0f}°" if abs(deg) > 1 else "0°")
