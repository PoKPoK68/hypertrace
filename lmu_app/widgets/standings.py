"""
Standings overlay — multi-class.

Player's class: top_n leaders + symmetric around_n window.
Other classes (optional, configurable top_n): shown below with a class header.
Only active classes (with non-garage drivers) appear.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtWidgets import QSizePolicy

from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.utils.class_colors import class_abbrev, class_color
from lmu_app.utils.logos import get_logo as _get_logo
from lmu_app.utils.theme import T, label_font, num_font, text_font
from lmu_app.widgets.base import BaseWidget, DEFAULT_SCALE

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_TRACK_TEMP_SVG = str(_ASSETS / "track-temp.svg")
_AIR_TEMP_SVG   = str(_ASSETS / "air-temp.svg")

ROW_H = 20
SEP_H = 4
CLS_H = 16
SESSION_BAR_H = 22

_CHAR_PX_BASE  = 7
_BADGE_PX_BASE = 22
_CP            = 3   # column inner padding (applied left AND right — gap between cols = 2*_CP)

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

_LOGO_COL_W = 26   # fixed width for manufacturer logo column

COLUMN_DEFS = {
    "pos":      ("",      24,          Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter),
    "logo":     ("",      _LOGO_COL_W, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter),
    "name":     ("",      -1,          Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
    "gap":      ("GAP",   52,          Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
    "interval": ("INT",   52,          Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
    "best":     ("BEST",  62,          Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
    "last":     ("LAST",  62,          Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
    "fuel_ve":  ("VE/F",  44,          Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
}
DEFAULT_COLUMNS = ["pos", "logo", "name", "gap", "interval", "best", "last"]

# All colors from theme.T — no hex literals in this module.


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

def _session_label(session_type: int) -> str:
    if session_type >= 10: return "Race"
    if 5 <= session_type <= 8: return "Qualifying"
    return "Practice"

def _fmt_session_time(elapsed: float, remaining: float) -> str:
    def _f(t: float) -> str:
        t = max(0, int(t))
        h, r = divmod(t, 3600)
        m, s = divmod(r, 60)
        return f"{h}:{m:02d}:{s:02d}"
    total   = round((elapsed + max(0.0, remaining)) / 60) * 60
    elapsed = max(0, total - int(max(0.0, remaining)))
    return f"{_f(elapsed)} / {_f(total)}"

def _apply_case(name: str, case: str) -> str:
    if case == "title":
        return name.title()
    if case == "mixed":
        parts = name.rsplit(" ", 1)
        if len(parts) == 2:
            return f"{parts[0].title()} {parts[1].upper()}"
        return name.upper()
    return name.upper()

def _col_w(col: str, ncw: int, font_size: int = 9, dw: dict | None = None) -> int:
    if col == "name":
        return ncw
    if dw and col in dw:
        return dw[col]
    base = COLUMN_DEFS[col][1] if col in COLUMN_DEFS else 0
    if base <= 0:
        return 0
    return max(8, round(base * font_size / 9))

def _total_w(columns: list, ncw: int, font_size: int = 9, dw: dict | None = None) -> int:
    return sum(_col_w(c, ncw, font_size, dw) for c in columns if c in COLUMN_DEFS) + 4

def _row_h(font_size: int) -> int:
    return font_size + 11


def _true_laps_behind(leader, v) -> int:
    """Correct laps-down count using time_into_lap (same logic as relative widget).
    raw==1 only counts as +1L if the leader is also further into the current lap —
    avoids false positive when the leader just crossed the line but v is still ahead on track."""
    raw = leader.total_laps - v.total_laps
    if raw <= 0:
        return 0
    if raw >= 2:
        return raw
    return 1 if leader.time_into_lap >= v.time_into_lap else 0


def _compute_h(entries: list, row_h: int = ROW_H, show_class_header: bool = True) -> int:
    """Compute widget height. Header row is always present and merged with column labels."""
    h = SESSION_BAR_H + 8
    for e in entries:
        if e.get("is_sep"):
            h += SEP_H
        elif e.get("is_class_header"):
            h += CLS_H if show_class_header else 0
        else:
            h += row_h
    return h


class StandingsWidget(BaseWidget):
    WIDGET_NAME = "Standings"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Appearance"},
        {"key": "opacity",   "label": "Opacity (%)", "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 85},
        {"key": "scale",     "label": "Size (%)",    "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 100},
        {"key": "font_size", "label": "Font size",   "type": "int",
         "min": 7, "max": 14, "step": 1, "default": 9},
        {"type": "separator", "label": "Header"},
        {"key": "header_info", "label": "Content", "type": "choice",
         "options": [
             {"value": "session", "label": "Session + Time"},
             {"value": "temp",    "label": "Temperatures"},
             {"value": "none",    "label": "Nothing"},
         ], "default": "session"},
        {"key": "show_class_badge", "label": "Car class badge", "type": "bool", "default": True},
        {"type": "separator", "label": "Rows"},
        {"key": "top_n",    "label": "Top drivers (your class)", "type": "int",
         "min": 1, "max": 6, "step": 1, "default": 3},
        {"key": "around_n", "label": "Rows around your position", "type": "int",
         "min": 0, "max": 6, "step": 1, "default": 2},
        {"key": "show_other_classes",  "label": "Show other classes", "type": "bool", "default": False},
        {"key": "other_classes_top_n", "label": "Leaders per other class", "type": "int",
         "min": 1, "max": 6, "step": 1, "default": 3, "show_if": "show_other_classes"},
        {"type": "separator", "label": "Names"},
        {"key": "name_format", "label": "Format", "type": "choice",
         "options": [
             {"value": "full",    "label": "First Last"},
             {"value": "initial", "label": "F. Last"},
             {"value": "last",    "label": "Last only"},
         ], "default": "full"},
        {"key": "name_case", "label": "Case", "type": "choice",
         "options": [
             {"value": "upper", "label": "NAME LASTNAME"},
             {"value": "mixed", "label": "Name LASTNAME"},
             {"value": "title", "label": "Name Lastname"},
         ], "default": "upper"},
        {"key": "max_name_chars", "label": "Max characters", "type": "int",
         "min": 4, "max": 30, "step": 1, "default": 16},
        {"type": "separator", "label": "Player row"},
        {"key": "show_player_bg",    "label": "Highlight background", "type": "bool", "default": True},
        {"key": "player_color",      "label": "Color",      "type": "color", "default": "#ECAA43",
         "show_if": "show_player_bg"},
        {"key": "player_color_alpha","label": "Intensity (%)", "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 20, "show_if": "show_player_bg"},
        {"type": "separator", "label": "Columns"},
        {"key": "show_gap_col",      "label": "Gap to leader", "type": "bool", "default": True},
        {"key": "gap_decimals",      "label": "Decimals",      "type": "int",
         "min": 0, "max": 3, "step": 1, "default": 1, "show_if": "show_gap_col"},
        {"key": "show_interval_col", "label": "Interval",      "type": "bool", "default": True},
        {"key": "interval_decimals", "label": "Decimals",      "type": "int",
         "min": 0, "max": 3, "step": 1, "default": 1, "show_if": "show_interval_col"},
        {"key": "show_best_col",     "label": "Best lap",      "type": "bool", "default": True},
        {"key": "best_decimals",     "label": "Decimals",      "type": "int",
         "min": 0, "max": 3, "step": 1, "default": 3, "show_if": "show_best_col"},
        {"key": "show_last_col",     "label": "Last lap",      "type": "bool", "default": True},
        {"key": "last_decimals",     "label": "Decimals",      "type": "int",
         "min": 0, "max": 3, "step": 1, "default": 3, "show_if": "show_last_col"},
        {"key": "show_fuel_ve_col",  "label": "VE / Fuel",     "type": "bool", "default": False},
        {"type": "separator", "label": "Badges"},
        {"key": "show_lap_badge",  "label": "Pitted lap",  "type": "bool", "default": True},
        {"key": "show_out_badge",  "label": "Out lap",      "type": "bool", "default": True},
        {"key": "show_gar_badge",  "label": "Pit / Garage", "type": "bool", "default": True},
        {"type": "separator", "label": "Column order", "side_panel": True},
        {"key": "columns", "label": "", "type": "ordered_multiselect", "side_panel": True,
         "options": [
             {"value": "pos",      "label": "Position"},
             {"value": "logo",     "label": "Brand logo"},
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
         "default": ["pos", "logo", "name", "gap", "interval", "best", "last", "fuel_ve"]},
    ]

    def __init__(self, reader: DataReader,
                 columns: list[str] | None = None,
                 top_n: int = 3, around_n: int = 2,
                 max_name_chars: int = 16,
                 gap_decimals: int = 1, interval_decimals: int = 1,
                 name_format: str = "full", name_case: str = "upper",
                 header_info: str = "session",
                 show_gar_badge: bool = True, show_out_badge: bool = True,
                 show_other_classes: bool = False, other_classes_top_n: int = 3,
                 show_gap_col: bool = True, show_interval_col: bool = True,
                 show_best_col: bool = True, show_last_col: bool = True,
                 show_fuel_ve_col: bool = False,
                 font_size: int = 9,
                 best_decimals: int = 3, last_decimals: int = 3,
                 **kw):
        _show_map = {
            "pos": True, "logo": True, "name": True,
            "gap": show_gap_col, "interval": show_interval_col,
            "best": show_best_col, "last": show_last_col, "fuel_ve": show_fuel_ve_col,
        }
        _col_order = list(columns or COLUMN_DEFS.keys())
        self.columns              = [c for c in _col_order if c in COLUMN_DEFS and _show_map.get(c, True)] or ["pos", "name"]
        self._top_n               = top_n
        self._around_n            = around_n
        self._max_name_chars      = max_name_chars
        self._gap_decimals        = gap_decimals
        self._interval_decimals   = interval_decimals
        self._name_format         = name_format
        self._name_case           = name_case
        self._header_info         = header_info
        self._ses_type            = 0
        self._current_et          = 0.0
        self._ses_remaining       = 0.0
        self._track_temp          = 0.0
        self._air_temp            = 0.0
        self._show_gar_badge      = show_gar_badge
        self._show_out_badge      = show_out_badge
        self._show_lap_badge      = True
        self._show_class_badge    = True
        self._show_player_bg      = True
        self._show_other_classes  = show_other_classes
        self._other_classes_top_n = other_classes_top_n
        self._font_size           = max(7, min(14, int(font_size)))
        self._rh                  = _row_h(self._font_size)
        self._best_decimals       = max(0, min(3, int(best_decimals)))
        self._last_decimals       = max(0, min(3, int(last_decimals)))
        self._scale               = DEFAULT_SCALE / 100.0
        self._opacity             = 85
        self._player_color        = QColor(0xEC, 0xAA, 0x43, 51)
        self._entries:  list[dict]    = []
        self._best_by_class: dict[str, float] = {}
        self._player_fuel             = 0.0
        self._player_ve               = 0.0
        self._outlap_tracking:    dict[int, int]  = {}
        self._pit_lap_tracking:   dict[int, int]  = {}
        self._prev_in_pits:       dict[int, bool] = {}
        self._class_colors:       dict[str, str]  = {}
        self._temp_pm_trk = None
        self._temp_pm_air = None
        self._temp_pm_sz  = 0
        self._dw: dict[str, int] = {}
        super().__init__(reader, update_hz=5, **kw)
        self._recompute_sizes()
        ncw = self._max_name_chars * _char_px(self._font_size)
        n_init = top_n + 1 + 2 * around_n
        self.setFixedSize(int(_total_w(self.columns, ncw, self._font_size, self._dw) * self._scale),
                          int(_compute_h([{}] * n_init, self._rh) * self._scale))

    def _recompute_sizes(self) -> None:
        from PySide6.QtGui import QFontMetrics
        fsd = max(7, self._font_size - 1)
        fm  = QFontMetrics(num_font(fsd))
        def _gap_ref(d: int) -> str:
            return "+999" + (f".{'9'*d}" if d > 0 else "")
        def _lap_ref(d: int) -> str:
            return "9:99" + (f".{'9'*d}" if d > 0 else "")
        self._dw = {
            "gap":      fm.horizontalAdvance(_gap_ref(self._gap_decimals))      + 2 * _CP,
            "interval": fm.horizontalAdvance(_gap_ref(self._interval_decimals)) + 2 * _CP,
            "best":     fm.horizontalAdvance(_lap_ref(self._best_decimals))     + 2 * _CP,
            "last":     fm.horizontalAdvance(_lap_ref(self._last_decimals))     + 2 * _CP,
            "fuel_ve":  fm.horizontalAdvance("100%")                            + 2 * _CP,
        }

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
        self._name_case           = str(params.get("name_case", "upper"))
        self._header_info         = str(params.get("header_info", "session"))
        self._show_gar_badge      = bool(params.get("show_gar_badge",   True))
        self._show_out_badge      = bool(params.get("show_out_badge",   True))
        self._show_lap_badge      = bool(params.get("show_lap_badge",   True))
        self._show_class_badge    = bool(params.get("show_class_badge", True))
        self._show_player_bg      = bool(params.get("show_player_bg",   True))
        self._show_other_classes  = bool(params.get("show_other_classes", False))
        self._other_classes_top_n = int(params.get("other_classes_top_n", 3))
        self._font_size           = max(7, min(14, int(params.get("font_size", 9))))
        self._rh                  = _row_h(self._font_size)
        self._best_decimals       = max(0, min(3, int(params.get("best_decimals", 3))))
        self._last_decimals       = max(0, min(3, int(params.get("last_decimals", 3))))
        self._scale               = int(params.get("scale", DEFAULT_SCALE)) / 100.0
        self._opacity             = max(0, min(100, int(params.get("opacity", 85))))
        _c = QColor(str(params.get("player_color", "#ffc800")))
        if not _c.isValid(): _c = QColor(255, 200, 0)
        _c.setAlpha(round(255 * max(0, min(100, int(params.get("player_color_alpha", 20)))) / 100))
        self._player_color = _c
        # Column order from ordered_multiselect (contains all columns in user order)
        col_order = list(params.get("columns") or COLUMN_DEFS.keys())
        col_order = [c for c in col_order if c in COLUMN_DEFS]
        for c in COLUMN_DEFS:
            if c not in col_order:
                col_order.append(c)
        show_map = {
            "pos":      True,
            "logo":     True,
            "name":     True,
            "gap":      bool(params.get("show_gap_col",      True)),
            "interval": bool(params.get("show_interval_col", True)),
            "best":     bool(params.get("show_best_col",     True)),
            "last":     bool(params.get("show_last_col",     True)),
            "fuel_ve":  bool(params.get("show_fuel_ve_col",  False)),
        }
        self.columns = [c for c in col_order if show_map.get(c, True)] or ["pos", "name"]
        self._recompute_sizes()
        ncw   = self._max_name_chars * _char_px(self._font_size)
        ref   = self._entries if self._entries else [{}] * (self._top_n + 1 + 2 * self._around_n)
        new_h = _compute_h(ref, self._rh, self._show_class_badge)
        self.setFixedSize(int(_total_w(self.columns, ncw, self._font_size, self._dw) * self._scale),
                          int(new_h * self._scale))
        self.update()

    # ------------------------------------------------------------------

    def on_data(self, snap: LMUSnapshot):
        s       = snap.session
        is_race = s.session_type >= 10
        self._ses_type      = s.session_type
        self._current_et    = s.current_et
        self._ses_remaining = s.session_time_remaining
        self._track_temp    = s.track_temp
        self._air_temp      = s.ambient_temp

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

        self._best_by_class: dict[str, float] = {}
        for cls_name, cls_vehicles in by_class.items():
            valid = [v.best_lap for v in cls_vehicles if v.best_lap > 0]
            self._best_by_class[cls_name] = min(valid) if valid else 9999.0

        # Outlap / pit-lap tracking (all vehicles)
        new_prev: dict[int, bool] = {}
        for v in s.vehicles:
            slot     = v.slot_id
            was_pits = self._prev_in_pits.get(slot, v.in_pits)
            new_prev[slot] = v.in_pits
            if v.in_garage:
                self._outlap_tracking.pop(slot, None)
                self._pit_lap_tracking.pop(slot, None)
            elif not was_pits and v.in_pits:
                self._pit_lap_tracking[slot] = v.total_laps
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
        new_w = _total_w(self.columns, ncw, self._font_size, self._dw)
        new_h = _compute_h(entries, self._rh, self._show_class_badge)
        sw, sh = int(new_w * self._scale), int(new_h * self._scale)
        if self.width() != sw or self.height() != sh:
            self.setFixedSize(sw, sh)

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
                 else f"L{self._pit_lap_tracking[slot]}" if slot in self._pit_lap_tracking
                 else "")

        laps_behind    = _true_laps_behind(cls_leader, v)      if is_race else 0
        prev_laps_down = _true_laps_behind(cls_leader, prev_v) if (is_race and prev_v) else 0
        interval_laps  = laps_behind - prev_laps_down

        return {
            "pos":                   class_rank + 1,
            "vehicle_name":          v.vehicle_name or "",
            "name_raw":              v.driver_name or v.vehicle_name or f"Car {v.slot_id}",
            "best":                  v.best_lap,
            "last":                  v.last_lap,
            "gap":                   gap,
            "interval":              interval,
            "laps_behind":           laps_behind,
            "interval_laps":         interval_laps,
            "is_player":             v.is_player,
            "is_best":               v.best_lap > 0 and abs(v.best_lap - self._best_by_class.get(v.vehicle_class, 9999.0)) < 0.001,
            "is_last_session_best":  v.last_lap > 0 and abs(v.last_lap - self._best_by_class.get(v.vehicle_class, 9999.0)) < 0.001,
            "is_last_personal_best": v.last_lap > 0 and v.best_lap > 0 and abs(v.last_lap - v.best_lap) < 0.01,
            "is_race":               is_race,
            "is_outlap":             slot in self._outlap_tracking,
            "badge":                 badge,
            "virtual_energy":        v.virtual_energy,
            "fuel":                  v.fuel,
        }

    # ------------------------------------------------------------------

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)
        ncw  = self._max_name_chars * _char_px(self._font_size)
        W    = _total_w(self.columns, ncw, self._font_size, self._dw)
        H    = _compute_h(self._entries, self._rh, self._show_class_badge)

        self._draw_panel(p, W, H, accent=False)

        fs  = self._font_size
        fsd = max(7, fs - 1)
        fsh = max(6.0, fs - 1.5)   # column header labels (GAP, INT, BEST…)
        fss = max(6, fs - 2)   # class/row badges (HYP, GT3, GAR…)

        # ── Merged header row (session info + column labels) ──────────────
        pos_w  = _col_w("pos",  ncw, fs, self._dw) if "pos"  in self.columns else 0
        name_w = _col_w("name", ncw, fs, self._dw) if "name" in self.columns else 0
        left_w = pos_w + name_w   # area with empty labels — session info goes here

        p.setBrush(QColor(28, 30, 34, 200))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(1, 1, W - 2, SESSION_BAR_H, T.RADIUS, T.RADIUS)

        # hairline drawn after session bar so it paints on top (not hidden by bar bg)
        from lmu_app.utils.theme import accent_hairline as _ahl
        p.fillRect(QRectF(9, 0, W - 18, 2), _ahl(W, self._opacity))

        if left_w > 0:
            hi = self._header_info
            if hi == "session":
                lbl = _session_label(self._ses_type)[0]
                f = label_font(max(6, fsh))
                p.setFont(f)
                fm   = p.fontMetrics()
                lbl_w = fm.horizontalAdvance(lbl)
                baseline = 1 + (SESSION_BAR_H + fm.ascent() - fm.descent()) // 2
                p.setPen(QColor(T.ACCENT))
                p.drawText(6, baseline, lbl)
                p.setPen(QColor(T.TEXT))
                p.drawText(6 + lbl_w + 6, baseline,
                           _fmt_session_time(self._current_et, self._ses_remaining))
            elif hi == "temp":
                p.setFont(num_font(fss))
                fm = p.fontMetrics()
                trk_str = f"{self._track_temp:.0f}°"
                air_str = f"{self._air_temp:.0f}°"
                icon_sz = max(6, fss + 1)
                if icon_sz != self._temp_pm_sz:
                    self._temp_pm_trk = QIcon(_TRACK_TEMP_SVG).pixmap(icon_sz, icon_sz)
                    self._temp_pm_air = QIcon(_AIR_TEMP_SVG).pixmap(icon_sz, icon_sz)
                    self._temp_pm_sz  = icon_sz
                gap_px = 3; sep_px = 8
                trk_w = fm.horizontalAdvance(trk_str)
                air_w = fm.horizontalAdvance(air_str)
                x0     = 6
                icon_y = 1 + SESSION_BAR_H // 2 - icon_sz // 2
                p.drawPixmap(x0, icon_y, self._temp_pm_trk)
                p.setPen(QColor(T.DIM))
                p.drawText(x0 + icon_sz + gap_px, 1, trk_w + 2, SESSION_BAR_H,
                           Qt.AlignmentFlag.AlignVCenter, trk_str)
                ax = x0 + icon_sz + gap_px + trk_w + sep_px
                p.drawPixmap(ax, icon_y, self._temp_pm_air)
                p.setPen(QColor(T.DIM))
                p.drawText(ax + icon_sz + gap_px, 1, air_w + 2, SESSION_BAR_H,
                           Qt.AlignmentFlag.AlignVCenter, air_str)

        x_col = 2
        for col in self.columns:
            if col not in COLUMN_DEFS:
                continue
            hdr_label, _, align = COLUMN_DEFS[col]
            cw = _col_w(col, ncw, fs, self._dw)
            if hdr_label:
                p.setFont(label_font(max(6, fsh)))
                p.setPen(QColor(T.DIM))
                p.drawText(x_col + _CP, 1, cw - 2*_CP, SESSION_BAR_H, align, hdr_label)
            x_col += cw

        p.fillRect(QRectF(2, SESSION_BAR_H, W - 4, 1), T.FAINT)

        y = SESSION_BAR_H + 4

        for e in self._entries:

            # ── Separator ─────────────────────────────────────────────────
            if e.get("is_sep"):
                p.fillRect(QRectF(2, y + 1, W - 4, 1), T.FAINT)
                y += SEP_H
                continue

            # ── Class header ──────────────────────────────────────────────
            if e.get("is_class_header"):
                if not self._show_class_badge:
                    continue
                abbrev  = e.get("abbrev", "???")[:3]
                cls_col = e.get("cls_color")
                bdg_w   = len(abbrev) * _char_px(fs) + 8
                bdg_x, bdg_y, bdg_h = 4, y + 1, CLS_H - 2
                if cls_col is not None:
                    p.setBrush(cls_col)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawRoundedRect(bdg_x, bdg_y, bdg_w, bdg_h, 2, 2)
                p.setFont(label_font(max(6, fss)))
                p.setPen(QColor(T.TEXT))
                p.drawText(bdg_x, bdg_y, bdg_w, bdg_h, Qt.AlignmentFlag.AlignCenter, abbrev)
                y += CLS_H
                continue

            # ── Driver row ────────────────────────────────────────────────
            rh = self._rh
            if e["is_player"] and self._show_player_bg:
                p.setBrush(self._player_color)
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(1, y, W - 2, rh, 3, 3)

            x = 2
            for col in self.columns:
                if col not in COLUMN_DEFS:
                    continue
                _, _, align = COLUMN_DEFS[col]
                cw = _col_w(col, ncw, fs, self._dw)

                if col == "pos":
                    pos = e["pos"]
                    pc  = (QColor(T.P1) if pos == 1 else QColor(T.P2) if pos == 2
                           else QColor(T.P3) if pos == 3 else QColor(T.DIM))
                    p.setFont(num_font(fs))
                    p.setPen(pc)
                    p.drawText(x + _CP, y, cw - 2*_CP, rh, align, str(pos))

                elif col == "logo":
                    s  = self._scale
                    # Load at 3× physical size so Qt downsamples → sharp result
                    pw = max(12, round((_LOGO_COL_W - 2) * s * 3))
                    ph = max(6,  round((rh - 4)          * s * 3))
                    logo = _get_logo(e.get("vehicle_name", ""), pw, ph)
                    if logo:
                        max_lw = float(_LOGO_COL_W - 2)
                        max_lh = float(rh - 4)
                        sc  = min(max_lw / logo.width(), max_lh / logo.height())
                        dw  = logo.width()  * sc
                        dh  = logo.height() * sc
                        lx  = x + (_LOGO_COL_W - dw) / 2
                        ly  = y + (rh - dh) / 2
                        p.drawPixmap(QRectF(lx, ly, dw, dh), logo, QRectF(logo.rect()))

                elif col == "name":
                    raw_badge = e["badge"]
                    if raw_badge in ("GAR", "PIT") and not self._show_gar_badge:
                        raw_badge = ""
                    elif raw_badge == "OUT" and not self._show_out_badge:
                        raw_badge = ""
                    elif raw_badge.startswith("L") and not self._show_lap_badge:
                        raw_badge = ""
                    _badge_map = {
                        "GAR": (QColor(T.GAR_BG), QColor(T.GAR_FG)),
                        "PIT": (QColor(T.PIT_BG), QColor(T.PIT_FG)),
                        "OUT": (QColor(T.OUT_BG), QColor(T.OUT_FG)),
                    }
                    name_text = _apply_case(_fmt_name(e["name_raw"], self._name_format)[:self._max_name_chars], self._name_case)
                    p.setFont(text_font(fs))
                    p.setPen(QColor(T.TEXT))
                    p.drawText(x + 2, y, cw, rh, align, name_text)
                    if raw_badge:
                        if raw_badge in _badge_map:
                            bg_c, fg_c = _badge_map[raw_badge]
                        else:
                            bg_c, fg_c = QColor(T.LAP_BG), QColor(T.LAP_FG)
                        bdg = _badge_px(fs)
                        bx2, by2 = x + cw - bdg, y + 3
                        p.setBrush(bg_c); p.setPen(Qt.PenStyle.NoPen)
                        p.drawRoundedRect(bx2, by2, bdg, rh - 6, 2, 2)
                        p.setFont(num_font(fss)); p.setPen(fg_c)
                        p.drawText(bx2, by2, bdg, rh - 6, Qt.AlignmentFlag.AlignCenter, raw_badge)

                elif col == "best":
                    bc = (QColor(T.PURPLE) if e["is_best"]
                          else QColor(T.TEXT))
                    p.setFont(num_font(fsd)); p.setPen(bc)
                    p.drawText(x + _CP, y, cw - 2*_CP, rh, align, _fmt_lap(e["best"], self._best_decimals))

                elif col == "last":
                    lc = (QColor(T.PURPLE) if e["is_last_session_best"]
                          else QColor(T.GOOD) if e["is_last_personal_best"]
                          else QColor(T.TEXT))
                    p.setFont(num_font(fsd)); p.setPen(lc)
                    p.drawText(x + _CP, y, cw - 2*_CP, rh, align, _fmt_lap(e["last"], self._last_decimals))

                elif col == "gap":
                    if e["pos"] == 1:
                        txt = ""
                    elif e["laps_behind"] > 0:
                        txt = f"+{e['laps_behind']}L"
                    elif e["is_outlap"] and not e["is_race"]:
                        txt = "-"
                    else:
                        txt = _fmt_gap(e["gap"], e["is_race"], self._gap_decimals)
                    p.setFont(num_font(fsd))
                    p.setPen(QColor(T.TEXT) if txt else QColor(T.DIM))
                    p.drawText(x + _CP, y, cw - 2*_CP, rh, align, txt)

                elif col == "interval":
                    if e["pos"] == 1:
                        txt = ""
                    elif e["interval_laps"] > 0:
                        txt = f"+{e['interval_laps']}L"
                    elif e["is_outlap"] and not e["is_race"]:
                        txt = "-"
                    else:
                        txt = _fmt_gap(e["interval"], e["is_race"], self._interval_decimals)
                    p.setFont(num_font(fsd))
                    p.setPen(QColor(T.TEXT) if txt else QColor(T.DIM))
                    p.drawText(x + _CP, y, cw - 2*_CP, rh, align, txt)

                elif col == "fuel_ve":
                    ve   = e["virtual_energy"]
                    fuel = e.get("fuel", 0.0)
                    if ve > 0.001:
                        vc = (QColor(T.CRIT) if ve < 0.10
                              else QColor(T.WARN) if ve < 0.25
                              else QColor(T.GOOD))
                        txt = f"{ve*100:.0f}%"
                    elif fuel > 0.01:
                        vc = (QColor(T.CRIT) if fuel < 10
                              else QColor(T.WARN) if fuel < 25
                              else QColor(T.TEXT))
                        txt = f"{fuel:.0f}L"
                    else:
                        txt, vc = "---", QColor(T.DIM)
                    p.setFont(num_font(fsd)); p.setPen(vc)
                    p.drawText(x + _CP, y, cw - 2*_CP, rh, align, txt)

                x += cw
            y += rh

        p.end()
