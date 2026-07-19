"""lmu_app/widgets/base.py — Base class for all overlay widgets."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QPoint, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPen
from PySide6.QtWidgets import QApplication, QWidget

if TYPE_CHECKING:
    from lmu_app.api.reader import DataReader, LMUSnapshot

logger = logging.getLogger(__name__)

DEFAULT_SCALE = 115  # default overlay scale in %; change here to resize all overlays globally
_SNAP_DIST    = 5    # px — distance to screen edge / peer overlay that triggers magnetic snap


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
            self.grabKeyboard()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            raw = event.globalPosition().toPoint() - self._drag_offset
            self.move(self._snapped(raw.x(), raw.y()))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._dragging = False
            self.releaseKeyboard()
            if self._on_position_changed:
                self._on_position_changed(self.x(), self.y())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        step = 10 if event.modifiers() & Qt.KeyboardModifier.ControlModifier else 1
        key  = event.key()
        dx = dy = 0
        if   key == Qt.Key.Key_Left:  dx = -step
        elif key == Qt.Key.Key_Right: dx =  step
        elif key == Qt.Key.Key_Up:    dy = -step
        elif key == Qt.Key.Key_Down:  dy =  step
        else:
            super().keyPressEvent(event)
            return
        self.move(self.x() + dx, self.y() + dy)
        if self._on_position_changed:
            self._on_position_changed(self.x(), self.y())

    def _snapped(self, x: int, y: int) -> QPoint:
        """Return position snapped to screen edges and peer overlays when within _SNAP_DIST."""
        cx = x + self.width() // 2
        cy = y + self.height() // 2
        scr = QApplication.screenAt(QPoint(cx, cy)) or QApplication.primaryScreen()
        screen = scr.geometry()
        w, h   = self.width(), self.height()

        snap_x: int | None = None
        snap_y: int | None = None
        best_dx = _SNAP_DIST
        best_dy = _SNAP_DIST

        def _try_x(cx: int) -> None:
            nonlocal snap_x, best_dx
            d = abs(x - cx)
            if d < best_dx:
                best_dx = d; snap_x = cx

        def _try_y(cy: int) -> None:
            nonlocal snap_y, best_dy
            d = abs(y - cy)
            if d < best_dy:
                best_dy = d; snap_y = cy

        # Screen edges
        _try_x(screen.left())
        _try_x(screen.right() - w + 1)
        _try_y(screen.top())
        _try_y(screen.bottom() - h + 1)

        # Peer overlays
        for peer in QApplication.topLevelWidgets():
            if peer is self or not isinstance(peer, BaseWidget) or not peer.isVisible():
                continue
            px, py, pw, ph = peer.x(), peer.y(), peer.width(), peer.height()
            for cx in (px, px + pw, px - w, px + pw - w):
                _try_x(cx)
            for cy in (py, py + ph, py - h, py + ph - h):
                _try_y(cy)

        return QPoint(snap_x if snap_x is not None else x,
                      snap_y if snap_y is not None else y)

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
