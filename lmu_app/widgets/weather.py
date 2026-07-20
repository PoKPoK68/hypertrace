"""Weather overlay — air/track temps, rain, wetness, session forecast."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy

from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.utils.theme import T, label_font, num_font
from lmu_app.widgets.base import BaseWidget, DEFAULT_SCALE

logger = logging.getLogger(__name__)

_ASSETS      = Path(__file__).parent.parent / "assets"
_NODE_LABELS = ["S", "25", "50", "75", "F"]
_SKY_FILES   = [
    "00_clear.svg",
    "01_light_clouds.svg",
    "02_partially_cloudy.svg",
    "03_mostly_cloudy.svg",
    "04_overcast.svg",
    "05_cloudy_drizzle.svg",
    "06_cloudy_light_rain.svg",
    "07_overcast_light_rain.svg",
    "08_overcast_rain.svg",
    "09_overcast_heavy_rain.svg",
    "10_overcast_storm.svg",
]

BASE_W  = 172
_PAD_X  = 9
_PAD_Y  = 6
_LBL_H  = 10
_GAP    = 1
_VAL_H  = 17
_ROW_H  = _LBL_H + _GAP + _VAL_H
_SEP_Y  = _PAD_Y + _ROW_H * 2
_FC_TOP = _SEP_Y + 4
_FC_HDR = 10   # "FORECAST" label
_IC_H   = 18   # icon height (square)
_NL_H   = 10   # node label
BASE_H  = _FC_TOP + _FC_HDR + _IC_H + _NL_H + _PAD_Y


class WeatherWidget(BaseWidget):
    WIDGET_NAME = "Weather"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Appearance"},
        {"key": "opacity", "label": "Opacity (%)", "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 85},
        {"key": "scale", "label": "Size (%)", "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 100},
    ]

    def __init__(self, reader: DataReader, **kw):
        self._scale      = DEFAULT_SCALE / 100.0
        self._air_temp   = 0.0
        self._track_temp = 0.0
        self._raining    = 0.0
        self._wetness    = 0.0
        self._forecast: list[int] = []
        self._sky_now: int = -1   # current sky type from shared memory (instant, no REST)
        self._svg_air    = None
        self._svg_trk    = None
        self._sky_svgs: list = []
        super().__init__(reader, update_hz=1, **kw)
        self._load_svgs()
        self.setFixedSize(int(BASE_W * self._scale), int(BASE_H * self._scale))

    def _load_svgs(self) -> None:
        try:
            from PySide6.QtSvg import QSvgRenderer
        except ImportError:
            logger.warning("PySide6.QtSvg not available — weather icons disabled")
            return
        for fname, attr in [("air-temp.svg", "_svg_air"), ("track-temp.svg", "_svg_trk")]:
            try:
                r = QSvgRenderer(str(_ASSETS / fname))
                setattr(self, attr, r if r.isValid() else None)
            except Exception as exc:
                logger.warning("SVG load failed (%s): %s", fname, exc)
        self._sky_svgs = []
        for fname in _SKY_FILES:
            try:
                r = QSvgRenderer(str(_ASSETS / "weather" / fname))
                if not r.isValid():
                    logger.warning("SVG invalid: %s", fname)
                self._sky_svgs.append(r if r.isValid() else None)
            except Exception as exc:
                logger.warning("SVG load failed (%s): %s", fname, exc)
                self._sky_svgs.append(None)
        logger.debug("Weather SVGs loaded: %d/11", sum(1 for r in self._sky_svgs if r))

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_params(self, params: dict) -> None:
        self._scale   = int(params.get("scale",   DEFAULT_SCALE)) / 100.0
        self._opacity = max(0, min(100, int(params.get("opacity", 85))))
        self.setFixedSize(int(BASE_W * self._scale), int(BASE_H * self._scale))
        self.update()

    def on_data(self, snap: LMUSnapshot) -> None:
        s = snap.session
        self._air_temp     = s.ambient_temp
        self._track_temp   = s.track_temp
        self._raining      = s.raining
        self._wetness      = s.avg_path_wetness
        self._forecast     = s.weather_forecast   # forecast via reader/REST (no REST here)
        self._sky_now      = s.weather_sky        # current sky via shared memory (instant)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)
        self._draw_panel(p, BASE_W, BASE_H)
        self._draw_live(p)
        self._draw_forecast(p)
        p.end()

    def _render_svg(self, p: QPainter, renderer, rect: QRectF) -> None:
        if renderer is None:
            return
        vb = renderer.viewBoxF()
        if vb.height() == 0:
            return
        aspect = vb.width() / vb.height()
        ih = rect.height()
        iw = ih * aspect
        ix = rect.x() + (rect.width() - iw) / 2
        iy = rect.y() + (rect.height() - ih) / 2
        renderer.render(p, QRectF(ix, iy, iw, ih))

    def _draw_live(self, p: QPainter) -> None:
        half = BASE_W // 2
        rows = [
            [(self._svg_air, "AIR",  f"{self._air_temp:.0f}°",      0),
             (self._svg_trk, "TRK",  f"{self._track_temp:.0f}°",    1)],
            [(None,           "RAIN", f"{self._raining * 100:.0f}%", 0),
             (None,           "WET",  f"{self._wetness * 100:.0f}%", 1)],
        ]
        for row_idx, cells in enumerate(rows):
            y = _PAD_Y + row_idx * _ROW_H
            for svg, lbl, val, col in cells:
                x      = col * half
                lbl_r  = QRectF(x, y, half, _LBL_H)
                if svg is not None:
                    self._render_svg(p, svg, lbl_r)
                else:
                    p.setFont(label_font(7))
                    p.setPen(QColor(T.DIM))
                    p.drawText(lbl_r, Qt.AlignmentFlag.AlignCenter, lbl)
                p.setFont(num_font(12))
                p.setPen(QColor(T.TEXT))
                p.drawText(QRectF(x, y + _LBL_H + _GAP, half, _VAL_H),
                           Qt.AlignmentFlag.AlignCenter, val)

        # Vertical divider
        p.fillRect(QRectF(half, _PAD_Y + 2, 1, _ROW_H * 2 - 4), T.FAINT)

    def _draw_forecast(self, p: QPainter) -> None:
        p.fillRect(QRectF(2, _SEP_Y, BASE_W - 4, 1), T.FAINT)

        p.setFont(label_font(6))
        p.setPen(QColor(T.DIM))
        p.drawText(QRectF(_PAD_X, _FC_TOP, BASE_W - _PAD_X * 2, _FC_HDR),
                   Qt.AlignmentFlag.AlignCenter, "FORECAST")

        icon_y  = _FC_TOP + _FC_HDR
        label_y = icon_y + _IC_H + 1
        slot_w  = (BASE_W - _PAD_X * 2) / 5

        nodes = self._forecast

        if not nodes:
            # No forecast yet (REST not ready) — show current sky from shared
            # memory instantly if we have it, else "NO DATA".
            if 0 <= self._sky_now < len(self._sky_svgs) and self._sky_svgs[self._sky_now] is not None:
                ic_x = _PAD_X + (BASE_W - _PAD_X * 2 - _IC_H) / 2
                self._sky_svgs[self._sky_now].render(p, QRectF(ic_x, icon_y, _IC_H, _IC_H))
                p.setFont(label_font(6))
                p.setPen(QColor(T.DIM))
                p.drawText(QRectF(_PAD_X, label_y, BASE_W - _PAD_X * 2, _NL_H - 1),
                           Qt.AlignmentFlag.AlignCenter, "NOW")
            else:
                p.setFont(label_font(6))
                p.setPen(QColor(T.DIM))
                p.drawText(QRectF(_PAD_X, icon_y, BASE_W - _PAD_X * 2, _IC_H),
                           Qt.AlignmentFlag.AlignCenter, "NO DATA")
            return

        for i, sky in enumerate(nodes):
            slot_x  = _PAD_X + i * slot_w
            ic_size = _IC_H   # square icons (24×24 viewBox)
            ic_x    = slot_x + (slot_w - ic_size) / 2

            if 0 <= sky < len(self._sky_svgs) and self._sky_svgs[sky] is not None:
                self._sky_svgs[sky].render(p, QRectF(ic_x, icon_y, ic_size, ic_size))
            else:
                p.setFont(label_font(6))
                p.setPen(QColor(T.DIM))
                p.drawText(QRectF(slot_x, icon_y, slot_w, _IC_H),
                           Qt.AlignmentFlag.AlignCenter, f"?{sky}")

            p.setFont(label_font(6))
            p.setPen(QColor(T.DIM))
            p.drawText(QRectF(slot_x, label_y, slot_w, _NL_H - 1),
                       Qt.AlignmentFlag.AlignCenter, _NODE_LABELS[i])
