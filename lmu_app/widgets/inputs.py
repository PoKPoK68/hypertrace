"""Inputs overlay — throttle/brake/clutch bars + rotating steering wheel — Direction A."""
from __future__ import annotations
import math
from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy

from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.utils.theme import T, label_font, num_font
from lmu_app.widgets.base import BaseWidget

BASE_W, BASE_H = 154, 88

_BAR_W   = 16
_BAR_H   = 52
_BAR_X0  = 10
_BAR_Y0  = 19
_BAR_GAP = 6

_WHEEL_CX  = 112
_WHEEL_CY  = 36
_WHEEL_R   = 30
_WHEEL_MAX = 270

_RIM_COL = QColor("#D8D2C4")

_ASSETS_DIR        = Path(__file__).parent.parent / "assets"
_DEFAULT_WHEEL_SVG = _ASSETS_DIR / "wheel_default.svg"


def _load_wheel_pixmap(path_str: str) -> QPixmap | None:
    size = _WHEEL_R * 2
    path = Path(path_str) if path_str else _DEFAULT_WHEEL_SVG
    if not path.exists():
        return None
    if path.suffix.lower() == ".svg":
        try:
            from PySide6.QtSvg import QSvgRenderer
            renderer = QSvgRenderer(str(path))
            if not renderer.isValid():
                return None
            px = QPixmap(size, size)
            px.fill(Qt.GlobalColor.transparent)
            painter = QPainter(px)
            renderer.render(painter, QRectF(0, 0, size, size))
            painter.end()
            return px
        except Exception:
            return None
    px = QPixmap(str(path))
    if px.isNull():
        return None
    return px.scaled(size, size,
                     Qt.AspectRatioMode.KeepAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)


class InputsWidget(BaseWidget):
    WIDGET_NAME = "Inputs"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Window"},
        {"key": "opacity",     "label": "Opacity (%)", "type": "int",
         "min": 0,  "max": 100, "step": 5, "default": 85},
        {"key": "scale",       "label": "Size (%)",    "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 65},
        {"key": "wheel_image", "label": "Wheel image", "type": "filepath",
         "default": ""},
    ]

    def __init__(self, reader: DataReader, **kw):
        self._t = self._b = self._c = self._s = 0.0
        self._scale = 0.65
        self._wheel_image_path = ""
        self._wheel_pixmap: QPixmap | None = None
        super().__init__(reader, update_hz=60, **kw)
        self._wheel_pixmap = _load_wheel_pixmap(self._wheel_image_path)
        self.setFixedSize(int(BASE_W * self._scale), int(BASE_H * self._scale))

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_params(self, params: dict) -> None:
        new_path = str(params.get("wheel_image", ""))
        if new_path != self._wheel_image_path:
            self._wheel_image_path = new_path
            self._wheel_pixmap = _load_wheel_pixmap(self._wheel_image_path)
        self._scale   = int(params.get("scale", 65)) / 100.0
        self._opacity = max(0, min(100, int(params.get("opacity", 85))))
        self.setFixedSize(int(BASE_W * self._scale), int(BASE_H * self._scale))
        self.update()

    def on_data(self, snap: LMUSnapshot):
        v = snap.vehicle
        t = max(0., min(1., v.throttle))
        b = max(0., min(1., v.brake))
        c = max(0., min(1., v.clutch))
        s = max(-1., min(1., v.steering))
        if t != self._t or b != self._b or c != self._c or s != self._s:
            self._t, self._b, self._c, self._s = t, b, c, s
            self.update()

    def paintEvent(self, _):
        s = self._scale
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(s, s)

        self._draw_panel(p, BASE_W, BASE_H)
        self._draw_bars(p)
        self._draw_wheel(p)
        p.end()

    def _draw_bars(self, p: QPainter):
        items = [
            ("T", self._t, QColor(T.THROTTLE)),
            ("B", self._b, QColor(T.BRAKE)),
            ("C", self._c, QColor(T.CLUTCH)),
        ]
        for i, (lbl, val, col) in enumerate(items):
            x = _BAR_X0 + i * (_BAR_W + _BAR_GAP)
            y, bw, bh = _BAR_Y0, _BAR_W, _BAR_H

            # Track
            p.setBrush(T.TRACK)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, bw, bh, 3, 3)

            # Solid fill rising from bottom
            fh = int(bh * val)
            if fh > 0:
                p.setBrush(col)
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(x, y + bh - fh, bw, fh, 3, 3)

            # Value above bar — col when active, dim when zero
            val_col = QColor(T.DIM) if val == 0 else col.lighter(150)
            p.setFont(num_font(7))
            p.setPen(val_col)
            p.drawText(QRectF(x - 2, y - 15, bw + 4, 14),
                       Qt.AlignmentFlag.AlignCenter, str(int(val * 100)))

            # Letter below bar — always dim, uppercase tracking
            p.setFont(label_font(6))
            p.setPen(QColor(T.DIM))
            p.drawText(QRectF(x, y + bh + 2, bw, 10),
                       Qt.AlignmentFlag.AlignCenter, lbl)

    def _draw_wheel(self, p: QPainter):
        cx, cy, r = _WHEEL_CX, _WHEEL_CY, _WHEEL_R
        deg = self._s * _WHEEL_MAX

        p.save()
        p.translate(cx, cy)
        p.rotate(deg)

        if self._wheel_pixmap and not self._wheel_pixmap.isNull():
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawPixmap(-r, -r, self._wheel_pixmap)
        else:
            self._draw_wheel_builtin(p, r)

        p.restore()

        # Angle label below wheel
        angle_str = f"{int(deg):+d}°" if abs(deg) > 1 else "0°"
        p.setFont(num_font(7))
        p.setPen(QColor(T.DIM))
        p.drawText(QRectF(cx - 32, cy + r + 4, 64, 12),
                   Qt.AlignmentFlag.AlignCenter, angle_str)

    def _draw_wheel_builtin(self, p: QPainter, r: int):
        hub_r   = max(4, r // 5)
        spoke_r = r - 3

        # Rim
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(_RIM_COL, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(-r, -r, r * 2, r * 2)

        # 3 branches: right (0°), bottom (π/2), left (π) — open at top
        p.setPen(QPen(_RIM_COL, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for angle in (0.0, math.pi / 2, math.pi):
            xe = int(spoke_r * math.cos(angle))
            ye = int(spoke_r * math.sin(angle))
            xh = int(hub_r   * math.cos(angle))
            yh = int(hub_r   * math.sin(angle))
            p.drawLine(xh, yh, xe, ye)

        # Hub
        p.setBrush(_RIM_COL)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(-hub_r, -hub_r, hub_r * 2, hub_r * 2)
