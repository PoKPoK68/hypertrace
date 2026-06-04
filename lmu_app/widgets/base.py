"""
lmu_app/widgets/base.py

Classe de base pour tous les widgets overlay.
Gère :
  - Fenêtre transparente sans bordure (overlay)
  - Drag & drop pour repositionner
  - QTimer pour le polling des données
  - Auto-hide quand le joueur n'est pas en piste
  - Sauvegarde/restauration de la position
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from lmu_app.api.reader import DataReader, LMUSnapshot

logger = logging.getLogger(__name__)


class BaseWidget(QWidget):
    """
    Widget overlay de base.

    Sous-classes doivent implémenter :
      - on_data(snapshot: LMUSnapshot) → met à jour l'affichage
      - (optionnel) setup_ui() → construit l'UI interne
    """

    WIDGET_NAME: str = "Widget"

    def __init__(
        self,
        reader: DataReader,
        update_hz: int = 20,
        auto_hide: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._reader = reader
        self._auto_hide = auto_hide
        self._dragging = False
        self._drag_offset = QPoint()
        self._locked = False
        self._hide_in_garage = False
        self._on_position_changed: Callable[[int, int], None] | None = None

        # Fenêtre overlay : transparente, sans décoration, toujours au-dessus
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # pas dans la taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Construction de l'UI du widget enfant
        self.setup_ui()

        # Timer de mise à jour
        self._timer = QTimer(self)
        self._timer.setInterval(int(1000 / update_hz))
        self._timer.timeout.connect(self._update)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Démarre les mises à jour et affiche le widget."""
        self._timer.start()
        self.show()

    def stop(self) -> None:
        """Arrête les mises à jour et cache le widget."""
        self._timer.stop()
        self.hide()

    def set_locked(self, locked: bool) -> None:
        self._dragging = False
        self._locked = locked

    def set_hide_in_garage(self, hide: bool) -> None:
        self._hide_in_garage = hide

    def apply_class_colors(self, colors: dict) -> None:
        """Override in widgets that display car class colors."""

    # ------------------------------------------------------------------
    # À surcharger dans les sous-classes
    # ------------------------------------------------------------------

    # Schéma des paramètres configurables.
    # Chaque entrée : {"key": str, "label": str, "type": "int"|"float"|"bool"|"choice",
    #                  "default": ..., "min": ..., "max": ..., "step": ...,
    #                  "options": [{"value": ..., "label": str}, ...]}
    CONFIG_SCHEMA: list[dict] = []

    def setup_ui(self) -> None:
        """Construire les éléments visuels du widget."""

    def on_data(self, snapshot: LMUSnapshot) -> None:
        """Appelé à chaque tick avec le snapshot courant. À surcharger."""

    def apply_params(self, params: dict) -> None:
        """Applique les paramètres de configuration. À surcharger."""

    # ------------------------------------------------------------------
    # Drag & drop
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._locked and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._dragging = False
            if self._on_position_changed:
                self._on_position_changed(self.x(), self.y())

    # ------------------------------------------------------------------
    # Tick interne
    # ------------------------------------------------------------------

    def _update(self) -> None:
        snapshot = self._reader.get()

        # Hide when player is in garage
        if self._hide_in_garage and snapshot.player_in_garage:
            if self.isVisible():
                self.hide()
            return
        elif self._hide_in_garage and not self.isVisible():
            self.show()

        # Auto-hide when not on track
        if self._auto_hide:
            if snapshot.is_on_track or not snapshot.game_running:
                if not self.isVisible():
                    self.show()
            else:
                if self.isVisible():
                    self.hide()
                return

        self.on_data(snapshot)
