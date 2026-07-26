"""hypertrace/calc/module_control.py — Starts/stops every calc module.

Port of TinyPedal's `tinypedal/module_control.py` pattern, simplified: this
app has a small, fixed set of modules (no user-facing enable/disable per
module), so registration is a static list rather than package auto-discovery.

This build has no REST integration at all (see CLAUDE.md) — every module
here is shared-memory only, and nothing makes network calls.
"""
from __future__ import annotations

import logging

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
        logger.info("calc: all modules started")

    def stop(self) -> None:
        for inst in self._instances:
            inst.stop()
        state_control.stop()
        logger.info("calc: all modules stopped")


mctrl = ModuleControl()
