"""Tyres overlay — 4 vertical wear bars (2×2) colored by temperature — Direction A."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy

from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.utils.theme import T, label_font, num_font
from lmu_app.widgets.base import BaseWidget, DEFAULT_SCALE

_BAR_W = 38
_BAR_H = 60
_G     = 5    # écart uniforme : bords, entre pneus gauche/droite, avant/arrière

WIDGET_W = _G * 2 + _BAR_W * 2 + _G   # = 3*G + 2*BAR_W
WIDGET_H = _G * 2 + _BAR_H * 2 + _G

_LABELS = ["FL", "FR", "RL", "RR"]

# Colour bands expressed as an offset (°C) from the tyre's own optimal temp.
_COLD_D      = -25.0   # at/below → fully cold (blue)
_OPT_LO_D    = -8.0    # start of the optimal window (green)
_OPT_HI_D    =  8.0    # end of the optimal window
_HOT_D       =  25.0   # at/above → fully hot (red)
_FALLBACK_OPT = 85.0   # used only if the game reports no optimal temp

_POSITIONS = [
    (_G,              _G),
    (_G + _BAR_W + _G, _G),
    (_G,              _G + _BAR_H + _G),
    (_G + _BAR_W + _G, _G + _BAR_H + _G),
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
    ]

    def __init__(self, reader: DataReader,
                 show_temp: bool = True, show_wear_pct: bool = True,
                 **kw):
        self._show_temp     = show_temp
        self._show_wear_pct = show_wear_pct
        self._scale         = DEFAULT_SCALE / 100.0
        self._opacity       = 85
        self._temps:  list[float] = [0.0] * 4
        self._wears:  list[float] = [1.0] * 4
        self._opts:   list[float] = [0.0] * 4
        super().__init__(reader, update_hz=10, **kw)
        self.setFixedSize(int(WIDGET_W * self._scale), int(WIDGET_H * self._scale))

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_params(self, params: dict) -> None:
        self._show_temp     = bool(params.get("show_temp",     True))
        self._show_wear_pct = bool(params.get("show_wear_pct", True))
        self._scale         = int(params.get("scale", DEFAULT_SCALE)) / 100.0
        self._opacity       = max(0, min(100, int(params.get("opacity", 85))))
        self.setFixedSize(int(WIDGET_W * self._scale), int(WIDGET_H * self._scale))
        self.update()

    def on_data(self, snap: LMUSnapshot) -> None:
        self._temps = list(snap.tyres.temp_carcass)
        self._wears = list(snap.tyres.wear)
        self._opts  = list(snap.tyres.optimal_temp)
        self.update()

    def _temp_color(self, t: float, opt: float) -> QColor:
        """Colour relative to this tyre's own optimal temperature (mOptimalTemp),
        so it adapts per car and compound instead of fixed thresholds."""
        if t <= 0:
            return QColor(T.DIM)
        if opt <= 0:
            opt = _FALLBACK_OPT      # game gave no optimal → sane default
        d = t - opt
        if d <= _COLD_D:
            return QColor(80, 140, 255)
        if d < _OPT_LO_D:
            f = (d - _COLD_D) / (_OPT_LO_D - _COLD_D)
            return QColor(int(80 - 80*f), int(140 + 80*f), int(255 - 175*f))
        if d <= _OPT_HI_D:
            return QColor(60, 220, 80)
        if d < _HOT_D:
            f = (d - _OPT_HI_D) / (_HOT_D - _OPT_HI_D)
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
        opt   =                   self._opts[idx]   if idx < 4 else 0.0
        label = _LABELS[idx] if idx < 4 else ""

        # Track background
        p.setBrush(T.TRACK)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(x, y, _BAR_W, _BAR_H, 4, 4)

        # Wear fill rising from bottom, colored by temperature
        fill_h = max(0, int(_BAR_H * wear))
        if fill_h > 0:
            p.setBrush(self._temp_color(temp, opt))
            p.drawRoundedRect(x, y + _BAR_H - fill_h, _BAR_W, fill_h, 4, 4)

        txt_col = QColor(T.TEXT)

        # Temperature — top center
        if self._show_temp and temp > 0:
            p.setFont(num_font(8))
            p.setPen(txt_col)
            p.drawText(QRectF(x, y + 1, _BAR_W, 15),
                       Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                       f"{temp:.0f}°")

        # Wear % — bottom center
        if self._show_wear_pct:
            p.setFont(num_font(8))
            p.setPen(txt_col)
            p.drawText(QRectF(x, y + _BAR_H - 15, _BAR_W, 15),
                       Qt.AlignmentFlag.AlignCenter, f"{wear * 100:.0f}%")

        # Corner label (FL/FR/RL/RR) — centered, drawn last
        p.setFont(label_font(7))
        p.setPen(QColor(255, 255, 255, 140))
        p.drawText(QRectF(x, y, _BAR_W, _BAR_H),
                   Qt.AlignmentFlag.AlignCenter, label)
