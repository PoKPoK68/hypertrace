"""lmu_app/calc/modules/module_wheels.py — Tyre wear/temperature/pressure.

Not a full port of TinyPedal's `module_wheels.py` (which also estimates
wear-rate-per-lap and suspension/cornering data nothing in this app displays)
— just a direct passthrough of live per-wheel telemetry into `minfo.wheels`,
matching exactly what the Tyres widget already shows. The colour-by-offset-
from-`mOptimalTemp` logic stays in the widget's own paint code, unchanged.
"""
from __future__ import annotations

from lmu_app.calc.api import api
from lmu_app.calc.module_info import minfo
from lmu_app.calc.modules._base import DataModule
from lmu_app.calc.realtime_state import realtime_state


class Realtime(DataModule):
    def __init__(self) -> None:
        super().__init__("wheels", active_interval=0.1, idle_interval=0.5)

    def update_data(self) -> None:
        _event_wait = self._event.wait
        output = minfo.wheels

        while not _event_wait(self.active_interval if realtime_state.active else self.idle_interval):
            if not realtime_state.live:
                continue

            output.wear         = list(api.read.tyre.wear())
            output.surfaceTemp  = list(api.read.tyre.surface_temperature())
            output.innerTemp    = list(api.read.tyre.inner_temperature())
            output.carcassTemp  = list(api.read.tyre.carcass_temperature())
            output.optimalTemp  = list(api.read.tyre.optimal_temperature())
            output.pressure     = list(api.read.tyre.pressure())
            output.brakeTemp    = list(api.read.tyre.brake_temperature())
            output.compounds    = list(api.read.tyre.compound_name())
