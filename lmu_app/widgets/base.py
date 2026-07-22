"""lmu_app/widgets/base.py — Base class for all overlay widgets.

Update/visibility engine ported from TinyPedal's `tinypedal/widget/_base.py`
(s-victor/TinyPedal, GPLv3): a QBasicTimer instead of QTimer, paused/resumed
and shown/hidden from the shared `realtime_state` singleton (calc/realtime_state.py)
instead of each widget pulling its own snapshot and recomputing game state.

Drag/snap/lock and all drawing code are this app's own and untouched by the
port — see the `_snapped()` docstring for the magnetic-snap fix from earlier
this session, which stays exactly as it was.
"""
from __future__ import annotations

import logging
import os
from typing import Callable

from PySide6.QtCore import QBasicTimer, QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPen
from PySide6.QtWidgets import QApplication, QWidget

from lmu_app.calc.module_info import minfo
from lmu_app.calc.realtime_state import realtime_state

logger = logging.getLogger(__name__)

DEFAULT_SCALE = 100  # default overlay scale in %; change here to resize all overlays globally
                     # MUST match every widget's own CONFIG_SCHEMA "scale" default (100) —
                     # a mismatch here (was 115) meant a fresh install rendered at the code
                     # constant, then shrank the instant any setting was first touched and
                     # the settings dialog applied the schema's own default instead.
_SNAP_DIST    = 5    # px — distance to screen edge / peer overlay that triggers magnetic snap
_SNAP_VICINITY = 150 # px — a peer overlay farther than this on BOTH axes is ignored entirely

# Appended to every auto-hiding widget's CONFIG_SCHEMA by WidgetConfigDialog —
# not duplicated in each widget's own schema list since the meaning (and the
# fields read in _apply_session_visibility/_session_visible below) is
# identical everywhere.
SESSION_VISIBILITY_SCHEMA = [
    {"type": "separator", "label": "Visibility in session"},
    {"key": "show_practice",   "label": "Practice",   "type": "bool", "default": True},
    {"key": "show_qualifying", "label": "Qualifying", "type": "bool", "default": True},
    {"key": "show_race",       "label": "Race",       "type": "bool", "default": True},
]


def _session_category(session_type: int) -> str:
    """Raw mSession: 0-4 practice, 5-8 qualify, 9 warmup, 10-13 race."""
    if session_type >= 10:
        return "race"
    if 5 <= session_type <= 8:
        return "qualifying"
    return "practice"


def _player_in_garage() -> bool:
    # Computed once per module_vehicles.py scan, not re-scanned here — this
    # used to loop over every car on every call, and it's called by all 9
    # widgets independently each tick.
    return minfo.vehicles.playerInGarage


