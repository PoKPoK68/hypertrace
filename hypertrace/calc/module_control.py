"""hypertrace/calc/module_control.py — Starts/stops every calc module.

Port of TinyPedal's `tinypedal/module_control.py` pattern, simplified: this
app has a small, fixed set of modules (no user-facing enable/disable per
module), so registration is a static list rather than package auto-discovery.

`rest_merge` is deliberately NOT started here — unlike the shared-memory
modules above, it's the one thing in this app that makes network calls
(localhost:6397), and none of the 9 primary desktop overlays need it (weather
forecast included — see widgets/weather.py's empty-forecast fallback). It's
only ever needed by the broadcast/live-timing tooling, so its lifecycle is
tied to the Stream tab's on/off toggle instead (main.py, main_window.py).

For the same reason this build never calls `rest_merge.pin()` — that's the
full build's way of making the Broadcast toggle's `stop()` a no-op, because
there REST also feeds the desktop overlays. Here `stop()` must genuinely
stop, so nothing is pinned and `force=True` below is merely explicit.
"""
from __future__ import annotations

import logging

from hypertrace.calc.ext.rest_merge import rest_merge
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
        rest_merge.stop(force=True)   # nothing is pinned on this build — explicit for parity
        for inst in self._instances:
            inst.stop()
        state_control.stop()
        logger.info("calc: all modules stopped")


mctrl = ModuleControl()
