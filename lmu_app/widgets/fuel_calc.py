"""Fuel Calculator overlay — bar + 5-column table (USAGE / LAPS / REFUEL / FINISH)."""
from __future__ import annotations
from collections import deque
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.utils.class_colors import CLASS_ENTRIES
from lmu_app.utils.theme import T, label_font, num_font, draw_panel
from lmu_app.widgets.base import BaseWidget, DEFAULT_SCALE

# ── Layout constants (shared with ve_calc via import) ─────────────────────
_PAD      = 5
_BH       = 15    # bar height
_LVL_H    = 10    # text-only level row height (bar hidden, level shown)
_HDR      = 9     # column header row height
_RH       = 13    # data row height
_CG       = 3     # gap between columns
_LABEL_W  = 32    # label column width
_MIN_COL_W = 35   # minimum data column width
_MIN_W    = 105   # minimum widget width

def _widget_w(n_data_cols: int) -> int:
    if n_data_cols == 0:
        return _MIN_W
    table = _LABEL_W + _CG + n_data_cols * _MIN_COL_W + (n_data_cols - 1) * _CG
    return max(_MIN_W, 2 * _PAD + table)

BASE_W = _widget_w(4)  # 240 — used as default / maximum


# ── Shared helpers ──────────────────────────────────────────────────────────

