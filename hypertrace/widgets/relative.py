"""
Relative overlay.

Separate drivers_ahead / drivers_behind counts.
Badge overlays the name text (no column shrink).
"""
from __future__ import annotations
import math as _math
from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from functools import lru_cache

from PySide6.QtGui import QColor, QFontMetrics, QIcon, QPainter
from PySide6.QtWidgets import QSizePolicy

from hypertrace.calc.module_info import minfo
from hypertrace.utils.class_colors import class_color
from hypertrace.utils.logos import get_logo as _get_logo
from hypertrace.utils.theme import T, draw_bold, label_font, num_font, text_font
from hypertrace.widgets.base import BaseWidget, DEFAULT_SCALE

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_TRACK_TEMP_SVG = str(_ASSETS / "track-temp.svg")
_AIR_TEMP_SVG   = str(_ASSETS / "air-temp.svg")

_MARGIN       = 6     # marge droite
_NAME_PAD_L   = 5     # gap between the position chip and the driver name
_GAP_PAD_L    = 5     # gap between the name/badge zone and the relative-time text
                      # (avoids "+123.4" touching a PIT/OUT/L{n} badge)
def _session_bar_h(font_size: int) -> int:
    """Header height follows the font size (22 px at the former default of 9)."""
    return font_size + 13


def _char_px(font_size: int) -> int:
    return max(4, round(7 * font_size / 9))


_POS_CHIP_X = 4   # left inset of the position chip
_POS_CHIP_R = 2   # gap between the chip's right edge and the driver name


@lru_cache(maxsize=64)
def _pos_chip_w(font_size: int) -> int:
    """Position chip width, measured from real font metrics.

    Was a fixed 22 px regardless of font size, so a 2-digit position (10+)
    grazed the chip's edges — and at larger font sizes, since drawText clips
    to its rect by default, actually got clipped by them.
    """
    fm = QFontMetrics(num_font(font_size))
    return max(18, fm.horizontalAdvance("99") + 6)


def _pos_col_w(font_size: int) -> int:
    return _POS_CHIP_X + _pos_chip_w(font_size) + _POS_CHIP_R


_LOGO_COL_W = 22   # fixed width for the manufacturer logo column — matches
                   # Standings' own convention (pos | logo | name), sized
                   # slightly smaller for this widget's tighter rows.


_BADGE_PAD = 5   # inner horizontal padding on each side of a badge label


@lru_cache(maxsize=64)
def _badge_px(font_size: int) -> int:
    """Badge width sized from the actual text metrics, so the label never
    touches the edges (a width merely scaled from the font size did)."""
    fm = QFontMetrics(num_font(max(6, font_size - 2)))
    return max(14, fm.horizontalAdvance("GAR") + 2 * _BADGE_PAD)


@lru_cache(maxsize=64)
def _gap_col_w(font_size: int, decimals: int) -> int:
    """Widest gap the column must fit, measured from real font metrics.

    Was a per-character estimate (chars × avg width), which could run 2 px
    narrower than the actual text once Montserrat's digits got wider than the
    previous monospaced face — same class of bug already fixed on the GAR/PIT
    badge width and the standings gap/interval/best/last columns.
    """
    # 3-digit worst case (a long track like Le Mans has ~200s laps, and a
    # multi-lap gap can exceed 100s) — matches the "+999" reference standings
    # already uses. Using "+12" here understated the width and let a wide
    # gap value overflow past the badge padding.
    ref = "+999." + "9" * decimals if decimals > 0 else "+999"
    return QFontMetrics(num_font(font_size)).horizontalAdvance(ref) + 6


@lru_cache(maxsize=64)
def _lastlap_col_w(font_size: int) -> int:
    """Widest lap time the column must fit — "9:59.999", matching Standings'
    own LAST column reference. Fixed 3 decimals (no per-widget setting, unlike
    Standings' LAST/BEST — one fewer knob for a column this widget didn't have
    at all before)."""
    return QFontMetrics(num_font(font_size)).horizontalAdvance("9:59.999") + 6


