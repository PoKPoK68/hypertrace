"""Battery overlay — hybrid SoC management.

Standalone widget, not built on the Fuel/VE calculators' table architecture —
this only ever shows one resource (SoC) with no REFUEL/TO END/TANKS concepts
(a battery isn't topped up mid-stint the way fuel is). The SoC bar reuses
_draw_bar from fuel_calc.py so it reads as the same kind of gauge as the
calculators; everything else here is its own compact layout.

Not auto-hidden by vehicle class — LMU's hybrid fields (SoC, regen, motor map)
are only meaningful for Hypercar, so a non-Hypercar car just reads 0%/0kW/0/0
here rather than the widget hiding itself; toggle it off by hand if that's
not wanted.
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy

from hypertrace.calc.module_info import minfo
from hypertrace.utils.theme import T
from hypertrace.widgets.base import BaseWidget, DEFAULT_SCALE
from hypertrace.widgets.fuel_calc import _draw_bar, _draw_level

_WIDGET_W = 130
_PAD      = 6
_BH       = 15   # SoC bar height
_RH       = 15   # text row height
_ROW_GAP  = 4    # gap between the bar and the rows below it


def _fmt_soc(v: float) -> str:
    return f"{v:.0f}%"


def _fmt_soc_delta(v: float) -> str:
    """Signed — a lap can net-gain charge when it regens more than it deploys."""
    return f"{v:+.1f}%"


def _fmt_kw(v: float) -> str:
    return f"{v:.0f}kW"


def _fmt_map(cur: int, mx: int) -> str:
    return f"{cur}/{mx}" if mx > 0 else "-"


def _soc_col(ratio: float) -> tuple[QColor, QColor]:
    """Same low-charge warning thresholds as the Fuel/VE bars (_fuel_col/_ve_col
    in fuel_calc.py/ve_calc.py) — not imported, since duplicating a 5-line
    threshold check doesn't pull in the table architecture this widget is
    otherwise deliberately independent of."""
    if ratio < 0.10:
        c = QColor(T.CRIT); return c, c.lighter(120)
    if ratio < 0.25:
        c = QColor(T.WARN); return c, c.lighter(120)
    return QColor(T.BATTERY_LO), QColor(T.BATTERY_HI)


def _delta_col(v: float) -> QColor:
    """Highlight a net-positive lap (gained charge) — the common case (net
    drain) stays plain text rather than reading as a problem by default."""
    return QColor(T.GOOD) if v > 0 else QColor(T.TEXT)


class BatteryWidget(BaseWidget):
    WIDGET_NAME = "Battery"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Appearance"},
        {"key": "opacity", "label": "Opacity (%)", "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 85},
        {"key": "scale",   "label": "Size (%)",    "type": "int",
         "min": 50, "max": 200, "step": 5, "default": 100},
        {"type": "separator", "label": "Display"},
        {"key": "show_soc_bar",  "label": "SoC bar",       "type": "bool", "default": True},
        {"key": "show_last_lap", "label": "LAST LAP row",  "type": "bool", "default": True},
        {"key": "show_this_lap", "label": "THIS LAP row",  "type": "bool", "default": True},
        {"key": "show_deploy",   "label": "DEPLOY row",    "type": "bool", "default": True},
        {"key": "show_regen",    "label": "REGEN row",     "type": "bool", "default": True},
    ]

    def __init__(self, **kw):
        self._scale        = DEFAULT_SCALE / 100.0
        self._opacity      = 85
        self._show_soc_bar  = True
        self._show_last_lap = True
        self._show_this_lap = True
        self._show_deploy   = True
        self._show_regen    = True

        self._soc            = 0.0
        self._last_lap_used   = 0.0
        self._this_lap_used   = 0.0
        self._regen_kw        = 0.0
        self._motor_map       = 0
        self._motor_map_max   = 0

        self._layout_h = 0
        super().__init__(update_hz=5, **kw)
        self._refresh_layout()

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _refresh_layout(self) -> None:
        bar_h = _BH + _ROW_GAP if self._show_soc_bar else 0
        n_rows = sum((self._show_last_lap, self._show_this_lap,
                      self._show_deploy, self._show_regen))
        self._layout_h = _PAD * 2 + bar_h + n_rows * _RH
        self.setFixedSize(int(_WIDGET_W * self._scale), int(self._layout_h * self._scale))

    def apply_params(self, params: dict) -> None:
        self._scale        = int(params.get("scale", DEFAULT_SCALE)) / 100.0
        self._opacity       = max(0, min(100, int(params.get("opacity", 85))))
        self._show_soc_bar  = bool(params.get("show_soc_bar",  True))
        self._show_last_lap = bool(params.get("show_last_lap", True))
        self._show_this_lap = bool(params.get("show_this_lap", True))
        self._show_deploy   = bool(params.get("show_deploy",   True))
        self._show_regen    = bool(params.get("show_regen",    True))
        self._apply_session_visibility(params)
        self._refresh_layout()
        self.update()

    def on_data(self) -> None:
        b = minfo.battery
        h = minfo.hybrid
        self._soc            = b.amountCurrent
        self._last_lap_used   = b.amountUsedLast
        self._this_lap_used   = b.amountUsedCurrent
        self._regen_kw        = h.regenKw
        self._motor_map       = h.motorMap
        self._motor_map_max   = h.motorMapMax
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)
        self._draw_panel(p, _WIDGET_W, self._layout_h)

        bw = _WIDGET_W - 2 * _PAD
        y  = _PAD

        if self._show_soc_bar:
            ratio = max(0.0, min(1.0, self._soc / 100.0))
            col_lo, col_hi = _soc_col(ratio)
            _draw_bar(p, _PAD, y, bw, _BH, ratio, col_lo, col_hi,
                      "SOC", _fmt_soc(self._soc))
            y += _BH + _ROW_GAP

        rows = []
        if self._show_last_lap:
            rows.append(("LAST LAP", _fmt_soc_delta(self._last_lap_used), _delta_col(self._last_lap_used)))
        if self._show_this_lap:
            rows.append(("THIS LAP", _fmt_soc_delta(self._this_lap_used), _delta_col(self._this_lap_used)))
        if self._show_deploy:
            rows.append(("DEPLOY", _fmt_map(self._motor_map, self._motor_map_max), QColor(T.TEXT)))
        if self._show_regen:
            rows.append(("REGEN", _fmt_kw(self._regen_kw), QColor(T.TEXT)))

        for label, val, col in rows:
            _draw_level(p, _PAD, y, bw, _RH, label, val, col)
            y += _RH

        p.end()
