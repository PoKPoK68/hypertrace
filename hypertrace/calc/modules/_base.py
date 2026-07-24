"""hypertrace/calc/modules/_base.py — Data module base.

Adapted from an established reference implementation (see
THIRD_PARTY_NOTICES.md) to this app's simpler per-module config (fixed active/idle intervals
per module instead of a full per-module settings dict — this app doesn't
expose per-module update-rate settings to the user).
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


class DataModule:
    """One background thread per calc module. Subclasses implement
    `update_data()` with their own `while not self._event.wait(interval): ...`
    loop — the base class only owns thread start/stop plumbing."""

    def __init__(self, module_name: str, active_interval: float = 0.1, idle_interval: float = 0.5):
        self.module_name = module_name
        self.closed = True
        self.active_interval = active_interval   # seconds, while realtime_state.active
        self.idle_interval = idle_interval        # seconds, while not active
        self._event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.closed:
            return
        self.closed = False
        self._event.clear()
        self._thread = threading.Thread(target=self.__tasks, name=self.module_name, daemon=True)
        self._thread.start()
        logger.info("calc: ENABLED %s", self.module_name)

    def stop(self) -> None:
        self._event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def update_data(self) -> None:
        """Rewrite in child class."""

    def __tasks(self) -> None:
        self.update_data()
        self.closed = True
        logger.info("calc: DISABLED %s", self.module_name)