def _widget_w(name_width: int, font_size: int = 9, decimals: int = 1,
             show_last_lap: bool = True, show_logo: bool = True) -> int:
    w = (_pos_col_w(font_size) + name_width + _GAP_PAD_L
         + _gap_col_w(font_size, decimals) + _MARGIN)
    if show_last_lap:
        w += _GAP_PAD_L + _lastlap_col_w(font_size)
    if show_logo:
        w += _LOGO_COL_W
    return w


def _row_h(font_size: int) -> int:
    return font_size + 13


def _widget_h(ahead: int, behind: int, font_size: int = 9,
              show_session_bar: bool = False) -> int:
    return ((_session_bar_h(font_size) if show_session_bar else 0)
            + (ahead + 1 + behind) * _row_h(font_size) + 8)


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
    """Remaining session time only.

    The former "elapsed / total" form is twice as wide and got clipped by the
    header whenever the name column is configured narrow.
    """
    t = max(0, int(max(0.0, remaining)))
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}"

def _apply_case(name: str, case: str) -> str:
    if case == "title":
        return name.title()
    if case == "mixed":
        parts = name.rsplit(" ", 1)
        if len(parts) == 2:
            return f"{parts[0].title()} {parts[1].upper()}"
        return name.upper()
    return name.upper()

def _fmt_gap(g: float, decimals: int = 1) -> str:
    return f"{g:+.{decimals}f}"


# TinyPedal's own default for both lap_difference_ahead_threshold and
# lap_difference_behind_threshold (tinypedal/module/module_vehicles.py +
# calculation.py's lap_difference()) — not 1.0. See _lap_diff_sign.
_LAP_DIFF_THRESHOLD = 0.9


def _lap_progress(total_laps: int, lap_dist: float, track_length: float) -> float:
    """One continuous number per car: laps completed + fractional distance
    into the current lap (0-1). Same as TinyPedal's totalLapProgress."""
    if track_length < 1:
        return float(total_laps)
    frac = lap_dist / track_length
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else frac
    return total_laps + frac


def _lap_diff_sign(v_total_laps: int, v_lap_dist: float,
                   plr_total_laps: int, plr_lap_dist: float, track_length: float) -> int:
    """+1 if this car is a lap ahead of the player (about to lap us / already
    has), -1 if a lap behind (we're about to lap them / already have), 0
    otherwise. Ported from TinyPedal's own lap_difference(): continuous
    progress (laps completed + fractional track position), zeroed out
    whenever the two are within `_LAP_DIFF_THRESHOLD` of a lap apart — not a
    raw total_laps compare (a car still on the same physical lap as the
    player, just a moment from crossing the line itself, would misread as
    genuinely a lap down the instant the player crosses first — total_laps
    differs by 1 but the real, continuous gap is nearly zero), and not a
    plain ±1.0 threshold either (that only flips at the exact moment of
    physical passing — a car catching up to lap the player, still trailing
    on track, has continuous progress just under 1.0 lap ahead well before
    it draws level, and should already color as about to lap). 0.9 is
    TinyPedal's own tuned middle ground between those two failure modes."""
    diff = (_lap_progress(v_total_laps, v_lap_dist, track_length)
            - _lap_progress(plr_total_laps, plr_lap_dist, track_length))
    if -_LAP_DIFF_THRESHOLD < diff < _LAP_DIFF_THRESHOLD:
        return 0
    return 1 if diff > 0 else -1


