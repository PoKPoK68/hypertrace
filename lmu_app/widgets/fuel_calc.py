"""Fuel Calculator overlay — bar + 5-column table (USAGE / LAPS / REFUEL / FINISH)."""
from __future__ import annotations
from collections import deque
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget

# ── Layout constants (shared with ve_calc via import) ─────────────────────
_PAD      = 7
_BH       = 22    # bar height
_LVL_H    = 14    # text-only level row height (bar hidden, level shown)
_HDR      = 13    # column header row height
_RH       = 19    # data row height
_CG       = 4     # gap between columns
_LABEL_W  = 38    # label column width — fits "AVG 5" at 7pt bold
_MIN_COL_W = 43   # minimum data column width
_MIN_W    = 150   # minimum widget width (bar-only / few-columns mode)

def _widget_w(n_data_cols: int) -> int:
    """Widget width for n visible data columns (>=150, grows by ~43px per col above 2)."""
    if n_data_cols == 0:
        return _MIN_W
    table = _LABEL_W + _CG + n_data_cols * _MIN_COL_W + (n_data_cols - 1) * _CG
    return max(_MIN_W, 2 * _PAD + table)

BASE_W = _widget_w(4)  # 240 — used as default / maximum

# ── Colors (shared with ve_calc) ───────────────────────────────────────────
_C_TRACK     = QColor(35,  35,  35)
_C_FUEL_OK   = QColor(30,  100, 210)
_C_FUEL_WARN = QColor(210, 150, 0)
_C_FUEL_CRIT = QColor(210, 40,  40)
_C_VE        = QColor(50,  190, 80)
_C_LABEL     = QColor(110, 110, 110)
_C_VALUE     = QColor(220, 220, 220)
_C_GOOD      = QColor(80,  210, 80)
_C_SEP       = QColor(70,  70,  70, 180)


# ── Shared helpers ──────────────────────────────────────────────────────────

