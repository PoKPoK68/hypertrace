"""
Relative overlay.

Separate drivers_ahead / drivers_behind counts.
Badge overlays the name text (no column shrink).
"""
from __future__ import annotations
import math as _math
from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QIcon, QPainter
from PySide6.QtWidgets import QSizePolicy

from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.utils.class_colors import class_color
from lmu_app.utils.theme import T, draw_bold, label_font, num_font, text_font
from lmu_app.widgets.base import BaseWidget, DEFAULT_SCALE

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_TRACK_TEMP_SVG = str(_ASSETS / "track-temp.svg")
_AIR_TEMP_SVG   = str(_ASSETS / "air-temp.svg")

_POS_COL_W    = 28    # largeur colonne position
_MARGIN       = 6     # marge droite
SESSION_BAR_H = 22


def _char_px(font_size: int) -> int:
    return max(4, round(7 * font_size / 9))


def _badge_px(font_size: int) -> int:
    return max(14, round(22 * font_size / 9))


def _gap_col_w(font_size: int, decimals: int) -> int:
    # "+12.345" = 4 chars de base + nb décimales
    max_chars = 4 + max(0, decimals)
    return max_chars * _char_px(font_size) + 4


def _widget_w(max_name_chars: int, font_size: int = 9, decimals: int = 1) -> int:
    return _POS_COL_W + max_name_chars * _char_px(font_size) + _gap_col_w(font_size, decimals) + _MARGIN


def _row_h(font_size: int) -> int:
    return font_size + 13


def _widget_h(ahead: int, behind: int, font_size: int = 9,
              show_session_bar: bool = False) -> int:
    return (SESSION_BAR_H if show_session_bar else 0) + (ahead + 1 + behind) * _row_h(font_size) + 8


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

def _fmt_gap(g: float, decimals: int = 1) -> str:
    return f"{g:+.{decimals}f}"


