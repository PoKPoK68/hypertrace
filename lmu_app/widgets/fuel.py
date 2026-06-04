"""Fuel & Virtual Energy overlay — compact, text inside bars."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget

BASE_W, BASE_H = 180, 60   # compact default size


class FuelWidget(BaseWidget):
    WIDGET_NAME = "Fuel & Virtual Energy"
    CONFIG_SCHEMA = [
        {"key": "scale", "label": "Size (%)", "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 100},
    ]

    C_BG         = QColor(10, 10, 10, 210)
    C_BORDER     = QColor(55, 55, 55, 180)
    C_TRACK      = QColor(35, 35, 35)
    # Fuel = darker blue, VE = green
    C_FUEL_OK    = QColor(30, 100, 210)
    C_FUEL_WARN  = QColor(210, 150, 0)
    C_FUEL_CRIT  = QColor(210, 40, 40)
    C_VE         = QColor(50, 190, 80)

    def __init__(self, reader: DataReader, **kw):
        self._fuel     = 0.
        self._fuel_cap = 100.
        self._ve       = 0.
        self._scale    = 1.0
        super().__init__(reader, update_hz=10, **kw)
        self.setFixedSize(BASE_W, BASE_H)

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_params(self, params: dict) -> None:
        self._scale = int(params.get("scale", 100)) / 100.0
        self.setFixedSize(int(BASE_W * self._scale), int(BASE_H * self._scale))
        self.update()

    def on_data(self, snapshot: LMUSnapshot):
        v = snapshot.vehicle
        self._fuel     = v.fuel
        self._fuel_cap = max(1., v.fuel_capacity)
        self._ve       = v.virtual_energy
        self.update()

    def paintEvent(self, _):
        s = self._scale
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(s, s)
        w, h = BASE_W, BASE_H

        p.setBrush(self.C_BG); p.setPen(QPen(self.C_BORDER, 1))
        p.drawRoundedRect(0, 0, w, h, 8, 8)

        pad, bh, gap = 6, 22, 4
        bw = w - pad * 2

        # Fuel bar
        ratio_f = max(0., min(1., self._fuel / self._fuel_cap))
        col_f   = (self.C_FUEL_CRIT if ratio_f < 0.10 else
                   self.C_FUEL_WARN if ratio_f < 0.25 else self.C_FUEL_OK)
        y1 = pad
        self._bar(p, pad, y1, bw, bh, ratio_f, col_f)
        p.setFont(QFont("Monospace", max(6, int(8 * s)), QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 210))
        p.drawText(pad + 4, y1, bw // 2, bh, Qt.AlignmentFlag.AlignVCenter, "FUEL")
        p.drawText(pad, y1, bw - 4, bh,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                   f"{self._fuel:.1f} L")

        # VE bar
        ratio_ve = max(0., min(1., self._ve))
        y2 = pad + bh + gap
        self._bar(p, pad, y2, bw, bh, ratio_ve, self.C_VE)
        p.setFont(QFont("Monospace", max(6, int(8 * s)), QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 210))
        p.drawText(pad + 4, y2, bw // 2, bh, Qt.AlignmentFlag.AlignVCenter, "VE")
        p.drawText(pad, y2, bw - 4, bh,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                   f"{ratio_ve * 100:.0f}%")

        p.end()

    def _bar(self, p: QPainter, x, y, w, h, ratio, col):
        p.setBrush(self.C_TRACK); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(x, y, w, h, 4, 4)
        fw = int(w * ratio)
        if fw > 2:
            g = QLinearGradient(x, y, x + fw, y)
            g.setColorAt(0., col); g.setColorAt(1., col.lighter(130))
            p.setBrush(g)
            p.drawRoundedRect(x, y, fw, h, 4, 4)
