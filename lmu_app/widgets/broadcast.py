"""lmu_app/widgets/broadcast.py — Broadcast overlay widgets: Tower, Battle, Driver Card."""
from __future__ import annotations

import time as _time
from collections import defaultdict

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from lmu_app.api.reader import LMUSnapshot
from lmu_app.utils.class_colors import class_abbrev, class_color
from lmu_app.utils.logos import get_logo as _get_logo
from lmu_app.utils.compounds import draw_compound_badge as _draw_compound_badge
from lmu_app.utils.theme import T, accent_hairline, border_pen, label_font, num_font, panel_brush, text_font


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_lap(t: float, d: int = 1) -> str:
    if t <= 0:
        return "—"
    m = int(t // 60)
    s = t - m * 60
    return f"{m}:{s:0{d + 3}.{d}f}" if d > 0 else f"{m}:{int(s):02d}"


def _ses_name(stype: int) -> str:
    if stype >= 10:
        return "Race"
    if 5 <= stype <= 8:
        return "Qualifying"
    return "Practice"


def _ses_clock(remaining: float) -> str:
    t = max(0, int(remaining))
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _fmt_name(raw: str, is_team: bool) -> str:
    """Return display-ready name: full for teams, abbreviated for drivers."""
    return raw if is_team else _name_short(raw)


_VE_ABBREVS = ("HYP", "GTP", "LMH", "GT3")

def _ve_label(abbrev: str) -> str:
    """'VE' for Hypercar/GTP/LMH classes, 'FUEL' for all others."""
    return "VE" if any(k in abbrev.upper() for k in _VE_ABBREVS) else "FUEL"


# ---------------------------------------------------------------------------
# Compound badge helpers
def _name_short(raw: str) -> str:
    """'Firstname Lastname' → 'F. LASTNAME'"""
    if not raw:
        return raw
    parts = raw.strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}. {' '.join(parts[1:]).upper()}"
    return raw.upper()


def _name_last(raw: str) -> str:
    """'Firstname Lastname' → 'LASTNAME'"""
    if not raw:
        return raw
    parts = raw.strip().split()
    return ' '.join(parts[1:]).upper() if len(parts) >= 2 else raw.upper()


def _class_rank(cls_name: str) -> int:
    vc = cls_name.strip().upper()
    _KWS = [
        ("HYPERCAR", "LMH", "GTP", "HYPER"),
        ("LMP2", "P2"),
        ("LMP3", "P3"),
        ("GTE", "GT2"),
        ("LMGT3", "GT3", "GTD"),
        ("GTC",),
        ("GT4",),
    ]
    for i, kws in enumerate(_KWS):
        if any(k in vc for k in kws):
            return i
    return 99


# ---------------------------------------------------------------------------
# Shared broadcast state (director controls)
# ---------------------------------------------------------------------------

class BroadcastState:
    """Mutable state shared between MainWindow director controls and broadcast widgets."""

    def __init__(self) -> None:
        self.tower_mode:             int = 0   # 0=Overall, 1=Multiclass, 2=Class filter
        self.tower_count_overall:    int = 10
        self.tower_count_multiclass: int = 5
        self.tower_count_ourclass:   int = 10
        self.tower_parade_count:     int = 5   # rows in the scrolling mobile section
        self.tower_filter_class:     str = ""  # abbrev like "GT3"; "" = auto (viewed car's class)
        self.pinned_slot_id:         int = -1  # manual override for viewed driver; -1 = auto
        self.show_team: bool = False   # True = show team name; False = show driver name

    @property
    def tower_count(self) -> int:
        if self.tower_mode == 1:
            return self.tower_count_multiclass
        elif self.tower_mode == 2:
            return self.tower_count_ourclass
        return self.tower_count_overall

    @tower_count.setter
    def tower_count(self, v: int) -> None:
        if self.tower_mode == 1:
            self.tower_count_multiclass = v
        elif self.tower_mode == 2:
            self.tower_count_ourclass = v
        else:
            self.tower_count_overall = v


# ---------------------------------------------------------------------------
# Base broadcast widget
# ---------------------------------------------------------------------------

class _BcWidget(QWidget):
    WIDGET_NAME:   str  = ""
    CONFIG_SCHEMA: list = []
    stream_hz:     int  = 20   # broadcast overlays don't need high refresh

    def __init__(self) -> None:
        super().__init__(None)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._opacity = 90

    def _bg(self) -> int:
        return round(255 * self._opacity / 100)

    def _panel(self, p: QPainter, w: float, h: float) -> None:
        p.setBrush(panel_brush(0, 0, h, self._bg()))
        p.setPen(border_pen(self._opacity))
        p.drawRoundedRect(0, 0, w, h, T.RADIUS, T.RADIUS)
        p.fillRect(QRectF(9, 0, w - 18, 2), accent_hairline(w, self._opacity))

    def on_data(self, snap: LMUSnapshot) -> None: ...
    def apply_params(self, params: dict) -> None: ...


# ---------------------------------------------------------------------------
# Broadcast Tower
# ---------------------------------------------------------------------------

_TRH     = 26    # row height
_TSEH    = 40    # session bar height
_TCLSH   = 16    # class header height
_TCP     = 3     # column padding

_TPOS_W  = 24
_TLOGO_W = 28   # manufacturer logo column
_TNUM_W  = 36   # car number column
_TINFO_W = 90

# Panel width depends on mode (team names need more space)
_TW_DRV  = 338   # driver mode panel width
_TW_TEAM = 388   # team mode panel width

# Derived name column widths
_TNME_W_DRV  = _TW_DRV  - 8 - _TPOS_W - _TLOGO_W - _TNUM_W - _TINFO_W
_TNME_W_TEAM = _TW_TEAM - 8 - _TPOS_W - _TLOGO_W - _TNUM_W - _TINFO_W

# Badge area (protrudes to the right of the panel)
_TBDG_GAP  = 4
_TBDG_W    = 34
_TW_FULL_DRV  = _TW_DRV  + _TBDG_GAP + _TBDG_W
_TW_FULL_TEAM = _TW_TEAM + _TBDG_GAP + _TBDG_W

_TBDG_COLS = {"PIT": "#B05010", "GAR": "#484848", "DNF": "#880000", "DQ": "#660066"}

_COL_LABELS      = ("GAP", "Interval", "VE", "Pos +/-")
_COL_CYCLE_S     = 6.0    # seconds per column mode
_LAP_FLASH_S     = 5.0    # seconds to show new lap time
_PARADE_INTERVAL = 20.0   # seconds between parades
_PARADE_STEP     = 5.0    # seconds per parade window step
_TSEP_H          = 5      # separator height between fixed and mobile sections


