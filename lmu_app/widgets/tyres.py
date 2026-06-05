"""Tyres overlay — carcass temperature and wear for all 4 tyres."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget

_CELL_W = 72
_PAD    = 6
_GAP    = 4

WIDGET_W = _PAD * 2 + _CELL_W * 2 + _GAP    # 160

C_BG     = QColor(10, 10, 10, 215)
C_BORDER = QColor(55, 55, 55, 180)
C_DIM    = QColor(110, 110, 110)
C_TEXT   = QColor(220, 220, 220)
C_TRACK  = QColor(35, 35, 35)


def _wear_color(w: float) -> QColor:
    if w > 0.6:
        return QColor(60, 220, 80)
    if w > 0.3:
        return QColor(220, 180, 0)
    return QColor(220, 60, 60)


class TyresWidget(BaseWidget):
    WIDGET_NAME = "Tyres"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Display"},
        {"key": "show_temp",     "label": "Show carcass temp",   "type": "bool", "default": True},
        {"key": "show_wear",     "label": "Show wear bar",       "type": "bool", "default": True},
        {"key": "show_wear_pct", "label": "Show wear %",         "type": "bool", "default": True},
        {"key": "show_pressure", "label": "Show pressure (kPa)", "type": "bool", "default": False},
        {"type": "separator", "label": "Temperature range (°C)"},
        {"key": "temp_cold",   "label": "Cold below",   "type": "int", "min": 20,  "max": 100, "step": 5, "default": 60},
        {"key": "temp_opt_lo", "label": "Optimal from", "type": "int", "min": 40,  "max": 120, "step": 5, "default": 80},
        {"key": "temp_opt_hi", "label": "Optimal to",   "type": "int", "min": 60,  "max": 150, "step": 5, "default": 100},
        {"key": "temp_hot",    "label": "Hot above",    "type": "int", "min": 80,  "max": 200, "step": 5, "default": 120},
    ]

    def __init__(self, reader: DataReader,
                 show_temp: bool = True, show_wear: bool = True,
                 show_wear_pct: bool = True, show_pressure: bool = False,
                 temp_cold: int = 60, temp_opt_lo: int = 80,
                 temp_opt_hi: int = 100, temp_hot: int = 120,
                 **kw):
        self._show_temp     = show_temp
        self._show_wear     = show_wear
        self._show_wear_pct = show_wear_pct
        self._show_pressure = show_pressure
        self._t_cold    = temp_cold
        self._t_opt_lo  = temp_opt_lo
        self._t_opt_hi  = temp_opt_hi
        self._t_hot     = temp_hot
        self._temps:     list[float] = [0.0] * 4
        self._wears:     list[float] = [1.0] * 4
        self._pressures: list[float] = [0.0] * 4
        super().__init__(reader, update_hz=10, **kw)
        self._h = self._compute_h()
        self.setFixedSize(WIDGET_W, self._h)

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _compute_h(self) -> int:
        wear_row = self._show_wear or self._show_wear_pct
        rows = sum([self._show_temp, wear_row, self._show_pressure])
        cell_h = max(1, rows) * 16 + 4
        return _PAD * 2 + cell_h * 2 + _GAP

    def apply_params(self, params: dict) -> None:
        self._show_temp     = bool(params.get("show_temp",     True))
        self._show_wear     = bool(params.get("show_wear",     True))
        self._show_wear_pct = bool(params.get("show_wear_pct", True))
        self._show_pressure = bool(params.get("show_pressure", False))
        self._t_cold    = int(params.get("temp_cold",   60))
        self._t_opt_lo  = int(params.get("temp_opt_lo", 80))
        self._t_opt_hi  = int(params.get("temp_opt_hi", 100))
        self._t_hot     = int(params.get("temp_hot",    120))
        self._h = self._compute_h()
        self.setFixedSize(WIDGET_W, self._h)
        self.update()

    def on_data(self, snap: LMUSnapshot) -> None:
        self._temps     = list(snap.tyres.temp_carcass)
        self._wears     = list(snap.tyres.wear)
        self._pressures = list(snap.tyres.pressure)
        self.update()

    def _temp_color(self, t: float) -> QColor:
        if t <= 0:
            return C_DIM
        if t < self._t_cold:
            return QColor(80, 140, 255)
        if t < self._t_opt_lo:
            f = (t - self._t_cold) / max(1, self._t_opt_lo - self._t_cold)
            return QColor(int(80 - 80 * f), int(140 + 80 * f), int(255 - 175 * f))
        if t <= self._t_opt_hi:
            return QColor(60, 220, 80)
        if t < self._t_hot:
            f = (t - self._t_opt_hi) / max(1, self._t_hot - self._t_opt_hi)
            return QColor(int(60 + 195 * f), int(220 - 160 * f), int(80 - 60 * f))
        return QColor(255, 60, 60)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        H = self._h
        cell_h = (H - 2 * _PAD - _GAP) // 2

        p.setBrush(C_BG); p.setPen(QPen(C_BORDER, 1))
        p.drawRoundedRect(0, 0, WIDGET_W, H, 8, 8)

        for i, (col, row) in enumerate([(0, 0), (1, 0), (0, 1), (1, 1)]):
            x = _PAD + col * (_CELL_W + _GAP)
            y = _PAD + row * (cell_h + _GAP)
            self._draw_tyre(p, x, y, i)

        p.end()

    def _draw_tyre(self, p: QPainter, x: int, y: int, idx: int):
        temp  = self._temps[idx]     if idx < len(self._temps)     else 0.0
        wear  = self._wears[idx]     if idx < len(self._wears)     else 1.0
        pres  = self._pressures[idx] if idx < len(self._pressures) else 0.0

        ty = y

        if self._show_temp:
            c   = self._temp_color(temp)
            txt = f"{temp:.0f}°C" if temp > 0 else "---"
            p.setFont(QFont("Monospace", 9, QFont.Weight.Bold)); p.setPen(c)
            p.drawText(x, ty, _CELL_W, 14,
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, txt)
            ty += 16

        if self._show_wear:
            c   = _wear_color(wear)
            pct = wear * 100
            bar_area = _CELL_W - (28 if self._show_wear_pct else 0)
            bar_w    = max(0, int(bar_area * wear))
            p.setBrush(C_TRACK); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, ty + 3, bar_area, 8, 2, 2)
            if bar_w > 0:
                p.setBrush(c)
                p.drawRoundedRect(x, ty + 3, bar_w, 8, 2, 2)
            if self._show_wear_pct:
                p.setFont(QFont("Monospace", 7)); p.setPen(c)
                p.drawText(x + _CELL_W - 26, ty, 26, 14,
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                           f"{pct:.0f}%")
            ty += 16
        elif self._show_wear_pct:
            c = _wear_color(wear)
            p.setFont(QFont("Monospace", 9, QFont.Weight.Bold)); p.setPen(c)
            p.drawText(x, ty, _CELL_W, 14,
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f"{wear * 100:.0f}%")
            ty += 16

        if self._show_pressure:
            txt = f"{pres:.1f} kPa" if pres > 0 else "---"
            p.setFont(QFont("Monospace", 8)); p.setPen(C_TEXT)
            p.drawText(x, ty, _CELL_W, 14,
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, txt)
