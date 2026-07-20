"""Speed / Gear / RPM bar overlay — Direction A "Broadcast"."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QSizePolicy

from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.utils.theme import T, label_font, rpm_seg_color
from functools import lru_cache

from PySide6.QtGui import QFontMetrics

from lmu_app.widgets.base import BaseWidget, DEFAULT_SCALE

BASE_H    = 58
_GEAR_GAP = 6   # breathing room between the KM/H unit and the gear
_PAD_X, _PAD_Y = 6, 6
_RPM_H  = 5
_RPM_Y  = _PAD_Y
_RPM_GAP = 1


def _content_h() -> int:
    """Height of the content row below the RPM bar — single source of truth
    shared by _layout_w() and paintEvent(). They used to compute this
    independently with two different formulas (BASE_H - 2*_PAD_Y = 40 here vs
    the real bar_y + _RPM_H + 6 = 19 in paintEvent, giving content_h=26): the
    width was sized for a font ~35px tall while only ~22px was ever drawn,
    leaving a large unexplained gap before the gear."""
    bar_y     = _RPM_Y + 4
    content_y = bar_y + _RPM_H + 6
    return BASE_H - content_y - _PAD_Y


@lru_cache(maxsize=8)
def _layout_w() -> int:
    """Widget width measured from the fonts actually in use.

    A hard-coded width broke when the font changed: Montserrat's digits are
    wider than the previous monospaced face, so the speed block alone ate the
    whole widget and pushed "KM/H" onto the gear.
    """
    num_px = int(_content_h() * 0.88)
    fm_num = QFontMetrics(_num_px(num_px))
    spd_w  = fm_num.horizontalAdvance("000")
    kph_w  = QFontMetrics(label_font(6)).horizontalAdvance("KM/H") + 4
    # "8" isn't actually the widest gear glyph — "N" (neutral, shown constantly
    # at a stop) is wider still. drawText(rect, ...) clips to its rect by
    # default, so an under-sized reference here silently chopped the left
    # edge off "N"/"R" instead of just looking a bit off-centre.
    gear_w = max(fm_num.horizontalAdvance(c) for c in "0123456789NR")
    return _PAD_X + spd_w + 3 + kph_w + _GEAR_GAP + gear_w + _PAD_X


def _num_px(px: int) -> QFont:
    """Saira SemiCondensed Bold at an explicit pixel size — DPI-independent."""
    f = QFont(T.F_NUM)
    f.setPixelSize(px)
    f.setWeight(QFont.Weight.Bold)
    f.setStyleHint(QFont.StyleHint.TypeWriter)
    return f


class SpeedWidget(BaseWidget):
    WIDGET_NAME = "Speed & Gear"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Appearance"},
        {"key": "opacity", "label": "Opacity (%)",  "type": "int",
         "min": 0,  "max": 100, "step": 5, "default": 85},
        {"key": "scale",   "label": "Size (%)",     "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 100},
    ]

    def __init__(self, reader: DataReader, **kw):
        self._speed   = 0.0
        self._gear    = 0
        self._rpm     = 0.0
        self._rpm_max = 9000.0
        self._scale   = DEFAULT_SCALE / 100.0
        super().__init__(reader, update_hz=30, **kw)
        self.setFixedSize(int(_layout_w() * self._scale), int(BASE_H * self._scale))

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_params(self, params: dict) -> None:
        self._scale   = int(params.get("scale", DEFAULT_SCALE)) / 100.0
        self._opacity = max(0, min(100, int(params.get("opacity", 85))))
        self.setFixedSize(int(_layout_w() * self._scale), int(BASE_H * self._scale))
        self.update()

    def on_data(self, snapshot: LMUSnapshot):
        v = snapshot.vehicle
        spd, gear, rpm, rpm_max = v.speed_kmh, v.gear, v.rpm, v.rpm_max
        if (spd != self._speed or gear != self._gear
                or rpm != self._rpm or rpm_max != self._rpm_max):
            self._speed, self._gear, self._rpm, self._rpm_max = spd, gear, rpm, rpm_max
            self.update()

    def paintEvent(self, _):
        s = self._scale
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(s, s)
        w, h = _layout_w(), BASE_H

        self._draw_panel(p, w, h)

        # ── RPM bar — full overlay width ──────────────────────────────────
        ratio = min(1.0, self._rpm / self._rpm_max) if self._rpm_max > 0 else 0.0
        n     = T.RPM_SEGMENTS
        lit   = round(ratio * n)
        bar_y = _RPM_Y + 4
        bar_w = w - 2 * _PAD_X
        seg_w = (bar_w - (n - 1) * _RPM_GAP) / n

        p.setPen(Qt.PenStyle.NoPen)
        for i in range(n):
            x = _PAD_X + i * (seg_w + _RPM_GAP)
            p.setBrush(rpm_seg_color(i / (n - 1)) if i < lit else T.TRACK)
            r = 3.0 if (i == 0 or i == n - 1) else 1.0
            p.drawRoundedRect(QRectF(x, bar_y, seg_w, _RPM_H), r, r)

        # ── Content area ───────────────────────────────────────────────────
        content_h = _content_h()
        content_y = h - content_h - _PAD_Y

        # Font size in painter-px (DPI-independent: always 88 % of content_h)
        num_px    = int(content_h * 0.88)       # ≈ 59 px
        avc       = Qt.AlignmentFlag.AlignVCenter
        speed_str = str(int(self._speed))

        # Speed — right-aligned in a fixed 3-digit-wide zone so digits don't jump
        p.setFont(_num_px(num_px))
        fm_spd   = p.fontMetrics()
        spd_base = content_y + (content_h - fm_spd.height()) / 2 + fm_spd.ascent()
        ref_w    = fm_spd.horizontalAdvance("000")
        p.setPen(QColor(T.TEXT))
        p.drawText(QRectF(_PAD_X, content_y, ref_w, content_h),
                   avc | Qt.AlignmentFlag.AlignRight, speed_str)

        # KM/H — always at the same fixed position, baseline-aligned with speed
        p.setFont(label_font(6))
        fm_kph  = p.fontMetrics()
        kph_x   = _PAD_X + ref_w + 3
        kph_w   = fm_kph.horizontalAdvance("KM/H") + 4
        p.setPen(QColor(T.DIM))
        p.drawText(QRectF(kph_x, spd_base - fm_kph.ascent(),
                          kph_w, fm_kph.height()),
                   avc | Qt.AlignmentFlag.AlignLeft, "KM/H")

        # Gear — right-aligned in right 32 %
        p.setFont(_num_px(num_px))
        p.setPen(QColor(T.ACCENT))
        gear_x = kph_x + kph_w + _GEAR_GAP
        p.drawText(QRectF(gear_x, content_y, w - gear_x - _PAD_X, content_h),
                   avc | Qt.AlignmentFlag.AlignRight,
                   {0: "N", -1: "R"}.get(self._gear, str(self._gear)))

        p.end()