def _fmt_lap(t: float, decimals: int = 3) -> str:
    """Same format as Standings' LAST/BEST columns — m:ss.sss."""
    if t <= 0: return "-"
    m = int(t // 60); s = t - m * 60
    if decimals > 0:
        return f"{m}:{s:0{decimals + 3}.{decimals}f}"
    return f"{m}:{int(s):02d}"


class RelativeWidget(BaseWidget):
    WIDGET_NAME = "Relative"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Appearance"},
        {"key": "opacity",           "label": "Opacity (%)", "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 85},
        {"key": "scale",             "label": "Size (%)",    "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 100},
        {"key": "font_size",         "label": "Font size",   "type": "int",
         "min": 7, "max": 14, "step": 1, "default": 11},
        {"type": "separator", "label": "Rows"},
        {"key": "drivers_ahead",     "label": "Drivers ahead",  "type": "int",
         "min": 1, "max": 10, "step": 1, "default": 4},
        {"key": "drivers_behind",    "label": "Drivers behind", "type": "int",
         "min": 1, "max": 10, "step": 1, "default": 4},
        {"key": "interval_decimals", "label": "Gap decimals",   "type": "int",
         "min": 0, "max": 3,  "step": 1, "default": 1},
        {"type": "separator", "label": "Names"},
        {"key": "show_logo",         "label": "Brand logo",  "type": "bool", "default": True},
        {"key": "show_lap_diff",     "label": "Color name red/blue when a lap apart", "type": "bool", "default": True},
        {"key": "name_format",       "label": "Format", "type": "choice",
         "options": [
             {"value": "full",    "label": "First Last"},
             {"value": "initial", "label": "F. Last"},
             {"value": "last",    "label": "Last only"},
         ], "default": "full"},
        {"key": "name_case",         "label": "Case", "type": "choice",
         "options": [
             {"value": "upper", "label": "NAME LASTNAME"},
             {"value": "mixed", "label": "Name LASTNAME"},
             {"value": "title", "label": "Name Lastname"},
         ], "default": "upper"},
        {"key": "name_width",        "label": "Name width (px)", "type": "int",
         "min": 60, "max": 400, "step": 5, "default": 150},
        {"type": "separator", "label": "Player row"},
        {"key": "player_color",      "label": "Color",        "type": "color", "default": "#ECAA43"},
        {"key": "player_color_alpha","label": "Intensity (%)", "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 20},
        {"type": "separator", "label": "Header"},
        {"key": "show_session_bar",  "label": "Show header",  "type": "bool", "default": False},
        {"key": "header_info",       "label": "Content",      "type": "choice",
         "options": [
             {"value": "session", "label": "Session + Time"},
             {"value": "temp",    "label": "Temperatures"},
             {"value": "none",    "label": "Nothing"},
         ], "default": "session", "show_if": "show_session_bar"},
        {"type": "separator", "label": "Badges"},
        {"key": "show_badges",       "label": "PIT / OUT badges", "type": "bool", "default": True},
        {"type": "separator", "label": "Last lap"},
        {"key": "show_last_lap",     "label": "LAST LAP column",  "type": "bool", "default": True},
    ]

    # All colors from theme.T — no hex literals in this class.

    def __init__(self,
                 drivers_ahead:      int = 4,
                 drivers_behind:     int = 4,
                 interval_decimals:  int = 1,
                 show_badges:        bool = True,
                 name_width:         int = 150,
                 name_format:        str = "full",
                 name_case:          str = "upper",
                 show_session_bar:   bool = False,
                 header_info:        str = "session",
                 font_size:          int = 11,
                 show_last_lap:      bool = True,
                 show_logo:          bool = True,
                 show_lap_diff:      bool = True,
                 **kw):
        self._ahead              = drivers_ahead
        self._behind             = drivers_behind
        self._interval_decimals  = interval_decimals
        self._show_badges        = show_badges
        self._show_last_lap      = show_last_lap
        self._show_logo          = show_logo
        self._show_lap_diff      = show_lap_diff
        self._name_width = name_width
        self._name_format         = name_format
        self._name_case           = name_case
        self._show_session_bar    = show_session_bar
        self._header_info         = header_info
        self._ses_type            = 0
        self._is_race             = False
        self._current_et          = 0.0
        self._ses_remaining       = 0.0
        self._track_temp          = 0.0
        self._air_temp            = 0.0
        self._scale               = DEFAULT_SCALE / 100.0
        self._font_size           = max(7, min(14, int(font_size)))
        self._rows:  list    = []
        self._outlap_tracking:  dict[int, int]  = {}
        self._pit_lap_tracking: dict[int, int]  = {}
        self._prev_in_pits:     dict[int, bool] = {}
        self._last_reset_count: int = -1
        self._class_colors:   dict[str, str]  = {}
        self._player_color = QColor(0xEC, 0xAA, 0x43, 51)
        self._temp_pm_trk = None
        self._temp_pm_air = None
        self._temp_pm_sz  = 0
        self._opacity = 85
        super().__init__(update_hz=10, **kw)
        self.setFixedSize(int(_widget_w(name_width, self._font_size, self._interval_decimals, show_last_lap, show_logo) * self._scale),
                          int(_widget_h(drivers_ahead, drivers_behind, self._font_size, show_session_bar) * self._scale))

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def apply_class_colors(self, colors: dict) -> None:
        self._class_colors = colors
        self.update()

    def apply_params(self, params: dict) -> None:
        self._ahead             = int(params.get("drivers_ahead", 4))
        self._behind            = int(params.get("drivers_behind", 4))
        self._interval_decimals = int(params.get("interval_decimals", 1))
        self._show_badges       = bool(params.get("show_badges", True))
        self._show_last_lap     = bool(params.get("show_last_lap", True))
        self._show_logo         = bool(params.get("show_logo", True))
        self._show_lap_diff     = bool(params.get("show_lap_diff", True))
        self._name_width = int(params.get("name_width", 150))
        self._name_format         = str(params.get("name_format", "full"))
        self._name_case           = str(params.get("name_case", "upper"))
        self._show_session_bar    = bool(params.get("show_session_bar",  False))
        self._header_info         = str(params.get("header_info", "session"))
        self._scale               = int(params.get("scale", DEFAULT_SCALE)) / 100.0
        self._font_size           = max(7, min(14, int(params.get("font_size", 11))))
        self._opacity        = max(0, min(100, int(params.get("opacity", 85))))
        _c = QColor(str(params.get("player_color", "#ECAA43")))
        if not _c.isValid(): _c = QColor(255, 200, 0)
        _c.setAlpha(round(255 * max(0, min(100, int(params.get("player_color_alpha", 20)))) / 100))
        self._player_color = _c
        self._apply_session_visibility(params)
        self.setFixedSize(int(_widget_w(self._name_width, self._font_size, self._interval_decimals, self._show_last_lap, self._show_logo) * self._scale),
                          int(_widget_h(self._ahead, self._behind, self._font_size, self._show_session_bar) * self._scale))
        self.update()

    def on_data(self):
        s = minfo.session
        self._ses_type      = s.sessionType
        self._is_race       = s.sessionType >= 10
        self._current_et    = s.currentEt
        self._ses_remaining = s.timeRemaining
        self._track_temp    = s.trackTemp
        self._air_temp      = s.ambientTemp

        # New session / restart → clear badge state. module_stint.py bumps
        # resetCount on any detected reset; comparing with != survives this
        # widget polling at a different cadence than that module's own tick.
        if minfo.stint.resetCount != self._last_reset_count:
            self._last_reset_count = minfo.stint.resetCount
            self._outlap_tracking.clear()
            self._pit_lap_tracking.clear()
            self._prev_in_pits.clear()

        vehicles = minfo.vehicles.dataSet
        player   = next((v for v in vehicles if v.is_player), None)
        if not player:
            return

        # Outlap / pit-lap tracking
        new_prev: dict[int, bool] = {}
        for v in vehicles:
            slot     = v.slot_id
            in_pit   = v.in_pit_lane
            was_pits = self._prev_in_pits.get(slot, in_pit)
            new_prev[slot] = in_pit
            if v.in_garage:
                self._outlap_tracking.pop(slot, None)
                self._pit_lap_tracking.pop(slot, None)
            elif not was_pits and in_pit:
                self._pit_lap_tracking[slot] = v.total_laps
            elif was_pits and not in_pit:
                self._outlap_tracking[slot] = v.total_laps
            elif slot in self._outlap_tracking and v.total_laps > self._outlap_tracking[slot]:
                del self._outlap_tracking[slot]
        self._prev_in_pits = new_prev

        # Class position map: sort each class group by overall place
        class_groups: dict[str, list] = {}
        for v in vehicles:
            cls = v.vehicle_class.lower()
            if cls not in class_groups:
                class_groups[cls] = []
            class_groups[cls].append(v)
        class_pos: dict[int, int] = {}
        for grp in class_groups.values():
            for rank, v in enumerate(sorted(grp, key=lambda x: x.place), 1):
                class_pos[v.slot_id] = rank

        laptime_est = player.estimated_lap_time
        if laptime_est <= 0:
            best_laps = [v.best_lap for v in vehicles if v.best_lap > 10]
            laptime_est = min(best_laps) if best_laps else 120.0

        plr_time     = player.time_into_lap
        track_length = s.trackLength

        ahead_list:  list[tuple[float, dict]] = []
        behind_list: list[tuple[float, dict]] = []

        for v in vehicles:
            if v.is_player or v.in_garage:
                continue

            diff_time  = v.time_into_lap - plr_time
            gap        = diff_time - (diff_time // laptime_est) * laptime_est
            gap_ahead  = gap if gap >= 0 else gap + laptime_est
            gap_behind = gap - laptime_est if gap > 0 else gap

            slot  = v.slot_id
            badge = ("PIT" if v.in_pit_lane
                     else "OUT" if slot in self._outlap_tracking
                     else f"L{self._pit_lap_tracking[slot]}" if slot in self._pit_lap_tracking
                     else "")

            entry = {
                "pos":       class_pos.get(v.slot_id, v.place),
                "name_raw":  v.driver_name or f"Car {v.place}",
                "is_player": False,
                "badge":     badge,
                "cls":       v.vehicle_class,
                "vehicle_name": v.vehicle_name,
                "last_lap":  v.last_lap,
                "is_pb":     v.last_lap > 0 and v.best_lap > 0 and v.last_lap <= v.best_lap,
                "lap_diff":  _lap_diff_sign(v.total_laps, v.lap_dist,
                                            player.total_laps, player.lap_dist, track_length),
            }
            ahead_list.append((gap_ahead,  {**entry, "gap": -gap_ahead}))
            behind_list.append((gap_behind, {**entry, "gap": -gap_behind}))

        ahead_list.sort(reverse=True)    # closest-to-player first = largest gap_ahead
        behind_list.sort(reverse=True)   # closest-to-player first = least-negative gap_behind

        ahead_entries  = [e for _, e in ahead_list[-self._ahead:]]
        behind_entries = [e for _, e in behind_list[:self._behind]]

        p_slot  = player.slot_id
        # GAR only ever applies to the player: other drivers in the garage are
        # filtered out of the relative list above.
        p_badge = ("GAR" if player.in_garage
                   else "PIT" if player.in_pit_lane
                   else "OUT" if p_slot in self._outlap_tracking
                   else f"L{self._pit_lap_tracking[p_slot]}" if p_slot in self._pit_lap_tracking
                   else "")

        player_entry = {
            "pos":       class_pos.get(player.slot_id, player.place),
            "name_raw":  player.driver_name or "Player",
            "gap":       0.0,
            "is_player": True,
            "badge":     p_badge,
            "cls":       player.vehicle_class,
            "vehicle_name": player.vehicle_name,
            "last_lap":  player.last_lap,
            "is_pb":     player.last_lap > 0 and player.best_lap > 0 and player.last_lap <= player.best_lap,
            "lap_diff":  0,
        }

        # Pad ahead list to always have self._ahead rows
        empty = {"pos": 0, "name_raw": "", "gap": 0.0, "is_player": False, "badge": "", "cls": "",
                 "vehicle_name": "", "last_lap": -1.0, "is_pb": False, "lap_diff": 0}
        ahead_padded  = [empty] * max(0, self._ahead - len(ahead_entries)) + ahead_entries
        behind_padded = behind_entries + [empty] * max(0, self._behind - len(behind_entries))

        self._rows = ahead_padded + [player_entry] + behind_padded
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)
        W    = _widget_w(self._name_width, self._font_size, self._interval_decimals, self._show_last_lap, self._show_logo)
        _show_bar = self._show_session_bar and self._header_info != "none"
        H    = _widget_h(self._ahead, self._behind, self._font_size, _show_bar)
        ncw  = self._name_width
        bdg  = _badge_px(self._font_size)
        pos_w  = _pos_col_w(self._font_size)
        chip_w = _pos_chip_w(self._font_size)
        logo_w = _LOGO_COL_W if self._show_logo else 0
        name_x = pos_w + logo_w
        gap_w  = _gap_col_w(self._font_size, self._interval_decimals)
        last_w = _lastlap_col_w(self._font_size)
        # Last Lap sits before Gap now — lastlap_x hoisted here, gx derives
        # from it. Deliberately not named `lx` — the per-row logo block below
        # already uses that name for its own local pixel position, and reused
        # it would silently shadow this one on every row (found the hard way:
        # Last Lap rendered on top of the logo/position chip instead of after
        # the name).
        lastlap_x = name_x + ncw + _GAP_PAD_L
        gx        = lastlap_x + (last_w + _GAP_PAD_L if self._show_last_lap else 0)
        _sbh = _session_bar_h(self._font_size) if _show_bar else 0

        self._draw_panel(p, W, H)

        fs  = self._font_size
        fsh = fs   # headers match the driver-name size (same perceived weight)
        fss = max(5, fs - 2)   # row badges (GAR, PIT, OUT…)
        rh  = _row_h(fs)

        # ── Session bar ───────────────────────────────────────────────────
        if _show_bar:
            hi = self._header_info
            if hi == "session":
                lbl = _session_label(self._ses_type)
                f = label_font(max(6, fsh))
                p.setFont(f)
                fm   = p.fontMetrics()
                lbl_w = fm.horizontalAdvance(lbl)
                baseline = 1 + (_sbh + fm.ascent() - fm.descent()) // 2
                p.setPen(QColor(T.ACCENT))
                draw_bold(p, lambda: p.drawText(6, baseline, lbl))
                p.setFont(num_font(max(6, fsh), hint=False))
                p.setPen(QColor(T.TEXT))
                _st = _fmt_session_time(self._current_et, self._ses_remaining)
                draw_bold(p, lambda: p.drawText(6 + lbl_w + 6, baseline, _st))
            elif hi == "temp":
                p.setFont(num_font(fsh))
                fm = p.fontMetrics()
                trk_str = f"{self._track_temp:.0f}°"
                air_str = f"{self._air_temp:.0f}°"
                icon_sz = max(6, fsh + 1)
                if icon_sz != self._temp_pm_sz:
                    self._temp_pm_trk = QIcon(_TRACK_TEMP_SVG).pixmap(icon_sz, icon_sz)
                    self._temp_pm_air = QIcon(_AIR_TEMP_SVG).pixmap(icon_sz, icon_sz)
                    self._temp_pm_sz  = icon_sz
                gap_px = 3
                sep_px = 8
                trk_w = fm.horizontalAdvance(trk_str)
                air_w = fm.horizontalAdvance(air_str)
                x0 = 6
                icon_y = 1 + _sbh // 2 - icon_sz // 2
                p.drawPixmap(x0, icon_y, self._temp_pm_trk)
                p.setPen(QColor(T.DIM))
                p.drawText(x0 + icon_sz + gap_px, 1, trk_w + 2, _sbh,
                           Qt.AlignmentFlag.AlignVCenter, trk_str)
                ax = x0 + icon_sz + gap_px + trk_w + sep_px
                p.drawPixmap(ax, icon_y, self._temp_pm_air)
                p.setPen(QColor(T.DIM))
                p.drawText(ax + icon_sz + gap_px, 1, air_w + 2, _sbh,
                           Qt.AlignmentFlag.AlignVCenter, air_str)
            p.fillRect(QRectF(2, _sbh, W - 4, 1), T.FAINT)

        _badge_map = {
            "GAR": (QColor(T.GAR_BG), QColor(T.GAR_FG)),
            "PIT": (QColor(T.PIT_BG), QColor(T.PIT_FG)),
            "OUT": (QColor(T.OUT_BG), QColor(T.OUT_FG)),
        }

        for i, row in enumerate(self._rows):
            y = _sbh + 4 + i * rh
            if not row["name_raw"] and not row["is_player"]:
                continue

            is_p  = row["is_player"]
            gap   = row["gap"]
            badge = row["badge"] if self._show_badges else ""
            name  = _apply_case(_fmt_name(row["name_raw"], self._name_format), self._name_case)

            # Player row highlight
            if is_p:
                p.setBrush(self._player_color)
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(1, y, W - 2, rh, 3, 3)

            # Position chip — class color background, white text
            if row["pos"] > 0:
                cc = class_color(row.get("cls", ""), self._class_colors)
                if cc:
                    c2 = QColor(cc); c2.setAlpha(255)
                    p.setBrush(c2); p.setPen(Qt.PenStyle.NoPen)
                    p.drawRoundedRect(_POS_CHIP_X, y + 1, chip_w, rh - 2, 2, 2)
                p.setFont(num_font(fs))
                p.setPen(QColor(T.TEXT))
                p.drawText(_POS_CHIP_X, y, chip_w, rh, Qt.AlignmentFlag.AlignCenter, str(row["pos"]))

            # Manufacturer logo — own small column between the position chip
            # and the name, same convention as Standings (pos | logo | name).
            if self._show_logo and row["pos"] > 0:
                s  = self._scale
                pw = max(10, round((_LOGO_COL_W - 4) * s))
                ph = max(6,  round((rh - 4) * s))
                logo = _get_logo(row.get("vehicle_name", ""), pw, ph)
                if logo:
                    max_lw = float(_LOGO_COL_W - 4)
                    max_lh = float(rh - 4)
                    sc  = min(max_lw / logo.width(), max_lh / logo.height())
                    dw  = logo.width()  * sc
                    dh  = logo.height() * sc
                    lx  = pos_w + (logo_w - dw) / 2
                    ly  = y + (rh - dh) / 2
                    p.drawPixmap(QRectF(lx, ly, dw, dh), logo, QRectF(logo.rect()))

            # Driver name — elided to the column width: a character count no
            # longer maps to a width now that the text font is proportional.
            # Tinted red/blue when this car and the player are on different
            # lap counts (see _lap_diff_sign) — Relative only ever shows cars
            # physically near the player, so this always means the lap is
            # about to be taken/given, not some distant, meaningless gap.
            # Race only: in Practice/Qualifying a lap "apart" is just fuel
            # loads and out-laps, not a real lap-count gap.
            lap_diff = row.get("lap_diff", 0) if (self._show_lap_diff and self._is_race) else 0
            name_col = (QColor(T.CRIT) if lap_diff > 0
                        else QColor(T.COLD) if lap_diff < 0
                        else QColor(T.TEXT))
            p.setFont(text_font(fs))
            p.setPen(name_col)
            avail = ncw - _NAME_PAD_L - (bdg + 2 if badge else 0)
            shown = p.fontMetrics().elidedText(name, Qt.TextElideMode.ElideRight, max(10, avail))
            p.drawText(name_x + _NAME_PAD_L, y, ncw - _NAME_PAD_L, rh,
                       Qt.AlignmentFlag.AlignVCenter, shown)

            # Badge overlaid at right edge of name zone
            if badge:
                if badge in _badge_map:
                    bg_c, fg_c = _badge_map[badge]
                else:
                    bg_c, fg_c = QColor(T.LAP_BG), QColor(T.LAP_FG)
                bx2, by2 = name_x + ncw - bdg, y + 3
                p.setBrush(bg_c); p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(bx2, by2, bdg, rh - 6, 2, 2)
                p.setFont(num_font(fss)); p.setPen(fg_c)
                draw_bold(p, lambda: p.drawText(
                    bx2, by2, bdg, rh - 6, Qt.AlignmentFlag.AlignCenter, badge))

            # Last lap — drawn before Gap now. Shown for every real row,
            # including the player's own (unlike Gap, which is meaningless
            # relative to oneself). Purple like Standings' session-best would
            # need a grid-wide comparison this widget doesn't otherwise
            # compute; personal-best (green) only needs each car's own
            # best_lap, already on hand. lastlap_x hoisted above the loop.
            if self._show_last_lap and row["pos"] > 0:
                lc = QColor(T.GOOD) if row.get("is_pb") else QColor(T.TEXT)
                p.setFont(num_font(fs)); p.setPen(lc)
                p.drawText(lastlap_x, y, last_w, rh,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           _fmt_lap(row.get("last_lap", -1.0)))

            # Gap — fixed-width column, drawn after Last Lap now. gx hoisted
            # above the loop — same for every row.
            if not is_p and row["pos"] > 0:
                p.setFont(num_font(fs))
                p.setPen(QColor(T.TEXT))
                p.drawText(gx, y, gap_w, rh,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           _fmt_gap(gap, self._interval_decimals))

        p.end()
