"""
Standings overlay — multi-class.

Player's class: top_n leaders + symmetric around_n window.
Other classes (optional, configurable top_n): shown below with a class header.
Only active classes (with non-garage drivers) appear.
"""
from __future__ import annotations
from collections import defaultdict
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget
from lmu_app.utils.class_colors import class_abbrev, class_color

ROW_H = 20
SEP_H = 4
CLS_H = 16

_CHAR_PX_BASE  = 7
_BADGE_PX_BASE = 22

def _char_px(font_size: int) -> int:
    return max(4, round(_CHAR_PX_BASE * font_size / 9))

def _badge_px(font_size: int) -> int:
    return max(14, round(_BADGE_PX_BASE * font_size / 9))

# Fastest → slowest, with the same keyword sets as class_colors.CLASS_ENTRIES.
# Each tuple lists all substrings that identify that class (uppercase match).
_CLASS_KEYWORDS: list[tuple[str, ...]] = [
    ("HYPERCAR", "LMH", "GTP", "HYPER"),   # Hypercar / GTP
    ("LMP2", "P2"),                          # LMP2
    ("LMP3", "P3"),                          # LMP3
    ("GTE", "GT2"),                          # GTE / GT2
    ("LMGT3", "GT3", "GTD"),                # GT3 / LMGT3
    ("GTC",),
    ("GT4",),
]

def _class_rank(cls_name: str) -> int:
    vc = cls_name.strip().upper()
    for i, keywords in enumerate(_CLASS_KEYWORDS):
        if any(k in vc for k in keywords):
            return i
    return 99

