"""Widget Fuel & Virtual Energy."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget


class FuelWidget(BaseWidget):
    WIDGET_NAME = "Fuel & Virtual Energy"
    W, H = 240, 100

    C_BG        = QColor(10, 10, 10, 210)
    C_BORDER    = QColor(55, 55, 55, 180)
    C_TRACK     = QColor(35, 35, 35)
    C_LABEL     = QColor(120, 120, 120)
    C_FUEL_OK   = QColor(60, 180, 255)
    C_FUEL_WARN = QColor(255, 180, 0)
    C_FUEL_CRIT = QColor(220, 55, 55)
    C_VE        = QColor(160, 80, 255)

    def __init__(self, reader: DataReader, **kw):
        self._fuel = 0.; self._fuel_cap = 100.
        self._ve = 0.5   # Virtual Energy 0-1, placeholder until reader exposes it
        super().__init__(reader, update_hz=10, **kw)
        self.setFixedSize(self.W, self.H)

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def on_data(self, snap: LMUSnapshot):
        v = snap.vehicle
        self._fuel = v.fuel
        self._fuel_cap = max(1., v.fuel_capacity)
        self._ve = v.virtual_energy
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(self.C_BG); p.setPen(QPen(self.C_BORDER, 1))
        p.drawRoundedRect(0, 0, self.W, self.H, 10, 10)

        pad, bh = 14, 18
        bw = self.W - pad * 2

        # --- Fuel ---
        ratio_f = max(0., min(1., self._fuel / self._fuel_cap))
        col_f = (self.C_FUEL_CRIT if ratio_f < 0.1 else
                 self.C_FUEL_WARN if ratio_f < 0.25 else self.C_FUEL_OK)
        self._bar(p, pad, 24, bw, bh, ratio_f, col_f)
        p.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
        p.setPen(col_f)
        p.drawText(pad, 10, bw // 2, 13, Qt.AlignmentFlag.AlignLeft, "FUEL")
        p.setPen(QColor(220, 220, 220))
        p.drawText(pad, 10, bw, 13, Qt.AlignmentFlag.AlignRight,
                   f"{self._fuel:.1f} L")

        # --- Virtual Energy ---
        ratio_ve = max(0., min(1., self._ve))
        self._bar(p, pad, 62, bw, bh, ratio_ve, self.C_VE)
        p.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
        p.setPen(self.C_VE)
        p.drawText(pad, 48, bw // 2, 13, Qt.AlignmentFlag.AlignLeft, "VIRTUAL ENERGY")
        p.setPen(QColor(220, 220, 220))
        p.drawText(pad, 48, bw, 13, Qt.AlignmentFlag.AlignRight,
                   f"{ratio_ve*100:.1f} %")

        p.end()

    def _bar(self, p: QPainter, x, y, w, h, ratio, col):
        p.setBrush(self.C_TRACK); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(x, y, w, h, 4, 4)
        fw = int(w * ratio)
        if fw > 2:
            g = QLinearGradient(x, y, x + fw, y)
            g.setColorAt(0., col); g.setColorAt(1., col.lighter(130))
            p.setBrush(g); p.drawRoundedRect(x, y, fw, h, 4, 4)
