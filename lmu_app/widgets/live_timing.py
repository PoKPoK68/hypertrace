"""lmu_app/widgets/live_timing.py — Live timing panel with camera focus control."""
from __future__ import annotations

import threading
import urllib.request as _ur
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from lmu_app.utils.class_colors import class_abbrev, class_color
from lmu_app.utils.theme import T

if TYPE_CHECKING:
    from lmu_app.api.reader import DataReader
    from lmu_app.widgets.broadcast import BroadcastState

_REST_BASE = "http://localhost:6397"

_SS_BTN = (
    "QPushButton { background: rgba(255,255,255,0.07); color: #ccc; "
    "border: 1px solid rgba(255,255,255,0.14); border-radius: 3px; "
    "padding: 0 6px; font-size: 10px; }"
    "QPushButton:hover { background: rgba(255,255,255,0.14); }"
    "QPushButton:pressed { background: rgba(255,255,255,0.22); }"
)
_SS_CAM_TV = (
    "QPushButton { background: #1a3560; color: #6ab4ff; border: none; "
    "font-size: 9px; font-weight: bold; border-radius: 2px; }"
    "QPushButton:hover { background: #2a4d8a; }"
    "QPushButton:pressed { background: #0a2040; }"
)
_SS_CAM_OB = (
    "QPushButton { background: #1a4020; color: #6dcc7f; border: none; "
    "font-size: 9px; font-weight: bold; border-radius: 2px; }"
    "QPushButton:hover { background: #2a6030; }"
    "QPushButton:pressed { background: #0a2010; }"
)

_BG_EVEN  = QColor("#13151a")
_BG_ODD   = QColor("#181b21")
_BG_FOCUS = QColor(30, 58, 30)