def _draw_bar(p: QPainter, x: int, y: int, w: int, h: int,
              ratio: float, col_lo: QColor, col_hi: QColor,
              label: str, val_str: str,
              show_val: bool = True) -> None:
    p.setBrush(T.TRACK); p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(x, y, w, h, 5, 5)
    fw = int(w * max(0., min(1., ratio)))
    if fw > 2:
        p.setBrush(col_hi); p.drawRoundedRect(x, y, fw, h, 5, 5)
    p.setFont(label_font(6))
    p.setPen(QColor(255, 255, 255, 200))
    p.drawText(x + 4, y, w // 2, h, Qt.AlignmentFlag.AlignVCenter, label)
    if show_val:
        p.setFont(num_font(9))
        p.setPen(QColor(T.TEXT))
        p.drawText(x, y, w - 4, h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, val_str)


def _draw_level(p: QPainter, x: int, y: int, w: int, h: int,
                label: str, val_str: str, val_col: QColor) -> None:
    """Compact text-only row: label (dim) on left, value (colored) on right."""
    p.setFont(label_font(6))
    p.setPen(QColor(T.DIM))
    p.drawText(x, y, w // 2, h, Qt.AlignmentFlag.AlignVCenter, label)
    p.setFont(num_font(9))
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


def _fuel_col(ratio: float) -> tuple[QColor, QColor]:
    if ratio < 0.10:
        c = QColor(T.CRIT); return c, c.lighter(120)
    if ratio < 0.25:
        c = QColor(T.WARN); return c, c.lighter(120)
    return QColor(T.FUEL_LO), QColor(T.FUEL_HI)


def _calc(rate: float, current: float, rem: float, safety: float):
    """(laps_on_current, refuel_needed, finish_level) — refuel/finish None outside race."""
    laps_on = (current / rate) if rate > 0 else None
    if rem > 0 and rate > 0:
        refuel = max(0., (rem + safety) * rate - current)
        finish = max(0., current - rem * rate) if refuel < 0.005 else None
        return laps_on, refuel, finish
    return laps_on, None, None


def _table_layout(refs: dict[str, str], show_usage: bool, show_laps: bool,
                  show_refuel: bool, show_finish: bool) -> tuple[int, dict[str, tuple[int, int]]]:
    """Return (widget_width, {key: (x, width)}) with each column sized to its
    own content — the widest of its header and its reference value — instead of
    splitting the width equally. Avoids dead space on short columns while
    guaranteeing long values (e.g. "XX.X %") still fit.
    """
    vis = [k for k, v in [("usage", show_usage), ("laps", show_laps),
                          ("refuel", show_refuel), ("finish", show_finish)] if v]
    if not vis:
        return _MIN_W, {"label": (_PAD, _LABEL_W)}

    fm_val = QFontMetrics(num_font(8))
    fm_hdr = QFontMetrics(label_font(6))
    widths = {
        k: max(_MIN_COL_W,
               max(fm_val.horizontalAdvance(refs.get(k, "")),
                   fm_hdr.horizontalAdvance(_HDR_NAMES[k])) + 2 * _CG)
        for k in vis
    }

    widget_w = max(_MIN_W,
                   2 * _PAD + _LABEL_W + _CG + sum(widths.values()) + (len(vis) - 1) * _CG)
    result: dict[str, tuple[int, int]] = {"label": (_PAD, _LABEL_W)}
    x = _PAD + _LABEL_W + _CG
    for k in vis:
        result[k] = (x, widths[k])
        x += widths[k] + _CG
    return widget_w, result


def _fmt_fuel(v: float) -> str:
    """One decimal up to 99.9 L; none at 100 L (the tank max) to stay 3 digits."""
    return f"{v:.0f} L" if v >= 100 else f"{v:.1f} L"


def _fmt_ref_fuel(v: float) -> str:
    return f"+{v:.0f} L" if v >= 100 else f"+{v:.1f} L"


_HDR_NAMES = {"usage": "USAGE", "laps": "LAPS", "refuel": "REFUEL", "finish": "FINISH"}

# Widest value each column must be able to render, used to size the columns.
_FUEL_REFS = {"usage": "99.9 L", "laps": "99.9", "refuel": "+99.9 L", "finish": "99.9 L"}
_VE_REFS   = {"usage": "99.9 %", "laps": "99.9", "refuel": "+99.9 %", "finish": "99.9 %"}

_VE_ENTRY_KEYS = {"HYPERCAR", "GT3"}

def _class_has_ve(vehicle_class: str) -> bool:
    """True si la classe utilise la VE — même logique de matching que class_colors."""
    if not vehicle_class:
        return False
    vc = vehicle_class.strip().upper()
    for entry in CLASS_ENTRIES:
        if entry["keywords"] and any(k in vc for k in entry["keywords"]):
            return entry["key"] in _VE_ENTRY_KEYS
    return False


# ── Widget ──────────────────────────────────────────────────────────────────

class FuelCalcWidget(BaseWidget):
    WIDGET_NAME = "Fuel Calculator"
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
        self._show_fuel_bar   = True
        self._show_fuel_level = True
        self._show_last       = True
        self._show_avg5       = True
        self._show_usage      = True
        self._show_laps       = True
        self._show_refuel     = True
        self._show_finish     = True

        self._scale        = DEFAULT_SCALE / 100.0
        self._safety_laps  = 1.0
        self._merge        = False

        self._last_total_laps   = -1
        self._fuel_at_lap_start = -1.0
        self._fuel_prev_tick    = -1.0
        self._fuel_history: deque[float] = deque(maxlen=5)
        self._last_lap_fuel     = 0.0
        self._last_session_id   = -1

        self._current_fuel   = 0.0
        self._fuel_cap       = 100.0
        self._laps_remaining = 0.0

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

    def _update(self) -> None:
        if self._merge:
            snap = self._reader.get()
            if snap.game_running:
                player_sc = next((x for x in snap.session.vehicles if x.is_player), None)
                if player_sc and player_sc.vehicle_class:
                    if _class_has_ve(player_sc.vehicle_class):
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

        if has_table:
            self._w, self._col_pos = _table_layout(
                _FUEL_REFS, self._show_usage, self._show_laps,
                self._show_refuel, self._show_finish)
        else:
            self._w, self._col_pos = _widget_w(0), {"label": (_PAD, _LABEL_W)}
        self._bw         = self._w - 2 * _PAD
        self._fuel_sec_h = fuel_h
        self._sep_h      = sep_h
        self._vis_rows   = vis_rows
        self._has_table  = has_table
        self._layout_h   = max(_PAD + fuel_h + sep_h + hdr_h + vis_rows * _RH + _PAD, _PAD * 2)
        self.setFixedSize(int(self._w * self._scale), int(self._layout_h * self._scale))

    def apply_params(self, params: dict) -> None:
        self._scale       = int(params.get("scale", DEFAULT_SCALE)) / 100.0
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

        # New session / restart (reader bumps session_id) → clear fuel history
        if s.session_id != self._last_session_id:
            self._last_session_id   = s.session_id
            self._last_total_laps   = -1
            self._fuel_history.clear()
            self._last_lap_fuel     = 0.0
            self._fuel_at_lap_start = -1.0

        self._current_fuel = v.fuel
        self._fuel_cap     = max(1.0, v.fuel_capacity)

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

        draw_panel(p, self._w, self._layout_h, self._opacity, self._bg_alpha())

        y = _PAD
        fuel_col = _fuel_col(self._current_fuel / self._fuel_cap)

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

        if not self._has_table:
            p.end(); return

        # ── Separator ──────────────────────────────────────────────────────
        if self._sep_h:
            y += 4
            p.fillRect(_PAD, y, self._bw, 1, T.FAINT)
            y += 6

        # ── Column headers ─────────────────────────────────────────────────
        p.setFont(label_font(6))
        p.setPen(QColor(T.DIM))
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

            cx, cw = self._col_pos["label"]
            p.setFont(label_font(7))
            p.setPen(QColor(T.DIM))
            p.drawText(cx, y, cw, _RH, Qt.AlignmentFlag.AlignVCenter, lbl)

            if "usage" in self._col_pos:
                cx, cw = self._col_pos["usage"]
                p.setFont(num_font(8)); p.setPen(QColor(T.TEXT))
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           _fmt_fuel(rate) if rate > 0 else "-")

            if "laps" in self._col_pos:
                cx, cw = self._col_pos["laps"]
                p.setFont(num_font(8)); p.setPen(QColor(T.TEXT))
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           f"{laps_on:.1f}" if laps_on is not None else "-")

            if "refuel" in self._col_pos:
                cx, cw = self._col_pos["refuel"]
                p.setFont(num_font(8))
                if refuel is None:
                    p.setPen(QColor(T.TEXT)); ref_str = "-"
                elif refuel < 0.005:
                    p.setPen(QColor(T.GOOD)); ref_str = "OK"
                else:
                    p.setPen(QColor(T.TEXT)); ref_str = _fmt_ref_fuel(refuel)
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, ref_str)

            if "finish" in self._col_pos:
                cx, cw = self._col_pos["finish"]
                p.setFont(num_font(8))
                if finish is None:
                    p.setPen(QColor(T.TEXT)); fin_str = "-"
                else:
                    p.setPen(QColor(T.TEXT)); fin_str = _fmt_fuel(finish)
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, fin_str)

            y += _RH

        p.end()
