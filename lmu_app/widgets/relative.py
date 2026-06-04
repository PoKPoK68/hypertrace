"""
Widget Relative — implémentation fidèle à TinyPedal (module_relative.py).

Formule (lignes 155-171 de module_relative.py TinyPedal) :
    diff_time = opt_time_into_lap - plr_time_into_lap
    gap = diff_time - (diff_time // laptime_est) * laptime_est
    gap_ahead  = gap          si gap >= 0, sinon gap + laptime_est
    gap_behind = gap - laptime_est  si gap > 0, sinon gap

    → négatif = devant le joueur (ahead), positif = derrière (behind)

laptime_est = mEstimatedLapTime de chaque véhicule (disponible pour tous dans scoring).
On utilise la valeur du joueur comme référence, comme TinyPedal.

Badges :
  PIT = en pitlane (roule)
  OUT = outlap (sorti des pits, pas encore de best lap)

Paramètres configurables :
  rows         : nombre de lignes (impair, défaut 9)
  show_badges  : afficher les badges PIT/OUT
"""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy
from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget

ROW_H = 22
W     = 260


class RelativeWidget(BaseWidget):
    WIDGET_NAME = "Relative"
    C_BG     = QColor(10, 10, 10, 215)
    C_BORDER = QColor(55, 55, 55, 180)
    C_PLAYER = QColor(255, 200, 0, 50)
    C_TEXT   = QColor(220, 220, 220)
    C_DIM    = QColor(110, 110, 110)
    C_AHEAD  = QColor(100, 200, 255)
    C_BEHIND = QColor(255, 120, 80)
    C_PIT_BG = QColor(60, 120, 200)
    C_PIT_FG = QColor(240, 240, 240)
    C_OUT_BG = QColor(200, 140, 0)
    C_OUT_FG = QColor(10, 10, 10)

    def __init__(self, reader: DataReader,
                 rows: int = 9,
                 show_badges: bool = True,
                 **kw):
        self._rows_count  = rows if rows % 2 == 1 else rows + 1
        self._show_badges = show_badges
        self._rows        = []
        super().__init__(reader, update_hz=10, **kw)
        self.setFixedSize(W, self._rows_count * ROW_H + 16)

    def setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def on_data(self, snap: LMUSnapshot):
        vehicles = snap.session.vehicles
        player   = next((v for v in vehicles if v.is_player), None)
        if not player:
            return

        # laptime_est = mEstimatedLapTime du joueur (comme TinyPedal)
        laptime_est = player.estimated_lap_time
        if laptime_est <= 0:
            # Fallback sur best lap session si pas encore disponible
            best_laps = [v.best_lap for v in vehicles if v.best_lap > 10]
            laptime_est = min(best_laps) if best_laps else 120.0

        plr_time = player.time_into_lap

        ahead_list  = []  # (gap_ahead, vehicle)  — gap positif, trié décroissant
        behind_list = []  # (gap_behind, vehicle) — gap négatif, trié décroissant

        for v in vehicles:
            if v.is_player or v.in_garage:
                continue

            # Formule exacte TinyPedal
            diff_time = v.time_into_lap - plr_time
            gap = diff_time - (diff_time // laptime_est) * laptime_est  # modulo dans [0, laptime_est]

            gap_ahead  = gap if gap >= 0 else gap + laptime_est   # toujours >= 0
            gap_behind = gap - laptime_est if gap > 0 else gap     # toujours <= 0

            badge = ("PIT" if v.in_pits
                     else "OUT" if v.best_lap <= 0
                     else "")

            entry = {
                "pos":       v.place,
                "name":      v.driver_name or f"Car {v.place}",
                "is_player": False,
                "in_pits":   v.in_pits,
                "badge":     badge,
            }

            ahead_list.append((gap_ahead,  {**entry, "gap": -gap_ahead}))   # négatif = devant
            behind_list.append((gap_behind, {**entry, "gap": -gap_behind}))  # positif = derrière

        # Trier comme TinyPedal : ahead = décroissant (plus proche en premier)
        #                         behind = décroissant (plus proche en premier, valeurs négatives)
        ahead_list.sort(reverse=True)   # ex: [5.0, 3.2, 1.1] → le 1.1 est le plus proche devant
        behind_list.sort(reverse=True)  # ex: [-1.5, -8.0, -20.0] → le -1.5 est le plus proche derrière

        # Prendre center voitures de chaque côté
        center = self._rows_count // 2
        ahead_entries  = [e for _, e in ahead_list[-center:]]   # les center plus proches devant
        behind_entries = [e for _, e in behind_list[:center]]    # les center plus proches derrière

        player_entry = {
            "pos": player.place, "name": player.driver_name or "Player",
            "gap": 0.0, "is_player": True, "in_pits": player.in_pits, "badge": "",
        }

        # Construire la liste finale : ahead (devant → joueur), joueur, behind (derrière)
        # ahead_entries est [le plus loin...le plus proche], on veut [loin→proche→joueur]
        self._rows = (
            [None] * max(0, center - len(ahead_entries))   # lignes vides en haut
            + ahead_entries
            + [player_entry]
            + behind_entries
            + [None] * max(0, center - len(behind_entries))  # lignes vides en bas
        )
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        H = self._rows_count * ROW_H + 16
        p.setBrush(self.C_BG); p.setPen(QPen(self.C_BORDER, 1))
        p.drawRoundedRect(0, 0, W, H, 10, 10)

        for i, row in enumerate(self._rows[:self._rows_count]):
            y = 8 + i * ROW_H
            if row is None:
                continue

            is_p  = row["is_player"]
            gap   = row["gap"]
            badge = row["badge"] if self._show_badges else ""

            if is_p:
                p.setBrush(self.C_PLAYER); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(1, y, W-2, ROW_H)

            # Barre gap visuelle (max 30s)
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

            # Nom
            name_w = 128 - (26 if badge else 0)
            font   = QFont("Monospace", 9)
            if row["in_pits"] and not is_p: font.setItalic(True)
            p.setFont(font)
            p.setPen(QColor(255, 220, 80) if is_p else
                     self.C_DIM if row["in_pits"] else self.C_TEXT)
            p.drawText(34, y, name_w, ROW_H, Qt.AlignmentFlag.AlignVCenter, row["name"][:16])

            # Badge PIT / OUT
            if badge:
                bx2 = 34 + name_w + 2
                bg  = self.C_PIT_BG if badge == "PIT" else self.C_OUT_BG
                fg  = self.C_PIT_FG if badge == "PIT" else self.C_OUT_FG
                p.setBrush(bg); p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(bx2, y+3, 24, ROW_H-6, 2, 2)
                p.setFont(QFont("Monospace", 7, QFont.Weight.Bold))
                p.setPen(fg)
                p.drawText(bx2, y+3, 24, ROW_H-6, Qt.AlignmentFlag.AlignCenter, badge)

            # Gap (sans "s")
            if not is_p:
                col_gap = self.C_AHEAD if gap < 0 else self.C_BEHIND
                p.setPen(col_gap)
                p.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
                p.drawText(6, y, W-12, ROW_H,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                           f"{gap:+.1f}")
        p.end()