class BaseWidget(QWidget):
    """Frameless, always-on-top overlay widget with drag-to-move and auto-hide."""

    WIDGET_NAME: str = "Widget"

    def __init__(
        self,
        update_hz: int = 20,
        auto_hide: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._auto_hide = auto_hide
        self._dragging = False
        self._drag_offset = QPoint()
        self._locked = False
        self._hide_in_garage = False
        self._on_position_changed: Callable[[int, int], None] | None = None
        self._opacity: int = 85
        self._show_practice   = True
        self._show_qualifying = True
        self._show_race       = True

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # DIAGNOSTIC ONLY — set LMUAPP_DIAG_OPAQUE=1 to disable per-pixel-alpha
        # translucent windows (ugly solid rectangles) to test whether that's
        # the source of freezes reported while overlays are visible. Remove
        # once the question is answered either way.
        if not os.environ.get("LMUAPP_DIAG_OPAQUE"):
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setup_ui()

        self._timer = QBasicTimer()
        self._timer_interval = max(1, int(1000 / update_hz))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._timer.start(self._timer_interval, self)
        self.show()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def set_locked(self, locked: bool) -> None:
        self._dragging = False
        self._locked = locked

    def set_hide_in_garage(self, hide: bool) -> None:
        self._hide_in_garage = hide

    def _apply_session_visibility(self, params: dict) -> None:
        """Call from apply_params() — reads the SESSION_VISIBILITY_SCHEMA
        fields WidgetConfigDialog appends to every auto-hiding widget."""
        self._show_practice   = bool(params.get("show_practice",   True))
        self._show_qualifying = bool(params.get("show_qualifying", True))
        self._show_race       = bool(params.get("show_race",       True))

    def _session_visible(self) -> bool:
        cat = _session_category(minfo.session.sessionType)
        if cat == "race":
            return self._show_race
        if cat == "qualifying":
            return self._show_qualifying
        return self._show_practice

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

    def on_data(self) -> None:
        """Called every active timer tick — read `lmu_app.calc.module_info.minfo`."""

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

        # Peer overlays — X/Y snapping is now gated per axis by proximity on
        # the OTHER axis. Previously a peer's left edge could snap the widget
        # into X-alignment no matter how far apart they were vertically (and
        # symmetrically for Y), which looked like snapping along an infinite
        # line across the whole screen. Matching edges only makes sense for
        # peers that are actually nearby in the perpendicular direction:
        # stacking (X match) needs a reasonable Y gap, side-by-side (Y match)
        # needs a reasonable X gap. The final snap still requires the usual
        # _SNAP_DIST proximity on the matching axis itself.
        def _gap(a0: float, a1: float, b0: float, b1: float) -> float:
            return max(0.0, a0 - b1, b0 - a1)   # 0 when the intervals overlap

        for peer in QApplication.topLevelWidgets():
            if peer is self or not isinstance(peer, BaseWidget) or not peer.isVisible():
                continue
            px, py, pw, ph = peer.x(), peer.y(), peer.width(), peer.height()
            x_gap = _gap(x, x + w, px, px + pw)
            y_gap = _gap(y, y + h, py, py + ph)
            if y_gap <= _SNAP_VICINITY:
                for cx in (px, px + pw, px - w, px + pw - w):
                    _try_x(cx)
            if x_gap <= _SNAP_VICINITY:
                for cy in (py, py + ph, py - h, py + ph - h):
                    _try_y(cy)

        return QPoint(snap_x if snap_x is not None else x,
                      snap_y if snap_y is not None else y)

    # ------------------------------------------------------------------
    # Internal tick
    # ------------------------------------------------------------------

    def _log_state(self, state: str) -> None:
        """Log why this widget is shown/hidden, once per state change."""
        if state != getattr(self, "_last_state", None):
            self._last_state = state
            logger.info("[%s] %s", self.WIDGET_NAME, state)

    def timerEvent(self, event) -> None:
        if event.timerId() != self._timer.timerId():
            super().timerEvent(event)
            return
        self._update()

    def _update(self) -> None:
        # `active` alone (TinyPedal's own approach) isn't enough for LMU:
        # mInRealtime/ignition apparently don't get reset when kicked back to
        # the main menu, so `active` can stay stuck true there. What DOES
        # reliably change is whether the session clock is still advancing —
        # realtime_state.paused already tracks exactly that (mCurrentET
        # frozen for >2s). Still requiring numVehicles/currentEt > 0 handles
        # the case of a genuinely fresh "no session at all" menu state, where
        # nothing is frozen (nothing was ever ticking) but there's still no
        # session to show data for. Being *in* a session (garage included)
        # keeps the clock ticking either way, so this doesn't affect that.
        session_active = (
            minfo.session.numVehicles > 0
            and minfo.session.currentEt > 0
            and not realtime_state.paused
        )

        if not (realtime_state.game_running and realtime_state.connected and session_active):
            self._log_state(f"hidden: game_running={realtime_state.game_running} "
                             f"connected={realtime_state.connected} "
                             f"session_active={session_active}")
            if self.isVisible():
                self.hide()
            return

        # Checked unconditionally (not just when _auto_hide is set) — every
        # desktop overlay is constructed with auto_hide=False (see main.py),
        # so gating this behind _auto_hide meant it never actually applied.
        if not self._session_visible():
            self._log_state("hidden: this session type is disabled in settings")
            if self.isVisible():
                self.hide()
            return

        if self._hide_in_garage and _player_in_garage():
            self._log_state("hidden: player_in_garage and 'hide in garage' is on")
            if self.isVisible():
                self.hide()
            return
        elif self._hide_in_garage and not self.isVisible():
            self.show()

        if self._auto_hide:
            if realtime_state.active:
                self._log_state("visible")
                if not self.isVisible():
                    self.show()
            else:
                self._log_state("hidden: auto_hide and not active")
                if self.isVisible():
                    self.hide()
                return
        else:
            self._log_state("visible")
            if not self.isVisible():
                self.show()

        self.on_data()
