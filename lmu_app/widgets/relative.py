"""
Relative overlay.

Separate drivers_ahead / drivers_behind counts.
Badge overlays the name text (no column shrink).
"""
from __future__ import annotations
import math as _math
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.utils.class_colors import class_color
from lmu_app.widgets.base import BaseWidget

_W_BASE  = 74    # fixed: 28px pos column + 40px gap area + 6px margin


def _char_px(font_size: int) -> int:
    return max(4, round(7 * font_size / 9))


def _badge_px(font_size: int) -> int:
    return max(14, round(22 * font_size / 9))


def _widget_w(max_name_chars: int, font_size: int = 9) -> int:
    return max_name_chars * _char_px(font_size) + _W_BASE


def _row_h(font_size: int) -> int:
    return font_size + 13


def _widget_h(ahead: int, behind: int, font_size: int = 9) -> int:
    return (ahead + 1 + behind) * _row_h(font_size) + 8


def _fmt_name(raw: str, fmt: str) -> str:
    if not raw: return raw
    parts = raw.strip().split()
    if fmt == "last":
        return parts[-1] if parts else raw
    if fmt == "initial" and len(parts) >= 2:
        return f"{parts[0][0]}. {' '.join(parts[1:])}"
    return raw

def _fmt_gap(g: float, decimals: int = 1) -> str:
    return f"{g:+.{decimals}f}"


