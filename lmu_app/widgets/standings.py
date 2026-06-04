"""
Standings overlay.

Badges overlap name text (not a separate column).
around_n controls symmetric window around player; widget height is dynamic.
"""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget
from lmu_app.utils.class_colors import class_color, class_abbrev

ROW_H  = 20
SEP_H  = 4

_CHAR_PX  = 7
_BADGE_PX = 22   # badge pill width (drawn over the name text)

COLUMN_DEFS = {
    "pos":      ("",      16, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
    "class":    ("CLS",   30, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter),
    "name":     ("",      -1, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
    "gap":      ("GAP",   52, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "interval": ("INT",   52, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "best":     ("BEST",  62, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "last":     ("LAST",  62, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "fuel_ve":  ("VE/F",  44, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
}
DEFAULT_COLUMNS = ["pos", "name", "gap", "interval", "best", "last"]

C_BG      = QColor(10, 10, 10, 215)
C_BORDER  = QColor(55, 55, 55, 180)
C_SEP     = QColor(70, 70, 70, 180)
C_PLAYER  = QColor(255, 200, 0, 40)
C_TEXT    = QColor(220, 220, 220)
C_DIM     = QColor(110, 110, 110)
C_P1      = QColor(255, 215, 0)
C_P2      = QColor(192, 192, 192)
C_P3      = QColor(205, 127, 50)
C_PURPLE  = QColor(180, 100, 255)
C_GREEN   = QColor(80, 220, 80)
C_GAR_BG  = QColor(70, 70, 70, 210)
C_GAR_FG  = QColor(200, 200, 200)
C_PIT_BG  = QColor(50, 110, 200, 210)
C_PIT_FG  = QColor(240, 240, 240)
C_OUT_BG  = QColor(190, 130, 0, 210)
C_OUT_FG  = QColor(20, 20, 20)


def _fmt_lap(t: float) -> str:
    if t <= 0: return "-"
    m = int(t // 60); s = t - m * 60
    return f"{m}:{s:06.3f}"

def _fmt_gap(g: float, is_race: bool, decimals: int = 1) -> str:
    if g < 0: return "-"
    return f"+{g:.{decimals}f}"

def _fmt_name(raw: str, fmt: str) -> str:
    if not raw: return raw
    parts = raw.strip().split()
    if fmt == "last":
        return parts[-1] if parts else raw
    if fmt == "initial" and len(parts) >= 2:
        return f"{parts[0][0]}. {' '.join(parts[1:])}"
    return raw

def _col_w(col: str, ncw: int) -> int:
    return ncw if col == "name" else (COLUMN_DEFS[col][1] if col in COLUMN_DEFS else 0)

def _total_w(columns: list, ncw: int) -> int:
    return sum(_col_w(c, ncw) for c in columns if c in COLUMN_DEFS) + 4

def _total_h(show_header: bool, has_sep: bool, n_rows: int) -> int:
    return (22 if show_header else 0) + n_rows * ROW_H + (SEP_H if has_sep else 0) + 8


class StandingsWidget(BaseWidget):
    WIDGET_NAME = "Standings"
    CONFIG_SCHEMA = [
        {"key": "top_n",          "label": "Leaders shown",          "type": "int",
         "min": 1, "max": 6, "step": 1, "default": 3},
        {"key": "around_n",       "label": "Around player",          "type": "int",
         "min": 0, "max": 6, "step": 1, "default": 2},
        {"key": "max_name_chars", "label": "Name max chars",         "type": "int",
         "min": 4, "max": 30, "step": 1, "default": 16},
        {"key": "gap_decimals",   "label": "Gap decimals (0-3)",     "type": "int",
         "min": 0, "max": 3,  "step": 1, "default": 1},
        {"key": "name_format",    "label": "Name format",            "type": "choice",
         "options": [
             {"value": "full",    "label": "First Last"},
             {"value": "initial", "label": "F. Last"},
             {"value": "last",    "label": "Last only"},
         ], "default": "full"},
        {"key": "show_header",    "label": "Column headers",         "type": "bool", "default": False},
        {"key": "show_gar_badge", "label": "GAR badge (garage)",     "type": "bool", "default": True},
        {"key": "show_out_badge", "label": "OUT badge (outlap)",     "type": "bool", "default": True},
        {"key": "columns",        "label": "Columns (drag to reorder)","type": "ordered_multiselect",
         "options": [
             {"value": "pos",      "label": "Position"},
             {"value": "class",    "label": "Car class"},
             {"value": "name",     "label": "Name"},
             {"value": "gap",      "label": "Gap to leader"},
             {"value": "interval", "label": "Interval"},
             {"value": "best",     "label": "Best lap"},
             {"value": "last",     "label": "Last lap"},
             {"value": "fuel_ve",  "label": "VE / Fuel"},
         ],
         "default": ["pos", "name", "gap", "interval", "best", "last"]},
    ]

    def __init__(self, reader: DataReader,
                 columns: list[str] | None = None,
                 top_n: int = 3, around_n: int = 2,
                 show_header: bool = False, max_name_chars: int = 16,
                 gap_decimals: int = 1, name_format: str = "full",
                 show_gar_badge: bool = True, show_out_badge: bool = True,
                 **kw):
        self.columns          = columns or DEFAULT_COLUMNS
        self._top_n           = top_n
        self._around_n        = around_n
        self._show_header     = show_header
        self._max_name_chars  = max_name_chars
        self._gap_decimals    = gap_decimals
        self._name_format     = name_format
        self._show_gar_badge  = show_gar_badge
        self._show_out_badge  = show_out_badge
        self._header_h        = 22 if show_header else 0
        self._entries:  list[dict] = []
        self._sep_after: int = -1
        self._n_rows:    int = top_n + 1 + 2 * around_n
        self._best_overall   = 9999.0
        self._player_fuel    = 0.0
        self._player_ve      = 0.0
        self._has_ve         = False
        self._outlap_tracking: dict[int, int] = {}
        self._prev_in_pits:   dict[int, bool] = {}
        self._class_colors:   dict[str, str]  = {}
        super().__init__(reader, update_hz=5, **kw)
        ncw = self._max_name_chars * _CHAR_PX
        self.setFixedSize(_total_w(self.columns, ncw),
                          _total_h(show_header, False, self._n_rows))

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_class_colors(self, colors: dict) -> None:
        self._class_colors = colors
        self.update()

    def apply_params(self, params: dict) -> None:
        self._top_n          = int(params.get("top_n", 3))
        self._around_n       = int(params.get("around_n", 2))
        self._max_name_chars = int(params.get("max_name_chars", 16))
        self._gap_decimals   = int(params.get("gap_decimals", 1))
        self._name_format    = str(params.get("name_format", "full"))
        self._show_header    = bool(params.get("show_header", False))
        self._show_gar_badge = bool(params.get("show_gar_badge", True))
        self._show_out_badge = bool(params.get("show_out_badge", True))
        cols = params.get("columns", DEFAULT_COLUMNS)
        self.columns     = [c for c in cols if c in COLUMN_DEFS] or list(DEFAULT_COLUMNS)
        self._header_h   = 22 if self._show_header else 0
        self._n_rows     = self._top_n + 1 + 2 * self._around_n
        ncw = self._max_name_chars * _CHAR_PX
        self.setFixedSize(_total_w(self.columns, ncw),
                          _total_h(self._show_header, False, self._n_rows))
        self.update()

    def on_data(self, snap: LMUSnapshot):
        s       = snap.session
        is_race = s.session_type >= 10
        vehicles = sorted(s.vehicles, key=lambda v: v.place)

        valid_best = [v.best_lap for v in vehicles if v.best_lap > 0]
        if valid_best: self._best_overall = min(valid_best)

        player = next((v for v in vehicles if v.is_player), None)
        if not player:
            return

        self._player_fuel = snap.vehicle.fuel
        self._player_ve   = snap.vehicle.virtual_energy
        self._has_ve      = snap.vehicle.virtual_energy > 0 or snap.vehicle.state_of_charge > 0

        # Outlap tracking
        new_prev: dict[int, bool] = {}
        for v in vehicles:
            slot     = v.slot_id
            was_pits = self._prev_in_pits.get(slot, v.in_pits)
            new_prev[slot] = v.in_pits
            if v.in_garage:
                self._outlap_tracking.pop(slot, None)
            elif was_pits and not v.in_pits:
                self._outlap_tracking[slot] = v.total_laps
            elif slot in self._outlap_tracking and v.total_laps > self._outlap_tracking[slot]:
                del self._outlap_tracking[slot]
        self._prev_in_pits = new_prev

        n     = len(vehicles)
        p_idx = player.place - 1
        top_indices = list(range(min(self._top_n, n)))

        # Player window: around_n on each side, compensate near boundaries
        half    = self._around_n
        p_start = max(0, p_idx - half)
        p_end   = min(n - 1, p_idx + half)
        if p_idx - p_start < half:
            p_end = min(n - 1, p_end + (half - (p_idx - p_start)))
        if p_end - p_idx < half:
            p_start = max(0, p_start - (half - (p_end - p_idx)))

        player_indices = list(range(p_start, p_end + 1))
        if p_idx not in player_indices:
            player_indices.append(p_idx); player_indices.sort()

        overlap = set(top_indices) & set(player_indices)
        if overlap or (player_indices and player_indices[0] <= self._top_n):
            all_indices     = sorted(set(top_indices) | set(player_indices))
            self._sep_after = -1
        else:
            all_indices     = top_indices + player_indices
            self._sep_after = len(top_indices) - 1

        # Dynamic row count — no padding to TOTAL_ROWS
        self._n_rows = len(all_indices)
        leader_best = vehicles[0].best_lap if vehicles and vehicles[0].best_lap > 0 else -1.0

        self._entries = []
        for rank, i in enumerate(all_indices):
            v = vehicles[i]

            if is_race:
                gap      = v.time_behind_leader
                prev     = vehicles[all_indices[rank-1]] if rank > 0 else None
                interval = (v.time_behind_leader - prev.time_behind_leader) if prev else 0.0
            else:
                gap = (v.best_lap - leader_best
                       if v.best_lap > 0 and leader_best > 0 else -1.0)
                prev = vehicles[all_indices[rank-1]] if rank > 0 else None
                interval = (v.best_lap - prev.best_lap
                            if prev and v.best_lap > 0 and prev.best_lap > 0 else -1.0)

            slot = v.slot_id
            if v.in_garage:
                badge = "GAR"
            elif v.in_pits:
                badge = "PIT"
            elif slot in self._outlap_tracking:
                badge = "OUT"
            else:
                badge = ""

            self._entries.append({
                "pos":            v.place,
                "name_raw":       v.driver_name or v.vehicle_name or f"Car {v.place}",
                "vclass":         v.vehicle_class,
                "class_color":    class_color(v.vehicle_class, self._class_colors),
                "best":           v.best_lap,
                "last":           v.last_lap,
                "gap":            gap,
                "interval":       interval,
                "is_player":      v.is_player,
                "is_best":        v.best_lap > 0 and abs(v.best_lap - self._best_overall) < 0.001,
                "is_race":        is_race,
                "is_outlap":      slot in self._outlap_tracking,
                "badge":          badge,
                "virtual_energy": v.virtual_energy,
            })

        # Resize widget if row count changed
        ncw = self._max_name_chars * _CHAR_PX
        new_h = _total_h(self._show_header, self._sep_after >= 0, self._n_rows)
        if self.height() != new_h:
            self.setFixedSize(_total_w(self.columns, ncw), new_h)

        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ncw = self._max_name_chars * _CHAR_PX
        W   = _total_w(self.columns, ncw)
        H   = _total_h(self._show_header, self._sep_after >= 0, self._n_rows)

        p.setBrush(C_BG); p.setPen(QPen(C_BORDER, 1))
        p.drawRoundedRect(0, 0, W, H, 8, 8)

        if self._show_header:
            p.setBrush(QColor(30, 30, 30)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(1, 1, W-2, 22, 7, 7)
            x = 2
            for col in self.columns:
                if col not in COLUMN_DEFS: continue
                label, _, align = COLUMN_DEFS[col]
                cw = _col_w(col, ncw)
                if label:
                    p.setFont(QFont("Monospace", 7)); p.setPen(C_DIM)
                    p.drawText(x, 0, cw, 22, align, label)
                x += cw

        sep_extra = 0

        for row_i, e in enumerate(self._entries):
            y = self._header_h + row_i * ROW_H + sep_extra

            if row_i == self._sep_after + 1 and self._sep_after >= 0:
                sep_extra += SEP_H; y += SEP_H
                p.setBrush(C_SEP); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(2, y - SEP_H + 1, W - 4, 1)

            if e["is_player"]:
                p.setBrush(C_PLAYER); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(1, y, W-2, ROW_H)

            x = 2
            for col in self.columns:
                if col not in COLUMN_DEFS: continue
                _, _, align = COLUMN_DEFS[col]
                cw = _col_w(col, ncw)

                if col == "pos":
                    pos = e["pos"]
                    c   = C_P1 if pos==1 else C_P2 if pos==2 else C_P3 if pos==3 else C_DIM
                    p.setFont(QFont("Monospace", 9, QFont.Weight.Bold)); p.setPen(c)
                    p.drawText(x, y, cw, ROW_H, align, str(pos))

                elif col == "class":
                    cls_col = e["class_color"]
                    if cls_col is not None:
                        p.setBrush(cls_col); p.setPen(Qt.PenStyle.NoPen)
                        p.drawRect(x, y, cw, ROW_H)
                    p.setFont(QFont("Monospace", 7, QFont.Weight.Bold))
                    p.setPen(C_TEXT)
                    p.drawText(x, y, cw, ROW_H,
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
                               class_abbrev(e["vclass"]))

                elif col == "name":
                    raw_badge = e["badge"]
                    is_player = e["is_player"]

                    if raw_badge == "GAR" and not self._show_gar_badge:
                        raw_badge = ""
                    elif raw_badge == "OUT" and not self._show_out_badge:
                        raw_badge = ""

                    if raw_badge == "GAR":
                        bg_c, fg_c = C_GAR_BG, C_GAR_FG
                    elif raw_badge == "PIT":
                        bg_c, fg_c = C_PIT_BG, C_PIT_FG
                    else:
                        bg_c, fg_c = C_OUT_BG, C_OUT_FG

                    # Name always uses FULL column — badge overlays on top
                    name_text = _fmt_name(e["name_raw"], self._name_format)[:self._max_name_chars]
                    p.setFont(QFont("Monospace", 9))
                    p.setPen(QColor(255, 220, 80) if is_player else C_TEXT)
                    p.drawText(x+2, y, cw, ROW_H, align, name_text)

                    # Badge overlaid at right edge of name column
                    if raw_badge:
                        bx2 = x + cw - _BADGE_PX; by2 = y + 3
                        p.setBrush(bg_c); p.setPen(Qt.PenStyle.NoPen)
                        p.drawRoundedRect(bx2, by2, _BADGE_PX, ROW_H-6, 2, 2)
                        p.setFont(QFont("Monospace", 7, QFont.Weight.Bold))
                        p.setPen(fg_c)
                        p.drawText(bx2, by2, _BADGE_PX, ROW_H-6,
                                   Qt.AlignmentFlag.AlignCenter, raw_badge)

                elif col == "best":
                    c = C_PURPLE if e["is_best"] else (C_GREEN if e["is_player"] else
                        C_DIM if e["best"] <= 0 else C_TEXT)
                    p.setFont(QFont("Monospace", 8)); p.setPen(c)
                    p.drawText(x, y, cw, ROW_H, align, _fmt_lap(e["best"]))

                elif col == "last":
                    p.setFont(QFont("Monospace", 8))
                    p.setPen(C_DIM if e["last"] <= 0 else C_TEXT)
                    p.drawText(x, y, cw, ROW_H, align, _fmt_lap(e["last"]))

                elif col == "gap":
                    txt = ("" if e["pos"] == 1
                           else "-" if e["is_outlap"] and not e["is_race"]
                           else _fmt_gap(e["gap"], e["is_race"], self._gap_decimals))
                    p.setFont(QFont("Monospace", 8)); p.setPen(C_DIM if not txt else C_TEXT)
                    p.drawText(x, y, cw, ROW_H, align, txt)

                elif col == "interval":
                    txt = ("" if e["pos"] == 1
                           else "-" if e["is_outlap"] and not e["is_race"]
                           else _fmt_gap(e["interval"], e["is_race"], self._gap_decimals))
                    p.setFont(QFont("Monospace", 8)); p.setPen(C_DIM if not txt else C_TEXT)
                    p.drawText(x, y, cw, ROW_H, align, txt)

                elif col == "fuel_ve":
                    ve = e["virtual_energy"]
                    if ve > 0.001:
                        txt   = f"{ve*100:.0f}%"
                        col_c = QColor(50, 190, 80)
                    elif e["is_player"]:
                        txt   = f"{self._player_fuel:.1f}L"
                        col_c = C_TEXT
                    else:
                        txt, col_c = "---", C_DIM
                    p.setFont(QFont("Monospace", 8)); p.setPen(col_c)
                    p.drawText(x, y, cw, ROW_H, align, txt)

                x += cw
        p.end()
