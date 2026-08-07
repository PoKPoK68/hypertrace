"""VE Calculator overlay — VE bar + fuel bar + 5-column table + fuel ratio."""
from __future__ import annotations
import math
from collections import deque
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy
from hypertrace.calc.module_info import minfo
from hypertrace.calc.realtime_state import realtime_state
from hypertrace.utils.theme import T, draw_bold, label_font, num_font, draw_panel
from hypertrace.widgets.base import BaseWidget, DEFAULT_SCALE
from hypertrace.widgets.fuel_calc import (
    _BH, _LVL_H, _PAD, _HDR, _RH, _LABEL_W,
    _draw_bar, _draw_level, _fuel_col, _calc,
    _table_layout, _widget_w, _HDR_NAMES, _VE_REFS, _class_has_ve, _fmt_fuel,
    _fmt_tanks,
)


def _fmt_ve(v: float) -> str:
    """One decimal up to 99.9 %; none at 100 % (the max) to stay 3 digits."""
    return f"{v:.0f}%" if v >= 100 else f"{v:.1f}%"


def _fmt_ref_ve(v: float) -> str:
    """Signed — negative reads as surplus (you already have more than needed)."""
    return f"{v:+.0f}%" if abs(v) >= 100 else f"{v:+.1f}%"


def _ve_col(ratio: float) -> tuple[QColor, QColor]:
    """Same thresholds as the VE column in Standings: red under 10%, orange
    under 25%, green otherwise."""
    if ratio < 0.10:
        c = QColor(T.CRIT); return c, c.lighter(120)
    if ratio < 0.25:
        c = QColor(T.WARN); return c, c.lighter(120)
    return QColor(T.VE_LO), QColor(T.VE_HI)