class BroadcastTower(_BcWidget):
    WIDGET_NAME = "Broadcast Tower"

    def __init__(self, state: BroadcastState) -> None:
        super().__init__()
        self._state      = state
        self._entries:    list[dict]     = []
        self._start_pos:  dict[int, int] = {}
        self._last_stp    = -1
        self._ses_type    = 0
        self._game_phase  = 0
        self._et          = 0.0
        self._rem         = 0.0
        self._viewed_slot_id = -1
        # Cycling column state
        self._col_mode: int   = 0
        self._col_ts:   float = 0.0
        # Lap flash: slot_id → (expire_mono, formatted_time, color_hex)
        self._lap_flash: dict[int, tuple[float, str, str]] = {}
        self._prev_last: dict[int, float] = {}
        self._ses_best:  dict[str, float] = {}
        self._pers_best: dict[int, float] = {}
        # Parade state
        self._parade_active: bool  = False
        self._parade_offset: int   = 0
        self._parade_step_ts: float = 0.0
        self._last_normal_ts: float = 0.0   # 0 = uninitialised
        self.setFixedSize(_TW_FULL_DRV, _TSEH + 8)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _reset_session(self, vehicles) -> None:
        self._start_pos      = {}
        self._lap_flash      = {}
        self._prev_last      = {}
        self._ses_best       = {}
        self._pers_best      = {}
        self._parade_active  = False
        self._parade_offset  = 0
        self._last_normal_ts = 0.0
        # Seed bests so first-lap comparisons are accurate
        for v in vehicles:
            if v.best_lap > 0:
                self._pers_best[v.slot_id] = v.best_lap
                cls = v.vehicle_class
                if v.best_lap < self._ses_best.get(cls, float('inf')):
                    self._ses_best[cls] = v.best_lap
            if v.last_lap > 0:
                self._prev_last[v.slot_id] = v.last_lap

    def on_data(self, snap: LMUSnapshot) -> None:
        now = _time.monotonic()
        s       = snap.session
        is_race = s.session_type >= 10
        self._ses_type       = s.session_type
        self._game_phase     = s.game_phase
        self._et             = s.current_et
        self._rem            = s.session_time_remaining
        self._viewed_slot_id = snap.viewed_slot_id

        if s.session_type != self._last_stp:
            self._last_stp = s.session_type
            self._reset_session(s.vehicles)

        # Advance column mode — skip POS (3) in non-race sessions
        if self._col_ts == 0.0:
            self._col_ts = now
        elif now - self._col_ts >= _COL_CYCLE_S:
            next_mode = (self._col_mode + 1) % 4
            if not is_race and next_mode == 3:
                next_mode = 0
            self._col_mode = next_mode
            self._col_ts   = now
        elif not is_race and self._col_mode == 3:
            self._col_mode = 0  # snap back if mode was set while in race

        # Expire old flashes
        self._lap_flash = {k: v for k, v in self._lap_flash.items() if v[0] > now}

        # Detect new completed laps
        for v in s.vehicles:
            if v.in_garage or v.last_lap <= 0:
                continue
            prev = self._prev_last.get(v.slot_id)
            if prev is None:
                self._prev_last[v.slot_id] = v.last_lap
                continue
            if v.last_lap == prev:
                continue
            # New lap detected
            self._prev_last[v.slot_id] = v.last_lap
            ll  = v.last_lap
            cls = v.vehicle_class
            sb  = self._ses_best.get(cls, float('inf'))
            pb  = self._pers_best.get(v.slot_id, float('inf'))
            if ll < sb:
                col = T.PURPLE
                self._ses_best[cls] = ll
            elif ll < pb:
                col = T.GOOD
            else:
                col = T.WARN
            if ll < pb:
                self._pers_best[v.slot_id] = ll
            self._lap_flash[v.slot_id] = (now + _LAP_FLASH_S, _fmt_lap(ll, 3), col)

        # Sort key: for multiclass, inactive cars pushed to bottom within class
        def _sort(v):
            inactive = v.in_garage or v.finish_status in (2, 3, 4)
            return (1 if inactive else 0, v.place if v.place > 0 else 9999)

        # Sort key for overall/class modes: keep all cars at their place position
        def _sort_place(v):
            return v.place if v.place > 0 else 9999

        n       = self._state.tower_count
        mode    = self._state.tower_mode
        entries: list[dict] = []

        if mode == 1:  # ── Multiclass ──────────────────────────────────────
            by_class: dict[str, list] = defaultdict(list)
            for v in s.vehicles:
                by_class[v.vehicle_class].append(v)
            for cls in by_class:
                by_class[cls].sort(key=_sort_place)  # position réelle, garage inclus

            if is_race and not self._start_pos:
                for cls_name in sorted(by_class, key=_class_rank):
                    for i, v in enumerate(by_class[cls_name]):
                        if not v.in_garage:
                            self._start_pos[v.slot_id] = i + 1

            for cls_name in sorted(by_class, key=_class_rank):
                vlist = by_class[cls_name]
                if not vlist:
                    continue
                leader = vlist[0]
                ab = class_abbrev(cls_name)
                entries.append({"hdr": True,
                                "abbrev":   ab,
                                "cls_col":  class_color(cls_name, {}),
                                "ve_label": _ve_label(ab)})
                for i, v in enumerate(vlist[:n]):
                    prev_v = vlist[i - 1] if i else None
                    entries.append(self._row(v, prev_v, i + 1, is_race, leader, cls_pos=i + 1))

        else:  # ── Overall (0) or Class filter (2) ─────────────────────────
            if mode == 2:
                flt = self._state.tower_filter_class  # abbrev like "GT3", "" = auto
                if flt:
                    pool       = [v for v in s.vehicles if class_abbrev(v.vehicle_class) == flt]
                    hdr_abbrev = flt
                    hdr_color  = class_color(next((v.vehicle_class for v in pool), flt), {})
                else:
                    viewed = next((v for v in s.vehicles if v.slot_id == self._viewed_slot_id), None)
                    if viewed is None:
                        viewed = next((v for v in s.vehicles if v.is_player), None)
                    vcls = viewed.vehicle_class if viewed else ""
                    pool       = [v for v in s.vehicles if v.vehicle_class == vcls]
                    hdr_abbrev = class_abbrev(vcls) or "?"
                    hdr_color  = class_color(vcls, {})
                entries.append({"hdr": True, "abbrev": hdr_abbrev, "cls_col": hdr_color,
                                "ve_label": _ve_label(hdr_abbrev)})
            else:
                pool = list(s.vehicles)
                entries.append({
                    "hdr":      True,
                    "abbrev":   "OVERALL",
                    "cls_col":  QColor(50, 55, 65),
                    "ve_label": "VE/F",
                })

            all_v = sorted(pool, key=_sort_place)

            # mode 2 = class-relative positions (1,2,3…); mode 0 = overall v.place
            def _pos(v_item: object, idx: int) -> int:
                return (idx + 1) if mode == 2 else v_item.place

            # Class rank for every vehicle (used for Pos +/- column, always per class)
            _cls_ctr: dict[str, int] = defaultdict(int)
            _cls_pos_map: dict[int, int] = {}
            for _v in all_v:
                if not _v.in_garage:
                    _cls_ctr[_v.vehicle_class] += 1
                    _cls_pos_map[_v.slot_id] = _cls_ctr[_v.vehicle_class]

            if is_race and not self._start_pos:
                for v in all_v:
                    if not v.in_garage and v.slot_id in _cls_pos_map:
                        self._start_pos[v.slot_id] = _cls_pos_map[v.slot_id]

            active_v = [v for v in all_v if not v.in_garage and v.finish_status not in (2, 3, 4)]
            leader   = active_v[0] if active_v else (all_v[0] if all_v else None)

            # ── Parade — fixed top + scrolling mobile bottom ──────────────
            pc          = max(1, self._state.tower_parade_count)
            fixed_count = max(0, n - pc)
            mobile_pool = all_v[fixed_count:]

            if self._last_normal_ts == 0.0:
                self._last_normal_ts = now

            if not self._parade_active:
                if len(mobile_pool) > pc and now - self._last_normal_ts >= _PARADE_INTERVAL:
                    self._parade_active  = True
                    self._parade_offset  = pc   # start at second window
                    self._parade_step_ts = now
            else:
                if now - self._parade_step_ts >= _PARADE_STEP:
                    self._parade_offset += pc
                    self._parade_step_ts = now
                    if self._parade_offset >= len(mobile_pool):
                        self._parade_active  = False
                        self._parade_offset  = 0
                        self._last_normal_ts = now

            # ── Build entries ────────────────────────────────────────────
            # Fixed section (top)
            for i, v in enumerate(all_v[:fixed_count]):
                prev_v = all_v[i - 1] if i else None
                entries.append(self._row(v, prev_v, _pos(v, i), is_race, leader,
                                         cls_pos=_cls_pos_map.get(v.slot_id, 0)))

            # Separator
            if fixed_count > 0 and mobile_pool:
                entries.append({"sep": True})

            # Mobile section (bottom, scrolls)
            offset        = self._parade_offset if self._parade_active else 0
            mobile_window = mobile_pool[offset : offset + pc]
            for j, v in enumerate(mobile_window):
                abs_i  = fixed_count + offset + j
                prev_v = all_v[abs_i - 1] if abs_i > 0 else None
                entries.append(self._row(v, prev_v, _pos(v, abs_i), is_race, leader,
                                         cls_pos=_cls_pos_map.get(v.slot_id, 0)))

        tw      = _TW_TEAM if self._state.show_team else _TW_DRV
        tw_full = tw + _TBDG_GAP + _TBDG_W
        self._entries = entries
        h = _TSEH + 4
        for e in entries:
            if e.get("hdr"):   h += _TCLSH
            elif e.get("sep"): h += _TSEP_H
            else:              h += _TRH
        h += 4
        self.setFixedSize(tw_full, max(h, _TSEH + 8))
        self.update()

    def _row(self, v, prev, pos: int, is_race: bool, leader, cls_pos: int = 0) -> dict:
        # Status badge
        fs = v.finish_status
        if fs == 2:
            status = "DNF"
        elif fs == 4:
            status = "DQ"
        elif v.in_garage:
            status = "GAR"
        elif v.in_pit_lane:
            status = "PIT"
        else:
            status = None

        # Gap / interval — race: time behind class leader; quali/practice: lap-time delta
        if is_race:
            gap  = v.time_behind_class_leader
            intv = (v.time_behind_class_leader - prev.time_behind_class_leader) if prev else -1.0
        else:
            lb, pb = leader.best_lap if leader else -1, prev.best_lap if prev else -1
            gap  = (v.best_lap - lb)  if (v.best_lap > 0 and lb  > 0) else -1.0
            intv = (v.best_lap - pb)  if (v.best_lap > 0 and pb  > 0) else -1.0

        cp    = cls_pos if cls_pos > 0 else pos   # class position for POS gained/lost
        start = self._start_pos.get(v.slot_id, cp)

        # Info column — only truly out drivers (DNF/DQ) are fully blanked
        inactive = status in ("DNF", "DQ")
        flash    = self._lap_flash.get(v.slot_id)
        if flash and not inactive:
            info_txt, info_col = flash[1], flash[2]
        elif inactive:
            info_txt, info_col = "—", T.DIM
        else:
            col_mode = self._col_mode
            if col_mode == 0:   # GAP
                if pos == 1:
                    if is_race:
                        info_txt, info_col = "LEADER", T.DIM
                    elif v.best_lap > 0:
                        info_txt, info_col = _fmt_lap(v.best_lap, 3), T.TEXT
                    else:
                        info_txt, info_col = "—", T.DIM
                elif gap > 0:
                    info_txt, info_col = f"+{gap:.3f}", T.TEXT
                else:
                    info_txt, info_col = "—", T.DIM
            elif col_mode == 1:  # INT
                if pos == 1:
                    if is_race:
                        info_txt, info_col = "LEADER", T.DIM
                    elif v.best_lap > 0:
                        info_txt, info_col = _fmt_lap(v.best_lap, 3), T.TEXT
                    else:
                        info_txt, info_col = "—", T.DIM
                elif intv > 0:
                    info_txt, info_col = f"+{intv:.3f}", T.TEXT
                else:
                    info_txt, info_col = "—", T.DIM
            elif col_mode == 2:  # VE / FUEL
                if v.virtual_energy > 0.001:
                    ve = v.virtual_energy
                    info_col = (T.CRIT if ve < 0.10 else T.WARN if ve < 0.25 else T.GOOD)
                    info_txt = f"{ve * 100:.0f}%"
                elif v.fuel > 0.01:
                    fuel = v.fuel
                    info_col = (T.CRIT if fuel < 10 else T.WARN if fuel < 25 else T.TEXT)
                    info_txt = f"{fuel:.0f}L"
                else:
                    info_txt, info_col = "—", T.DIM
            else:                # POS gained/lost (class-relative)
                d = start - cp
                if is_race and d > 0:
                    info_txt, info_col = f"▲{d}", T.GOOD
                elif is_race and d < 0:
                    info_txt, info_col = f"▼{abs(d)}", "#E05050"
                else:
                    info_txt, info_col = ("" if not is_race else "—"), T.DIM

        pinned_id = self._state.pinned_slot_id
        return {
            "pos":          pos,
            "slot_id":      v.slot_id,
            "car_num":      v.car_number,
            "vehicle_name": v.vehicle_name or "",
            "name":      (v.team_name or v.vehicle_name or f"Car {v.slot_id}")
                         if self._state.show_team
                         else _name_last(v.driver_name or v.vehicle_name or f"Car {v.slot_id}"),
            "featured":  v.slot_id == self._viewed_slot_id,
            "pinned":    pinned_id > 0 and v.slot_id == pinned_id,
            "info_txt":  info_txt,
            "info_col":  info_col,
            "status":    status,
        }

    def paintEvent(self, _) -> None:
        W = _TW_TEAM if self._state.show_team else _TW_DRV
        H = self.height()
        tnme_w = _TNME_W_TEAM if self._state.show_team else _TNME_W_DRV
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._panel(p, W, H)        # panel drawn at panel width only

        # Session bar background
        p.setBrush(QColor(28, 30, 34, 200))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(1, 1, W - 2, _TSEH, T.RADIUS, T.RADIUS)

        # Clock (bigger) + session name — left-aligned, side by side
        clock_txt = _ses_clock(self._rem)
        ses_name  = _ses_name(self._ses_type).upper()

        p.setFont(num_font(14))
        p.setPen(QColor(T.TEXT))
        clock_w = p.fontMetrics().horizontalAdvance(clock_txt)
        p.drawText(QRectF(10, 0, clock_w, _TSEH),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, clock_txt)

        p.setFont(label_font(8))
        p.setPen(QColor(T.ACCENT))
        p.drawText(QRectF(10 + clock_w + 14, 0, 120, _TSEH),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, ses_name)

        # Flag indicator (14×14 rounded square, right)
        gp = self._game_phase
        if gp == 5:
            flag_col = QColor(T.GOOD)
        elif gp == 6:
            flag_col = QColor(T.WARN)
        elif gp == 7:
            flag_col = QColor(T.CRIT)
        else:
            flag_col = QColor(T.DIM)
        flag_sz = 14
        flag_x  = W - flag_sz - 10
        flag_y  = (_TSEH - flag_sz) // 2 + 1
        p.setBrush(flag_col)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(flag_x, flag_y, flag_sz, flag_sz, 3, 3)

        p.fillRect(QRectF(2, _TSEH, W - 4, 1), T.FAINT)

        y = _TSEH + 4
        for e in self._entries:
            if e.get("sep"):
                mid = y + _TSEP_H // 2
                p.setPen(QColor(T.ACCENT))
                p.drawLine(8, mid, W - 8, mid)
                y += _TSEP_H
                continue
            if e.get("hdr"):
                ab  = e["abbrev"]
                col = e["cls_col"]
                p.setFont(label_font(7))
                bw = max(p.fontMetrics().horizontalAdvance(ab) + 10, 28)
                p.setBrush(col if col else QColor(50, 55, 65))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(4, y + 1, bw, _TCLSH - 2, 2, 2)
                p.setPen(QColor(T.TEXT))
                p.drawText(4, y + 1, bw, _TCLSH - 2, Qt.AlignmentFlag.AlignCenter, ab)
                # Column label on the same row, in the info column area
                info_x = W - 4 - _TINFO_W
                col_label = (e.get("ve_label", "VE") if self._col_mode == 2
                             else _COL_LABELS[self._col_mode])
                p.setFont(label_font(7))
                p.setPen(QColor(T.DIM))
                p.drawText(info_x, y, _TINFO_W - 2, _TCLSH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           col_label)
                y += _TCLSH
                continue


            # Pinned indicator — thin accent strip on left edge
            if e.get("pinned"):
                p.setBrush(QColor(T.ACCENT)); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(1, y + 2, 3, _TRH - 4)

            x   = 4
            pos = e["pos"]
            pc  = (QColor(T.P1) if pos == 1 else QColor(T.P2) if pos == 2
                   else QColor(T.P3) if pos == 3 else QColor(T.TEXT))

            # Position number — right-aligned so it never bleeds into car number
            p.setFont(num_font(10)); p.setPen(pc)
            p.drawText(x, y, _TPOS_W - 2, _TRH,
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                       str(pos) if pos > 0 else "—")
            x += _TPOS_W

            # Manufacturer logo — shifted right of center toward car number
            logo = _get_logo(e.get("vehicle_name", ""))
            if logo:
                lx = x + (_TLOGO_W - logo.width()) // 2 + 4
                ly = y + (_TRH     - logo.height()) // 2
                p.drawPixmap(lx, ly, logo)
            x += _TLOGO_W

            # Car number
            num_txt = e.get("car_num", "")
            if num_txt:
                p.setFont(label_font(7)); p.setPen(QColor(T.DIM))
                p.drawText(x, y, _TNUM_W - 4, _TRH,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           f"#{num_txt}")
            x += _TNUM_W

            # Driver / team name (already formatted)
            p.setFont(text_font(10))
            p.setPen(QColor(T.TEXT))
            p.drawText(x + 2, y, tnme_w - 2, _TRH,
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       e["name"])
            x += tnme_w

            # Info column — right-aligned with small right margin
            p.setFont(num_font(9))
            p.setPen(QColor(e["info_col"]))
            p.drawText(x, y, _TINFO_W - 6, _TRH,
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                       e["info_txt"])

            # Status badge (protrudes beyond panel right edge)
            status = e.get("status")
            if status:
                bdg_col = QColor(_TBDG_COLS.get(status, "#484848"))
                bdg_x   = W + _TBDG_GAP
                bdg_h   = _TRH - 6
                bdg_y   = y + 3
                p.setBrush(bdg_col); p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(bdg_x, bdg_y, _TBDG_W, bdg_h, 3, 3)
                p.setFont(label_font(7)); p.setPen(QColor("#FFFFFF"))
                p.drawText(bdg_x, bdg_y, _TBDG_W, bdg_h,
                           Qt.AlignmentFlag.AlignCenter, status)

            y += _TRH

        p.end()

    def mousePressEvent(self, event) -> None:
        """Click a driver row to pin/unpin it as the viewed driver for overlays."""
        y = _TSEH + 4
        for e in self._entries:
            if e.get("hdr"):
                y += _TCLSH
            else:
                if y <= event.y() < y + _TRH:
                    slot_id = e.get("slot_id", -1)
                    if slot_id > 0:
                        # Toggle: click pinned row again to unpin
                        self._state.pinned_slot_id = (
                            -1 if self._state.pinned_slot_id == slot_id else slot_id
                        )
                        self.update()
                    return
                y += _TRH
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Broadcast Battle Card
# ---------------------------------------------------------------------------

