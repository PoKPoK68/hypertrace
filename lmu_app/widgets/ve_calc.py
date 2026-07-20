"""VE Calculator overlay — VE bar + fuel bar + 5-column table + fuel ratio."""
from __future__ import annotations
import math
from collections import deque
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.utils.theme import T, label_font, num_font, draw_panel
from lmu_app.widgets.base import BaseWidget, DEFAULT_SCALE
from lmu_app.widgets.fuel_calc import (
    _BH, _LVL_H, _PAD, _HDR, _RH, _LABEL_W,
    _draw_bar, _draw_level, _laps_remaining, _fuel_col, _calc,
    _table_layout, _widget_w, _HDR_NAMES, _VE_REFS, _class_has_ve, _fmt_fuel,
)


def _fmt_ve(v: float) -> str:
    """One decimal up to 99.9 %; none at 100 % (the max) to stay 3 digits."""
    return f"{v:.0f}%" if v >= 100 else f"{v:.1f}%"


def _fmt_ref_ve(v: float) -> str:
    return f"+{v:.0f}%" if v >= 100 else f"+{v:.1f}%"


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
        {"key": "show_finish", "label": "FINISH col", "type": "bool", "default": True},
        {"key": "show_ratio",  "label": "Fuel ratio", "type": "bool", "default": True},
    ]

    def __init__(self, reader: DataReader, **kw):
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
        self._show_ratio      = True

        self._scale        = DEFAULT_SCALE / 100.0
        self._safety_laps  = 1.0
        self._merge        = False

        self._last_total_laps   = -1
        self._ve_at_lap_start   = -1.0
        self._fuel_at_lap_start = -1.0
        self._fuel_prev_tick    = -1.0
        self._last_session_id   = -1

        self._ve_history:  deque[float] = deque(maxlen=5)
        self._last_lap_ratio = 0.0

        self._last_lap_ve   = 0.0
        self._last_lap_fuel = 0.0

        self._current_ve   = 0.0
        self._current_fuel = 0.0
        self._fuel_cap     = 100.0
        self._laps_remaining = 0.0

        self._w          = _widget_w(4)
        self._bw         = self._w - 2 * _PAD
        self._layout_h   = 147
        self._ve_sec_h   = _BH
        self._fuel_sec_h = _BH
        self._inter_h    = 4
        self._sep_h      = 10
        self._has_table  = True
        self._ratio_h    = 5 + _RH
        self._col_pos: dict[str, tuple[int, int]] = {}

        super().__init__(reader, update_hz=10, **kw)
        self._refresh_layout()

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _update(self) -> None:
        if self._merge:
            snap = self._reader.get()
            if snap.game_running:
                player_sc = next((x for x in snap.session.vehicles if x.is_player), None)
                if player_sc and player_sc.vehicle_class:
                    if not _class_has_ve(player_sc.vehicle_class):
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
            ("refuel", self._show_refuel), ("finish", self._show_finish)
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
                self._show_refuel, self._show_finish)
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
        self._show_ratio      = bool(params.get("show_ratio",  True))

        self._refresh_layout()
        self.update()

    def on_data(self, snap: LMUSnapshot) -> None:
        v = snap.vehicle
        s = snap.session
        player = next((x for x in s.vehicles if x.is_player), None)

        # New session / restart (reader bumps session_id) → clear VE history
        if s.session_id != self._last_session_id:
            self._last_session_id   = s.session_id
            self._last_total_laps   = -1
            self._ve_history.clear()
            self._last_lap_ve       = 0.0
            self._last_lap_fuel     = 0.0
            self._last_lap_ratio    = 0.0
            self._ve_at_lap_start   = -1.0
            self._fuel_at_lap_start = -1.0

        self._current_ve   = v.virtual_energy
        self._current_fuel = v.fuel
        self._fuel_cap     = max(1.0, v.fuel_capacity)

        if player:
            if self._fuel_prev_tick >= 0 and (v.fuel - self._fuel_prev_tick) > 2.0:
                self._fuel_at_lap_start = v.fuel
            if self._ve_at_lap_start >= 0 and (v.virtual_energy - self._ve_at_lap_start) > 0.05:
                self._ve_at_lap_start = v.virtual_energy

            if self._last_total_laps < 0:
                self._last_total_laps   = player.total_laps
                self._ve_at_lap_start   = v.virtual_energy
                self._fuel_at_lap_start = v.fuel
            elif player.total_laps > self._last_total_laps:
                ve_consumed   = self._ve_at_lap_start - v.virtual_energy
                fuel_consumed = self._fuel_at_lap_start - v.fuel

                self._ve_history.append(ve_consumed)
                self._last_lap_ve = ve_consumed

                if fuel_consumed > 0.05:
                    self._last_lap_fuel = fuel_consumed

                if ve_consumed > 0.001 and fuel_consumed > 0.05:
                    self._last_lap_ratio = fuel_consumed / (ve_consumed * 100.0)

                self._ve_at_lap_start   = v.virtual_energy
                self._fuel_at_lap_start = v.fuel
                self._last_total_laps   = player.total_laps

            self._laps_remaining = _laps_remaining(s, player)

        self._fuel_prev_tick = v.fuel
        self.update()

    def _avg5_ve(self) -> float:
        return sum(self._ve_history) / len(self._ve_history) if self._ve_history else 0.0

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)

        draw_panel(p, self._w, self._layout_h, self._opacity, self._bg_alpha())

        y = _PAD
        fuel_col = _fuel_col(self._current_fuel / self._fuel_cap)

        # ── VE bar / level ─────────────────────────────────────────────────
        if self._show_ve_bar:
            _draw_bar(p, _PAD, y, self._bw, _BH, self._current_ve,
                      QColor(T.VE_LO), QColor(T.VE_HI),
                      "VE", _fmt_ve(self._current_ve * 100),
                      show_val=self._show_ve_level)
            y += _BH
        elif self._show_ve_level:
            _draw_level(p, _PAD, y, self._bw, _LVL_H,
                        "VE", _fmt_ve(self._current_ve * 100), QColor(T.VE_LO))
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
                    p.drawText(cx, y, cw, _HDR,
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                               _HDR_NAMES[k])
            y += _HDR

            # ── VE data rows ────────────────────────────────────────────────
            rem     = self._laps_remaining
            sfty    = self._safety_laps
            cur_pct = self._current_ve * 100.

            rows = []
            if self._show_last: rows.append(("LAST",  self._last_lap_ve))
            if self._show_avg5: rows.append(("AVG 5", self._avg5_ve()))

            for lbl, ve_frac in rows:
                ve_pct = ve_frac * 100.
                laps_on, refuel_pct, finish_pct = _calc(ve_pct, cur_pct, rem, sfty)

                cx, cw = self._col_pos["label"]
                p.setFont(label_font(8)); p.setPen(QColor(T.DIM))
                p.drawText(cx, y, cw, _RH, Qt.AlignmentFlag.AlignVCenter, lbl)

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
                    elif refuel_pct < 0.05:
                        p.setPen(QColor(T.GOOD)); ref_str = "OK"
                    else:
                        p.setPen(QColor(T.TEXT)); ref_str = _fmt_ref_ve(refuel_pct)
                    p.drawText(cx, y, cw, _RH,
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                               ref_str)

                if "finish" in self._col_pos:
                    cx, cw = self._col_pos["finish"]
                    p.setFont(num_font(9))
                    if finish_pct is None:
                        p.setPen(QColor(T.TEXT)); fin_str = "-"
                    else:
                        p.setPen(QColor(T.TEXT)); fin_str = _fmt_ve(finish_pct)
                    p.drawText(cx, y, cw, _RH,
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                               fin_str)

                y += _RH

        # ── Fuel ratio row ─────────────────────────────────────────────────
        if self._ratio_h:
            y += 5
            ratio = self._last_lap_ratio
            ratio_str = f"{math.ceil(ratio * 100) / 100:.2f}" if ratio > 0 else "-"
            p.setFont(label_font(8)); p.setPen(QColor(T.DIM))
            p.drawText(_PAD, y, self._bw // 2, _RH, Qt.AlignmentFlag.AlignVCenter, "FUEL RATIO")
            p.setFont(num_font(9)); p.setPen(QColor(T.TEXT))
            p.drawText(_PAD, y, self._bw, _RH,
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, ratio_str)

        p.end()