COLUMN_DEFS = {
    "pos":      ("",      16, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
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


def _fmt_lap(t: float, decimals: int = 3) -> str:
    if t <= 0: return "-"
    m = int(t // 60); s = t - m * 60
    if decimals > 0:
        return f"{m}:{s:0{decimals + 3}.{decimals}f}"
    return f"{m}:{int(s):02d}"

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

def _col_w(col: str, ncw: int, font_size: int = 9) -> int:
    if col == "name":
        return ncw
    base = COLUMN_DEFS[col][1] if col in COLUMN_DEFS else 0
    if base <= 0:
        return 0
    return max(8, round(base * font_size / 9))

def _total_w(columns: list, ncw: int, font_size: int = 9) -> int:
    return sum(_col_w(c, ncw, font_size) for c in columns if c in COLUMN_DEFS) + 4

def _row_h(font_size: int) -> int:
    return font_size + 11


def _compute_h(show_header: bool, entries: list, row_h: int = ROW_H) -> int:
    """Compute widget height from entry list (is_sep / is_class_header / regular rows)."""
    h = (22 if show_header else 0) + 8  # 4px top + 4px bottom padding
    for e in entries:
        if e.get("is_sep"):
            h += SEP_H
        elif e.get("is_class_header"):
            h += CLS_H
        else:
            h += row_h
    return h


class StandingsWidget(BaseWidget):
    WIDGET_NAME = "Standings"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Window"},
        {"key": "opacity", "label": "Opacity (%)", "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 85},
        {"type": "separator", "label": "Rows"},
        {"key": "top_n",    "label": "Leaders shown", "type": "int",
         "min": 1, "max": 6, "step": 1, "default": 3},
        {"key": "around_n", "label": "Around player", "type": "int",
         "min": 0, "max": 6, "step": 1, "default": 2},
        {"type": "separator", "label": "Other classes"},
        {"key": "show_other_classes",  "label": "Show other classes",      "type": "bool", "default": False},
        {"key": "other_classes_top_n", "label": "Leaders per other class", "type": "int",
         "min": 1, "max": 6, "step": 1, "default": 3},
        {"type": "separator", "label": "Names"},
        {"key": "max_name_chars", "label": "Name max chars", "type": "int",
         "min": 4, "max": 30, "step": 1, "default": 16},
        {"key": "name_format", "label": "Name format", "type": "choice",
         "options": [
             {"value": "full",    "label": "First Last"},
             {"value": "initial", "label": "F. Last"},
             {"value": "last",    "label": "Last only"},
         ], "default": "full"},
        {"type": "separator", "label": "Display"},
        {"key": "show_header",     "label": "Column headers",          "type": "bool", "default": False},
        {"key": "show_gar_badge",  "label": "GAR badge (garage)",      "type": "bool", "default": True},
        {"key": "show_out_badge",  "label": "OUT badge (outlap)",      "type": "bool", "default": True},
        {"key": "show_best_col",   "label": "Show Best lap column",    "type": "bool", "default": True},
        {"key": "show_last_col",   "label": "Show Last lap column",    "type": "bool", "default": True},
        {"key": "show_fuel_ve_col","label": "Show VE/Fuel column",     "type": "bool", "default": False},
        {"key": "font_size",       "label": "Font size",               "type": "int",
         "min": 7, "max": 14, "step": 1, "default": 9},
        {"type": "separator", "label": "Gaps"},
        {"key": "show_gap_col",      "label": "Show Gap column",           "type": "bool", "default": True},
        {"key": "show_interval_col", "label": "Show Interval column",      "type": "bool", "default": True},
        {"key": "gap_decimals",      "label": "Gap decimals (0-3)",        "type": "int",
         "min": 0, "max": 3, "step": 1, "default": 1},
        {"key": "interval_decimals", "label": "Interval decimals (0-3)",   "type": "int",
         "min": 0, "max": 3, "step": 1, "default": 1},
        {"type": "separator", "label": "Laps"},
        {"key": "best_decimals", "label": "Best lap decimals (0-3)", "type": "int",
         "min": 0, "max": 3, "step": 1, "default": 3},
        {"key": "last_decimals", "label": "Last lap decimals (0-3)", "type": "int",
         "min": 0, "max": 3, "step": 1, "default": 3},
        {"type": "separator", "label": "Column order"},
        {"key": "columns", "label": "", "type": "ordered_multiselect",
         "options": [
             {"value": "pos",      "label": "Position"},
             {"value": "name",     "label": "Name"},
             {"value": "gap",      "label": "Gap to leader"},
             {"value": "interval", "label": "Interval"},
             {"value": "best",     "label": "Best lap"},
             {"value": "last",     "label": "Last lap"},
             {"value": "fuel_ve",  "label": "VE / Fuel"},
         ],
         "show_keys": {
             "gap":      "show_gap_col",
             "interval": "show_interval_col",
             "best":     "show_best_col",
             "last":     "show_last_col",
             "fuel_ve":  "show_fuel_ve_col",
         },
         "default": ["pos", "name", "gap", "interval", "best", "last", "fuel_ve"]},
    ]

    def __init__(self, reader: DataReader,
                 columns: list[str] | None = None,
                 top_n: int = 3, around_n: int = 2,
                 show_header: bool = False, max_name_chars: int = 16,
                 gap_decimals: int = 1, interval_decimals: int = 1,
                 name_format: str = "full",
                 show_gar_badge: bool = True, show_out_badge: bool = True,
                 show_other_classes: bool = False, other_classes_top_n: int = 3,
                 show_gap_col: bool = True, show_interval_col: bool = True,
                 show_best_col: bool = True, show_last_col: bool = True,
                 show_fuel_ve_col: bool = False,
                 font_size: int = 9,
                 best_decimals: int = 3, last_decimals: int = 3,
                 **kw):
        _show_map = {
            "pos": True, "name": True,
            "gap": show_gap_col, "interval": show_interval_col,
            "best": show_best_col, "last": show_last_col, "fuel_ve": show_fuel_ve_col,
        }
        _col_order = list(columns or COLUMN_DEFS.keys())
        self.columns              = [c for c in _col_order if c in COLUMN_DEFS and _show_map.get(c, True)] or ["pos", "name"]
        self._top_n               = top_n
        self._around_n            = around_n
        self._show_header         = show_header
        self._max_name_chars      = max_name_chars
        self._gap_decimals        = gap_decimals
        self._interval_decimals   = interval_decimals
        self._name_format         = name_format
        self._show_gar_badge      = show_gar_badge
        self._show_out_badge      = show_out_badge
        self._show_other_classes  = show_other_classes
        self._other_classes_top_n = other_classes_top_n
        self._font_size           = max(7, min(14, int(font_size)))
        self._rh                  = _row_h(self._font_size)
        self._best_decimals       = max(0, min(3, int(best_decimals)))
        self._last_decimals       = max(0, min(3, int(last_decimals)))
        self._opacity             = 85
        self._entries:  list[dict]    = []
        self._best_overall            = 9999.0
        self._player_fuel             = 0.0
        self._player_ve               = 0.0
        self._outlap_tracking: dict[int, int] = {}
        self._prev_in_pits:   dict[int, bool] = {}
        self._class_colors:   dict[str, str]  = {}
        super().__init__(reader, update_hz=5, **kw)
        ncw = self._max_name_chars * _char_px(self._font_size)
        n_init = top_n + 1 + 2 * around_n
        self.setFixedSize(_total_w(self.columns, ncw, self._font_size),
                          _compute_h(show_header, [{}] * n_init, self._rh))

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_class_colors(self, colors: dict) -> None:
        self._class_colors = colors
        self.update()

    def apply_params(self, params: dict) -> None:
        self._top_n               = int(params.get("top_n", 3))
        self._around_n            = int(params.get("around_n", 2))
        self._max_name_chars      = int(params.get("max_name_chars", 16))
        self._gap_decimals        = int(params.get("gap_decimals", 1))
        self._interval_decimals   = int(params.get("interval_decimals", self._gap_decimals))
        self._name_format         = str(params.get("name_format", "full"))
        self._show_header         = bool(params.get("show_header", False))
        self._show_gar_badge      = bool(params.get("show_gar_badge", True))
        self._show_out_badge      = bool(params.get("show_out_badge", True))
        self._show_other_classes  = bool(params.get("show_other_classes", False))
        self._other_classes_top_n = int(params.get("other_classes_top_n", 3))
        self._font_size           = max(7, min(14, int(params.get("font_size", 9))))
        self._rh                  = _row_h(self._font_size)
        self._best_decimals       = max(0, min(3, int(params.get("best_decimals", 3))))
        self._last_decimals       = max(0, min(3, int(params.get("last_decimals", 3))))
        self._opacity             = max(0, min(100, int(params.get("opacity", 85))))
        # Column order from ordered_multiselect (contains all columns in user order)
        col_order = list(params.get("columns") or COLUMN_DEFS.keys())
        col_order = [c for c in col_order if c in COLUMN_DEFS]
        for c in COLUMN_DEFS:
            if c not in col_order:
                col_order.append(c)
        show_map = {
            "pos":      True,
            "name":     True,
            "gap":      bool(params.get("show_gap_col",      True)),
            "interval": bool(params.get("show_interval_col", True)),
            "best":     bool(params.get("show_best_col",     True)),
            "last":     bool(params.get("show_last_col",     True)),
            "fuel_ve":  bool(params.get("show_fuel_ve_col",  False)),
        }
        self.columns = [c for c in col_order if show_map.get(c, True)] or ["pos", "name"]
        ncw   = self._max_name_chars * _char_px(self._font_size)
        ref   = self._entries if self._entries else [{}] * (self._top_n + 1 + 2 * self._around_n)
        new_h = _compute_h(self._show_header, ref, self._rh)
        self.setFixedSize(_total_w(self.columns, ncw, self._font_size), new_h)
        self.update()

    # ------------------------------------------------------------------

    def on_data(self, snap: LMUSnapshot):
        s       = snap.session
        is_race = s.session_type >= 10

        self._player_fuel = snap.vehicle.fuel
        self._player_ve   = snap.vehicle.virtual_energy

        # Group vehicles by class, sorted by overall place within each class
        by_class: dict[str, list] = defaultdict(list)
        for v in s.vehicles:
            by_class[v.vehicle_class].append(v)
        for cls in by_class:
            by_class[cls].sort(key=lambda v: v.place)

        player = next((v for v in s.vehicles if v.is_player), None)
        if not player:
            return
        player_class       = player.vehicle_class
        player_cls_vehicles = by_class[player_class]

        valid_best = [v.best_lap for v in player_cls_vehicles if v.best_lap > 0]
        self._best_overall = min(valid_best) if valid_best else 9999.0

        # Outlap tracking (all vehicles)
        new_prev: dict[int, bool] = {}
        for v in s.vehicles:
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

        entries: list[dict] = []

        # ── Classify other classes: faster (above) vs slower (below) ────────
        player_rank = _class_rank(player_class)
        faster_classes: list[tuple[int, str]] = []
        slower_classes: list[tuple[int, str]] = []
        if self._show_other_classes:
            for cls_name, cls_veh in by_class.items():
                if cls_name == player_class:
                    continue
                # Only include the section if at least one driver is on track
                if not any(not v.in_garage for v in cls_veh):
                    continue
                r = _class_rank(cls_name)
                if r < player_rank:
                    faster_classes.append((r, cls_name))
                else:
                    slower_classes.append((r, cls_name))
            faster_classes.sort()
            slower_classes.sort()

        def _add_other_class(cls_name: str) -> None:
            """Append a class header + top-N rows (garage drivers included)."""
            cls_veh   = by_class[cls_name]
            shown     = cls_veh[:self._other_classes_top_n]
            cls_col   = class_color(cls_name, self._class_colors)
            entries.append({"is_class_header": True, "label": cls_name,
                            "cls_color": cls_col, "abbrev": class_abbrev(cls_name)})
            leader      = shown[0]
            leader_best = leader.best_lap if leader.best_lap > 0 else -1.0
            for rank, v in enumerate(shown):
                prev = shown[rank - 1] if rank > 0 else None
                entries.append(self._make_row(v, prev, rank, is_race, leader, leader_best))

        # ── Faster classes (above player's class) ────────────────────────────
        if self._show_other_classes:
            for _, cls_name in faster_classes:
                _add_other_class(cls_name)

        # ── Player's class ──────────────────────────────────────────────────
        n     = len(player_cls_vehicles)
        p_idx = next((i for i, v in enumerate(player_cls_vehicles) if v.is_player), 0)
        half  = self._around_n

        top_indices = list(range(min(self._top_n, n)))

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
            merged = sorted(set(top_indices) | set(player_indices))
            target = min(n, self._top_n + 2 * half + 1)
            while len(merged) < target and merged[-1] + 1 < n:
                merged.append(merged[-1] + 1)
            all_indices = merged
            sep_after   = -1
        else:
            all_indices = top_indices + player_indices
            sep_after   = len(top_indices) - 1

        cls_leader      = player_cls_vehicles[0]
        cls_leader_best = cls_leader.best_lap if cls_leader.best_lap > 0 else -1.0

        if self._show_other_classes:
            cls_col = class_color(player_class, self._class_colors)
            entries.append({"is_class_header": True, "label": player_class,
                            "cls_color": cls_col, "abbrev": class_abbrev(player_class)})

        for rank, i in enumerate(all_indices):
            if sep_after >= 0 and rank == sep_after + 1:
                entries.append({"is_sep": True})
            v    = player_cls_vehicles[i]
            prev = player_cls_vehicles[all_indices[rank - 1]] if rank > 0 else None
            entries.append(self._make_row(v, prev, i, is_race, cls_leader, cls_leader_best))

        # ── Slower classes (below player's class) ────────────────────────────
        if self._show_other_classes:
            for _, cls_name in slower_classes:
                _add_other_class(cls_name)

        self._entries = entries

        ncw   = self._max_name_chars * _char_px(self._font_size)
        new_w = _total_w(self.columns, ncw, self._font_size)
        new_h = _compute_h(self._show_header, entries, self._rh)
        if self.width() != new_w or self.height() != new_h:
            self.setFixedSize(new_w, new_h)

        self.update()

    def _make_row(self, v, prev_v, class_rank: int, is_race: bool,
                  cls_leader, leader_best: float) -> dict:
        if is_race:
            gap      = v.time_behind_leader - cls_leader.time_behind_leader
            interval = (v.time_behind_leader - prev_v.time_behind_leader) if prev_v else 0.0
        else:
            gap      = (v.best_lap - leader_best if v.best_lap > 0 and leader_best > 0 else -1.0)
            interval = (v.best_lap - prev_v.best_lap
                        if prev_v and v.best_lap > 0 and prev_v.best_lap > 0 else -1.0)

        slot  = v.slot_id
        badge = ("GAR" if v.in_garage
                 else "PIT" if v.in_pits
                 else "OUT" if slot in self._outlap_tracking
                 else "")

        return {
            "pos":            class_rank + 1,
            "name_raw":       v.driver_name or v.vehicle_name or f"Car {v.slot_id}",
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
            "fuel":           v.fuel,
        }

    # ------------------------------------------------------------------

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ncw = self._max_name_chars * _char_px(self._font_size)
        W   = _total_w(self.columns, ncw, self._font_size)
        H   = _compute_h(self._show_header, self._entries)

        p.setBrush(QColor(10, 10, 10, self._bg_alpha())); p.setPen(self._border_pen())
        p.drawRoundedRect(0, 0, W, H, 8, 8)

        if self._show_header:
            p.setBrush(QColor(30, 30, 30)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(1, 1, W-2, 22, 7, 7)
            x = 2
            for col in self.columns:
                if col not in COLUMN_DEFS: continue
                label, _, align = COLUMN_DEFS[col]
                cw = _col_w(col, ncw, self._font_size)
                if label:
                    p.setFont(QFont("Monospace", max(6, self._font_size - 2))); p.setPen(C_DIM)
                    p.drawText(x, 0, cw, 22, align, label)
                x += cw

        y = (22 if self._show_header else 0) + 4  # 4px top padding

        for e in self._entries:

            if e.get("is_sep"):
                p.setBrush(C_SEP); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(2, y + 1, W - 4, 1)
                y += SEP_H
                continue

            if e.get("is_class_header"):
                abbrev  = e.get("abbrev", "???")[:3]
                cls_col = e.get("cls_color")
                chr_w   = _char_px(self._font_size)
                bdg_w   = len(abbrev) * chr_w + 8
                bdg_x, bdg_y, bdg_h = 4, y + 1, CLS_H - 2
                if cls_col is not None:
                    p.setBrush(cls_col); p.setPen(Qt.PenStyle.NoPen)
                    p.drawRoundedRect(bdg_x, bdg_y, bdg_w, bdg_h, 2, 2)
                p.setFont(QFont("Monospace", max(6, self._font_size - 2), QFont.Weight.Bold))
                p.setPen(QColor(255, 255, 255))
                p.drawText(bdg_x, bdg_y, bdg_w, bdg_h, Qt.AlignmentFlag.AlignCenter, abbrev)
                y += CLS_H
                continue

            # ── Regular driver row ──────────────────────────────────────
            rh = self._rh
            if e["is_player"]:
                p.setBrush(C_PLAYER); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(1, y, W-2, rh)

            x = 2
            for col in self.columns:
                if col not in COLUMN_DEFS: continue
                _, _, align = COLUMN_DEFS[col]
                cw = _col_w(col, ncw, self._font_size)

                fs  = self._font_size
                fsd = max(7, fs - 1)
                fss = max(6, fs - 2)

                if col == "pos":
                    pos = e["pos"]
                    c   = C_P1 if pos==1 else C_P2 if pos==2 else C_P3 if pos==3 else C_DIM
                    p.setFont(QFont("Monospace", fs, QFont.Weight.Bold)); p.setPen(c)
                    p.drawText(x, y, cw, rh, align, str(pos))

                elif col == "name":
                    raw_badge = e["badge"]
                    is_player = e["is_player"]
                    if raw_badge == "GAR" and not self._show_gar_badge:
                        raw_badge = ""
                    elif raw_badge == "OUT" and not self._show_out_badge:
                        raw_badge = ""
                    if raw_badge == "GAR":   bg_c, fg_c = C_GAR_BG, C_GAR_FG
                    elif raw_badge == "PIT": bg_c, fg_c = C_PIT_BG, C_PIT_FG
                    else:                    bg_c, fg_c = C_OUT_BG, C_OUT_FG

                    name_text = _fmt_name(e["name_raw"], self._name_format)[:self._max_name_chars]
                    p.setFont(QFont("Monospace", fs))
                    p.setPen(QColor(255, 220, 80) if is_player else C_TEXT)
                    p.drawText(x+2, y, cw, rh, align, name_text)

                    if raw_badge:
                        bdg = _badge_px(self._font_size)
                        bx2 = x + cw - bdg - 3; by2 = y + 3
                        p.setBrush(bg_c); p.setPen(Qt.PenStyle.NoPen)
                        p.drawRoundedRect(bx2, by2, bdg, rh - 6, 2, 2)
                        p.setFont(QFont("Monospace", fss, QFont.Weight.Bold)); p.setPen(fg_c)
                        p.drawText(bx2, by2, bdg, rh - 6,
                                   Qt.AlignmentFlag.AlignCenter, raw_badge)

                elif col == "best":
                    c = C_PURPLE if e["is_best"] else (C_GREEN if e["is_player"] else
                        C_DIM if e["best"] <= 0 else C_TEXT)
                    p.setFont(QFont("Monospace", fsd)); p.setPen(c)
                    p.drawText(x, y, cw, rh, align, _fmt_lap(e["best"], self._best_decimals))

                elif col == "last":
                    p.setFont(QFont("Monospace", fsd))
                    p.setPen(C_DIM if e["last"] <= 0 else C_TEXT)
                    p.drawText(x, y, cw, rh, align, _fmt_lap(e["last"], self._last_decimals))

                elif col == "gap":
                    txt = ("" if e["pos"] == 1
                           else "-" if e["is_outlap"] and not e["is_race"]
                           else _fmt_gap(e["gap"], e["is_race"], self._gap_decimals))
                    p.setFont(QFont("Monospace", fsd)); p.setPen(C_DIM if not txt else C_TEXT)
                    p.drawText(x, y, cw, rh, align, txt)

                elif col == "interval":
                    txt = ("" if e["pos"] == 1
                           else "-" if e["is_outlap"] and not e["is_race"]
                           else _fmt_gap(e["interval"], e["is_race"], self._interval_decimals))
                    p.setFont(QFont("Monospace", fsd)); p.setPen(C_DIM if not txt else C_TEXT)
                    p.drawText(x, y, cw, rh, align, txt)

                elif col == "fuel_ve":
                    ve   = e["virtual_energy"]
                    fuel = e.get("fuel", 0.0)
                    if ve > 0.001:
                        txt   = f"{ve*100:.0f}%"
                        col_c = QColor(50, 190, 80)
                    elif fuel > 0.01:
                        txt   = f"{fuel:.1f}L"
                        col_c = C_TEXT
                    else:
                        txt, col_c = "---", C_DIM
                    p.setFont(QFont("Monospace", fsd)); p.setPen(col_c)
                    p.drawText(x, y, cw, rh, align, txt)

                x += cw
            y += rh

        p.end()