_BW = 480   # battle width  (= _BLW + _BCW + _BRW)
_BH = 82    # battle height

_BLW     = 205  # left driver section
_BCW     = 70   # center gap section
_BRW     = 205  # right driver section
_BPOS_W  = 48   # position number column
_BLOGO_W = 36   # manufacturer logo column (between pos and name)
_BRPAD   = 8


class BroadcastBattle(_BcWidget):
    WIDGET_NAME = "Broadcast Battle"

    def __init__(self, state: BroadcastState) -> None:
        super().__init__()
        self._state     = state
        self._driver_a: dict | None = None
        self._driver_b: dict | None = None
        self._gap_s        = -1.0   # live gap (updated every tick)
        self._gap_display  = -1.0   # displayed gap (refreshed every 2 s)
        self._gap_last_ts  = 0.0
        self._is_race   = False
        self.setFixedSize(_BW, _BH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def on_data(self, snap: LMUSnapshot) -> None:
        vlist     = snap.session.vehicles
        is_race   = snap.session.session_type >= 10
        self._is_race = is_race

        # A = pinned driver if set, else auto-detect from shared memory
        raw_viewed = self._state.pinned_slot_id if self._state.pinned_slot_id > 0 else snap.viewed_slot_id
        va = next((v for v in vlist if v.slot_id == raw_viewed), None)
        if va is None:
            va = next((v for v in vlist if v.is_player), None)

        # B = nearest same-class rival (same lap only in race, free in quali/practice)
        vb = None
        if va is not None:
            same = [v for v in vlist
                    if v.vehicle_class == va.vehicle_class
                    and v.slot_id != va.slot_id
                    and not v.in_garage
                    and (not is_race or abs(v.total_laps - va.total_laps) <= 1)]
            vb = min(same, key=lambda v: abs(v.place - va.place)) if same else None

        def _cls_pos(car) -> int:
            same = sorted(
                [vh for vh in vlist if vh.vehicle_class == car.vehicle_class],
                key=lambda vh: vh.place if vh.place > 0 else 9999,
            )
            idx = next((i for i, vh in enumerate(same) if vh.slot_id == car.slot_id), None)
            return (idx + 1) if idx is not None else car.place

        # Session best per class (for purple colouring)
        cls_ses_best: dict[str, float] = {}
        for veh in vlist:
            if veh.best_lap > 0:
                c = veh.vehicle_class
                if c not in cls_ses_best or veh.best_lap < cls_ses_best[c]:
                    cls_ses_best[c] = veh.best_lap

        def _last_col(v) -> str:
            ll, bl = v.last_lap, v.best_lap
            if ll <= 0 or bl <= 0:
                return T.DIM
            sb = cls_ses_best.get(v.vehicle_class, float('inf'))
            if ll < bl:
                return T.PURPLE if bl <= sb else T.GOOD
            return T.WARN

        def _d(v) -> dict:
            bl  = v.best_lap
            sb  = cls_ses_best.get(v.vehicle_class, float('inf'))
            return {
                "pos":          _cls_pos(v),
                "car_num":      v.car_number,
                "vehicle_name": v.vehicle_name or "",
                "name":         _fmt_name(
                                    (v.team_name if self._state.show_team else v.driver_name)
                                    or v.vehicle_name or f"Car {v.slot_id}",
                                    self._state.show_team,
                                ),
                "last":         v.last_lap,
                "last_col":     _last_col(v),
                "best":         bl,
                "best_is_ses":  bl > 0 and bl <= sb,
                "compounds":    v.compounds,
            }

        if va and vb:
            # Opponent AHEAD → shown on LEFT; opponent BEHIND → shown on RIGHT
            if vb.place < va.place:
                left, right = vb, va
            else:
                left, right = va, vb
            self._driver_a = _d(left)
            self._driver_b = _d(right)
            if is_race:
                self._gap_s = abs(va.time_behind_leader - vb.time_behind_leader)
            elif va.best_lap > 0 and vb.best_lap > 0:
                self._gap_s = abs(va.best_lap - vb.best_lap)
            else:
                self._gap_s = -1.0
            now = _time.monotonic()
            if now - self._gap_last_ts >= 2.0:
                self._gap_display = self._gap_s
                self._gap_last_ts = now
        else:
            self._driver_a = None
            self._driver_b = None
            self._gap_display = -1.0
            self._gap_last_ts = 0.0
        self.update()

    def paintEvent(self, _) -> None:
        if not self._driver_a or not self._driver_b:
            return
        W, H = _BW, _BH
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._panel(p, W, H)

        # Vertical separator lines bounding the center gap area
        cx0 = _BLW
        cx1 = _BLW + _BCW
        p.fillRect(QRectF(cx0, 10, 1, H - 20), T.FAINT)
        p.fillRect(QRectF(cx1, 10, 1, H - 20), T.FAINT)

        # Center gap label + value (refreshed every 2 s to avoid visual noise)
        if self._gap_display >= 0:
            gap_txt = f"+{self._gap_display:.3f}"
        else:
            gap_txt = "—"
        p.setFont(label_font(7)); p.setPen(QColor(T.DIM))
        p.drawText(cx0, 10, _BCW, 16, Qt.AlignmentFlag.AlignCenter, "GAP")
        p.setFont(num_font(11 if len(gap_txt) <= 6 else 9)); p.setPen(QColor(T.ACCENT))
        p.drawText(cx0, 26, _BCW, 22, Qt.AlignmentFlag.AlignCenter, gap_txt)

        # Compound badges — left driver left, right driver right, bottom of gap column
        _bdg_cy = H - 16
        _draw_compound_badge(p, cx0 + _BCW // 4,     _bdg_cy, self._driver_a.get("compounds", []), r=10)
        _draw_compound_badge(p, cx0 + 3 * _BCW // 4, _bdg_cy, self._driver_b.get("compounds", []), r=10)

        # Draw driver panels
        for dx, driver, align_right in (
            (0,    self._driver_a, False),
            (cx1,  self._driver_b, True),
        ):
            pos = driver["pos"]
            pc  = (QColor(T.P1) if pos == 1 else QColor(T.P2) if pos == 2
                   else QColor(T.P3) if pos == 3 else QColor(T.TEXT))

            pos_align = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
            if align_right:
                # Right side: name | logo | pos  (+8 px left gap from centre divider)
                name_x      = dx + 8
                name_w      = _BRW - _BPOS_W - _BLOGO_W - 12  # for last/best rows
                name_full_w = name_w + _BLOGO_W + 4            # for name row: no logo reservation
                logo_x      = dx + 8 + name_w + 4
                pos_x       = dx + _BRW - _BPOS_W
            else:
                # Left side: pos | logo | name
                pos_x       = dx
                logo_x      = dx + _BPOS_W
                name_x      = dx + _BPOS_W + _BLOGO_W + 4
                name_w      = _BLW - _BPOS_W - _BLOGO_W - 8
                name_full_w = name_w

            lbl_font = label_font(7)
            lap_font = num_font(10)
            la = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

            # Position number (large) + car number below
            p.setFont(num_font(24)); p.setPen(pc)
            p.drawText(pos_x, 6, _BPOS_W, 38, pos_align, str(pos))
            num_txt = driver.get("car_num", "")
            if num_txt:
                p.setFont(label_font(10)); p.setPen(QColor(T.DIM))
                p.drawText(pos_x, 46, _BPOS_W, 14, pos_align, f"#{num_txt}")

            # Manufacturer logo — below the name row so it doesn't clip the name text
            logo = _get_logo(driver.get("vehicle_name", ""), 32, 26)
            if logo:
                lx = logo_x + (_BLOGO_W - logo.width()) // 2
                ly = 36 + (_BH - 36 - 8 - logo.height()) // 2
                p.drawPixmap(lx, ly, logo)

            # Driver name — uses full_w so the logo column doesn't restrict it
            name_align = (Qt.AlignmentFlag.AlignVCenter |
                          (Qt.AlignmentFlag.AlignLeft if align_right
                           else Qt.AlignmentFlag.AlignRight))
            p.setFont(text_font(11)); p.setPen(QColor(T.TEXT))
            p.drawText(name_x, 6, name_full_w, 26, name_align, driver["name"])

            # Last lap (coloured)
            last_txt = _fmt_lap(driver["last"], 3)
            last_col = driver.get("last_col", T.TEXT)
            ar = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
            if align_right:
                p.setFont(lbl_font); p.setPen(QColor(T.DIM))
                p.drawText(name_x, 34, 30, 18, la, "LAST")
                p.setFont(lap_font)
                p.setPen(QColor(T.DIM) if driver["last"] <= 0 else QColor(last_col))
                p.drawText(name_x + 30, 34, name_w - 30, 18, la, last_txt)
            else:
                p.setFont(lap_font)
                p.setPen(QColor(T.DIM) if driver["last"] <= 0 else QColor(last_col))
                p.drawText(name_x, 34, name_w - 30, 18, ar, last_txt)
                p.setFont(lbl_font); p.setPen(QColor(T.DIM))
                p.drawText(name_x + name_w - 30, 34, 30, 18, ar, "LAST")

            # Best lap (purple if session best)
            best_txt = _fmt_lap(driver["best"], 3)
            best_col = T.PURPLE if driver.get("best_is_ses") else T.TEXT
            if align_right:
                p.setFont(lbl_font); p.setPen(QColor(T.DIM))
                p.drawText(name_x, 56, 30, 18, la, "BEST")
                p.setFont(lap_font)
                p.setPen(QColor(T.DIM) if driver["best"] <= 0 else QColor(best_col))
                p.drawText(name_x + 30, 56, name_w - 30, 18, la, best_txt)
            else:
                p.setFont(lap_font)
                p.setPen(QColor(T.DIM) if driver["best"] <= 0 else QColor(best_col))
                p.drawText(name_x, 56, name_w - 30, 18, ar, best_txt)
                p.setFont(lbl_font); p.setPen(QColor(T.DIM))
                p.drawText(name_x + name_w - 30, 56, 30, 18, ar, "BEST")

        p.end()


# ---------------------------------------------------------------------------
# Broadcast Driver Card
# ---------------------------------------------------------------------------

_DW     = 360   # driver card width
_DH     = 80    # driver card height
_DPOS_W = 46    # position number column
_DVE_W  = 64    # VE/fuel value column (right of name)


class BroadcastDriverCard(_BcWidget):
    WIDGET_NAME = "Broadcast Driver Card"

    def __init__(self, state: BroadcastState) -> None:
        super().__init__()
        self._state  = state
        self._driver: dict | None = None
        self.setFixedSize(_DW, _DH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def on_data(self, snap: LMUSnapshot) -> None:
        vlist  = snap.session.vehicles
        raw_viewed = self._state.pinned_slot_id if self._state.pinned_slot_id > 0 else snap.viewed_slot_id
        v = next((veh for veh in vlist if veh.slot_id == raw_viewed), None)
        if v is None:
            v = next((veh for veh in vlist if veh.is_player), None)
        if v:
            same_class = sorted(
                [vh for vh in vlist if vh.vehicle_class == v.vehicle_class],
                key=lambda vh: vh.place if vh.place > 0 else 9999,
            )
            idx = next((i for i, vh in enumerate(same_class) if vh.slot_id == v.slot_id), None)
            cls_pos = (idx + 1) if idx is not None else v.place

            ses_best = min((vh.best_lap for vh in same_class if vh.best_lap > 0), default=float('inf'))
            ll, bl = v.last_lap, v.best_lap
            if ll <= 0:
                last_col = T.DIM
            elif bl > 0 and ll < bl:
                last_col = T.PURPLE if bl <= ses_best else T.GOOD
            else:
                last_col = T.TEXT

            self._driver = {
                "pos":          cls_pos,
                "car_num":      v.car_number,
                "vehicle_name": v.vehicle_name or "",
                "name":         _fmt_name(
                                    (v.team_name if self._state.show_team else v.driver_name)
                                    or v.vehicle_name or f"Car {v.slot_id}",
                                    self._state.show_team,
                                ),
                "team":         v.team_name,
                "last":         ll,
                "last_col":     last_col,
                "best":         bl,
                "best_is_ses":  bl > 0 and bl <= ses_best,
                "ve":           v.virtual_energy,
                "fuel":         v.fuel,
                "compounds":    v.compounds,
            }
        else:
            self._driver = None
        self.update()

    def paintEvent(self, _) -> None:
        if not self._driver:
            return
        W, H   = _DW, _DH
        driver = self._driver
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._panel(p, W, H)

        lbl_f = label_font(7)
        val_f = num_font(10)

        pos = driver["pos"]
        pc  = (QColor(T.P1) if pos == 1 else QColor(T.P2) if pos == 2
               else QColor(T.P3) if pos == 3 else QColor(T.TEXT))

        # ── Row 1: position | name | VE/fuel ──────────────────────────
        row1_y = 6
        row1_h = 40

        # Position number
        p.setFont(num_font(24)); p.setPen(pc)
        p.drawText(6, row1_y, _DPOS_W, row1_h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
                   str(pos))

        # Manufacturer logo — after position, before car number
        _dlogo_w = 28
        logo = _get_logo(driver.get("vehicle_name", ""))
        if logo:
            lx = 6 + _DPOS_W + 4 + (_dlogo_w - logo.width()) // 2
            ly = row1_y + (row1_h - logo.height()) // 2
            p.drawPixmap(lx, ly, logo)

        # Car number — shifted right by logo column
        num_txt = driver.get("car_num", "")
        _dnum_w = 32
        if num_txt:
            p.setFont(label_font(9)); p.setPen(QColor(T.DIM))
            p.drawText(6 + _DPOS_W + 4 + _dlogo_w + 4, row1_y, _dnum_w, row1_h,
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
                       f"#{num_txt}")

        # VE / fuel — right-aligned on row 1
        ve   = driver["ve"]
        fuel = driver["fuel"]
        if ve > 0.001:
            fv_txt, fv_col = f"{ve * 100:.0f}%", QColor(T.GOOD)
            fv_lbl = "VE"
        elif fuel > 0.01:
            fv_txt, fv_col = f"{fuel:.1f}L", QColor(T.TEXT)
            fv_lbl = "FUEL"
        else:
            fv_txt, fv_col = "", QColor(T.DIM)
            fv_lbl = ""

        ve_block_w = 0
        if fv_lbl:
            p.setFont(lbl_f); p.setPen(QColor(T.DIM))
            lbl_w = p.fontMetrics().horizontalAdvance(fv_lbl)
            p.setFont(val_f)
            val_w = p.fontMetrics().horizontalAdvance(fv_txt)
            ve_block_w = lbl_w + 4 + val_w + 6
            lbl_x = W - ve_block_w - 6
            val_x = lbl_x + lbl_w + 4
            p.setFont(lbl_f); p.setPen(QColor(T.DIM))
            p.drawText(lbl_x, row1_y, lbl_w + 4, row1_h,
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fv_lbl)
            p.setFont(val_f); p.setPen(fv_col)
            p.drawText(val_x, row1_y, val_w + 4, row1_h,
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, fv_txt)

        # Driver name (after logo column + car number)
        _dnum_w = 32
        name_x = 6 + _DPOS_W + 4 + _dlogo_w + 4 + (_dnum_w + 4 if num_txt else 0)
        name_w = W - name_x - ve_block_w - 12
        p.setFont(text_font(12)); p.setPen(QColor(T.TEXT))
        p.drawText(name_x, row1_y, name_w, row1_h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   driver["name"])

        # ── Separator ──────────────────────────────────────────────────
        sep_y = row1_y + row1_h + 2
        p.fillRect(QRectF(6, sep_y, W - 12, 1), T.FAINT)

        # ── Row 2: LAST + BEST ─────────────────────────────────────────
        row2_y = sep_y + 4
        row2_h = H - row2_y - 6

        last_txt = _fmt_lap(driver["last"], 3)
        p.setFont(lbl_f); p.setPen(QColor(T.DIM))
        p.drawText(6, row2_y, 28, row2_h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "LAST")
        p.setFont(val_f)
        p.setPen(QColor(driver["last_col"]))
        p.drawText(34, row2_y, 84, row2_h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, last_txt)

        best_txt = _fmt_lap(driver["best"], 3)
        p.setFont(lbl_f); p.setPen(QColor(T.DIM))
        p.drawText(126, row2_y, 28, row2_h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "BEST")
        p.setFont(val_f)
        p.setPen(QColor(T.PURPLE) if driver.get("best_is_ses") else QColor(T.TEXT) if driver["best"] > 0 else QColor(T.DIM))
        p.drawText(154, row2_y, 84, row2_h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, best_txt)

        # Compound badge — far right of row 2
        _draw_compound_badge(p, W - 17, row2_y + row2_h // 2, driver.get("compounds", []))

        p.end()


# ---------------------------------------------------------------------------
# Broadcast Sectors (Qualifying)
# ---------------------------------------------------------------------------

_QW   = 360                   # width (same as Driver Card)
_QH   = 110                   # height
_QSEC = (_QW - 16) // 3      # sector column width ≈ 114 px


def _sector_col(t: float, pb: float, ses_best: float) -> str | None:
    """Couleur de la barre de secteur.
    ses_best = meilleur temps de la session dans la classe (ref leader).
    pb       = meilleur temps personnel sur ce secteur.
    Violet → session best  |  Vert → personal best  |  Jaune → moins bon que perso
    """
    if t <= 0:
        return None
    if ses_best > 0 and t < ses_best:
        return T.PURPLE
    if pb > 0 and t < pb:
        return T.GOOD
    return T.WARN


class BroadcastSectors(_BcWidget):
    WIDGET_NAME = "Broadcast Sectors (Practice / Quali)"

    def __init__(self, state: BroadcastState) -> None:
        super().__init__()
        self._state = state
        self._data: dict | None = None
        self._tracked_slot: int  = -1
        self._prev_in_lap:  bool = False   # True when driver is mid-lap (cur_s1 or cur_s2 ≥ 0)
        self._blank_until:  float = 0.0    # monotonic deadline for the 10-s blank window
        self.setFixedSize(_QW, _QH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def on_data(self, snap: LMUSnapshot) -> None:
        vlist = snap.session.vehicles
        raw_viewed = (self._state.pinned_slot_id if self._state.pinned_slot_id > 0
                      else snap.viewed_slot_id)
        v = next((vh for vh in vlist if vh.slot_id == raw_viewed), None)
        if v is None:
            v = next((vh for vh in vlist if vh.is_player), None)
        if v is None:
            self._data = None
            self.update()
            return

        same_cls = sorted(
            [vh for vh in vlist if vh.vehicle_class == v.vehicle_class],
            key=lambda vh: vh.place if vh.place > 0 else 9999,
        )
        cls_pos = next((i + 1 for i, vh in enumerate(same_cls) if vh.slot_id == v.slot_id), v.place)
        leader = same_cls[0] if same_cls else v

        # Detect lap completion: driver transitions from mid-lap to start of new lap
        in_lap = v.cur_sector1 >= 0 or v.cur_sector2 >= 0
        if v.slot_id != self._tracked_slot:
            self._tracked_slot = v.slot_id
            self._prev_in_lap  = in_lap
            self._blank_until  = 0.0
        else:
            if self._prev_in_lap and not in_lap:
                # Driver just crossed the finish line — blank starts 10 s from now
                self._blank_until = _time.monotonic() + 10.0
            elif in_lap:
                # S1 crossed on new lap — cancel any pending blank
                self._blank_until = 0.0
            self._prev_in_lap = in_lap

        self._data = {
            "pos":          cls_pos,
            "car_num":      v.car_number,
            "vehicle_name": v.vehicle_name or "",
            "name":         _fmt_name(
                                (v.team_name if self._state.show_team else v.driver_name)
                                or v.vehicle_name or f"Car {v.slot_id}",
                                self._state.show_team,
                            ),
            "best_lap":  v.best_lap,
            "last_lap":  v.last_lap,
            "compounds": v.compounds,
            "cur_s1":    v.cur_sector1,
            "cur_s2":    v.cur_sector2,
            "last_s1":   v.last_sector1,
            "last_s2":   v.last_sector2,
            "best_s1":   v.best_sector1,
            "best_s2":   v.best_sector2,
            "ldr_s1":    leader.best_sector1,
            "ldr_s2":    leader.best_sector2,
            "ldr_lap":   leader.best_lap,
        }
        self.update()

    def paintEvent(self, _) -> None:
        if not self._data:
            return
        d    = self._data
        W, H = _QW, _QH
        p    = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._panel(p, W, H)

        # ── Top row: pos | logo | car# | name | best lap ─────────────────
        pos = d["pos"]
        pc  = (QColor(T.P1) if pos == 1 else QColor(T.P2) if pos == 2
               else QColor(T.P3) if pos == 3 else QColor(T.TEXT))

        _qpos_w  = 46
        _qlogo_w = 28
        _qnum_w  = 32
        top_y, top_h = 6, 40

        p.setFont(num_font(24)); p.setPen(pc)
        p.drawText(6, top_y, _qpos_w, top_h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter, str(pos))

        logo = _get_logo(d["vehicle_name"])
        if logo:
            lx = 6 + _qpos_w + 4 + (_qlogo_w - logo.width()) // 2
            ly = top_y + (top_h - logo.height()) // 2
            p.drawPixmap(lx, ly, logo)

        num_txt = d.get("car_num", "")
        if num_txt:
            p.setFont(label_font(9)); p.setPen(QColor(T.DIM))
            p.drawText(6 + _qpos_w + 4 + _qlogo_w + 4, top_y, _qnum_w, top_h,
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
                       f"#{num_txt}")

        best_lap = d["best_lap"]
        best_txt = _fmt_lap(best_lap, 3) if best_lap > 0 else "—"
        best_blk_w = 72
        _q_badge_space = 28   # 22px badge + 6px gap before BEST block
        ldr_lap = d["ldr_lap"]
        is_ses_best = best_lap > 0 and ldr_lap > 0 and best_lap <= ldr_lap
        p.setFont(num_font(10))
        p.setPen(QColor(T.PURPLE if is_ses_best else T.TEXT if best_lap > 0 else T.DIM))
        p.drawText(W - 6 - best_blk_w, top_y, best_blk_w, top_h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, best_txt)

        # Compound badge — between name and BEST block
        _draw_compound_badge(p, W - 6 - best_blk_w - _q_badge_space // 2,
                             top_y + top_h // 2, d.get("compounds", []))

        name_x = 6 + _qpos_w + 4 + _qlogo_w + 4 + (_qnum_w + 4 if num_txt else 0)
        name_w = W - name_x - best_blk_w - _q_badge_space - 12
        p.setFont(text_font(11)); p.setPen(QColor(T.TEXT))
        p.drawText(name_x, top_y, name_w, top_h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, d["name"])

        # ── Separator ────────────────────────────────────────────────────
        p.fillRect(QRectF(8, 50, W - 16, 1), T.FAINT)

        # ── Sector bars ──────────────────────────────────────────────────
        # Show last lap data for 10 s after crossing the line, then go blank.
        # As soon as cur_s1 ≥ 0 (S1 crossed on new lap) the blank is lifted.
        now = _time.monotonic()
        _post_lap   = self._blank_until > 0.0 and d["cur_s1"] < 0 and d["cur_s2"] < 0
        _show_blank = _post_lap and now >= self._blank_until  # ≥10 s after line

        cur_s1  = d["cur_s1"]
        cur_s2  = d["cur_s2"]
        s1_done = cur_s1 >= 0
        s2_done = cur_s2 >= 0

        # (cumulative_t, personal_best, leader_ref, in_progress, display_t)
        # cumulative_t / leader_ref are used for the delta gap (always cumulative).
        # display_t is the pure sector split shown inside the bar.
        ls1 = d["last_s1"]; ls2 = d["last_s2"]; llap = d["last_lap"]
        s2_split_cur  = (cur_s2  - cur_s1)  if (s2_done  and cur_s1  > 0) else -1.0
        s2_split_last = (ls2     - ls1)      if (ls2 > 0  and ls1     > 0) else -1.0
        s3_split_last = (llap    - ls2)      if (llap > 0 and ls2     > 0) else -1.0

        if _show_blank:
            sec1 = (-1.0, d["best_s1"],  d["ldr_s1"],  False, -1.0)
            sec2 = (-1.0, d["best_s2"],  d["ldr_s2"],  False, -1.0)
            sec3 = (-1.0, d["best_lap"], d["ldr_lap"], False, -1.0)
        elif s1_done:
            sec1 = (cur_s1, d["best_s1"],  d["ldr_s1"],  False, cur_s1)
            sec2 = (cur_s2, d["best_s2"],  d["ldr_s2"],  False, s2_split_cur) if s2_done else (-1.0, d["best_s2"],  d["ldr_s2"],  True, -1.0)
            sec3 = (-1.0,   d["best_lap"], d["ldr_lap"], True,  -1.0)
        else:
            sec1 = (ls1,  d["best_s1"],  d["ldr_s1"],  False, ls1)
            sec2 = (ls2,  d["best_s2"],  d["ldr_s2"],  False, s2_split_last)
            sec3 = (llap, d["best_lap"], d["ldr_lap"], False, s3_split_last)

        lbl_y   = 54
        delta_y = 63
        bar_y   = 77
        bar_h   = 26

        x = 8
        for label, (t, pb, ref, in_prog, disp_t) in zip(("S1", "S2", "S3"), (sec1, sec2, sec3)):
            sw = _QSEC

            p.setFont(label_font(7)); p.setPen(QColor(T.DIM))
            p.drawText(x, lbl_y, sw, 8, Qt.AlignmentFlag.AlignCenter, label)

            if not in_prog and t > 0 and ref > 0:
                delta = t - ref
                delta_txt = f"+{delta:.3f}" if delta >= 0 else f"{delta:.3f}"
                delta_col = QColor(T.TEXT)
            else:
                delta_txt = "—"
                delta_col = QColor(T.DIM)
            p.setFont(num_font(8)); p.setPen(delta_col)
            p.drawText(x, delta_y, sw, 12, Qt.AlignmentFlag.AlignCenter, delta_txt)

            bar_col_str = None if in_prog else _sector_col(t, pb, ref)
            p.setBrush(QColor(bar_col_str) if bar_col_str else QColor(40, 40, 46))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x + 2, bar_y, sw - 4, bar_h, 3, 3)

            if not in_prog and disp_t > 0:
                txt_col = "#111111" if bar_col_str == T.WARN else T.TEXT
                p.setFont(num_font(9)); p.setPen(QColor(txt_col))
                p.drawText(x + 2, bar_y, sw - 4, bar_h,
                           Qt.AlignmentFlag.AlignCenter, _fmt_lap(disp_t, 3))

            x += sw

        p.end()
