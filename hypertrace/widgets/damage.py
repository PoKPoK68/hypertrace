"""Damage overlay — top-down car silhouette, per design_handoff_damage_overlay.

Geometry is copied verbatim from the handoff's SVG (viewBox 230×300) and
scaled down as a whole, rather than redrawn from scratch, so it stays a
faithful reproduction rather than an approximation.

17 zones total: 4 body edges + 4 corners (shared memory, mDentSeverity), 4
wheels (shared memory, detached/puncture), 4 suspension wishbones (REST-only,
no shared-memory equivalent — see project memory), 1 rear wing (shared
memory, mDetached). No text or legend, matching the handoff spec.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy

from hypertrace.calc.module_info import minfo
from hypertrace.widgets.base import BaseWidget, DEFAULT_SCALE

# ── Geometry, in the handoff's own viewBox units (230×300) ──────────────────
_VB_W, _VB_H = 230.0, 300.0
_DISPLAY_W = 75.0   # half the handoff's specified 150px display width
_CAR_SCALE = _DISPLAY_W / _VB_W
_DISPLAY_H = _VB_H * _CAR_SCALE
_PAD = 6

WIDGET_W = round(_DISPLAY_W + _PAD * 2)
WIDGET_H = round(_DISPLAY_H + _PAD * 2)

_SILHOUETTE_RECT = QRectF(58, 34, 114, 232)
_SILHOUETTE_RADIUS = 28

# (p1, p2) — both stroked as one round-capped line each. The flanks are no
# longer continuous top-to-bottom: they're just the middle segment between the
# two wheel arches, leaving a real gap in the bodywork where each wheel now
# tucks in (see _WHEELS — they moved inboard and would otherwise sit on the
# line). Per the updated handoff.
_BODY_EDGES = {
    "front": ((91, 34), (139, 34)),
    "rear":  ((91, 266), (139, 266)),
    "left":  ((58, 117), (58, 183)),
    "right": ((172, 117), (172, 183)),
}
_BODY_STROKE = 7

# (center, p1, p2) — arc of radius 28 from p1 to p2, both already on that circle.
_CORNERS = {
    "fl": ((86, 62),  (58.4, 57.1),  (81.1, 34.4)),
    "fr": ((144, 62), (148.9, 34.4), (171.6, 57.1)),
    "rl": ((86, 238), (81.1, 265.6), (58.4, 242.9)),
    "rr": ((144, 238), (171.6, 242.9), (148.9, 265.6)),
}
_CORNER_RADIUS = 28
_CORNER_STROKE = 7

# (x, y) top-left corner — filled rect, 22×42, rx=5. Moved inboard (was at
# x=16/192, well outside the body) so each wheel now sits flush against the
# flank, its outer edge just past the x=58/172 body line, centred on the arch
# gap cut into that flank (see _BODY_EDGES). Per the updated handoff.
_WHEELS = {
    "fl": (52, 66),
    "fr": (156, 66),
    "rl": (52, 192),
    "rr": (156, 192),
}
_WHEEL_W, _WHEEL_H, _WHEEL_R = 22, 42, 5

# Wishbone: two line segments sharing an apex, stroked round-capped. Apex is
# pinned to the wheel side; both arms fan out to the chassis. Moved inboard
# with the wheels above. (apex_a, apex, apex_b) — apex is the shared point.
_SUSPENSION = {
    "fl": ((89, 79), (77, 87), (89, 97)),
    "fr": ((141, 79), (153, 87), (141, 97)),
    "rl": ((89, 205), (77, 213), (89, 223)),
    "rr": ((141, 205), (153, 213), (141, 223)),
}
_SUSP_STROKE = 4

# Rounded rect, asymmetric corners (top 7, bottom 2.5) — filled, no stroke.
_WING_BOX = QRectF(58, 277, 114, 14)
_WING_R_TOP, _WING_R_BOTTOM = 7, 2.5

# Index into bodySeverity (FL, FC, FR, CL, CR, RL, RC, RR — calc/api.py
# Damage.body_severity) for each edge/corner zone in the design.
_BODY_EDGE_INDEX = {"front": 1, "rear": 6, "left": 3, "right": 4}
_CORNER_INDEX = {"fl": 0, "fr": 2, "rl": 5, "rr": 7}

# Severity 0-3 → colour, shared by every zone. Red brightened from the
# handoff's muted "#e0433d" — flagged as not voyant enough at this size.
_SEV_COLOR = [QColor("#3f434a"), QColor("#e0a52a"), QColor("#e8701c"), QColor("#ff2020")]

# Wheel/suspension don't come from the game as a native 0-3 tier — these map
# our actual telemetry facts onto the same scale the design uses everywhere else.
_SUSP_TIER_1 = 0.02   # >= this fraction of suspension damage -> tier 1 (light)
_SUSP_TIER_2 = 0.15   # -> tier 2 (heavy)
_SUSP_TIER_3 = 0.80   # -> tier 3 (totaled)


def _sev_color(level: int) -> QColor:
    return _SEV_COLOR[max(0, min(3, level))]


def _suspension_tier(damage: float) -> int:
    if damage < 0 or damage < _SUSP_TIER_1:
        return 0
    if damage < _SUSP_TIER_2:
        return 1
    if damage < _SUSP_TIER_3:
        return 2
    return 3


def _arc_to(path: QPainterPath, center: tuple[float, float], radius: float,
            p_from: tuple[float, float], p_to: tuple[float, float]) -> None:
    """Append an arc along circle (center, radius) from p_from to p_to — both
    must already lie on that circle. Computed straight from the endpoints
    (Qt's clock-face angle convention: 0deg = 3 o'clock, positive = counter-
    clockwise) so the same helper works for every corner without hand-picking
    start/sweep angles per corner."""
    a1 = math.degrees(math.atan2(-(p_from[1] - center[1]), p_from[0] - center[0]))
    a2 = math.degrees(math.atan2(-(p_to[1] - center[1]), p_to[0] - center[0]))
    sweep = a2 - a1
    if sweep > 180:
        sweep -= 360
    elif sweep < -180:
        sweep += 360
    rect = QRectF(center[0] - radius, center[1] - radius, radius * 2, radius * 2)
    path.arcTo(rect, a1, sweep)


def _corner_path(name: str) -> QPainterPath:
    center, p1, p2 = _CORNERS[name]
    path = QPainterPath()
    path.moveTo(*p1)
    _arc_to(path, center, _CORNER_RADIUS, p1, p2)
    return path


def _wing_path() -> QPainterPath:
    """Rounded rect with different top/bottom corner radii — QPainterPath has
    no built-in for that, built manually from the same corner centers a
    uniform rounded rect would use."""
    x, y, w, h = _WING_BOX.x(), _WING_BOX.y(), _WING_BOX.width(), _WING_BOX.height()
    rt, rb = _WING_R_TOP, _WING_R_BOTTOM
    tl_c, tr_c = (x + rt, y + rt), (x + w - rt, y + rt)
    br_c, bl_c = (x + w - rb, y + h - rb), (x + rb, y + h - rb)
    path = QPainterPath()
    path.moveTo(x + rt, y)
    path.lineTo(x + w - rt, y)
    _arc_to(path, tr_c, rt, (x + w - rt, y), (x + w, y + rt))
    path.lineTo(x + w, y + h - rb)
    _arc_to(path, br_c, rb, (x + w, y + h - rb), (x + w - rb, y + h))
    path.lineTo(x + rb, y + h)
    _arc_to(path, bl_c, rb, (x + rb, y + h), (x, y + h - rb))
    path.lineTo(x, y + rt)
    _arc_to(path, tl_c, rt, (x, y + rt), (x + rt, y))
    path.closeSubpath()
    return path


class DamageWidget(BaseWidget):
    WIDGET_NAME = "Damage"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Appearance"},
        {"key": "opacity", "label": "Opacity (%)", "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 85},
        {"key": "scale",   "label": "Size (%)",    "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 100},
    ]

    def __init__(self, **kw):
        self._scale    = DEFAULT_SCALE / 100.0
        self._opacity  = 85
        self._body: list[int]       = [0] * 8
        self._wheel_off: list[bool] = [False] * 4
        self._puncture: list[bool]  = [False] * 4
        self._wing_off              = False
        self._suspension: list[float] = [-1.0] * 4
        super().__init__(update_hz=10, **kw)
        self.setFixedSize(int(WIDGET_W * self._scale), int(WIDGET_H * self._scale))

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_params(self, params: dict) -> None:
        self._scale   = int(params.get("scale", DEFAULT_SCALE)) / 100.0
        self._opacity = max(0, min(100, int(params.get("opacity", 85))))
        self._apply_session_visibility(params)
        self.setFixedSize(int(WIDGET_W * self._scale), int(WIDGET_H * self._scale))
        self.update()

    def on_data(self) -> None:
        dmg = minfo.damage
        self._body       = dmg.bodySeverity
        self._wheel_off  = dmg.wheelDetached
        self._puncture   = dmg.tyrePuncture
        self._wing_off   = dmg.rearWingDetached
        self._suspension = dmg.suspensionDamage
        self.update()

    def _wheel_severity(self, i: int) -> int:
        if self._wheel_off[i]:
            return 3
        if self._puncture[i]:
            return 2
        return 0

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)
        self._draw_panel(p, WIDGET_W, WIDGET_H)

        p.translate(_PAD, _PAD)
        p.scale(_CAR_SCALE, _CAR_SCALE)

        # Silhouette — static background, never coloured by damage.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 6))
        p.drawRoundedRect(_SILHOUETTE_RECT, _SILHOUETTE_RADIUS, _SILHOUETTE_RADIUS)

        # Wheels — filled, always opaque (even undamaged).
        for i, key in enumerate(("fl", "fr", "rl", "rr")):
            x, y = _WHEELS[key]
            level = self._wheel_severity(i)
            color = _sev_color(level)
            rect = QRectF(x, y, _WHEEL_W, _WHEEL_H)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(rect, _WHEEL_R, _WHEEL_R)

        # Body edges — 8 zones total with corners, straight from mDentSeverity.
        for key, (p1, p2) in _BODY_EDGES.items():
            idx = _BODY_EDGE_INDEX[key]
            level = self._body[idx] if len(self._body) > idx else 0
            color = _sev_color(level)
            path = QPainterPath()
            path.moveTo(*p1)
            path.lineTo(*p2)
            pen = QPen(color, _BODY_STROKE)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        for key in ("fl", "fr", "rl", "rr"):
            idx = _CORNER_INDEX[key]
            level = self._body[idx] if len(self._body) > idx else 0
            color = _sev_color(level)
            path = _corner_path(key)
            pen = QPen(color, _CORNER_STROKE)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        # Suspension — REST-only fraction, tiered onto the same 0-3 scale.
        for i, key in enumerate(("fl", "fr", "rl", "rr")):
            apex_a, apex, apex_b = _SUSPENSION[key]
            level = _suspension_tier(self._suspension[i] if i < 4 else -1.0)
            color = _sev_color(level)
            path = QPainterPath()
            path.moveTo(*apex_a)
            path.lineTo(*apex)
            path.moveTo(*apex_b)
            path.lineTo(*apex)
            pen = QPen(color, _SUSP_STROKE)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        # Rear wing — separate filled zone, binary attached/detached.
        wing_color = _sev_color(3 if self._wing_off else 0)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(wing_color)
        p.drawPath(_wing_path())

        p.end()
