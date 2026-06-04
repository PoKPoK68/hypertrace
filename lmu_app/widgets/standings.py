"""
Widget Standings — classement avec colonnes configurables.

Paramètres configurables (appli principale) :
  top_n          : nb de lignes pour les leaders (défaut 3)
  around_n       : nb de lignes autour du joueur (défaut 3)  → total = top_n + 1 + around_n (max 8)
  columns        : liste ordonnée des colonnes affichées
  max_name_chars : longueur max du nom affiché
  show_out_badge : afficher le badge OUT

Colonnes disponibles : "pos", "name", "gap", "interval", "best", "last", "fuel_ve"
"""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot, VehicleScoringEntry
from lmu_app.widgets.base import BaseWidget

ROW_H     = 20
SEP_H     = 4     # hauteur du séparateur entre leaders et groupe joueur
TOTAL_ROWS= 8     # nombre fixe de lignes affichées

# (label header, largeur px, alignement)
COLUMN_DEFS = {
    "pos":      ("",      24, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "name":     ("",     130, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
    "gap":      ("GAP",   62, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "interval": ("INT",   62, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "best":     ("BEST",  68, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "last":     ("LAST",  68, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
    "fuel_ve":  ("EV/F",  44, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
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
C_OUT_BG  = QColor(200, 140, 0)
C_OUT_FG  = QColor(10, 10, 10)


def _fmt_lap(t: float) -> str:
    if t <= 0: return "-"
    m = int(t // 60); s = t - m * 60
    return f"{m}:{s:06.3f}"

def _fmt_gap(g: float, is_race: bool) -> str:
    if g < 0: return "-"
    return f"+{g:.1f}" if is_race else f"+{g:.3f}"

def _total_w(columns):
    return sum(COLUMN_DEFS[c][1] for c in columns if c in COLUMN_DEFS) + 16

def _total_h(show_header, has_sep):
    header = 22 if show_header else 0
    sep    = SEP_H if has_sep else 0
    return header + TOTAL_ROWS * ROW_H + sep + 10


class StandingsWidget(BaseWidget):
    WIDGET_NAME = "Standings"

    def __init__(self, reader: DataReader,
                 columns: list[str] | None = None,
                 top_n: int = 3,
                 around_n: int = 2,
                 show_header: bool = False,
                 max_name_chars: int = 16,
                 show_out_badge: bool = True,
                 **kw):
        self.columns         = columns or DEFAULT_COLUMNS
        self._top_n          = top_n
        self._around_n       = around_n
        self._show_header    = show_header
        self._max_name_chars = max_name_chars
        self._show_out_badge = show_out_badge
        self._header_h       = 22 if show_header else 0
        self._entries        = []
        self._sep_after      = -1   # index après lequel dessiner le séparateur
        self._best_overall   = 9999.0
        self._session_info   = ""
        super().__init__(reader, update_hz=5, **kw)
        w = _total_w(self.columns)
        self.setFixedSize(w, _total_h(show_header, True))

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def on_data(self, snap: LMUSnapshot):
        s        = snap.session
        is_race  = s.session_type >= 10
        vehicles = sorted(s.vehicles, key=lambda v: v.place)

        valid_best = [v.best_lap for v in vehicles if v.best_lap > 0]
        if valid_best: self._best_overall = min(valid_best)

        player = next((v for v in vehicles if v.is_player), None)
        if not player:
            return

        self._session_info = f"Lap {player.total_laps}/{s.max_laps}"
        p_place = player.place
        n       = len(vehicles)

        # --- Construction des 8 lignes ---
        # Groupe leaders : top_n premiers
        # Groupe joueur  : autour_n avant + joueur + autour_n après
        # Si overlap → fusionner sans doublon ni séparateur

        top_indices    = list(range(min(self._top_n, n)))
        p_idx          = p_place - 1   # 0-based

        # Calculer le groupe joueur (around_n de chaque côté)
        half            = (TOTAL_ROWS - self._top_n - 1) // 2
        half            = max(1, half)
        p_start         = max(self._top_n, p_idx - half)
        p_end           = p_start + (TOTAL_ROWS - self._top_n - 1)
        if p_end >= n:
            p_end   = n - 1
            p_start = max(self._top_n, p_end - (TOTAL_ROWS - self._top_n - 1))
        player_indices  = list(range(p_start, p_end + 1))

        # Garantir que le joueur est inclus
        if p_idx not in player_indices:
            player_indices.append(p_idx)
            player_indices.sort()

        # Fusion et séparateur
        overlap = set(top_indices) & set(player_indices)
        if overlap or p_start <= self._top_n:
            # Pas de séparateur si les groupes se touchent
            all_indices  = sorted(set(top_indices) | set(player_indices))
            self._sep_after = -1
        else:
            all_indices  = top_indices + player_indices
            self._sep_after = len(top_indices) - 1

        # Compléter à 8 lignes si nécessaire
        while len(all_indices) < TOTAL_ROWS and all_indices[-1] + 1 < n:
            all_indices.append(all_indices[-1] + 1)

        # Construire les entrées
        leader_best = vehicles[0].best_lap if vehicles and vehicles[0].best_lap > 0 else -1.0

        self._entries = []
        for rank, i in enumerate(all_indices[:TOTAL_ROWS]):
            v = vehicles[i]

            if is_race:
                gap      = v.time_behind_leader
                prev     = vehicles[all_indices[rank-1]] if rank > 0 else None
                interval = (v.time_behind_leader - prev.time_behind_leader) if prev else 0.0
            else:
                gap      = (v.best_lap - leader_best
                            if v.best_lap > 0 and leader_best > 0 else -1.0)
                prev     = vehicles[all_indices[rank-1]] if rank > 0 else None
                if prev and v.best_lap > 0 and prev.best_lap > 0:
                    interval = v.best_lap - prev.best_lap
                else:
                    interval = -1.0

            is_outlap = v.best_lap <= 0

            self._entries.append({
                "pos":       v.place,
                "name":      (v.driver_name or v.vehicle_name or f"Car {v.place}")[:self._max_name_chars],
                "best":      v.best_lap,
                "last":      v.last_lap,
                "gap":       gap,
                "interval":  interval,
                "fuel_ve":   v.best_lap,   # placeholder — sera branché sur les données véhicule
                "is_player": v.is_player,
                "is_best":   v.best_lap > 0 and abs(v.best_lap - self._best_overall) < 0.001,
                "is_race":   is_race,
                "is_outlap": is_outlap,
            })

        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = _total_w(self.columns)
        H = _total_h(self._show_header, self._sep_after >= 0)
        p.setBrush(C_BG); p.setPen(QPen(C_BORDER, 1))
        p.drawRoundedRect(0, 0, W, H, 10, 10)

        # Header optionnel
        if self._show_header:
            p.setBrush(QColor(30,30,30)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(1, 1, W-2, 22, 9, 9)
            x = 8
            for col in self.columns:
                if col not in COLUMN_DEFS: continue
                label, cw, align = COLUMN_DEFS[col]
                if label:
                    p.setFont(QFont("Monospace", 8)); p.setPen(C_DIM)
                    p.drawText(x, 0, cw, 22, align, label)
                x += cw

        sep_extra = 0   # décalage vertical cumulé dû au séparateur

        for row_i, e in enumerate(self._entries):
            y = self._header_h + row_i * ROW_H + sep_extra

            # Séparateur
            if row_i == self._sep_after + 1 and self._sep_after >= 0:
                sep_extra += SEP_H
                y += SEP_H
                p.setBrush(C_SEP); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(8, y - SEP_H + 1, W - 16, 1)

            if e["is_player"]:
                p.setBrush(C_PLAYER); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(1, y, W-2, ROW_H)

            x = 8
            for col in self.columns:
                if col not in COLUMN_DEFS: continue
                _, cw, align = COLUMN_DEFS[col]

                if col == "pos":
                    pos = e["pos"]
                    c   = C_P1 if pos==1 else C_P2 if pos==2 else C_P3 if pos==3 else C_DIM
                    p.setFont(QFont("Monospace", 9, QFont.Weight.Bold)); p.setPen(c)
                    p.drawText(x, y, cw, ROW_H, align, str(pos))

                elif col == "name":
                    p.setFont(QFont("Monospace", 9))
                    p.setPen(QColor(255,220,80) if e["is_player"] else C_TEXT)
                    name_draw_w = cw - (26 if self._show_out_badge and e["is_outlap"] else 0)
                    p.drawText(x+4, y, name_draw_w, ROW_H, align, e["name"])
                    if self._show_out_badge and e["is_outlap"]:
                        bx2 = x + cw - 24
                        by2 = y + 3
                        p.setBrush(C_OUT_BG); p.setPen(Qt.PenStyle.NoPen)
                        p.drawRoundedRect(bx2, by2, 22, ROW_H-6, 2, 2)
                        p.setFont(QFont("Monospace", 7, QFont.Weight.Bold))
                        p.setPen(C_OUT_FG)
                        p.drawText(bx2, by2, 22, ROW_H-6, Qt.AlignmentFlag.AlignCenter, "OUT")

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
                    if e["pos"] == 1:
                        txt = ""
                    elif e["is_outlap"] and not e["is_race"]:
                        txt = "-"
                    else:
                        txt = _fmt_gap(e["gap"], e["is_race"])
                    p.setFont(QFont("Monospace", 8)); p.setPen(C_DIM if not txt else C_TEXT)
                    p.drawText(x, y, cw, ROW_H, align, txt)

                elif col == "interval":
                    if e["pos"] == 1:
                        txt = ""
                    elif e["is_outlap"] and not e["is_race"]:
                        txt = "-"
                    else:
                        txt = _fmt_gap(e["interval"], e["is_race"])
                    p.setFont(QFont("Monospace", 8)); p.setPen(C_DIM if not txt else C_TEXT)
                    p.drawText(x, y, cw, ROW_H, align, txt)

                elif col == "fuel_ve":
                    # Placeholder — à connecter aux données véhicule réelles
                    p.setFont(QFont("Monospace", 8)); p.setPen(C_DIM)
                    p.drawText(x, y, cw, ROW_H, align, "-")

                x += cw
        p.end()
