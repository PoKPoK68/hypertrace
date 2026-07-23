"""lmu_app/calc/modules/module_damage.py — Bodywork/wheel damage.

Direct passthrough into `minfo.damage` — the Damage widget maps these raw
facts to its own severity scale. Everything here is shared memory except
`suspensionDamage`, populated separately by calc/ext/rest_merge.py (REST
only, see project memory).
"""
from __future__ import annotations

from lmu_app.calc.api import api
from lmu_app.calc.module_info import minfo
from lmu_app.calc.modules._base import DataModule
from lmu_app.calc.realtime_state import realtime_state


class Realtime(DataModule):
    def __init__(self) -> None:
        super().__init__("damage", active_interval=0.2, idle_interval=0.5)

    def update_data(self) -> None:
        _event_wait = self._event.wait
        output = minfo.damage

        while not _event_wait(self.active_interval if realtime_state.active else self.idle_interval):
            if not realtime_state.live:
                continue

            output.bodySeverity     = list(api.read.damage.body_severity())
            output.wheelDetached    = list(api.read.damage.wheel_detached())
            output.tyrePuncture     = list(api.read.tyre.puncture())
            output.rearWingDetached = api.read.damage.rear_wing_detached()
