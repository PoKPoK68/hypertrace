"""Fuel Calculator overlay — bar + 5-column table (USAGE / LAPS / REFUEL / FINISH)."""
from __future__ import annotations
from collections import deque
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import QSizePolicy
from hypertrace.calc.module_info import minfo
from hypertrace.calc.realtime_state import realtime_state
from hypertrace.utils.class_colors import CLASS_ENTRIES
from hypertrace.utils.theme import T, label_font, num_font, draw_panel
from hypertrace.widgets.base import BaseWidget, DEFAULT_SCALE

# ── Layout constants (shared with ve_calc via import) ─────────────────────
_PAD      = 6
_BH       = 17    # bar height
_LVL_H    = 11    # text-only level row height (bar hidden, level shown)
_HDR      = 10    # column header row height
_RH       = 15    # data row height
_CG       = 3     # gap between columns
_LABEL_W  = 37    # label column width
_MIN_COL_W = 40   # minimum data column width
_MIN_W    = 121   # minimum widget width

def _widget_w(n_data_cols: int) -> int:
    if n_data_cols == 0:
        return _MIN_W
    table = _LABEL_W + _CG + n_data_cols * _MIN_COL_W + (n_data_cols - 1) * _CG
    return max(_MIN_W, 2 * _PAD + table)

