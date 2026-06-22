"""lmu_app/widgets/base.py — Base class for all overlay widgets."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QPoint, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPen
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from lmu_app.api.reader import DataReader, LMUSnapshot

logger = logging.getLogger(__name__)

DEFAULT_SCALE = 115  # default overlay scale in %; change here to resize all overlays globally


class BaseWidget(QWidget):
    """Frameless, always-on-top overlay widget with drag-to-move and auto-hide."""

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
        self._last_snap_ts: float = -1.0
        self._opacity: int = 85

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setup_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(int(1000 / update_hz))
        self._timer.timeout.connect(self._update)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._timer.start()
        self.show()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def set_locked(self, locked: bool) -> None:
        self._dragging = False
        self._locked = locked

    def set_hide_in_garage(self, hide: bool) -> None:
        self._hide_in_garage = hide

    def _bg_alpha(self) -> int:
        return round(255 * self._opacity / 100)

    def apply_class_colors(self, colors: dict) -> None:
        """Override in widgets that display car class colors."""

    def _draw_panel(self, p, w: float, h: float, accent: bool = True) -> None:
        """Broadcast panel: gradient fill + border + top amber accent hairline."""
        from lmu_app.utils.theme import T, panel_brush, border_pen, accent_hairline
        p.setBrush(panel_brush(0, 0, h, self._bg_alpha()))
        p.setPen(border_pen(self._opacity))
        p.drawRoundedRect(0, 0, w, h, T.RADIUS, T.RADIUS)
        if accent:
            p.fillRect(QRectF(9, 0, w - 18, 2), accent_hairline(w, self._opacity))

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    CONFIG_SCHEMA: list[dict] = []

    def setup_ui(self) -> None:
        pass

    def on_data(self, snapshot: LMUSnapshot) -> None:
        pass

    def apply_params(self, params: dict) -> None:
        pass

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
    # Internal tick
    # ------------------------------------------------------------------

    def _update(self) -> None:
        snapshot = self._reader.get()

        if not snapshot.game_running or not snapshot.session_active:
            if self.isVisible():
                self.hide()
            return

        if self._hide_in_garage and snapshot.player_in_garage:
            if self.isVisible():
                self.hide()
            return
        elif self._hide_in_garage and not self.isVisible():
            self.show()

        if self._auto_hide:
            if snapshot.is_on_track:
                if not self.isVisible():
                    self.show()
            else:
                if self.isVisible():
                    self.hide()
                return
        elif not self.isVisible():
            self.show()

        if snapshot.timestamp > 0 and snapshot.timestamp == self._last_snap_ts:
            return
        self._last_snap_ts = snapshot.timestamp

        self.on_data(snapshot)
