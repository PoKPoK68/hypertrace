"""Widget Speed / Gear / RPM bar."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget


class SpeedWidget(BaseWidget):
    WIDGET_NAME = "Speed & Gear"

    COLOR_BG      = QColor(10, 10, 10, 200)
    COLOR_TEXT    = QColor(255, 255, 255)
    COLOR_TEXT_DIM= QColor(150, 150, 150)
    COLOR_RPM     = QColor(80, 200, 120)
    COLOR_RPM_RED = QColor(220, 60, 60)
    COLOR_GEAR    = QColor(255, 200, 0)
    COLOR_BORDER  = QColor(60, 60, 60, 180)
    W, H = 220, 120

    def __init__(self, reader: DataReader, **kw):
        self._speed   = 0.0
        self._gear    = 0
        self._rpm     = 0.0
        self._rpm_max = 9000.0
        super().__init__(reader, update_hz=30, **kw)
        self.setFixedSize(self.W, self.H)

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def on_data(self, snapshot: LMUSnapshot):
        v = snapshot.vehicle
        self._speed   = v.speed_kmh
        self._gear    = v.gear
        self._rpm     = v.rpm
        self._rpm_max = v.rpm_max
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.W, self.H

        p.setBrush(self.COLOR_BG)
        p.setPen(QPen(self.COLOR_BORDER, 1))
        p.drawRoundedRect(0, 0, w, h, 10, 10)

        # RPM bar
        bar_h, bar_y = 10, h - 16
        bar_x, bar_w = 8, w - 16
        ratio   = min(1.0, self._rpm / self._rpm_max) if self._rpm_max > 0 else 0.0
        fill_w  = int(bar_w * ratio)
        p.setBrush(QColor(40, 40, 40)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)
        p.setBrush(self.COLOR_RPM_RED if ratio >= 0.85 else self.COLOR_RPM)
        p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 3, 3)

        # Speed
        p.setFont(QFont("Monospace", 42, QFont.Weight.Bold))
        p.setPen(self.COLOR_TEXT)
        p.drawText(10, 8, w-80, 70, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   f"{int(self._speed):3d}")
        p.setFont(QFont("Monospace", 11))
        p.setPen(self.COLOR_TEXT_DIM)
        p.drawText(10, 62, 60, 16, Qt.AlignmentFlag.AlignLeft, "km/h")

        # Gear
        p.setFont(QFont("Monospace", 44, QFont.Weight.Bold))
        p.setPen(self.COLOR_GEAR)
        gear_str = {0: "N", -1: "R"}.get(self._gear, str(self._gear))
        p.drawText(w-75, 4, 66, 72,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, gear_str)
        p.end()