class RelativeWidget(BaseWidget):
    WIDGET_NAME = "Relative"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Appearance"},
        {"key": "opacity",           "label": "Opacity (%)", "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 85},
        {"key": "scale",             "label": "Size (%)",    "type": "int",
         "min": 50, "max": 250, "step": 5, "default": 100},
        {"key": "font_size",         "label": "Font size",   "type": "int",
         "min": 7, "max": 14, "step": 1, "default": 9},
        {"type": "separator", "label": "Rows"},
        {"key": "drivers_ahead",     "label": "Drivers ahead",  "type": "int",
         "min": 1, "max": 10, "step": 1, "default": 4},
        {"key": "drivers_behind",    "label": "Drivers behind", "type": "int",
         "min": 1, "max": 10, "step": 1, "default": 4},
        {"key": "interval_decimals", "label": "Gap decimals",   "type": "int",
         "min": 0, "max": 3,  "step": 1, "default": 1},
        {"type": "separator", "label": "Names"},
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
        {"key": "max_name_chars",    "label": "Max characters", "type": "int",
         "min": 4, "max": 30, "step": 1, "default": 16},
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
    ]

    # All colors from theme.T — no hex literals in this class.

    def __init__(self, reader: DataReader,
                 drivers_ahead:      int = 4,
                 drivers_behind:     int = 4,
                 interval_decimals:  int = 1,
                 show_badges:        bool = True,
                 max_name_chars:     int = 16,
                 name_format:        str = "full",
                 name_case:          str = "upper",
                 show_session_bar:   bool = False,
                 header_info:        str = "session",
                 font_size:          int = 9,
                 **kw):
        self._ahead              = drivers_ahead
        self._behind             = drivers_behind
        self._interval_decimals  = interval_decimals
        self._show_badges        = show_badges
        self._max_name_chars = max_name_chars
        self._name_format         = name_format
        self._name_case           = name_case
        self._show_session_bar    = show_session_bar
        self._header_info         = header_info
        self._ses_type            = 0
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
        self._last_session_id:  int = -1
        self._class_colors:   dict[str, str]  = {}
        self._player_color = QColor(0xEC, 0xAA, 0x43, 51)
        self._temp_pm_trk = None
        self._temp_pm_air = None
        self._temp_pm_sz  = 0
        self._opacity = 85
        super().__init__(reader, update_hz=10, **kw)
        self.setFixedSize(int(_widget_w(max_name_chars, self._font_size, self._interval_decimals) * self._scale),
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
        self._max_name_chars = int(params.get("max_name_chars", 16))
        self._name_format         = str(params.get("name_format", "full"))
        self._name_case           = str(params.get("name_case", "upper"))
        self._show_session_bar    = bool(params.get("show_session_bar",  False))
        self._header_info         = str(params.get("header_info", "session"))
        self._scale               = int(params.get("scale", DEFAULT_SCALE)) / 100.0
        self._font_size           = max(7, min(14, int(params.get("font_size", 9))))
        self._opacity        = max(0, min(100, int(params.get("opacity", 85))))
        _c = QColor(str(params.get("player_color", "#ffc800")))
        if not _c.isValid(): _c = QColor(255, 200, 0)
        _c.setAlpha(round(255 * max(0, min(100, int(params.get("player_color_alpha", 20)))) / 100))
        self._player_color = _c
        self.setFixedSize(int(_widget_w(self._max_name_chars, self._font_size, self._interval_decimals) * self._scale),
                          int(_widget_h(self._ahead, self._behind, self._font_size, self._show_session_bar) * self._scale))
        self.update()

    def on_data(self, snap: LMUSnapshot):
        self._ses_type      = snap.session.session_type
        self._current_et    = snap.session.current_et
        self._ses_remaining = snap.session.session_time_remaining
        self._track_temp    = snap.session.track_temp
        self._air_temp      = snap.session.ambient_temp

        # New session / restart (reader bumps session_id) → clear badge state
        if snap.session.session_id != self._last_session_id:
            self._last_session_id = snap.session.session_id
            self._outlap_tracking.clear()
            self._pit_lap_tracking.clear()
            self._prev_in_pits.clear()

        vehicles = snap.session.vehicles
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

        plr_time = player.time_into_lap

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
        }

        # Pad ahead list to always have self._ahead rows
        empty = {"pos": 0, "name_raw": "", "gap": 0.0, "is_player": False, "badge": "", "cls": ""}
        ahead_padded  = [empty] * max(0, self._ahead - len(ahead_entries)) + ahead_entries
        behind_padded = behind_entries + [empty] * max(0, self._behind - len(behind_entries))

        self._rows = ahead_padded + [player_entry] + behind_padded
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self._scale, self._scale)
        W    = _widget_w(self._max_name_chars, self._font_size, self._interval_decimals)
        _show_bar = self._show_session_bar and self._header_info != "none"
        H    = _widget_h(self._ahead, self._behind, self._font_size, _show_bar)
        ncw  = self._max_name_chars * _char_px(self._font_size)
        bdg  = _badge_px(self._font_size)
        _sbh = SESSION_BAR_H if _show_bar else 0

        self._draw_panel(p, W, H)

        fs  = self._font_size
        fsh = max(6.0, fs - 1.5)   # session bar / column header labels
        fss = max(6, fs - 2)   # row badges (GAR, PIT, OUT…)
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
                p.drawText(6, baseline, lbl)
                f_num = label_font(max(6, fsh), hint=False)
                f_num.setCapitalization(QFont.Capitalization.MixedCase)
                p.setFont(f_num)
                p.setPen(QColor(T.TEXT))
                _st = _fmt_session_time(self._current_et, self._ses_remaining)
                draw_bold(p, lambda: p.drawText(6 + lbl_w + 6, baseline, _st))
            elif hi == "temp":
                p.setFont(num_font(fsh, hint=False))
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
                draw_bold(p, lambda: p.drawText(
                    x0 + icon_sz + gap_px, 1, trk_w + 2, _sbh,
                    Qt.AlignmentFlag.AlignVCenter, trk_str))
                ax = x0 + icon_sz + gap_px + trk_w + sep_px
                p.drawPixmap(ax, icon_y, self._temp_pm_air)
                p.setPen(QColor(T.DIM))
                draw_bold(p, lambda: p.drawText(
                    ax + icon_sz + gap_px, 1, air_w + 2, _sbh,
                    Qt.AlignmentFlag.AlignVCenter, air_str))
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
            name  = _apply_case(_fmt_name(row["name_raw"], self._name_format)[:self._max_name_chars], self._name_case)

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
                    p.drawRoundedRect(4, y + 1, 22, rh - 2, 2, 2)
                p.setFont(num_font(fs))
                p.setPen(QColor(T.TEXT))
                p.drawText(4, y, 22, rh, Qt.AlignmentFlag.AlignCenter, str(row["pos"]))

            # Driver name
            name_col = QColor(T.TEXT)
            p.setFont(text_font(fs, hint=False))
            p.setPen(name_col)
            draw_bold(p, lambda: p.drawText(28, y, ncw, rh,
                                            Qt.AlignmentFlag.AlignVCenter, name))

            # Badge overlaid at right edge of name zone
            if badge:
                if badge in _badge_map:
                    bg_c, fg_c = _badge_map[badge]
                else:
                    bg_c, fg_c = QColor(T.LAP_BG), QColor(T.LAP_FG)
                bx2, by2 = 28 + ncw - bdg, y + 3
                p.setBrush(bg_c); p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(bx2, by2, bdg, rh - 6, 2, 2)
                p.setFont(num_font(fss)); p.setPen(fg_c)
                p.drawText(bx2, by2, bdg, rh - 6, Qt.AlignmentFlag.AlignCenter, badge)

            # Gap
            if not is_p and row["pos"] > 0:
                p.setFont(num_font(fs))
                p.setPen(QColor(T.TEXT))
                p.drawText(28 + ncw, y, W - 28 - ncw - 4, rh,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           _fmt_gap(gap, self._interval_decimals))

        p.end()
