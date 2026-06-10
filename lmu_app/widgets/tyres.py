"""Tyres overlay — 4 vertical wear bars (2×2) colored by temperature — Direction A."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy

from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.utils.theme import T, label_font, num_font
from lmu_app.widgets.base import BaseWidget

_BAR_W = 33   # 100% at font 7 bold ≈ 28px + ~5px margin total
_BAR_H = 52
_PAD   = 5
_GAP_X = 6
_GAP_Y = 6

WIDGET_W = _PAD * 2 + _BAR_W * 2 + _GAP_X   # 82
WIDGET_H = _PAD * 2 + _BAR_H * 2 + _GAP_Y   # 120

_LABELS = ["FL", "FR", "RL", "RR"]

_POSITIONS = [
    (_PAD,                    _PAD),
    (_PAD + _BAR_W + _GAP_X, _PAD),
    (_PAD,                    _PAD + _BAR_H + _GAP_Y),
    (_PAD + _BAR_W + _GAP_X, _PAD + _BAR_H + _GAP_Y),
]


class TyresWidget(BaseWidget):
    WIDGET_NAME = "Tyres"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Appearance"},
        {"key": "opacity", "label": "Opacity (%)", "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 85},
        {"key": "scale",   "label": "Size (%)",    "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 100},
        {"type": "separator", "label": "Display"},
        {"key": "show_temp",     "label": "Show temperature (°C)", "type": "bool", "default": True},
        {"key": "show_wear_pct", "label": "Show wear %",           "type": "bool", "default": True},
        {"type": "separator", "label": "Temperature range (°C)"},
        {"key": "temp_cold",   "label": "Cold below",   "type": "int",
         "min": 20, "max": 100, "step": 5, "default": 60},
        {"key": "temp_opt_lo", "label": "Optimal from", "type": "int",
         "min": 40, "max": 120, "step": 5, "default": 80},
        {"key": "temp_opt_hi", "label": "Optimal to",   "type": "int",
         "min": 60, "max": 150, "step": 5, "default": 100},
        {"key": "temp_hot",    "label": "Hot above",    "type": "int",
         "min": 80, "max": 200, "step": 5, "default": 120},
    ]

    def __init__(self, reader: DataReader,
                 show_temp: bool = True, show_wear_pct: bool = True,
                 temp_cold: int = 60, temp_opt_lo: int = 80,
                 temp_opt_hi: int = 100, temp_hot: int = 120,
                 **kw):
        self._show_temp     = show_temp
        self._show_wear_pct = show_wear_pct
        self._scale         = 1.0
        self._opacity       = 85
        self._t_cold        = temp_cold
        self._t_opt_lo      = temp_opt_lo
        self._t_opt_hi      = temp_opt_hi
        self._t_hot         = temp_hot
        self._temps:  list[float] = [0.0] * 4
        self._wears:  list[float] = [1.0] * 4
        super().__init__(reader, update_hz=10, **kw)
        self.setFixedSize(WIDGET_W, WIDGET_H)

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_params(self, params: dict) -> None:
        self._show_temp     = bool(params.get("show_temp",     True))
        self._show_wear_pct = bool(params.get("show_wear_pct", True))
        self._scale         = int(params.get("scale", 100)) / 100.0
        self._opacity       = max(0, min(100, int(params.get("opacity", 85))))
        self._t_cold        = int(params.get("temp_cold",   60))
        self._t_opt_lo      = int(params.get("temp_opt_lo", 80))
        self._t_opt_hi      = int(params.get("temp_opt_hi", 100))
        self._t_hot         = int(params.get("temp_hot",    120))
        self.setFixedSize(int(WIDGET_W * self._scale), int(WIDGET_H * self._scale))
        self.update()

    def on_data(self, snap: LMUSnapshot) -> None:
        self._temps = list(snap.tyres.temp_carcass)
        self._wears = list(snap.tyres.wear)
        self.update()

    def _temp_color(self, t: float) -> QColor:
        if t <= 0: return QColor(T.DIM)
        if t < self._t_cold:
            return QColor(80, 140, 255)
        if t < self._t_opt_lo:
            f = (t - self._t_cold) / max(1, self._t_opt_lo - self._t_cold)
            return QColor(int(80 - 80*f), int(140 + 80*f), int(255 - 175*f))
        if t <= self._t_opt_hi:
            return QColor(60, 220, 80)
        if t < self._t_hot:
            f = (t - self._t_opt_hi) / max(1, self._t_hot - self._t_opt_hi)
            return QColor(int(60 + 195*f), int(220 - 160*f), int(80 - 60*f))
        return QColor(255, 60, 60)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)

        self._draw_panel(p, WIDGET_W, WIDGET_H)

        for i, (x, y) in enumerate(_POSITIONS):
            self._draw_tyre(p, x, y, i)
        p.end()

    def _draw_tyre(self, p: QPainter, x: int, y: int, idx: int) -> None:
        wear  = max(0.0, min(1.0, self._wears[idx] if idx < 4 else 1.0))
        temp  =                   self._temps[idx]  if idx < 4 else 0.0
        label = _LABELS[idx] if idx < 4 else ""

        p.save()
        p.setClipRect(x, y, _BAR_W, _BAR_H)

        # Track background
        p.setBrush(T.TRACK)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(x, y, _BAR_W, _BAR_H, 4, 4)

        # Wear fill rising from bottom, colored by temperature
        fill_h = max(0, int(_BAR_H * wear))
        if fill_h > 0:
            p.setBrush(self._temp_color(temp))
            p.drawRoundedRect(x, y + _BAR_H - fill_h, _BAR_W, fill_h, 4, 4)

        txt_col = QColor(T.TEXT)

        # Temperature — top center
        if self._show_temp and temp > 0:
            p.setFont(num_font(7))
            p.setPen(txt_col)
            p.drawText(QRectF(x, y + 1, _BAR_W, 13),
                       Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                       f"{temp:.0f}°")

        # Corner label (FL/FR/RL/RR) — centered in rectangle
        p.setFont(label_font(6))
        p.setPen(QColor(255, 255, 255, 140))
        p.drawText(QRectF(x, y, _BAR_W, _BAR_H),
                   Qt.AlignmentFlag.AlignCenter, label)

        # Wear % — bottom center
        if self._show_wear_pct:
            p.setFont(num_font(7))
            p.setPen(txt_col)
            p.drawText(QRectF(x, y + _BAR_H - 13, _BAR_W, 13),
                       Qt.AlignmentFlag.AlignCenter, f"{wear * 100:.0f}%")

        p.restore()