class RelativeWidget(BaseWidget):
    WIDGET_NAME = "Relative"
    CONFIG_SCHEMA = [
        {"type": "separator", "label": "Window"},
        {"key": "opacity",           "label": "Opacity (%)",            "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 85},
        {"type": "separator", "label": "Rows"},
        {"key": "drivers_ahead",     "label": "Drivers ahead",         "type": "int",
         "min": 1, "max": 10, "step": 1, "default": 4},
        {"key": "drivers_behind",    "label": "Drivers behind",        "type": "int",
         "min": 1, "max": 10, "step": 1, "default": 4},
        {"type": "separator", "label": "Names"},
        {"key": "max_name_chars",    "label": "Name max chars",        "type": "int",
         "min": 4, "max": 30, "step": 1, "default": 16},
        {"key": "name_format",       "label": "Name format",           "type": "choice",
         "options": [
             {"value": "full",    "label": "First Last"},
             {"value": "initial", "label": "F. Last"},
             {"value": "last",    "label": "Last only"},
         ], "default": "full"},
        {"type": "separator", "label": "Display"},
        {"key": "show_badges",       "label": "PIT / OUT badges",      "type": "bool", "default": True},
        {"key": "player_color",      "label": "Player row color",       "type": "color", "default": "#ffc800"},
        {"key": "player_color_alpha","label": "Player row opacity (%)", "type": "int",
         "min": 0, "max": 100, "step": 5, "default": 20},
        {"key": "interval_decimals", "label": "Interval decimals (0-3)","type": "int",
         "min": 0, "max": 3,  "step": 1, "default": 1},
        {"key": "font_size",         "label": "Font size",              "type": "int",
         "min": 7, "max": 14, "step": 1, "default": 9},
    ]

    C_BG     = QColor(10, 10, 10, 215)
    C_BORDER = QColor(55, 55, 55, 180)
    C_TEXT   = QColor(220, 220, 220)
    C_DIM    = QColor(110, 110, 110)
    C_AHEAD  = QColor(100, 200, 255)
    C_BEHIND = QColor(255, 120, 80)
    C_PIT_BG = QColor(50, 110, 200, 210)
    C_PIT_FG = QColor(240, 240, 240)
    C_OUT_BG = QColor(190, 130, 0, 210)
    C_OUT_FG = QColor(20, 20, 20)

    def __init__(self, reader: DataReader,
                 drivers_ahead:      int = 4,
                 drivers_behind:     int = 4,
                 interval_decimals:  int = 1,
                 show_badges:        bool = True,
                 max_name_chars:     int = 16,
                 name_format:        str = "full",
                 font_size:          int = 9,
                 **kw):
        self._ahead              = drivers_ahead
        self._behind             = drivers_behind
        self._interval_decimals  = interval_decimals
        self._show_badges        = show_badges
        self._max_name_chars = max_name_chars
        self._name_format    = name_format
        self._font_size      = max(7, min(14, int(font_size)))
        self._rows:  list    = []
        self._outlap_tracking: dict[int, int] = {}
        self._prev_in_pits:   dict[int, bool] = {}
        self._class_colors:   dict[str, str]  = {}
        self._player_color = QColor(255, 200, 0, 50)
        self._opacity = 85
        super().__init__(reader, update_hz=10, **kw)
        self.setFixedSize(_widget_w(max_name_chars, self._font_size), _widget_h(drivers_ahead, drivers_behind, self._font_size))

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
        self._name_format    = str(params.get("name_format", "full"))
        self._font_size      = max(7, min(14, int(params.get("font_size", 9))))
        self._opacity        = max(0, min(100, int(params.get("opacity", 85))))
        _c = QColor(str(params.get("player_color", "#ffc800")))
        if not _c.isValid(): _c = QColor(255, 200, 0)
        _c.setAlpha(round(255 * max(0, min(100, int(params.get("player_color_alpha", 20)))) / 100))
        self._player_color = _c
        self.setFixedSize(_widget_w(self._max_name_chars, self._font_size),
                          _widget_h(self._ahead, self._behind, self._font_size))
        self.update()

    def on_data(self, snap: LMUSnapshot):
        vehicles = snap.session.vehicles
        player   = next((v for v in vehicles if v.is_player), None)
        if not player:
            return

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
            badge = ("PIT" if v.in_pits
                     else "OUT" if slot in self._outlap_tracking
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
        p_badge = ("PIT" if player.in_pits
                   else "OUT" if p_slot in self._outlap_tracking
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
        W = self.width()
        H = self.height()
        ncw = self._max_name_chars * _char_px(self._font_size)
        bdg = _badge_px(self._font_size)

        p.setBrush(QColor(10, 10, 10, self._bg_alpha())); p.setPen(self._border_pen())
        p.drawRoundedRect(0, 0, W, H, 8, 8)

        player_row_idx = self._ahead  # index of player row in self._rows

        rh = _row_h(self._font_size)
        for i, row in enumerate(self._rows):
            y = 4 + i * rh
            if not row["name_raw"] and not row["is_player"]:
                continue  # empty slot

            is_p  = row["is_player"]
            gap   = row["gap"]
            badge = row["badge"] if self._show_badges else ""
            name  = _fmt_name(row["name_raw"], self._name_format)[:self._max_name_chars]

            if is_p:
                p.setBrush(self._player_color); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(1, y, W-2, rh)

            fs  = self._font_size
            fss = max(6, fs - 2)

            # Position — class color background (fully opaque)
            if row["pos"] > 0:
                cc = class_color(row.get("cls", ""), self._class_colors)
                if cc:
                    c2 = QColor(cc); c2.setAlpha(255)
                    p.setBrush(c2); p.setPen(Qt.PenStyle.NoPen)
                    p.drawRoundedRect(4, y + 1, 22, rh - 2, 2, 2)
            p.setFont(QFont("Monospace", fs, QFont.Weight.Bold))
            p.setPen(QColor(255, 220, 80) if is_p else self.C_TEXT)
            if row["pos"] > 0:
                p.drawText(4, y, 22, rh, Qt.AlignmentFlag.AlignCenter, str(row["pos"]))

            # Name — always full width, badge overlays on top
            p.setFont(QFont("Monospace", fs, QFont.Weight.Bold))
            p.setPen(self.C_TEXT)
            p.drawText(28, y, ncw, rh, Qt.AlignmentFlag.AlignVCenter, name)

            # Badge overlaid at right edge of name zone
            if badge:
                bx2 = 28 + ncw - bdg; by2 = y + 3
                bg  = self.C_PIT_BG if badge == "PIT" else self.C_OUT_BG
                fg  = self.C_PIT_FG if badge == "PIT" else self.C_OUT_FG
                p.setBrush(bg); p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(bx2, by2, bdg, rh - 6, 2, 2)
                p.setFont(QFont("Monospace", fss, QFont.Weight.Bold)); p.setPen(fg)
                p.drawText(bx2, by2, bdg, rh - 6, Qt.AlignmentFlag.AlignCenter, badge)

            # Gap value — white, drawn right-aligned after name zone
            if not is_p and row["pos"] > 0:
                p.setPen(self.C_TEXT)
                p.setFont(QFont("Monospace", fs, QFont.Weight.Bold))
                p.drawText(28 + ncw, y, W - 28 - ncw - 4, rh,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           _fmt_gap(gap, self._interval_decimals))
        p.end()
