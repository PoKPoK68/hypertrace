"""hypertrace/calc/module_control.py — Starts/stops every calc module.

Follows an established module-registration pattern (see
THIRD_PARTY_NOTICES.md), simplified: this app has a small, fixed set of
modules (no user-facing enable/disable per module), so registration is a
static list rather than package auto-discovery.
"""
from __future__ import annotations

import logging

from hypertrace.calc.ext.rest_merge import rest_merge
from hypertrace.calc.ext.ws_merge import ws_merge
from hypertrace.calc.modules import module_damage, module_delta, module_fuel, module_stint, module_telemetry, module_vehicles, module_wheels
from hypertrace.calc.realtime_state import state_control

logger = logging.getLogger(__name__)

_MODULES = (
    module_stint,     # session/stint reset detection first — others may read minfo.stint
    module_delta,
    module_fuel,       # also covers Virtual Energy + fuel/VE ratio
    module_wheels,
    module_damage,
    module_telemetry,  # Speed/Pedals — needs to be fast (30 Hz widgets), keep light
    module_vehicles,   # standings/relative — heaviest, last
)


class ModuleControl:
    def __init__(self) -> None:
        self._instances = [m.Realtime() for m in _MODULES]

    def start(self) -> None:
        state_control.start()
        for inst in self._instances:
            inst.start()
        # Full build: REST enriches the desktop overlays, not just Broadcast,
        # so it stays on for the whole session — pin() makes the Broadcast
        # toggle's stop() a no-op here (see calc/ext/rest_merge.py).
        rest_merge.pin()
        rest_merge.start()
        ws_merge.start()   # penalty-type enrichment, see calc/ext/ws_merge.py
        logger.info("calc: all modules started")

    def stop(self) -> None:
        rest_merge.stop(force=True)   # shutdown overrides the pin
        ws_merge.stop()
        for inst in self._instances:
            inst.stop()
        state_control.stop()
        logger.info("calc: all modules stopped")


mctrl = ModuleControl()