class VECalcWidget(BaseWidget):
    WIDGET_NAME = "VE Calculator"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Appearance"},
        {"key": "opacity",      "label": "Opacity (%)",          "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 85},
        {"key": "scale",        "label": "Size (%)",             "type": "int",
         "min": 50, "max": 200, "step": 5, "default": 100},
        {"type": "separator", "label": "Calculation"},
        {"key": "safety_laps",  "label": "Safety margin (laps)", "type": "float",
         "min": 0.0, "max": 5.0, "step": 0.5, "default": 1.0},
        {"key": "avg5_reset",   "label": "Reset AVG 5",          "type": "choice",
         "default": "never", "options": [
             {"label": "Never",            "value": "never"},
             {"label": "At session start", "value": "session"},
             {"label": "On pit exit",      "value": "pit_exit"},
         ]},
        {"type": "separator", "label": "Display"},
        {"key": "show_ve_bar",     "label": "VE bar",     "type": "bool", "default": True},
        {"key": "show_ve_level",   "label": "VE level",   "type": "bool", "default": True},
        {"key": "show_fuel_bar",   "label": "Fuel bar",   "type": "bool", "default": True},
        {"key": "show_fuel_level", "label": "Fuel level", "type": "bool", "default": True},
        {"key": "show_last",   "label": "LAST row",   "type": "bool", "default": True},
        {"key": "show_avg5",   "label": "AVG 5 row",  "type": "bool", "default": True},
        {"key": "show_usage",  "label": "USAGE col",  "type": "bool", "default": True},
        {"key": "show_laps",   "label": "LAPS col",   "type": "bool", "default": True},
        {"key": "show_refuel", "label": "REFUEL col", "type": "bool", "default": True},
        {"key": "show_finish", "label": "TO END col", "type": "bool", "default": True},
        {"key": "show_tanks",  "label": "TANKS col",  "type": "bool", "default": True},
        {"key": "show_ratio",  "label": "Fuel ratio", "type": "bool", "default": True},
    ]

    def __init__(self, **kw):
        self._show_ve_bar     = True
        self._show_ve_level   = True
        self._show_fuel_bar   = True
        self._show_fuel_level = True
        self._show_last       = True
        self._show_avg5       = True
        self._show_usage      = True
        self._show_laps       = True
        self._show_refuel     = True
        self._show_finish     = True
        self._show_tanks      = True
        self._show_ratio      = True

        self._scale        = DEFAULT_SCALE / 100.0
        self._safety_laps  = 1.0
        self._merge        = False

        self._fuel_ratio    = 0.0

        self._last_lap_ve       = 0.0
        self._last_amount_used  = -1.0
        self._ve_history: deque[float] = deque(maxlen=5)

        # AVG-5 auto-reset — see fuel_calc.py for the rationale.
        self._avg5_reset       = "never"
        self._last_reset_count = None
        self._prev_in_pit      = False

        self._current_ve   = 0.0
        self._current_fuel = 0.0
        self._fuel_cap     = 100.0
        self._laps_remaining = 0.0

        self._w          = _widget_w(5)
        self._bw         = self._w - 2 * _PAD
        self._layout_h   = 147
        self._ve_sec_h   = _BH
        self._fuel_sec_h = _BH
        self._inter_h    = 4
        self._sep_h      = 10
        self._has_table  = True
        self._ratio_h    = 5 + _RH
        self._col_pos: dict[str, tuple[int, int]] = {}

        super().__init__(update_hz=1, **kw)
        self._refresh_layout()

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _update(self) -> None:
        if self._merge and realtime_state.game_running:
            player = next((v for v in minfo.vehicles.dataSet if v.is_player), None)
            vclass = player.vehicle_class if player else ""
            if vclass:
                if not _class_has_ve(vclass):
                    if self.isVisible():
                        self.hide()
                    return
            elif not self.isVisible():
                return  # class unknown, stay hidden
        super()._update()

    def start(self) -> None:
        super().start()
        if self._merge:
            self.hide()

    def set_merge(self, enabled: bool) -> None:
        self._merge = enabled

    def _refresh_layout(self) -> None:
        ve_h   = _BH if self._show_ve_bar   else (_LVL_H if self._show_ve_level   else 0)
        fuel_h = _BH if self._show_fuel_bar else (_LVL_H if self._show_fuel_level else 0)
        inter  = 4 if ve_h > 0 and fuel_h > 0 else 0
        bars_h = ve_h + inter + fuel_h

        vis_data = [k for k, v in [
            ("usage", self._show_usage), ("laps", self._show_laps),
            ("refuel", self._show_refuel), ("finish", self._show_finish),
            ("tanks", self._show_tanks)
        ] if v]
        vis_rows = (1 if self._show_last else 0) + (1 if self._show_avg5 else 0)
        has_table = vis_rows > 0 and len(vis_data) > 0
        ratio_h = (5 + _RH) if self._show_ratio else 0

        has_below = has_table or ratio_h > 0
        sep_h = 10 if bars_h > 0 and has_below else 0
        hdr_h = _HDR if has_table else 0

        if has_table or ratio_h > 0:
            self._w, self._col_pos = _table_layout(
                _VE_REFS, self._show_usage, self._show_laps,
                self._show_refuel, self._show_finish, self._show_tanks)
        else:
            self._w, self._col_pos = _widget_w(0), {"label": (_PAD, _LABEL_W)}
        self._bw         = self._w - 2 * _PAD
        self._ve_sec_h   = ve_h
        self._fuel_sec_h = fuel_h
        self._inter_h    = inter
        self._sep_h      = sep_h
        self._has_table  = has_table
        self._vis_rows   = vis_rows
        self._ratio_h    = ratio_h
        self._layout_h   = max(
            _PAD + bars_h + sep_h + hdr_h + vis_rows * _RH + ratio_h + _PAD,
            _PAD * 2
        )
        self.setFixedSize(int(self._w * self._scale), int(self._layout_h * self._scale))

    def apply_params(self, params: dict) -> None:
        self._scale       = int(params.get("scale", DEFAULT_SCALE)) / 100.0
        self._opacity     = max(0, min(100, int(params.get("opacity", 85))))
        self._safety_laps = float(params.get("safety_laps", 1.0))
        self._avg5_reset  = str(params.get("avg5_reset", "never"))

        self._show_ve_bar     = bool(params.get("show_ve_bar",     True))
        self._show_ve_level   = bool(params.get("show_ve_level",   True))
        self._show_fuel_bar   = bool(params.get("show_fuel_bar",   True))
        self._show_fuel_level = bool(params.get("show_fuel_level", True))
        self._show_last       = bool(params.get("show_last",   True))
        self._show_avg5       = bool(params.get("show_avg5",   True))
        self._show_usage      = bool(params.get("show_usage",  True))
        self._show_laps       = bool(params.get("show_laps",   True))
        self._show_refuel     = bool(params.get("show_refuel", True))
        self._show_finish     = bool(params.get("show_finish", True))
        self._show_tanks      = bool(params.get("show_tanks",  True))
        self._show_ratio      = bool(params.get("show_ratio",  True))

        self._apply_session_visibility(params)
        self._refresh_layout()
        self.update()

    def on_data(self) -> None:
        # Laps-remaining and the live fuel/VE ratio come straight from the
        # background calc (module_fuel.py) — see fuel_calc.py's on_data()
        # for the full rationale.
        self._current_ve     = minfo.energy.amountCurrent / 100.0
        self._current_fuel   = minfo.fuel.amountCurrent
        self._fuel_cap        = max(1.0, minfo.fuel.capacity)
        self._laps_remaining  = minfo.energy.lapsRemaining
        self._fuel_ratio      = minfo.hybrid.fuelEnergyRatio

        if self._avg5_reset_triggered():
            self._ve_history.clear()
            self._last_amount_used = -1.0

        # AVG 5 = rolling average of the last 5 completed laps' VE
        # consumption. amountUsedLast only changes at a lap boundary, so a
        # change is exactly a new completed-lap reading.
        used_last = minfo.energy.amountUsedLast
        if used_last != self._last_amount_used:
            if self._last_amount_used >= 0 and 0.001 < used_last < 100.0:
                self._ve_history.append(used_last)
            self._last_amount_used = used_last
        self._last_lap_ve = used_last

        self.update()

    def _avg5_reset_triggered(self) -> bool:
        """See FuelCalcWidget._avg5_reset_triggered — same logic, VE history."""
        triggered = False

        reset_count = minfo.stint.resetCount
        if reset_count != self._last_reset_count:
            if self._avg5_reset == "session" and self._last_reset_count is not None:
                triggered = True
            self._last_reset_count = reset_count

        player = next((v for v in minfo.vehicles.dataSet if v.is_player), None)
        in_pit = player.in_pit_lane if player else False
        if self._avg5_reset == "pit_exit" and self._prev_in_pit and not in_pit:
            triggered = True
        self._prev_in_pit = in_pit

        return triggered

    def _avg5_ve(self) -> float:
        return sum(self._ve_history) / len(self._ve_history) if self._ve_history else 0.0

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)

        draw_panel(p, self._w, self._layout_h, self._opacity, self._bg_alpha())

        y = _PAD
        fuel_col = _fuel_col(self._current_fuel / self._fuel_cap)
        ve_col   = _ve_col(self._current_ve)

        # ── VE bar / level ─────────────────────────────────────────────────
        if self._show_ve_bar:
            _draw_bar(p, _PAD, y, self._bw, _BH, self._current_ve,
                      ve_col[0], ve_col[1],
                      "VE", _fmt_ve(self._current_ve * 100),
                      show_val=self._show_ve_level)
            y += _BH
        elif self._show_ve_level:
            _draw_level(p, _PAD, y, self._bw, _LVL_H,
                        "VE", _fmt_ve(self._current_ve * 100), ve_col[0])
            y += _LVL_H

        if self._inter_h:
            y += self._inter_h

        # ── Fuel bar / level ───────────────────────────────────────────────
        if self._show_fuel_bar:
            _draw_bar(p, _PAD, y, self._bw, _BH,
                      self._current_fuel / self._fuel_cap,
                      fuel_col[0], fuel_col[1],
                      "FUEL", _fmt_fuel(self._current_fuel),
                      show_val=self._show_fuel_level)
            y += _BH
        elif self._show_fuel_level:
            _draw_level(p, _PAD, y, self._bw, _LVL_H,
                        "FUEL", _fmt_fuel(self._current_fuel), fuel_col[0])
            y += _LVL_H

        if not (self._has_table or self._ratio_h > 0):
            p.end(); return

        # ── Separator ──────────────────────────────────────────────────────
        if self._sep_h:
            y += 4
            p.fillRect(_PAD, y, self._bw, 1, T.FAINT)
            y += 6

        if self._has_table:
            # ── Column headers ──────────────────────────────────────────────
            p.setFont(label_font(7))
            p.setPen(QColor(T.DIM))
            for k, (cx, cw) in self._col_pos.items():
                if k != "label":
                    draw_bold(p, lambda cx=cx, cw=cw, k=k: p.drawText(
                        cx, y, cw, _HDR,
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                        _HDR_NAMES[k]))
            y += _HDR

            # ── VE data rows ────────────────────────────────────────────────
            rem     = self._laps_remaining
            sfty    = self._safety_laps
            cur_pct = self._current_ve * 100.

            rows = []
            if self._show_last: rows.append(("LAST", self._last_lap_ve))
            if self._show_avg5: rows.append(("AVG 5", self._avg5_ve()))

            for lbl, ve_pct in rows:
                # VE has no liter tank — its "capacity" is always 100%.
                laps_on, refuel_pct, to_end_pct = _calc(ve_pct, cur_pct, rem, sfty, 100.0)

                cx, cw = self._col_pos["label"]
                p.setFont(label_font(8)); p.setPen(QColor(T.DIM))
                draw_bold(p, lambda cx=cx, cw=cw, lbl=lbl: p.drawText(
                    cx, y, cw, _RH, Qt.AlignmentFlag.AlignVCenter, lbl))

                if "usage" in self._col_pos:
                    cx, cw = self._col_pos["usage"]
                    p.setFont(num_font(9)); p.setPen(QColor(T.TEXT))
                    p.drawText(cx, y, cw, _RH,
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                               _fmt_ve(ve_pct) if ve_pct > 0.001 else "-")

                if "laps" in self._col_pos:
                    cx, cw = self._col_pos["laps"]
                    p.setFont(num_font(9)); p.setPen(QColor(T.TEXT))
                    p.drawText(cx, y, cw, _RH,
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                               f"{laps_on:.1f}" if laps_on is not None else "-")

                if "refuel" in self._col_pos:
                    cx, cw = self._col_pos["refuel"]
                    p.setFont(num_font(9))
                    if refuel_pct is None:
                        p.setPen(QColor(T.TEXT)); ref_str = "-"
                    else:
                        p.setPen(QColor(T.GOOD) if refuel_pct <= 0 else QColor(T.TEXT))
                        ref_str = _fmt_ref_ve(refuel_pct)
                    p.drawText(cx, y, cw, _RH,
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                               ref_str)

                if "finish" in self._col_pos:
                    cx, cw = self._col_pos["finish"]
                    p.setFont(num_font(9))
                    if to_end_pct is None:
                        p.setPen(QColor(T.TEXT)); fin_str = "-"
                    else:
                        p.setPen(QColor(T.GOOD) if to_end_pct <= 0 else QColor(T.TEXT))
                        fin_str = _fmt_ref_ve(to_end_pct)
                    p.drawText(cx, y, cw, _RH,
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                               fin_str)

                if "tanks" in self._col_pos:
                    cx, cw = self._col_pos["tanks"]
                    p.setFont(num_font(9))
                    if to_end_pct is None:
                        p.setPen(QColor(T.TEXT)); tanks_str = "-"
                    else:
                        p.setPen(QColor(T.GOOD) if to_end_pct <= 0 else QColor(T.TEXT))
                        tanks_str = _fmt_tanks(to_end_pct / 100.0)
                    p.drawText(cx, y, cw, _RH,
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                               tanks_str)

                y += _RH

        # ── Fuel ratio row ─────────────────────────────────────────────────
        if self._ratio_h:
            y += 5
            ratio = self._fuel_ratio
            ratio_str = f"{math.ceil(ratio * 100) / 100:.2f}" if ratio > 0 else "-"
            p.setFont(label_font(8)); p.setPen(QColor(T.DIM))
            draw_bold(p, lambda: p.drawText(
                _PAD, y, self._bw // 2, _RH, Qt.AlignmentFlag.AlignVCenter, "FUEL RATIO"))
            p.setFont(num_font(9)); p.setPen(QColor(T.TEXT))
            p.drawText(_PAD, y, self._bw, _RH,
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, ratio_str)

        p.end()
