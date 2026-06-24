"""Delta overlay — last lap / best lap / live delta."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy

from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.utils.theme import T, label_font, num_font
from lmu_app.widgets.base import BaseWidget, DEFAULT_SCALE

_BASE_W  = 100
_PAD     = 5
_ROW_H   = 16
_DELTA_H = 22
_BAR_H   = 7
_BAR_X   = 6
_BAR_W   = _BASE_W - _BAR_X * 2


def _fmt_lap(t: float) -> str:
    if t <= 0:
        return "—"
    m = int(t // 60)
    s = t - m * 60
    return f"{m}:{s:06.3f}"


class DeltaWidget(BaseWidget):
    WIDGET_NAME = "Delta"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Appearance"},
        {"key": "opacity",    "label": "Opacity (%)",   "type": "int",
         "min": 0,  "max": 100, "step": 5,  "default": 85},
        {"key": "scale",      "label": "Size (%)",       "type": "int",
         "min": 50, "max": 250, "step": 5,  "default": 80},
        {"type": "separator", "label": "Display"},
        {"key": "show_last",  "label": "Last Lap",       "type": "bool", "default": True},
        {"key": "show_best",  "label": "Best Lap",       "type": "bool", "default": True},
        {"key": "show_delta", "label": "Delta value",    "type": "bool", "default": True},
        {"key": "show_bar",   "label": "Delta bar",      "type": "bool", "default": True},
        {"type": "separator", "label": "Bar"},
        {"key": "bar_range",  "label": "Bar range (s)",  "type": "float",
         "min": 0.5, "max": 10.0, "step": 0.5, "default": 2.0,
         "show_if": ("show_bar", True)},
    ]

    def __init__(self, reader: DataReader, **kw):
        self._delta        = 0.0
        self._best_lap     = -1.0
        self._last_lap     = -1.0
        self._cls_ses_best = -1.0
        self._has_ref      = False
        self._scale        = 80 / 100.0
        self._bar_range    = 2.0
        self._show_last    = True
        self._show_best    = True
        self._show_delta   = True
        self._show_bar     = True
        super().__init__(reader, update_hz=20, **kw)
        self._apply_size()

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _base_h(self) -> int:
        h = _PAD
        if self._show_last:  h += _ROW_H + 2
        if self._show_best:  h += _ROW_H + 2
        if self._show_delta:
            if self._show_last or self._show_best:
                h += 2
            h += _DELTA_H
        if self._show_bar:
            h += 2 + _BAR_H + _PAD
        else:
            h += _PAD
        return max(h, _PAD * 2 + 10)   # minimum visible height

    def _apply_size(self):
        self.setFixedSize(int(_BASE_W * self._scale), int(self._base_h() * self._scale))

    def apply_params(self, params: dict) -> None:
        self._scale      = int(params.get("scale",      80))          / 100.0
        self._opacity    = max(0, min(100, int(params.get("opacity",  85))))
        self._bar_range  = float(params.get("bar_range",  2.0))
        self._show_last  = bool(params.get("show_last",   True))
        self._show_best  = bool(params.get("show_best",   True))
        self._show_delta = bool(params.get("show_delta",  True))
        self._show_bar   = bool(params.get("show_bar",    True))
        self._apply_size()
        self.update()

    def on_data(self, snap: LMUSnapshot) -> None:
        player = next((x for x in snap.session.vehicles if x.is_player), None)
        if player:
            self._best_lap = player.best_lap
            self._last_lap = player.last_lap
            self._has_ref  = player.best_lap > 0
            cls   = player.vehicle_class
            bests = [v.best_lap for v in snap.session.vehicles
                     if v.vehicle_class == cls and v.best_lap > 0]
            self._cls_ses_best = min(bests) if bests else -1.0
        self._delta = snap.vehicle.delta_best
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)
        bh = self._base_h()
        self._draw_panel(p, _BASE_W, bh)

        lbl_w = 28
        y = _PAD

        # ── Last Lap ──────────────────────────────────────────────────
        if self._show_last:
            p.setFont(label_font(6))
            p.setPen(QColor(T.DIM))
            p.drawText(QRectF(_PAD, y, lbl_w, _ROW_H),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "LAST")
            if self._last_lap <= 0:
                last_col = QColor(T.TEXT)
            elif self._cls_ses_best > 0 and abs(self._last_lap - self._cls_ses_best) < 0.002:
                last_col = QColor(T.PURPLE)
            elif self._best_lap > 0 and abs(self._last_lap - self._best_lap) < 0.002:
                last_col = QColor(T.GOOD)
            else:
                last_col = QColor(T.TEXT)
            p.setFont(num_font(9))
            p.setPen(last_col)
            p.drawText(QRectF(_PAD + lbl_w, y, _BASE_W - _PAD - lbl_w - _PAD, _ROW_H),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                       _fmt_lap(self._last_lap))
            y += _ROW_H + 2

        # ── Best Lap ──────────────────────────────────────────────────
        if self._show_best:
            p.setFont(label_font(6))
            p.setPen(QColor(T.DIM))
            p.drawText(QRectF(_PAD, y, lbl_w, _ROW_H),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "BEST")
            p.setFont(num_font(9))
            p.setPen(QColor(T.PURPLE))
            p.drawText(QRectF(_PAD + lbl_w, y, _BASE_W - _PAD - lbl_w - _PAD, _ROW_H),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                       _fmt_lap(self._best_lap))
            y += _ROW_H + 2

        # ── Delta value ───────────────────────────────────────────────
        if self._show_delta:
            if self._show_last or self._show_best:
                y += 2
            if not self._has_ref:
                p.setFont(num_font(13))
                p.setPen(QColor(T.DIM))
                p.drawText(QRectF(0, y, _BASE_W, _DELTA_H),
                           Qt.AlignmentFlag.AlignCenter, "—")
            else:
                d = self._delta
                if d < 0:
                    col, txt = QColor(T.GOOD),  f"{d:.3f}"
                elif d > 0:
                    col, txt = QColor(T.CRIT),  f"+{d:.3f}"
                else:
                    col, txt = QColor(T.TEXT),  "0.000"
                p.setFont(num_font(13))
                p.setPen(col)
                p.drawText(QRectF(0, y, _BASE_W, _DELTA_H),
                           Qt.AlignmentFlag.AlignCenter, txt)
            y += _DELTA_H

        # ── Bar ───────────────────────────────────────────────────────
        if self._show_bar:
            by = y + 2
            cx = _BAR_X + _BAR_W // 2
            p.setBrush(QColor(T.TRACK))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(_BAR_X, by, _BAR_W, _BAR_H, 2, 2)
            if self._has_ref:
                rng     = max(0.1, self._bar_range)
                clamped = max(-rng, min(rng, self._delta))
                fill_w  = int(abs(clamped) / rng * (_BAR_W / 2))
                if fill_w > 0:
                    col = QColor(T.GOOD) if clamped < 0 else QColor(T.CRIT)
                    p.setBrush(col)
                    p.setPen(Qt.PenStyle.NoPen)
                    if clamped < 0:
                        p.drawRoundedRect(cx - fill_w, by, fill_w, _BAR_H, 2, 2)
                    else:
                        p.drawRoundedRect(cx, by, fill_w, _BAR_H, 2, 2)
            p.setPen(QColor(T.DIM))
            p.drawLine(cx, by, cx, by + _BAR_H)

        p.end()
