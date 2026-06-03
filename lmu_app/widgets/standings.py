"""
Widget Standings — colonnes configurables.

Colonnes disponibles (activables/réordonnables via l'appli principale) :
  "pos"       Position
  "name"      Nom pilote
  "best"      Meilleur tour
  "last"      Dernier tour
  "gap"       Gap vs leader
  "interval"  Intervalle vs voiture devant

Config par défaut : ["pos", "name", "gap", "interval", "best"]
"""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot, VehicleScoringEntry
from lmu_app.widgets.base import BaseWidget

ROW_H = 20
W     = 340   # un peu plus large pour les colonnes


# Définition des colonnes : (clé, label, largeur, alignement)
COLUMN_DEFS = {
    "pos":      ("",       24,  Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "name":     ("",      140,  Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
    "best":     ("BEST",   70,  Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "last":     ("LAST",   70,  Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "gap":      ("GAP",    65,  Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "interval": ("INT",    65,  Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
}

DEFAULT_COLUMNS = ["pos", "name", "gap", "interval", "best"]
MAX_ROWS = 10


def _fmt_time(t: float) -> str:
    """Formate un temps en m:ss.xxx"""
    if t <= 0: return "-:--.---"
    m = int(t // 60)
    s = t - m * 60
    return f"{m}:{s:06.3f}"


def _total_w(columns: list[str]) -> int:
    return sum(COLUMN_DEFS[c][1] for c in columns if c in COLUMN_DEFS) + 16


def _h(show_header: bool, max_rows: int) -> int:
    return (22 if show_header else 0) + max_rows * ROW_H + 10


class StandingsWidget(BaseWidget):
    WIDGET_NAME = "Standings"

    C_BG      = QColor(10, 10, 10, 215)
    C_BORDER  = QColor(55, 55, 55, 180)
    C_HEADER  = QColor(30, 30, 30)
    C_PLAYER  = QColor(255, 200, 0, 40)
    C_TEXT    = QColor(220, 220, 220)
    C_DIM     = QColor(110, 110, 110)
    C_P1      = QColor(255, 215, 0)
    C_P2      = QColor(192, 192, 192)
    C_P3      = QColor(205, 127, 50)
    C_PURPLE  = QColor(180, 100, 255)   # meilleur tour toute session
    C_GREEN   = QColor(80, 220, 80)     # meilleur tour personnel

    def __init__(self, reader: DataReader,
                 columns: list[str] | None = None,
                 show_header: bool = False,
                 max_rows: int = MAX_ROWS,
                 **kw):
        # Colonnes configurables — seront modifiables depuis l'appli principale
        self.columns      = columns or DEFAULT_COLUMNS
        self._show_header = show_header
        self._header_h    = 22 if show_header else 0
        self._max_rows    = max_rows
        self._entries     = []
        self._session_info = ""
        self._best_lap_overall = 9999.0   # meilleur tour toute session
        super().__init__(reader, update_hz=5, **kw)
        w = _total_w(self.columns)
        self.setFixedSize(w, _h(show_header, max_rows))

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def on_data(self, snap: LMUSnapshot):
        s = snap.session
        vehicles = sorted(s.vehicles, key=lambda v: v.place)

        valid_best = [v.best_lap for v in vehicles if v.best_lap > 0]
        if valid_best:
            self._best_lap_overall = min(valid_best)

        player = next((v for v in vehicles if v.is_player), None)
        self._session_info = f"Lap {player.total_laps}/{s.max_laps}" if player else ""

        # Practice/Quali (0-8): gap = diff best lap. Course (10-13): gap = time_behind_leader
        is_race = s.session_type >= 10
        leader_best = self._best_lap_overall

        self._entries = []
        sorted_v = vehicles[:self._max_rows]
        for i, v in enumerate(sorted_v):
            if is_race:
                gap      = v.time_behind_leader
                interval = (v.time_behind_leader - sorted_v[i-1].time_behind_leader
                            if i > 0 else 0.0)
            else:
                gap      = (v.best_lap - leader_best
                            if v.best_lap > 0 and leader_best < 9999 else -1.0)
                prev_best = sorted_v[i-1].best_lap if i > 0 else 0.0
                interval  = (v.best_lap - prev_best
                             if v.best_lap > 0 and prev_best > 0 else -1.0)

            self._entries.append({
                "pos":       v.place,
                "name":      v.driver_name or v.vehicle_name or f"Car {v.place}",
                "best":      v.best_lap,
                "last":      v.last_lap,
                "gap":       gap,
                "interval":  interval,
                "is_player": v.is_player,
                "is_best":   v.best_lap > 0 and v.best_lap == self._best_lap_overall,
                "is_race":   is_race,
            })
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = _total_w(self.columns)
        H = _h(self._show_header, self._max_rows)
        p.setBrush(self.C_BG); p.setPen(QPen(self.C_BORDER, 1))
        p.drawRoundedRect(0, 0, W, H, 10, 10)

        # Header optionnel
        if self._show_header:
            p.setBrush(self.C_HEADER); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(1, 1, W-2, 22, 9, 9)
            p.setFont(QFont("Monospace", 8))
            p.setPen(self.C_DIM)
            x = 8
            for col in self.columns:
                if col not in COLUMN_DEFS: continue
                label, cw, align = COLUMN_DEFS[col]
                if label:
                    p.drawText(x, 0, cw, 22, align, label)
                x += cw

        for i, e in enumerate(self._entries):
            y = self._header_h + i * ROW_H
            if e["is_player"]:
                p.setBrush(self.C_PLAYER); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(1, y, W-2, ROW_H)

            x = 8
            for col in self.columns:
                if col not in COLUMN_DEFS: continue
                _, cw, align = COLUMN_DEFS[col]

                if col == "pos":
                    pos = e["pos"]
                    col_pos = (self.C_P1 if pos==1 else self.C_P2 if pos==2 else
                               self.C_P3 if pos==3 else self.C_DIM)
                    p.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
                    p.setPen(col_pos)
                    p.drawText(x, y, cw, ROW_H, align, str(pos))

                elif col == "name":
                    p.setFont(QFont("Monospace", 9))
                    p.setPen(QColor(255, 220, 80) if e["is_player"] else self.C_TEXT)
                    # Tronquer si trop long
                    name = e["name"][:18]
                    p.drawText(x + 4, y, cw, ROW_H, align, name)

                elif col == "best":
                    t = e["best"]
                    col_t = self.C_PURPLE if e["is_best"] else self.C_DIM if t <= 0 else self.C_GREEN if e["is_player"] else self.C_TEXT
                    p.setFont(QFont("Monospace", 8))
                    p.setPen(col_t)
                    p.drawText(x, y, cw, ROW_H, align, _fmt_time(t))

                elif col == "last":
                    t = e["last"]
                    p.setFont(QFont("Monospace", 8))
                    p.setPen(self.C_DIM if t <= 0 else self.C_TEXT)
                    p.drawText(x, y, cw, ROW_H, align, _fmt_time(t))

                elif col == "gap":
                    g = e["gap"]
                    p.setFont(QFont("Monospace", 8))
                    p.setPen(self.C_DIM if e["pos"] == 1 else self.C_TEXT)
                    p.drawText(x, y, cw, ROW_H, align,
                               "" if e["pos"] == 1 else f"+{g:.1f}")

                elif col == "interval":
                    iv = e["interval"]
                    p.setFont(QFont("Monospace", 8))
                    p.setPen(self.C_DIM if e["pos"] == 1 else self.C_TEXT)
                    p.drawText(x, y, cw, ROW_H, align,
                               "" if e["pos"] == 1 else f"+{iv:.1f}")

                x += cw
        p.end()
