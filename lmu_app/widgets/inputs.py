"""Inputs overlay — throttle/brake/clutch bars + rotating steering wheel."""
from __future__ import annotations
import math
from pathlib import Path
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget

BASE_W, BASE_H = 128, 88

_BAR_W, _BAR_H, _BAR_X0, _BAR_Y0, _BAR_GAP = 16, 58, 8, 13, 5
_WHEEL_CX, _WHEEL_CY, _WHEEL_R              = 96, 40, 24
_WHEEL_MAX                                   = 270

_ASSETS_DIR        = Path(__file__).parent.parent / "assets"
_DEFAULT_WHEEL_SVG = _ASSETS_DIR / "wheel_default.svg"


def _load_wheel_pixmap(path_str: str) -> QPixmap | None:
    """Render a wheel image (SVG or raster) to a QPixmap of diameter 2*_WHEEL_R.
    Returns None on failure (falls back to built-in draw)."""
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
    else:
        px = QPixmap(str(path))
        if px.isNull():
            return None
        return px.scaled(size, size,
                         Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)


class InputsWidget(BaseWidget):
    WIDGET_NAME = "Inputs"
    CONFIG_SCHEMA = [
        {"key": "scale",       "label": "Size (%)",    "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 100},
        {"key": "wheel_image", "label": "Wheel image", "type": "filepath",
         "default": ""},
    ]

    C_BG    = QColor(10, 10, 10, 210)
    C_BDR   = QColor(55, 55, 55, 180)
    C_TRACK = QColor(35, 35, 35)
    C_LBL   = QColor(110, 110, 110)
    C_T     = QColor(60, 210, 90)
    C_B     = QColor(220, 55, 55)
    C_C     = QColor(70, 140, 220)
    C_RIM   = QColor(190, 190, 190)
    C_SPOKE = QColor(150, 150, 150)
    C_HUB   = QColor(120, 120, 120)

    def __init__(self, reader: DataReader, **kw):
        self._t = self._b = self._c = self._s = 0.0
        self._scale = 1.0
        self._wheel_image_path = ""
        self._wheel_pixmap: QPixmap | None = None
        super().__init__(reader, update_hz=60, **kw)
        self._wheel_pixmap = _load_wheel_pixmap(self._wheel_image_path)
        self.setFixedSize(BASE_W, BASE_H)

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_params(self, params: dict) -> None:
        new_path = str(params.get("wheel_image", ""))
        if new_path != self._wheel_image_path:
            self._wheel_image_path = new_path
            self._wheel_pixmap = _load_wheel_pixmap(self._wheel_image_path)
        self._scale = int(params.get("scale", 100)) / 100.0
        self.setFixedSize(int(BASE_W * self._scale), int(BASE_H * self._scale))
        self.update()

    def on_data(self, snap: LMUSnapshot):
        v = snap.vehicle
        self._t = max(0., min(1., v.throttle))
        self._b = max(0., min(1., v.brake))
        self._c = max(0., min(1., v.clutch))
        self._s = max(-1., min(1., v.steering))
        self.update()

    def paintEvent(self, _):
        s = self._scale
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(s, s)
        p.setBrush(self.C_BG); p.setPen(QPen(self.C_BDR, 1))
        p.drawRoundedRect(0, 0, BASE_W, BASE_H, 8, 8)
        self._draw_bars(p)
        self._draw_wheel(p)
        p.end()

    def _draw_bars(self, p: QPainter):
        items = [("T", self._t, self.C_T), ("B", self._b, self.C_B), ("C", self._c, self.C_C)]
        p.setFont(QFont("Monospace", 7, QFont.Weight.Bold))
        for i, (lbl, val, col) in enumerate(items):
            x = _BAR_X0 + i * (_BAR_W + _BAR_GAP)
            y, bw, bh = _BAR_Y0, _BAR_W, _BAR_H
            p.setBrush(self.C_TRACK); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, bw, bh, 3, 3)
            fh = int(bh * val)
            if fh > 0:
                g = QLinearGradient(x, y + bh - fh, x, y + bh)
                g.setColorAt(0., col.lighter(130)); g.setColorAt(1., col)
                p.setBrush(g); p.drawRoundedRect(x, y + bh - fh, bw, fh, 3, 3)
            p.setPen(self.C_LBL if val == 0 else col.lighter(150))
            p.drawText(x-2, y - 13, bw+4, 12, Qt.AlignmentFlag.AlignHCenter,
                       f"{int(val*100)}")
            p.setPen(self.C_LBL)
            p.drawText(x, y + bh + 3, bw, 12, Qt.AlignmentFlag.AlignHCenter, lbl)

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

        p.setFont(QFont("Monospace", 7)); p.setPen(self.C_LBL)
        p.drawText(cx - 22, cy + r + 4, 44, 12, Qt.AlignmentFlag.AlignHCenter,
                   f"{int(deg):+.0f}°" if abs(deg) > 1 else "0°")

    def _draw_wheel_builtin(self, p: QPainter, r: int):
        hub_r   = max(4, r // 5)
        spoke_r = r - 3
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(self.C_RIM, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(-r, -r, r * 2, r * 2)
        for deg_spoke in (30, 150):
            rad = math.radians(deg_spoke)
            xe  = int(spoke_r * math.cos(rad))
            ye  = int(spoke_r * math.sin(rad))
            xh  = int(hub_r   * math.cos(rad))
            yh  = int(hub_r   * math.sin(rad))
            p.setPen(QPen(self.C_SPOKE, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(xh, yh, xe, ye)
        p.setBrush(self.C_HUB); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(-hub_r, -hub_r, hub_r * 2, hub_r * 2)