# No ::item selector — required for setBackground() to work
_TABLE_SS = """
QTableWidget {
    color: #ddd;
    gridline-color: #23262e;
    border: none;
    selection-background-color: #1e3a1e;
    selection-color: #fff;
    font-size: 11px;
    background: #13151a;
    outline: none;
}
QHeaderView::section {
    background-color: #1c1f26;
    color: #777;
    padding: 3px 4px;
    border: none;
    border-bottom: 1px solid #2a2d35;
    font-size: 10px;
    font-weight: bold;
}
QScrollBar:vertical {
    background: #13151a;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3a3d45;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

_COLS       = ["P", "C", "#", "Driver / Team", "Cls",
               "Best Lap", "Last Lap", "S1", "S2", "S3", "Gap", "Status", "TV", "WS", "CP"]
_COL_WIDTHS = [28, 28, 42, 160, 40, 80, 80, 58, 58, 58, 70, 55, 30, 30, 30]
_COL_TV     = 12
_COL_WS     = 13   # Windshield
_COL_CP     = 14   # Cockpit

# Camera type integers — PUT /rest/watch/focus/{cameraType}/{trackSideGroup}/{shouldAdvance}
# Verified by probing GET /rest/replay/CameraController/getCameraInfo after each call:
#   0 = Onboard/ONBOARD01 (cockpit interior)   1 = Driving/COCKPIT   2 = Driving/NOSECAM
#   3 = Driving/SWINGMAN   4 = TracksideCycle   5 = Trackside (fixed)
#   6 = Onboard/ONBOARD01 (windshield)         7 = Onboard/ONBOARD02   8 = Onboard/ONBOARD03
_CAM_TV = 4          # cameraType int — TracksideCycle (reliable absolute group)
_CAM_WS = "ONBOARD02"  # Windshield — needs confirmation (ONBOARD01 was CP, trying next)
_CAM_CP = "ONBOARD01"  # Cockpit interior — confirmed by user


def _rest_put(path: str, wait_response: bool = False) -> None:
    """PUT via raw socket.  wait_response=True reads the response before returning
    (guarantees server has processed the request before the caller continues)."""
    import socket
    try:
        msg = (
            f"PUT {path} HTTP/1.0\r\n"
            f"Host: localhost:6397\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        ).encode()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.4)
        s.connect(("127.0.0.1", 6397))
        s.sendall(msg)
        if wait_response:
            try:
                s.recv(256)   # read response header — confirms server processed it
            except Exception:
                pass
        s.close()
    except Exception:
        pass


def _rest_put_bg(path: str) -> None:
    threading.Thread(target=_rest_put, args=(path,), daemon=True).start()


def _get_cam_info() -> dict:
    """Blocking GET of current camera info (short timeout for local server)."""
    import urllib.request as _ur2, json as _json
    try:
        with _ur2.urlopen(f"{_REST_BASE}/rest/replay/CameraController/getCameraInfo",
                          timeout=0.3) as r:
            return _json.loads(r.read().decode())
    except Exception:
        return {}


# Onboard ring order verified empirically — 7 cameras cycling in numerical order.
_ONBOARD_RING = ["ONBOARD00","ONBOARD01","ONBOARD02","ONBOARD03",
                 "ONBOARD04","ONBOARD05","ONBOARD06"]


def _seek_onboard_cam(target: str) -> None:
    """Switch to a specific Onboard camera as fast as possible.

    Reads current camera once, calculates the exact advance count using the
    known ring order, then fires all advances back-to-back (each waits for ACK
    to guarantee ordering).  Typical latency: 1 GET + N×PUT ≈ 10–50 ms.
    Falls back to poll-and-advance if the current camera isn't in the ring.
    """
    import time as _time
    info = _get_cam_info()
    current = info.get("cameraName", "")

    if current == target:
        return

    if current in _ONBOARD_RING and target in _ONBOARD_RING:
        ci = _ONBOARD_RING.index(current)
        ti = _ONBOARD_RING.index(target)
        advances = (ti - ci) % len(_ONBOARD_RING)
    else:
        # Not in known ring (e.g. TV group) — enter Onboard first then re-check
        _rest_put("/rest/watch/focus/7/0/false", wait_response=True)
        _time.sleep(0.03)
        info = _get_cam_info()
        current = info.get("cameraName", "")
        if current == target:
            return
        if current in _ONBOARD_RING and target in _ONBOARD_RING:
            ci = _ONBOARD_RING.index(current)
            ti = _ONBOARD_RING.index(target)
            advances = (ti - ci) % len(_ONBOARD_RING)
        else:
            advances = 4  # last-resort fallback

    for _ in range(advances):
        _rest_put("/rest/watch/focus/7/0/false", wait_response=True)

    # Verify — if the ring read was 1 step stale, correct with one extra advance.
    import time as _time2
    _time2.sleep(0.03)
    if _get_cam_info().get("cameraName") != target:
        _rest_put("/rest/watch/focus/7/0/false", wait_response=True)


def _fmt_lap(t: float) -> str:
    if t <= 0:
        return "—"
    m = int(t // 60)
    s = t - m * 60
    return f"{m}:{s:06.3f}"


def _last_lap_color(last_lap: float, best_lap: float, cls_ses_best: float) -> QColor | None:
    """purple=session best, green=personal best, yellow=no improvement."""
    if last_lap <= 0:
        return None
    if best_lap <= 0:
        return QColor(T.WARN)
    if last_lap <= best_lap + 0.002:
        if best_lap <= cls_ses_best + 0.002:
            return QColor(T.PURPLE)
        return QColor(T.GOOD)
    return QColor(T.WARN)


def _fmt_sector(t: float) -> str:
    if t <= 0:
        return "—"
    return f"{t:.3f}"


def _sector_color(t: float, personal_best: float, cls_best: float) -> QColor | None:
    """purple=class best, green=personal best, yellow=no improvement."""
    if t <= 0:
        return None
    if cls_best > 0 and t <= cls_best + 0.001:
        return QColor(T.PURPLE)
    if personal_best > 0 and t <= personal_best + 0.001:
        return QColor(T.GOOD)
    return QColor(T.WARN)


def _cam_btn_widget(label: str, ss: str, on_click) -> QWidget:
    """Minimal camera button widget — click logic is handled by caller."""
    btn = QPushButton(label)
    btn.setFixedSize(26, 18)
    btn.setStyleSheet(ss)
    btn.clicked.connect(on_click)
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    lay = QHBoxLayout(w)
    lay.setContentsMargins(2, 2, 2, 2)
    lay.addWidget(btn)
    return w


class LiveTimingPanel(QWidget):
    """Standalone live timing window with camera focus control."""

    def __init__(self, reader: "DataReader", bc_state: "BroadcastState") -> None:
        super().__init__(None)
        self._reader   = reader
        self._bc_state = bc_state
        self._slot_ids: list[int] = []
        self._prev_slot_ids: list[int] = []
        self._cam_mode: str = ""   # "tv" | "ob" | ""

        self.setWindowTitle("LMU Live Timing")
        self.setMinimumSize(760, 450)
        self.resize(920, 600)
        self.setWindowFlag(Qt.WindowType.Window)
        self._apply_dark()
        self._build_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(400)

    def _apply_dark(self) -> None:
        self.setStyleSheet(
            "QWidget { background: #13151a; color: #ddd; }"
            f"QLabel {{ color: {T.DIM}; font-size: 11px; }}"
        )

    def _build_ui(self) -> None:
        vl = QVBoxLayout(self)
        vl.setContentsMargins(8, 8, 8, 8)
        vl.setSpacing(6)

        # ── Header bar ───────────────────────────────────────────────
        hdr = QHBoxLayout(); hdr.setSpacing(6)

        self._lbl_session = QLabel("—")
        self._lbl_session.setStyleSheet(f"color: {T.ACCENT}; font-size: 13px; font-weight: bold;")
        hdr.addWidget(self._lbl_session)

        hdr.addSpacing(6)

        self._lbl_clock = QLabel("—:——:——")
        self._lbl_clock.setStyleSheet(
            f"color: {T.TEXT}; font-size: 12px; font-family: monospace;")
        hdr.addWidget(self._lbl_clock)

        self._lbl_track = QLabel("")
        self._lbl_track.setStyleSheet(f"color: {T.TEXT}; font-size: 11px;")
        hdr.addWidget(self._lbl_track)

        hdr.addStretch()

        hdr.addSpacing(12)

        btn_prev = QPushButton("◀ Prev"); btn_prev.setFixedSize(64, 24)
        btn_prev.setStyleSheet(_SS_BTN)
        btn_prev.clicked.connect(lambda: _rest_put_bg("/rest/watch/focusBackward"))
        hdr.addWidget(btn_prev)

        btn_next = QPushButton("Next ▶"); btn_next.setFixedSize(64, 24)
        btn_next.setStyleSheet(_SS_BTN)
        btn_next.clicked.connect(lambda: _rest_put_bg("/rest/watch/focusForward"))
        hdr.addWidget(btn_next)

        vl.addLayout(hdr)

        sep = QWidget(); sep.setFixedHeight(1)
        sep.setStyleSheet("background: #2a2d35;")
        vl.addWidget(sep)

        # ── Table ────────────────────────────────────────────────────
        self._table = QTableWidget(0, len(_COLS))
        self._table.setHorizontalHeaderLabels(_COLS)
        self._table.setStyleSheet(_TABLE_SS)
        self._table.setAlternatingRowColors(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(22)
        self._table.setShowGrid(True)
        self._table.horizontalHeader().setHighlightSections(False)

        hh = self._table.horizontalHeader()
        for i, w in enumerate(_COL_WIDTHS):
            self._table.setColumnWidth(i, w)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        vl.addWidget(self._table)

        # ── Footer ───────────────────────────────────────────────────
        ftr = QHBoxLayout()
        self._lbl_focused = QLabel("Double-click = focus  •  TV/OB = change camera")
        self._lbl_focused.setStyleSheet(f"color: {T.DIM}; font-size: 10px;")
        ftr.addWidget(self._lbl_focused)
        ftr.addStretch()
        lbl_hint = QLabel("REST API: localhost:6397")
        lbl_hint.setStyleSheet(f"color: {T.DIM}; font-size: 9px;")
        ftr.addWidget(lbl_hint)
        vl.addLayout(ftr)

    def _set_status(self, msg: str) -> None:
        self._lbl_focused.setText(msg)
        self._lbl_focused.setStyleSheet(f"color: {T.ACCENT}; font-size: 10px;")

    def _tv_click(self, slot: int) -> None:
        self._set_status(f"TV → #{slot}")
        mode_was = self._cam_mode
        self._cam_mode = "tv"
        def _do():
            if mode_was != "tv":
                # Only send camera-type change when NOT already in TracksideCycle —
                # re-sending type 4 would advance the cycle to the next camera group.
                _rest_put(f"/rest/watch/focus/{_CAM_TV}/0/false", wait_response=True)
            _rest_put(f"/rest/watch/focus/{slot}")
        threading.Thread(target=_do, daemon=True).start()

    def _ws_click(self, slot: int) -> None:
        self._set_status(f"WS → #{slot}")
        self._cam_mode = "ws"
        def _do():
            _seek_onboard_cam(_CAM_WS)
            _rest_put(f"/rest/watch/focus/{slot}")
        threading.Thread(target=_do, daemon=True).start()

    def _cp_click(self, slot: int) -> None:
        self._set_status(f"CP → #{slot}")
        self._cam_mode = "cp"
        def _do():
            _seek_onboard_cam(_CAM_CP)
            _rest_put(f"/rest/watch/focus/{slot}")
        threading.Thread(target=_do, daemon=True).start()

    # ── Data refresh ─────────────────────────────────────────────────

    def _refresh(self) -> None:
        snap = self._reader.get()
        if not snap.game_running:
            return

        s = snap.session
        is_race = s.session_type >= 10

        t = s.session_type
        if t <= 4:
            ses_name = "PRACTICE"
        elif t <= 8:
            ses_name = "QUALIFYING"
        elif t == 9:
            ses_name = "WARMUP"
        else:
            ses_name = "RACE"
        self._lbl_session.setText(ses_name)
        self._lbl_track.setText(f"  {s.track_name}")

        rem = max(0, int(s.session_time_remaining))
        h, r = divmod(rem, 3600); m, sc = divmod(r, 60)
        self._lbl_clock.setText(f"{h}:{m:02d}:{sc:02d}")

        vehicles = sorted(s.vehicles, key=lambda v: v.place if v.place > 0 else 9999)
        new_slot_ids = [v.slot_id for v in vehicles]

        # Class position index
        by_class: dict[str, list] = {}
        for v in s.vehicles:
            by_class.setdefault(v.vehicle_class, []).append(v)
        cls_pos: dict[int, int] = {}
        for vlist in by_class.values():
            sv = sorted(vlist, key=lambda v: v.place if v.place > 0 else 9999)
            for i, v in enumerate(sv):
                cls_pos[v.slot_id] = i + 1

        # Session best lap per class
        cls_ses_best: dict[str, float] = {}
        for v in vehicles:
            if v.best_lap > 0:
                cls = v.vehicle_class
                if cls not in cls_ses_best or v.best_lap < cls_ses_best[cls]:
                    cls_ses_best[cls] = v.best_lap

        # Class best sectors (for purple color)
        cls_best_s1: dict[str, float] = {}
        cls_best_s2: dict[str, float] = {}
        cls_best_s3: dict[str, float] = {}
        for v in vehicles:
            cls = v.vehicle_class
            s1 = v.best_sector1
            s2 = (v.best_sector2 - v.best_sector1) if (v.best_sector2 > 0 and v.best_sector1 > 0) else -1.0
            s3 = (v.best_lap - v.best_lap_sector2) if (v.best_lap > 0 and v.best_lap_sector2 > 0) else -1.0
            if s1 > 0:
                cls_best_s1[cls] = min(cls_best_s1.get(cls, s1), s1)
            if s2 > 0:
                cls_best_s2[cls] = min(cls_best_s2.get(cls, s2), s2)
            if s3 > 0:
                cls_best_s3[cls] = min(cls_best_s3.get(cls, s3), s3)

        # Class leader best for quali gap
        cls_leader_best: dict[str, float] = {}
        if not is_race:
            for v in vehicles:
                if v.best_lap > 0:
                    cls = v.vehicle_class
                    if cls not in cls_leader_best or v.best_lap < cls_leader_best[cls]:
                        cls_leader_best[cls] = v.best_lap

        show_team    = self._bc_state.show_team
        focused_slot = snap.viewed_slot_id

        rebuild_cams       = (new_slot_ids != self._prev_slot_ids)
        self._slot_ids     = new_slot_ids
        self._prev_slot_ids = new_slot_ids

        self._table.setRowCount(len(vehicles))

        for row, v in enumerate(vehicles):
            is_focused = (v.slot_id == focused_slot)
            row_bg = _BG_FOCUS if is_focused else (_BG_EVEN if row % 2 == 0 else _BG_ODD)

            def _cell(text: str,
                      align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
                      color: QColor | None = None,
                      bg: QColor | None = None,
                      bold: bool = False,
                      _rbg=row_bg) -> QTableWidgetItem:
                item = QTableWidgetItem(text)
                item.setTextAlignment(align)
                if color:
                    item.setForeground(color)
                item.setBackground(bg if bg is not None else _rbg)
                if bold:
                    f = item.font(); f.setBold(True); item.setFont(f)
                return item

            # P
            pos = v.place
            pc = (QColor(T.P1) if pos == 1 else QColor(T.P2) if pos == 2
                  else QColor(T.P3) if pos == 3 else QColor(T.TEXT))
            self._table.setItem(row, 0, _cell(str(pos) if pos > 0 else "—",
                                              color=pc, bold=(pos <= 3)))
            # C
            cp = cls_pos.get(v.slot_id, 0)
            self._table.setItem(row, 1, _cell(str(cp) if cp > 0 else "—"))

            # #
            self._table.setItem(row, 2, _cell(f"#{v.car_number}" if v.car_number else ""))

            # Driver / Team — full team name (no abbreviation)
            name = (v.team_name if show_team else v.driver_name) or v.vehicle_name or ""
            self._table.setItem(row, 3, _cell(
                name,
                align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                color=QColor(T.ACCENT) if is_focused else None,
                bold=is_focused,
            ))

            # Cls badge
            ab  = class_abbrev(v.vehicle_class) or v.vehicle_class[:4]
            col = class_color(v.vehicle_class, {})
            self._table.setItem(row, 4, _cell(ab, bg=col, color=QColor("#fff"), bold=True))

            # Best Lap
            self._table.setItem(row, 5, _cell(_fmt_lap(v.best_lap)))

            # Last Lap
            ll_col = _last_lap_color(v.last_lap, v.best_lap,
                                     cls_ses_best.get(v.vehicle_class, float('inf')))
            self._table.setItem(row, 6, _cell(_fmt_lap(v.last_lap), color=ll_col))

            # S1 / S2 / S3
            cls = v.vehicle_class
            # Display: current in-progress sectors if available, else last lap
            disp_s1 = v.cur_sector1 if v.cur_sector1 > 0 else v.last_sector1
            disp_s2 = ((v.cur_sector2 - v.cur_sector1)
                       if (v.cur_sector2 > 0 and v.cur_sector1 > 0)
                       else ((v.last_sector2 - v.last_sector1)
                             if (v.last_sector2 > 0 and v.last_sector1 > 0)
                             else -1.0))
            disp_s3 = ((v.last_lap - v.last_sector2)
                       if (v.last_lap > 0 and v.last_sector2 > 0)
                       else -1.0)
            # Personal best per sector
            pb_s1 = v.best_sector1
            pb_s2 = ((v.best_sector2 - v.best_sector1)
                     if (v.best_sector2 > 0 and v.best_sector1 > 0) else -1.0)
            pb_s3 = ((v.best_lap - v.best_lap_sector2)
                     if (v.best_lap > 0 and v.best_lap_sector2 > 0) else -1.0)
            self._table.setItem(row, 7, _cell(_fmt_sector(disp_s1),
                color=_sector_color(disp_s1, pb_s1, cls_best_s1.get(cls, -1.0))))
            self._table.setItem(row, 8, _cell(_fmt_sector(disp_s2),
                color=_sector_color(disp_s2, pb_s2, cls_best_s2.get(cls, -1.0))))
            self._table.setItem(row, 9, _cell(_fmt_sector(disp_s3),
                color=_sector_color(disp_s3, pb_s3, cls_best_s3.get(cls, -1.0))))

            # Gap
            if is_race:
                if v.laps_behind_class_leader > 0:
                    gap_txt = f"+{v.laps_behind_class_leader}L"
                elif v.time_behind_class_leader > 0:
                    gap_txt = f"+{v.time_behind_class_leader:.3f}"
                elif cls_pos.get(v.slot_id, 0) == 1:
                    gap_txt = ""
                else:
                    gap_txt = "—"
            else:
                cls_best = cls_leader_best.get(v.vehicle_class, 0.0)
                if v.best_lap <= 0 or cls_best <= 0:
                    gap_txt = "—"
                else:
                    delta = v.best_lap - cls_best
                    gap_txt = "" if delta < 0.001 else f"+{delta:.3f}"
            self._table.setItem(row, 10, _cell(gap_txt))

            # Status
            if v.finish_status == 2:
                st, st_col = "DNF", QColor("#E05050")
            elif v.finish_status == 4:
                st, st_col = "DQ", QColor("#8050A0")
            elif v.in_garage:
                st, st_col = "GARAGE", QColor(T.DIM)
            elif v.in_pits:
                st, st_col = "PIT", QColor("#E08030")
            else:
                st, st_col = "—", QColor(T.DIM)
            self._table.setItem(row, 11, _cell(st, color=st_col))

            # Camera buttons — only recreated when slot list changes
            if rebuild_cams:
                s = v.slot_id
                self._table.setCellWidget(row, _COL_TV,
                    _cam_btn_widget("TV", _SS_CAM_TV, lambda _=None, sl=s: self._tv_click(sl)))
                self._table.setCellWidget(row, _COL_WS,
                    _cam_btn_widget("WS", _SS_CAM_OB, lambda _=None, sl=s: self._ws_click(sl)))
                self._table.setCellWidget(row, _COL_CP,
                    _cam_btn_widget("CP", _SS_CAM_OB, lambda _=None, sl=s: self._cp_click(sl)))
