"""hypertrace/calc/modules/module_telemetry.py — Raw local-player telemetry.

Speed and Pedals used to call `api.read.*` straight from their `on_data()`,
which runs on the GUI thread's QBasicTimer callback — a direct shared-memory
touch from the GUI thread on every tick (30 Hz for both). This module moves
that read onto its own background thread, same as every other calc module;
the widgets now only ever read `minfo.player`.
"""
from __future__ import annotations

from hypertrace.calc.api import api
from hypertrace.calc.module_info import minfo
from hypertrace.calc.modules._base import DataModule
from hypertrace.calc.realtime_state import realtime_state


class Realtime(DataModule):
    def __init__(self) -> None:
        super().__init__("telemetry", active_interval=0.02, idle_interval=0.5)

    def update_data(self) -> None:
        _event_wait = self._event.wait

        while not _event_wait(self.active_interval if realtime_state.active else self.idle_interval):
            if not realtime_state.live:
                continue

            p = minfo.player
            p.speedMs  = api.read.vehicle.speed()
            p.gear     = api.read.engine.gear()
            p.rpm      = api.read.engine.rpm()
            p.rpmMax   = api.read.engine.rpm_max()
            p.throttle = api.read.inputs.throttle()
            p.brake    = api.read.inputs.brake()
            p.clutch   = api.read.inputs.clutch()