BASE_W = _widget_w(5)  # used as default / maximum


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
    p.setFont(label_font(9))   # was 6 — too small next to the num_font(10) value
    p.setPen(QColor(255, 255, 255, 200))
    p.drawText(x + 4, y, w // 2, h, Qt.AlignmentFlag.AlignVCenter, label)
    if show_val:
        p.setFont(num_font(10))
        p.setPen(QColor(T.TEXT))
        p.drawText(x, y, w - 4, h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, val_str)


def _draw_level(p: QPainter, x: int, y: int, w: int, h: int,
                label: str, val_str: str, val_col: QColor) -> None:
    """Compact text-only row: label (dim) on left, value (colored) on right."""
    p.setFont(label_font(9))   # was 6 — too small next to the num_font(10) value
    p.setPen(QColor(T.DIM))
    p.drawText(x, y, w // 2, h, Qt.AlignmentFlag.AlignVCenter, label)
    p.setFont(num_font(10))
    p.setPen(val_col)
    p.drawText(x, y, w, h,
               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, val_str)


def _fuel_col(ratio: float) -> tuple[QColor, QColor]:
    if ratio < 0.10:
        c = QColor(T.CRIT); return c, c.lighter(120)
    if ratio < 0.25:
        c = QColor(T.WARN); return c, c.lighter(120)
    return QColor(T.FUEL_LO), QColor(T.FUEL_HI)


def _calc(rate: float, current: float, rem: float, safety: float, cap: float):
    """(laps_on_current, refuel_next_stop, needed_to_end).

    `needed_to_end` is the total additional amount needed to cover the rest
    of the race (laps remaining + safety margin) — not capped to what a
    single tank can hold, so on a long race it can legitimately be several
    times the tank capacity (several full refills' worth). Can go negative:
    that means the current amount already covers the rest of the race with
    room to spare, and the negative value is exactly that spare amount.

    `refuel_next_stop` is what actually makes sense to put in at the next
    stop: the full `needed_to_end` if that already fits in the tank (this
    is your last stop), otherwise fill up to capacity (there will be at
    least one more stop regardless of exactly how much goes in now). Also
    goes negative under the same surplus condition as `needed_to_end`.

    Both None outside a race or before there's a consumption rate yet.
    """
    laps_on = (current / rate) if rate > 0 else None
    if rem > 0 and rate > 0:
        needed_to_end = (rem + safety) * rate - current
        refuel_next_stop = min(needed_to_end, max(0., cap - current))
        return laps_on, refuel_next_stop, needed_to_end
    return laps_on, None, None


def _table_layout(refs: dict[str, str], show_usage: bool, show_laps: bool,
                  show_refuel: bool, show_finish: bool, show_tanks: bool
                  ) -> tuple[int, dict[str, tuple[int, int]]]:
    """Return (widget_width, {key: (x, width)}) with each column sized to its
    own content — the widest of its header and its reference value — instead of
    splitting the width equally. Avoids dead space on short columns while
    guaranteeing long values (e.g. "XX.X%") still fit.
    """
    vis = [k for k, v in [("usage", show_usage), ("laps", show_laps),
                          ("refuel", show_refuel), ("finish", show_finish),
                          ("tanks", show_tanks)] if v]
    if not vis:
        return _MIN_W, {"label": (_PAD, _LABEL_W)}

    fm_val = QFontMetrics(num_font(9))
    fm_hdr = QFontMetrics(label_font(7))
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
    return f"{v:.0f}L" if v >= 100 else f"{v:.1f}L"


def _fmt_ref_fuel(v: float) -> str:
    """Signed — negative reads as surplus (you already have more than needed)."""
    return f"{v:+.0f}L" if abs(v) >= 100 else f"{v:+.1f}L"


def _fmt_tanks(v: float) -> str:
    """TO END expressed as a number of full tanks/refills instead of a raw
    amount — e.g. a 50L tank and 400L needed to finish reads as "8.0"."""
    return f"{v:.1f}"


_HDR_NAMES = {"usage": "USAGE", "laps": "LAPS", "refuel": "REFUEL", "finish": "TO END", "tanks": "TANKS"}

# Widest value each column must be able to render, used to size the columns.
# Fuel Calculator sizes its table off _VE_REFS too (not fuel-specific strings)
# so both widgets always compute the same widget width — "%" renders a few
# px wider than "L", so sizing off "99.9L" etc. made this widget narrower.
# "finish" (TO END) is sized for up to 5 digits, not REFUEL's "+99.9%" —
# unlike REFUEL (capped to what a tank can hold), TO END is the *total*
# amount left for the rest of the race, uncapped, and can run into the
# thousands on a long/fuel-thirsty combo (e.g. "+2400L", "+1500%").
_VE_REFS = {"usage": "99.9%", "laps": "99.9", "refuel": "+99.9%", "finish": "+99999%", "tanks": "99.9"}

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
        {"key": "avg5_reset",   "label": "Reset AVG 5",          "type": "choice",
         "default": "never", "options": [
             {"label": "Never",            "value": "never"},
             {"label": "At session start", "value": "session"},
             {"label": "On pit exit",      "value": "pit_exit"},
         ]},
        {"type": "separator", "label": "Display"},
        {"key": "show_fuel_bar",   "label": "Fuel bar",   "type": "bool", "default": True},
        {"key": "show_fuel_level", "label": "Fuel level", "type": "bool", "default": True},
        {"key": "show_last",   "label": "LAST row",   "type": "bool", "default": True},
        {"key": "show_avg5",   "label": "AVG 5 row",  "type": "bool", "default": True},
        {"key": "show_usage",  "label": "USAGE col",  "type": "bool", "default": True},
        {"key": "show_laps",   "label": "LAPS col",   "type": "bool", "default": True},
        {"key": "show_refuel", "label": "REFUEL col", "type": "bool", "default": True},
        {"key": "show_finish", "label": "TO END col", "type": "bool", "default": True},
        {"key": "show_tanks",  "label": "TANKS col",  "type": "bool", "default": True},
    ]

    def __init__(self, **kw):
        self._show_fuel_bar   = True
        self._show_fuel_level = True
        self._show_last       = True
        self._show_avg5       = True
        self._show_usage      = True
        self._show_laps       = True
        self._show_refuel     = True
        self._show_finish     = True
        self._show_tanks      = True

        self._scale        = DEFAULT_SCALE / 100.0
        self._safety_laps  = 1.0
        self._merge        = False

        self._last_lap_fuel        = 0.0
        self._last_amount_used     = -1.0
        self._fuel_history: deque[float] = deque(maxlen=5)

        # AVG-5 auto-reset: "never" | "session" | "pit_exit". Tracks the two
        # trigger signals continuously (so switching mode mid-run never fires a
        # stale one), and only clears the rolling history on the selected one.
        self._avg5_reset       = "never"
        self._last_reset_count = None   # None until first seen, so startup never counts as a reset
        self._prev_in_pit      = False

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

        super().__init__(update_hz=1, **kw)
        self._refresh_layout()

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _update(self) -> None:
        if self._merge and realtime_state.game_running:
            player = next((v for v in minfo.vehicles.dataSet if v.is_player), None)
            vclass = player.vehicle_class if player else ""
            if vclass:
                if _class_has_ve(vclass):
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
            ("refuel", self._show_refuel), ("finish", self._show_finish),
            ("tanks", self._show_tanks)
        ] if v]
        vis_rows = (1 if self._show_last else 0) + (1 if self._show_avg5 else 0)
        has_table = vis_rows > 0 and len(vis_data) > 0

        sep_h = 10 if fuel_h > 0 and has_table else 0
        hdr_h = _HDR if has_table else 0

        if has_table:
            self._w, self._col_pos = _table_layout(
                _VE_REFS, self._show_usage, self._show_laps,
                self._show_refuel, self._show_finish, self._show_tanks)
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
        self._avg5_reset  = str(params.get("avg5_reset", "never"))

        self._show_fuel_bar   = bool(params.get("show_fuel_bar",   True))
        self._show_fuel_level = bool(params.get("show_fuel_level", True))
        self._show_last       = bool(params.get("show_last",   True))
        self._show_avg5       = bool(params.get("show_avg5",   True))
        self._show_usage      = bool(params.get("show_usage",  True))
        self._show_laps       = bool(params.get("show_laps",   True))
        self._show_refuel     = bool(params.get("show_refuel", True))
        self._show_finish     = bool(params.get("show_finish", True))
        self._show_tanks      = bool(params.get("show_tanks",  True))

        self._apply_session_visibility(params)
        self._refresh_layout()
        self.update()

    def on_data(self) -> None:
        # Consumption, laps-remaining and estimates all come straight from
        # module_fuel.py — a background-thread, position-interpolated
        # estimate (updates continuously through the lap, not just at lap
        # end) and a laps-remaining figure precise to the current on-track
        # position, not just to the lap.
        self._current_fuel  = minfo.fuel.amountCurrent
        self._fuel_cap       = max(1.0, minfo.fuel.capacity)
        self._laps_remaining = minfo.fuel.lapsRemaining

        # Auto-reset the rolling average on the configured trigger. Also drop
        # the last-used baseline so the first lap after the reset seeds a fresh
        # history instead of being diffed against a pre-reset reading.
        if self._avg5_reset_triggered():
            self._fuel_history.clear()
            self._last_amount_used = -1.0

        # AVG 5 = rolling average of the last 5 completed laps' consumption.
        # amountUsedLast only changes at a lap boundary (module_fuel.py holds
        # it steady the rest of the lap), so a change is exactly a new
        # completed-lap reading — push it into the history. First reading
        # after a reset is a baseline, not a lap, so it's never pushed.
        used_last = minfo.fuel.amountUsedLast
        if used_last != self._last_amount_used:
            if self._last_amount_used >= 0 and 0.05 < used_last < self._fuel_cap * 0.8:
                self._fuel_history.append(used_last)
            self._last_amount_used = used_last
        self._last_lap_fuel = used_last

        self.update()

    def _avg5_reset_triggered(self) -> bool:
        """Whether the AVG-5 history should be cleared this tick. Both signals
        are tracked every tick regardless of the selected mode, so the first
        tick (and a mode switch) never counts as a trigger; only the mode in
        effect actually clears."""
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
        p.setFont(label_font(7))
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
        if self._show_last: rows.append(("LAST", self._last_lap_fuel))
        if self._show_avg5: rows.append(("AVG 5", self._avg5()))

        for lbl, rate in rows:
            laps_on, refuel, to_end = _calc(rate, self._current_fuel, rem, sfty, self._fuel_cap)

            cx, cw = self._col_pos["label"]
            p.setFont(label_font(8))
            p.setPen(QColor(T.DIM))
            p.drawText(cx, y, cw, _RH, Qt.AlignmentFlag.AlignVCenter, lbl)

            if "usage" in self._col_pos:
                cx, cw = self._col_pos["usage"]
                p.setFont(num_font(9)); p.setPen(QColor(T.TEXT))
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           _fmt_fuel(rate) if rate > 0 else "-")

            if "laps" in self._col_pos:
                cx, cw = self._col_pos["laps"]
                p.setFont(num_font(9)); p.setPen(QColor(T.TEXT))
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           f"{laps_on:.1f}" if laps_on is not None else "-")

            if "refuel" in self._col_pos:
                cx, cw = self._col_pos["refuel"]
                p.setFont(num_font(9))
                if refuel is None:
                    p.setPen(QColor(T.TEXT)); ref_str = "-"
                else:
                    p.setPen(QColor(T.GOOD) if refuel <= 0 else QColor(T.TEXT))
                    ref_str = _fmt_ref_fuel(refuel)
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, ref_str)

            if "finish" in self._col_pos:
                cx, cw = self._col_pos["finish"]
                p.setFont(num_font(9))
                if to_end is None:
                    p.setPen(QColor(T.TEXT)); fin_str = "-"
                else:
                    p.setPen(QColor(T.GOOD) if to_end <= 0 else QColor(T.TEXT))
                    fin_str = _fmt_ref_fuel(to_end)
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, fin_str)

            if "tanks" in self._col_pos:
                cx, cw = self._col_pos["tanks"]
                p.setFont(num_font(9))
                if to_end is None:
                    p.setPen(QColor(T.TEXT)); tanks_str = "-"
                else:
                    p.setPen(QColor(T.GOOD) if to_end <= 0 else QColor(T.TEXT))
                    tanks_str = _fmt_tanks(to_end / self._fuel_cap)
                p.drawText(cx, y, cw, _RH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, tanks_str)

            y += _RH

        p.end()
