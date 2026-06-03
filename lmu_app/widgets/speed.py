"""
lmu_app/widgets/speed.py

Widget Vitesse / Gear / RPM bar.
Premier widget de test pour valider le pipeline complet.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from lmu_app.api.reader import DataReader, LMUSnapshot
from lmu_app.widgets.base import BaseWidget


class SpeedWidget(BaseWidget):
    """
    Affiche :
      - Vitesse en km/h (grand chiffre)
      - Rapport engagé
      - Barre RPM avec zone rouge
    """

    WIDGET_NAME = "Vitesse & Gear"

    # Palette — facile à thématiser plus tard
    COLOR_BG = QColor(10, 10, 10, 200)
    COLOR_TEXT = QColor(255, 255, 255)
    COLOR_TEXT_DIM = QColor(150, 150, 150)
    COLOR_RPM = QColor(80, 200, 120)
    COLOR_RPM_RED = QColor(220, 60, 60)
    COLOR_GEAR = QColor(255, 200, 0)
    COLOR_BORDER = QColor(60, 60, 60, 180)

    W = 220
    H = 120

    def __init__(self, reader: DataReader, **kwargs) -> None:
        self._speed = 0.0
        self._gear = 0
        self._rpm = 0.0
        self._rpm_max = 9000.0
        self._throttle = 0.0
        self._brake = 0.0
        super().__init__(reader, update_hz=30, **kwargs)
        self.setFixedSize(self.W, self.H)

    def setup_ui(self) -> None:
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def on_data(self, snapshot: LMUSnapshot) -> None:
        v = snapshot.vehicle
        self._speed = v.speed_kmh
        self._gear = v.gear
        self._rpm = v.rpm
        self._rpm_max = v.rpm_max
        self._throttle = v.throttle
        self._brake = v.brake
        self.update()  # déclenche paintEvent

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.W, self.H

        # --- Fond arrondi ---
        p.setBrush(self.COLOR_BG)
        p.setPen(QPen(self.COLOR_BORDER, 1))
        p.drawRoundedRect(0, 0, w, h, 10, 10)

        # --- Barre RPM (bas) ---
        bar_h = 10
        bar_y = h - bar_h - 6
        bar_w = w - 16
        bar_x = 8
        ratio = min(1.0, self._rpm / self._rpm_max) if self._rpm_max > 0 else 0.0
        redline = 0.85  # zone rouge à partir de 85%

        # fond de la barre
        p.setBrush(QColor(40, 40, 40))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)

        # remplissage
        fill_w = int(bar_w * ratio)
        color = self.COLOR_RPM_RED if ratio >= redline else self.COLOR_RPM
        p.setBrush(color)
        p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 3, 3)

        # --- Vitesse ---
        font_speed = QFont("Monospace", 42, QFont.Weight.Bold)
        p.setFont(font_speed)
        p.setPen(self.COLOR_TEXT)
        speed_str = f"{int(self._speed):3d}"
        p.drawText(10, 8, w - 80, 70, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, speed_str)

        # unité km/h
        font_unit = QFont("Monospace", 11)
        p.setFont(font_unit)
        p.setPen(self.COLOR_TEXT_DIM)
        p.drawText(10, 62, 60, 16, Qt.AlignmentFlag.AlignLeft, "km/h")

        # --- Gear ---
        font_gear = QFont("Monospace", 44, QFont.Weight.Bold)
        p.setFont(font_gear)
        p.setPen(self.COLOR_GEAR)
        gear_str = {0: "N", -1: "R"}.get(self._gear, str(self._gear))
        p.drawText(w - 75, 4, 66, 72, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, gear_str)

        p.end()
