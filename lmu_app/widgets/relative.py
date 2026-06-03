"""
Widget Relative — gap basé sur position en piste (mTimeIntoLap).

Logique :
  gap = time_into_lap(opponent) - time_into_lap(player)
  Si gap > track_half  → la voiture est en fait devant (wrap)
  Si gap < -track_half → la voiture est en fait derrière (wrap)

  Résultat : négatif = devant le joueur, positif = derrière le joueur
  (même convention que TinyPedal)
"""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget

ROWS   = 9
ROW_H  = 22
W      = 260
H      = ROWS * ROW_H + 16
CENTER = ROWS // 2


class RelativeWidget(BaseWidget):
    WIDGET_NAME = "Relative"
    C_BG     = QColor(10, 10, 10, 215)
    C_BORDER = QColor(55, 55, 55, 180)
    C_PLAYER = QColor(255, 200, 0, 50)
    C_TEXT   = QColor(220, 220, 220)
    C_DIM    = QColor(110, 110, 110)
    C_AHEAD  = QColor(100, 200, 255)   # négatif = devant
    C_BEHIND = QColor(255, 120, 80)    # positif = derrière

    def __init__(self, reader: DataReader, **kw):
        self._rows = []
        super().__init__(reader, update_hz=10, **kw)
        self.setFixedSize(W, H)

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def on_data(self, snap: LMUSnapshot):
        vehicles  = snap.session.vehicles
        player    = next((v for v in vehicles if v.is_player), None)
        if not player:
            return

        # Estimation de la durée d'un tour via best lap ou elapsed time
        # On utilise une valeur fixe de 9999 si pas dispo — le wrap sera ignoré
        # En pratique mTimeIntoLap reset à 0 au passage de la ligne
        # On estime la longueur du tour en secondes depuis les données session
        # (on prendra le meilleur tour ou une valeur par défaut)
        best_laps = [v.best_lap for v in vehicles if v.best_lap > 10]
        lap_time_est = min(best_laps) if best_laps else 120.0
        half_lap = lap_time_est / 2.0

        p_til = player.time_into_lap

        # Calculer le gap pour chaque voiture et trier par gap croissant
        entries = []
        for v in vehicles:
            raw_gap = v.time_into_lap - p_til
            # Correction wrap : si > demi-tour, la voiture est en fait devant
            if raw_gap > half_lap:
                raw_gap -= lap_time_est
            elif raw_gap < -half_lap:
                raw_gap += lap_time_est
            entries.append({
                "pos":       v.place,
                "name":      v.driver_name or f"Car {v.place}",
                "gap":       raw_gap,
                "is_player": v.is_player,
                "in_pits":   v.in_pits,
            })

        # Trier par gap (joueur = 0, devant = négatif, derrière = positif)
        entries.sort(key=lambda e: e["gap"])

        # Trouver l'index du joueur dans la liste triée
        p_idx = next((i for i, e in enumerate(entries) if e["is_player"]), 0)

        # Extraire les ROWS voitures autour du joueur
        self._rows = []
        for i in range(ROWS):
            idx = p_idx - CENTER + i
            if 0 <= idx < len(entries):
                self._rows.append(entries[idx])
            else:
                self._rows.append(None)

        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(self.C_BG); p.setPen(QPen(self.C_BORDER, 1))
        p.drawRoundedRect(0, 0, W, H, 10, 10)

        for i, row in enumerate(self._rows):
            y = 8 + i * ROW_H
            if row is None:
                continue
            is_p = row["is_player"]
            gap  = row["gap"]

            if is_p:
                p.setBrush(self.C_PLAYER); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(1, y, W-2, ROW_H)

            # Barre gap visuelle (max 30s = barre pleine)
            if not is_p and abs(gap) > 0.1:
                col = self.C_AHEAD if gap < 0 else self.C_BEHIND
                bw  = int(min(abs(gap) / 30.0, 1.0) * 80)
                bx  = W//2 - bw if gap < 0 else W//2
                p.setBrush(QColor(col.red(), col.green(), col.blue(), 60))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(bx, y+4, bw, ROW_H-8)

            # Position
            p.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
            p.setPen(QColor(255, 220, 80) if is_p else self.C_DIM)
            p.drawText(6, y, 26, ROW_H, Qt.AlignmentFlag.AlignVCenter, str(row["pos"]))

            # Nom (italique si aux stands)
            name = row["name"]
            font = QFont("Monospace", 9)
            if row["in_pits"]: font.setItalic(True)
            p.setFont(font)
            p.setPen(QColor(255, 220, 80) if is_p else
                     self.C_DIM if row["in_pits"] else self.C_TEXT)
            p.drawText(34, y, 130, ROW_H, Qt.AlignmentFlag.AlignVCenter, name)

            # Gap
            if not is_p:
                col_gap = self.C_AHEAD if gap < 0 else self.C_BEHIND
                p.setPen(col_gap)
                p.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
                p.drawText(6, y, W-12, ROW_H,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           f"{gap:+.1f}s")
        p.end()
