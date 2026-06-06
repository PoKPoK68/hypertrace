"""Fuel & Virtual Energy overlay — compact, text inside bars.

If the car has no VE system (VE stays 0 for 10 consecutive ticks),
the VE row is hidden and the widget shrinks from the top so the
bottom edge stays fixed on screen.
"""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget

BASE_W, BASE_H = 180, 60   # full height (both bars)
_PAD, _BH, _GAP = 6, 22, 4  # layout constants (matches paintEvent)


def _total_h(has_ve: bool) -> int:
    return BASE_H if has_ve else _PAD + _BH + _PAD


class FuelWidget(BaseWidget):
    WIDGET_NAME = "Fuel & Virtual Energy"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Window"},
        {"key": "opacity", "label": "Opacity (%)", "type": "int",
         "min": 0,  "max": 100, "step": 5, "default": 85},
        {"key": "scale",   "label": "Size (%)",    "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 85},
    ]

    C_BG         = QColor(10, 10, 10, 210)
    C_TRACK      = QColor(35, 35, 35)
    C_FUEL_OK    = QColor(30, 100, 210)
    C_FUEL_WARN  = QColor(210, 150, 0)
    C_FUEL_CRIT  = QColor(210, 40, 40)
    C_VE         = QColor(50, 190, 80)

    def __init__(self, reader: DataReader, **kw):
        self._fuel      = 0.
        self._fuel_cap  = 100.
        self._ve        = 0.
        self._scale     = 0.85
        self._has_ve    = True      # assume VE until 10 zeros prove otherwise
        self._ve_zeros  = 0
        super().__init__(reader, update_hz=10, **kw)
        self.setFixedSize(int(BASE_W * self._scale),
                          int(_total_h(self._has_ve) * self._scale))

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_params(self, params: dict) -> None:
        self._scale   = int(params.get("scale",   85)) / 100.0
        self._opacity = max(0, min(100, int(params.get("opacity", 85))))
        self.setFixedSize(int(BASE_W * self._scale),
                          int(_total_h(self._has_ve) * self._scale))
        self.update()

    def on_data(self, snapshot: LMUSnapshot):
        v = snapshot.vehicle
        self._fuel     = v.fuel
        self._fuel_cap = max(1., v.fuel_capacity)
        self._ve       = v.virtual_energy

        # Detect VE presence after 10 stable zero-readings
        if self._has_ve and self._ve <= 0.001:
            self._ve_zeros += 1
            if self._ve_zeros >= 10:
                self._change_ve(False)
        elif self._ve > 0.001:
            self._ve_zeros = 0
            if not self._has_ve:
                self._change_ve(True)

        self.update()

    def _change_ve(self, has_ve: bool) -> None:
        old_h = self.height()
        self._has_ve = has_ve
        new_h = int(_total_h(has_ve) * self._scale)
        self.setFixedSize(int(BASE_W * self._scale), new_h)
        # Shrink from top: keep bottom edge fixed
        delta = old_h - new_h
        self.move(self.x(), self.y() + delta)
        if self._on_position_changed:
            self._on_position_changed(self.x(), self.y())

    def paintEvent(self, _):
        s = self._scale
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(s, s)
        w = BASE_W
        h = _total_h(self._has_ve)

        p.setBrush(QColor(10, 10, 10, self._bg_alpha()))
        p.setPen(self._border_pen())
        p.drawRoundedRect(0, 0, w, h, 8, 8)

        bw = w - _PAD * 2

        # Fuel bar
        ratio_f = max(0., min(1., self._fuel / self._fuel_cap))
        col_f   = (self.C_FUEL_CRIT if ratio_f < 0.10 else
                   self.C_FUEL_WARN if ratio_f < 0.25 else self.C_FUEL_OK)
        self._bar(p, _PAD, _PAD, bw, _BH, ratio_f, col_f)
        p.setFont(QFont("Monospace", max(6, int(8 * s)), QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 210))
        p.drawText(_PAD + 4, _PAD, bw // 2, _BH, Qt.AlignmentFlag.AlignVCenter, "FUEL")
        p.drawText(_PAD, _PAD, bw - 4, _BH,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                   f"{self._fuel:.1f} L")

        # VE bar — only when car has VE system
        if self._has_ve:
            ratio_ve = max(0., min(1., self._ve))
            y2 = _PAD + _BH + _GAP
            self._bar(p, _PAD, y2, bw, _BH, ratio_ve, self.C_VE)
            p.setFont(QFont("Monospace", max(6, int(8 * s)), QFont.Weight.Bold))
            p.setPen(QColor(255, 255, 255, 210))
            p.drawText(_PAD + 4, y2, bw // 2, _BH, Qt.AlignmentFlag.AlignVCenter, "VE")
            p.drawText(_PAD, y2, bw - 4, _BH,
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
