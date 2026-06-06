"""Speed / Gear / RPM bar overlay."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget

BASE_W, BASE_H = 155, 80


class SpeedWidget(BaseWidget):
    WIDGET_NAME = "Speed & Gear"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Window"},
        {"key": "opacity", "label": "Opacity (%)",  "type": "int",
         "min": 0,  "max": 100, "step": 5, "default": 85},
        {"key": "scale",   "label": "Size (%)",     "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 75},
    ]

    COLOR_TEXT     = QColor(255, 255, 255)
    COLOR_TEXT_DIM = QColor(150, 150, 150)
    COLOR_RPM      = QColor(80, 200, 120)
    COLOR_RPM_RED  = QColor(220, 60, 60)
    COLOR_GEAR     = QColor(255, 200, 0)
    COLOR_BORDER   = QColor(60, 60, 60, 180)

    def __init__(self, reader: DataReader, **kw):
        self._speed   = 0.0
        self._gear    = 0
        self._rpm     = 0.0
        self._rpm_max = 9000.0
        self._scale   = 0.75
        super().__init__(reader, update_hz=30, **kw)
        self.setFixedSize(int(BASE_W * self._scale), int(BASE_H * self._scale))

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_params(self, params: dict) -> None:
        self._scale   = int(params.get("scale", 75)) / 100.0
        self._opacity = max(0, min(100, int(params.get("opacity", 85))))
        self.setFixedSize(int(BASE_W * self._scale), int(BASE_H * self._scale))
        self.update()

    def on_data(self, snapshot: LMUSnapshot):
        v = snapshot.vehicle
        self._speed   = v.speed_kmh
        self._gear    = v.gear
        self._rpm     = v.rpm
        self._rpm_max = v.rpm_max
        self.update()

    def paintEvent(self, _):
        s = self._scale
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(s, s)
        w, h = BASE_W, BASE_H

        p.setBrush(QColor(10, 10, 10, self._bg_alpha()))
        p.setPen(self._border_pen())
        p.drawRoundedRect(0, 0, w, h, 8, 8)

        # RPM bar
        bar_h, bar_y = 8, h - 14
        bar_x, bar_w = 8, w - 16
        ratio  = min(1.0, self._rpm / self._rpm_max) if self._rpm_max > 0 else 0.0
        fill_w = int(bar_w * ratio)
        p.setBrush(QColor(40, 40, 40)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)
        p.setBrush(self.COLOR_RPM_RED if ratio >= 0.85 else self.COLOR_RPM)
        p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 3, 3)

        # Speed
        p.setFont(QFont("Monospace", 32, QFont.Weight.Bold))
        p.setPen(self.COLOR_TEXT)
        p.drawText(8, 4, w - 60, 48,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   f"{int(self._speed):3d}")
        p.setFont(QFont("Monospace", 8))
        p.setPen(self.COLOR_TEXT_DIM)
        p.drawText(8, 50, 50, 12, Qt.AlignmentFlag.AlignLeft, "km/h")

        # Gear
        p.setFont(QFont("Monospace", 34, QFont.Weight.Bold))
        p.setPen(self.COLOR_GEAR)
        gear_str = {0: "N", -1: "R"}.get(self._gear, str(self._gear))
        p.drawText(w - 54, 2, 46, 50,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, gear_str)
        p.end()
