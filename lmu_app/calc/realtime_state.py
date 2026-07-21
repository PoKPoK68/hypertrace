"""lmu_app/calc/realtime_state.py — Session-liveness signal + connection control.

`RealtimeState` is the shared flag every calc module and widget reads to
decide active-vs-idle behavior (port of TinyPedal's `realtime_state` +
`OverlayControl.__updating`, tinypedal/overlay_control.py).

Connection handling (probe-before-connect, reconnect-on-all-zeros) is our own
addition, not present in TinyPedal's connector — proven necessary this app:
Windows' `mmap()` CREATES the named mapping if it doesn't exist yet, so an
app started before LMU attaches to its own empty mapping and would otherwise
read zeros forever with no way to recover once the game actually starts.
"""
from __future__ import annotations

import logging
import sys
import threading
import time

from lmu_app.calc.api import api

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 0.2       # matches TinyPedal's OverlayControl poll rate
_ZERO_RECONNECT_AFTER = 3.0  # seconds of all-zero reads before dropping the mapping


class RealtimeState:
    """Shared coarse liveness flags. Plain mutable object, no locking — a
    widget reading mid-update just repaints one frame stale, never wrong
    long enough to matter at these poll rates (same tradeoff as `minfo`)."""

    __slots__ = ("active", "paused", "game_running", "connected")

    def __init__(self) -> None:
        self.active = False        # driving/on-track right now
        self.paused = False        # game stopped producing new data
        self.game_running = False  # gameVersion != 0
        self.connected = False     # shared-memory mapping opened

    @property
    def live(self) -> bool:
        """True whenever there's a real, current connection to compute
        against — regardless of whether the player is actually driving right
        now. Calc modules gate their actual work on this, not on `active`:
        gating on `active` alone made every overlay freeze (stop updating
        `minfo` at all) the instant you're not literally driving — e.g.
        sitting in the garage with the engine off — a real regression from
        the old reader.py, which had no such pause and kept updating
        regardless of whether you were on track."""
        return self.game_running and self.connected and not self.paused


realtime_state = RealtimeState()


def _mapping_exists(name: str = "LMU_Data") -> tuple[bool, int]:
    """(exists, win32_error) — see module docstring for why this matters."""
    if sys.platform != "win32":
        return True, 0
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenFileMappingW.restype  = wintypes.HANDLE
        k32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        handle = k32.OpenFileMappingW(0x0004, False, name)   # FILE_MAP_READ
        if handle:
            k32.CloseHandle(handle)
            return True, 0
        return False, ctypes.get_last_error()
    except Exception as exc:
        logger.debug("Mapping probe failed (%s) — attempting to connect anyway", exc)
        return True, 0


_WIN_ERR = {
    2: "mapping not found — LMU is not publishing its shared memory "
       "(is the Shared Memory option enabled in the game?)",
    5: "access denied — LMU is most likely running as administrator while this "
       "app is not; run both the same way",
}


class StateControl:
    """Background thread: owns the connect/reconnect lifecycle and keeps
    `realtime_state` current. Started once at app startup."""

    def __init__(self) -> None:
        self._running = False
        self._thread: threading.Thread | None = None
        self._connected = False
        self._last_probe_err: int | None = None
        self._zero_ticks = 0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="LMUStateControl", daemon=True)
        self._thread.start()
        logger.info("StateControl started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._connected:
            try:
                api.stop()
            except Exception:
                pass
        logger.info("StateControl stopped")

    def _connect(self) -> bool:
        exists, err = _mapping_exists()
        if not exists:
            if err != self._last_probe_err:
                self._last_probe_err = err
                logger.warning("LMU shared memory unavailable (win32 error %d): %s",
                                err, _WIN_ERR.get(err, "unknown error"))
            return False
        self._last_probe_err = None
        try:
            api.start()
            self._connected = True
            realtime_state.connected = True
            logger.info("LMU shared memory connected")
            return True
        except Exception as exc:
            logger.warning("Cannot open LMU shared memory: %s — LMU running?", exc)
            return False

    def _disconnect(self) -> None:
        if self._connected:
            try:
                api.stop()
            except Exception:
                pass
        self._connected = False
        realtime_state.connected = False

    def _loop(self) -> None:
        while self._running:
            if not self._connected:
                if not self._connect():
                    time.sleep(2.0)
                    continue

            running = api.read.state.game_running()
            realtime_state.game_running = running

            if not running:
                self._zero_ticks += 1
                if self._zero_ticks * _POLL_INTERVAL >= _ZERO_RECONNECT_AFTER:
                    logger.info("Shared memory reads all zeros — reconnecting "
                                "(LMU may have started after the app)")
                    self._zero_ticks = 0
                    self._disconnect()
                realtime_state.active = False
                realtime_state.paused = False
                time.sleep(_POLL_INTERVAL)
                continue
            self._zero_ticks = 0

            realtime_state.active = api.read.state.active()
            realtime_state.paused = api.read.state.paused()
            time.sleep(_POLL_INTERVAL)


state_control = StateControl()