def _draw_bar(p: QPainter, x: int, y: int, w: int, h: int,
              ratio: float, col: QColor, label: str, val_str: str,
              show_val: bool = True) -> None:
    p.setBrush(_C_TRACK); p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(x, y, w, h, 4, 4)
    fw = int(w * max(0., min(1., ratio)))
    if fw > 2:
        g = QLinearGradient(x, y, x + fw, y)
        g.setColorAt(0., col); g.setColorAt(1., col.lighter(130))
        p.setBrush(g); p.drawRoundedRect(x, y, fw, h, 4, 4)
    p.setFont(QFont("Monospace", 7, QFont.Weight.Bold))
    p.setPen(QColor(255, 255, 255, 200))
    p.drawText(x + 5, y, w // 2, h, Qt.AlignmentFlag.AlignVCenter, label)
    if show_val:
        p.drawText(x, y, w - 5, h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, val_str)


def _draw_level(p: QPainter, x: int, y: int, w: int, h: int,
                label: str, val_str: str, val_col: QColor) -> None:
    """Compact text-only row: label (dim) on left, value (colored) on right."""
    p.setFont(QFont("Monospace", 7, QFont.Weight.Bold))
    p.setPen(_C_LABEL)
    p.drawText(x, y, w // 2, h, Qt.AlignmentFlag.AlignVCenter, label)
    p.setPen(val_col)
    p.drawText(x, y, w, h,
               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, val_str)


def _laps_remaining(s, player) -> float:
    if s.session_type < 10:
        return 0.0
    if s.max_laps > 0:
        return max(0.0, s.max_laps - player.total_laps)
    if s.session_time_remaining > 0:
        avg_lap = player.estimated_lap_time
        if avg_lap <= 0:
            bests = [v.best_lap for v in s.vehicles if v.best_lap > 10]
            avg_lap = min(bests) if bests else 120.0
        return s.session_time_remaining / avg_lap
    return 0.0


def _fuel_col(ratio: float) -> QColor:
    return (_C_FUEL_CRIT if ratio < 0.10 else
            _C_FUEL_WARN if ratio < 0.25 else _C_FUEL_OK)


def _calc(rate: float, current: float, rem: float, safety: float):
    """(laps_on_current, refuel_needed, finish_level) — refuel/finish None outside race."""
    laps_on = (current / rate) if rate > 0 else None
    if rem > 0 and rate > 0:
        refuel = max(0., (rem + safety) * rate - current)
        finish = max(0., current + refuel - rem * rate)
        return laps_on, refuel, finish
    return laps_on, None, None


def _col_layout(widget_w: int, show_usage: bool, show_laps: bool,
                show_refuel: bool, show_finish: bool) -> dict[str, tuple[int, int]]:
    """Return {key: (x, width)} for visible table columns (includes 'label')."""
    vis = [k for k, v in [("usage", show_usage), ("laps", show_laps),
                            ("refuel", show_refuel), ("finish", show_finish)] if v]
    avail = widget_w - 2 * _PAD - _LABEL_W - _CG
    n = len(vis)
    col_w = (avail - (n - 1) * _CG) // n if n > 0 else avail
    result: dict[str, tuple[int, int]] = {"label": (_PAD, _LABEL_W)}
    x = _PAD + _LABEL_W + _CG
    for k in vis:
        result[k] = (x, col_w)
        x += col_w + _CG
    return result


def _fmt_fuel(v: float) -> str:
    return f"{v:.0f} L" if v >= 10 else f"{v:.1f} L"


def _fmt_ref_fuel(v: float) -> str:
    return f"+{v:.0f} L" if v >= 10 else f"+{v:.1f} L"


_HDR_NAMES = {"usage": "USAGE", "laps": "LAPS", "refuel": "REFUEL", "finish": "FINISH"}

# Classes that use Virtual Energy in LMU — these show the VE calculator in merge mode
_VE_CLASSES = {"LMH", "GTP", "LMGT3"}

def _class_has_ve(vehicle_class: str) -> bool:
    cls = vehicle_class.upper()
    return any(k in cls for k in _VE_CLASSES)


# ── Widget ──────────────────────────────────────────────────────────────────

class FuelCalcWidget(BaseWidget):
    WIDGET_NAME = "Fuel Calculator"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Window"},
        {"key": "opacity",      "label": "Opacity (%)",          "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 85},
        {"key": "scale",        "label": "Size (%)",             "type": "int",
         "min": 50, "max": 200, "step": 5, "default": 100},
        {"type": "separator", "label": "Calculation"},
        {"key": "safety_laps",  "label": "Safety margin (laps)", "type": "float",
         "min": 0.0, "max": 5.0, "step": 0.5, "default": 1.0},
        {"type": "separator", "label": "Display"},
        {"key": "show_fuel_bar",   "label": "Fuel bar",   "type": "bool", "default": True},
        {"key": "show_fuel_level", "label": "Fuel level", "type": "bool", "default": True},
        {"key": "show_last",   "label": "LAST row",   "type": "bool", "default": True},
        {"key": "show_avg5",   "label": "AVG 5 row",  "type": "bool", "default": True},
        {"key": "show_usage",  "label": "USAGE col",  "type": "bool", "default": True},
        {"key": "show_laps",   "label": "LAPS col",   "type": "bool", "default": True},
        {"key": "show_refuel", "label": "REFUEL col", "type": "bool", "default": True},
        {"key": "show_finish", "label": "FINISH col", "type": "bool", "default": True},
    ]

    def __init__(self, reader: DataReader, **kw):
        # Display flags (match CONFIG_SCHEMA defaults)
        self._show_fuel_bar   = True
        self._show_fuel_level = True
        self._show_last       = True
        self._show_avg5       = True
        self._show_usage      = True
        self._show_laps       = True
        self._show_refuel     = True
        self._show_finish     = True

        self._scale        = 1.0
        self._safety_laps  = 1.0
        self._merge        = False

        self._last_total_laps   = -1
        self._fuel_at_lap_start = -1.0
        self._fuel_prev_tick    = -1.0
        self._fuel_history: deque[float] = deque(maxlen=5)
        self._last_lap_fuel     = 0.0

        self._current_fuel   = 0.0
        self._fuel_cap       = 100.0
        self._laps_remaining = 0.0

        # Computed layout state (set by _refresh_layout)
        self._w         = BASE_W
        self._bw        = BASE_W - 2 * _PAD
        self._layout_h  = 97
        self._has_table = True
        self._fuel_sec_h = _BH
        self._sep_h     = 10
        self._col_pos: dict[str, tuple[int, int]] = {}

        super().__init__(reader, update_hz=10, **kw)
        self._refresh_layout()

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def start(self) -> None:
        super().start()
        if self._merge:
            self.hide()  # on_data will show when VE is absent

    def set_merge(self, enabled: bool) -> None:
        self._merge = enabled

    def _refresh_layout(self) -> None:
        sf_bar = self._show_fuel_bar
        sf_lvl = self._show_fuel_level
        fuel_h = _BH if sf_bar else (_LVL_H if sf_lvl else 0)

        vis_data = [k for k, v in [
            ("usage", self._show_usage), ("laps", self._show_laps),
            ("refuel", self._show_refuel), ("finish", self._show_finish)
        ] if v]
        vis_rows = (1 if self._show_last else 0) + (1 if self._show_avg5 else 0)
        has_table = vis_rows > 0 and len(vis_data) > 0

        sep_h = 10 if fuel_h > 0 and has_table else 0
        hdr_h = _HDR if has_table else 0

        self._w          = _widget_w(len(vis_data)) if has_table else _widget_w(0)
        self._bw         = self._w - 2 * _PAD
        self._fuel_sec_h = fuel_h
        self._sep_h      = sep_h
        self._vis_rows   = vis_rows
        self._has_table  = has_table
        self._layout_h   = max(_PAD + fuel_h + sep_h + hdr_h + vis_rows * _RH + _PAD, _PAD * 2)
        self._col_pos    = _col_layout(self._w, self._show_usage, self._show_laps,
                                       self._show_refuel, self._show_finish)

        self.setFixedSize(int(self._w * self._scale), int(self._layout_h * self._scale))

    def apply_params(self, params: dict) -> None:
        self._scale       = int(params.get("scale", 100)) / 100.0
        self._opacity     = max(0, min(100, int(params.get("opacity", 85))))
        self._safety_laps = float(params.get("safety_laps", 1.0))

        self._show_fuel_bar   = bool(params.get("show_fuel_bar",   True))
        self._show_fuel_level = bool(params.get("show_fuel_level", True))
        self._show_last       = bool(params.get("show_last",   True))
        self._show_avg5       = bool(params.get("show_avg5",   True))
        self._show_usage      = bool(params.get("show_usage",  True))
        self._show_laps       = bool(params.get("show_laps",   True))
        self._show_refuel     = bool(params.get("show_refuel", True))
        self._show_finish     = bool(params.get("show_finish", True))

        self._refresh_layout()
        self.update()

    def on_data(self, snap: LMUSnapshot) -> None:
        v = snap.vehicle
        s = snap.session
        player = next((x for x in s.vehicles if x.is_player), None)

        self._current_fuel = v.fuel
        self._fuel_cap     = max(1.0, v.fuel_capacity)

        if self._merge:
            player_sc = next((x for x in s.vehicles if x.is_player), None)
            if player_sc and player_sc.vehicle_class:
                self.setVisible(not _class_has_ve(player_sc.vehicle_class))

        if player:
            if self._fuel_prev_tick >= 0 and (v.fuel - self._fuel_prev_tick) > 2.0:
                self._fuel_at_lap_start = v.fuel

            if self._last_total_laps < 0:
                self._last_total_laps   = player.total_laps
                self._fuel_at_lap_start = v.fuel
            elif player.total_laps > self._last_total_laps:
                if self._fuel_at_lap_start >= 0:
                    consumed = self._fuel_at_lap_start - v.fuel
                    if 0.05 < consumed < self._fuel_cap * 0.8:
                        self._fuel_history.append(consumed)
                        self._last_lap_fuel = consumed
                self._fuel_at_lap_start = v.fuel
                self._last_total_laps   = player.total_laps

            self._laps_remaining = _laps_remaining(s, player)

        self._fuel_prev_tick = v.fuel
        self.update()

    def _avg5(self) -> float:
        return sum(self._fuel_history) / len(self._fuel_history) if self._fuel_history else 0.0

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)

        p.setBrush(QColor(10, 10, 10, self._bg_alpha()))
        p.setPen(self._border_pen())
        p.drawRoundedRect(0, 0, self._w, self._layout_h, 8, 8)

        y = _PAD
        fuel_ratio = self._current_fuel / self._fuel_cap

        # ── Fuel bar / level ───────────────────────────────────────────────
        if self._show_fuel_bar:
            _draw_bar(p, _PAD, y, self._bw, _BH, fuel_ratio, _fuel_col(fuel_ratio),
                      "FUEL", f"{self._current_fuel:.1f} L",
                      show_val=self._show_fuel_level)
            y += _BH
        elif self._show_fuel_level:
            _draw_level(p, _PAD, y, self._bw, _LVL_H,
                        "FUEL", f"{self._current_fuel:.1f} L", _fuel_col(fuel_ratio))
            y += _LVL_H

        if not self._has_table:
            p.end(); return

        # ── Separator ──────────────────────────────────────────────────────
        if self._sep_h:
            y += 4
            p.setBrush(_C_SEP); p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(_PAD, y, self._bw, 1)
            y += 6

        # ── Column headers ─────────────────────────────────────────────────
        p.setFont(QFont("Monospace", 6, QFont.Weight.Bold))
        p.setPen(_C_LABEL)
        for k, (cx, cw) in self._col_pos.items():
            if k != "label":
                p.drawText(cx, y, cw, _HDR,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           _HDR_NAMES[k])
        y += _HDR

        # ── Data rows ──────────────────────────────────────────────────────
        rem  = self._laps_remaining
        sfty = self._safety_laps
        rows = []
        if self._show_last: rows.append(("LAST",  self._last_lap_fuel))
        if self._show_avg5: rows.append(("AVG 5", self._avg5()))

        for lbl, rate in rows:
            laps_on, refuel, finish = _calc(rate, self._current_fuel, rem, sfty)
            p.setFont(QFont("Monospace", 7, QFont.Weight.Bold))

            cx, cw = self._col_pos["label"]
            p.setPen(_C_LABEL)
            p.drawText(cx, y, cw, _RH, Qt.AlignmentFlag.AlignVCenter, lbl)

            if "usage" in self._col_pos:
                cx, cw = self._col_pos["usage"]
                p.setPen(_C_VALUE)
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           _fmt_fuel(rate) if rate > 0 else "---")

            if "laps" in self._col_pos:
                cx, cw = self._col_pos["laps"]
                p.setPen(_C_VALUE)
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           f"{laps_on:.1f}" if laps_on is not None else "---")

            if "refuel" in self._col_pos:
                cx, cw = self._col_pos["refuel"]
                if refuel is None:
                    p.setPen(_C_LABEL); ref_str = "---"
                elif refuel < 0.005:
                    p.setPen(_C_GOOD); ref_str = "OK"
                else:
                    p.setPen(_C_VALUE); ref_str = _fmt_ref_fuel(refuel)
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, ref_str)

            if "finish" in self._col_pos:
                cx, cw = self._col_pos["finish"]
                if finish is None:
                    p.setPen(_C_LABEL); fin_str = "---"
                else:
                    p.setPen(_C_VALUE); fin_str = _fmt_fuel(finish)
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, fin_str)

            y += _RH

        p.end()
