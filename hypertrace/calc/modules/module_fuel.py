"""hypertrace/calc/modules/module_fuel.py — Fuel + Virtual Energy consumption.

Simplified adaptation of an established reference implementation (see
THIRD_PARTY_NOTICES.md). Same two simplifications as module_delta.py: raw
`api.read.lap.distance()` instead of GPS-position-sync, and no cross-session
file persistence of the last-lap-consumption trace (in-memory only).

Fuel, Virtual Energy and hybrid battery SoC are computed by the same
generator, run three times — fuel in litres (tank capacity), VE and SoC in
percent (capacity fixed at 100) — treating them as the same shape of problem.
The generator already separates a rising reading (regen) from a falling one
(burn/deployment) — see its own comment on amount_diff — so it needed no
battery-specific branch, just a third telemetry source. The fuel/VE ratio and
the live-only hybrid readings (regen kW, deployment map) are set here too, not
in a separate hybrid module — there's no per-lap tracking involved for those.
"""
from __future__ import annotations

from math import ceil
from typing import Callable, Generator

from hypertrace.calc._calc_util import (
    DELTA_DEFAULT, DELTA_ZERO,
    delta_telemetry, end_lap_consumption, end_lap_empty_capacity,
    end_stint_fuel, end_stint_laps, end_stint_minutes, end_stint_pit_counts,
    fuel_to_energy_ratio, lap_type_full_laps_remain, lap_type_laps_remain,
    time_type_laps_remain, valid_delta_raw,
)
from hypertrace.calc.api import api
from hypertrace.calc.module_info import FuelInfo, minfo
from hypertrace.calc.modules._base import DataModule
from hypertrace.calc.realtime_state import realtime_state

_MIN_DELTA_DISTANCE = 5.0   # meters between recorded samples


def _telemetry_fuel() -> tuple[float, float]:
    return max(api.read.engine.tank_capacity(), 0.01), api.read.engine.fuel()


def _telemetry_energy() -> tuple[float, float]:
    return 100.0, api.read.engine.virtual_energy() * 100.0


def _telemetry_battery() -> tuple[float, float]:
    return 100.0, api.read.engine.state_of_charge()


def _reference_laptime() -> float:
    """Best available lap-time reference for laps-remaining estimates."""
    for t in (minfo.delta.lapTimeBest, minfo.delta.lapTimeSession, minfo.delta.lapTimeEstimated):
        if t > 0:
            return t
    return 0.0


def _calc_consumption(output: FuelInfo, telemetry_func: Callable[[], tuple[float, float]]) -> Generator[None, None, None]:
    recording = False
    validating = 0.0
    is_pit_lap = False

    delta_array_raw: list[tuple[float, ...]] = [DELTA_ZERO]
    delta_array_last: tuple = DELTA_DEFAULT
    delta_array_temp: tuple = DELTA_DEFAULT
    used_last_valid = 0.0
    delta_amount = 0.0

    amount_last = 0.0
    used_curr = 0.0
    used_last_raw = 0.0

    last_lap_stime = float("inf")
    pos_recorded = pos_last = 0.0

    while True:
        yield

        capacity, amount_curr = telemetry_func()
        lap_stime = api.read.timing.start()
        elapsed_time = api.read.timing.elapsed()
        laptime_curr = api.read.timing.current_laptime()
        time_left = api.read.session.remaining()
        in_garage = api.read.vehicle.in_garage()
        pos_curr = api.read.lap.distance()
        laps_done = api.read.lap.completed_laps()
        lap_into = api.read.lap.progress()
        is_pit_lap |= api.read.vehicle.in_pits()
        laptime_pace = _reference_laptime()

        # Realtime consumption — distinguish regen/refuel (amount went up) from burn (went down).
        amount_diff = amount_last - amount_curr
        if amount_last < amount_curr:
            if api.read.vehicle.speed() > 1:   # moving + amount increased → regen
                used_curr += amount_diff
            amount_last = amount_curr
        elif amount_last > amount_curr:
            used_curr += amount_diff
            amount_last = amount_curr

        # Lap start/finish detection
        if lap_stime > last_lap_stime:
            if not is_pit_lap and valid_delta_raw(delta_array_raw, used_curr, 1):
                delta_array_raw.append((round(pos_last + 10, 6), round(used_curr, 6)))
                delta_array_temp = tuple(delta_array_raw)
                validating = elapsed_time
            delta_array_raw = [DELTA_ZERO]
            pos_last = pos_recorded = pos_curr
            used_last_raw = used_curr
            used_curr = 0.0
            recording = laptime_curr < 1
            is_pit_lap = False
        last_lap_stime = lap_stime

        if 0 < laptime_curr < 1 and pos_curr > 300:
            pos_last = pos_recorded = pos_curr = 0.0

        if 0 <= pos_curr != pos_last:
            if recording and pos_curr - pos_recorded >= _MIN_DELTA_DISTANCE:
                delta_array_raw.append((round(pos_curr, 6), round(used_curr, 6)))
                pos_recorded = pos_curr
            pos_last = pos_curr

        if validating:
            timer = elapsed_time - validating
            if timer > 3:
                validating = 0.0
            elif timer > 0.3 and api.read.timing.last_laptime() > 0:
                used_last_valid = used_last_raw
                delta_array_last = delta_array_temp
                delta_array_temp = DELTA_DEFAULT
                validating = 0.0

        delta_amount = delta_telemetry(
            delta_array_last, pos_curr, used_curr, laptime_curr > 0.3 and not in_garage)

        used_est = end_lap_consumption(used_last_valid, delta_amount, not is_pit_lap and laps_done > 0)

        if api.read.session.finish_type() == 1:   # laps-only
            full_laps_left = lap_type_full_laps_remain(api.read.lap.maximum(), laps_done)
            laps_left = lap_type_laps_remain(full_laps_left, lap_into)
        elif laptime_pace > 0:
            end_timer_laps_left = (time_left / laptime_pace + lap_into) if time_left > 0 else lap_into
            full_laps_left = ceil(end_timer_laps_left)
            laps_left = time_type_laps_remain(full_laps_left, lap_into)
        else:
            laps_left = 0.0

        amount_need_abs = laps_left * used_est
        amount_need_rel = amount_need_abs - amount_curr
        amount_end = end_stint_fuel(amount_curr, used_curr, used_est)
        est_runlaps = end_stint_laps(amount_curr, used_est)
        est_runmins = end_stint_minutes(est_runlaps, laptime_pace)

        output.capacity          = capacity
        output.amountCurrent     = amount_curr
        output.amountUsedLast    = used_last_raw
        output.amountUsedAvg     = used_last_valid + delta_amount
        output.amountUsedCurrent = used_curr
        output.estimatedLaps     = est_runlaps
        output.estimatedMinutes  = est_runmins
        output.neededRelative    = amount_need_rel
        output.amountEndStint    = amount_end
        output.lapsRemaining     = laps_left


class Realtime(DataModule):
    def __init__(self) -> None:
        super().__init__("fuel", active_interval=0.1, idle_interval=0.5)

    def update_data(self) -> None:
        _event_wait = self._event.wait
        reset = False
        interval = self.idle_interval

        gen_fuel = gen_energy = gen_battery = None

        while not _event_wait(interval):
            if not realtime_state.live:
                if reset:
                    reset = False
                    interval = self.idle_interval
                continue

            # Gate on `live`, not `active` — see RealtimeState.live. `active`
            # still governs the poll rate below.
            interval = self.active_interval if realtime_state.active else self.idle_interval

            if not reset:
                reset = True
                gen_fuel    = _calc_consumption(minfo.fuel, _telemetry_fuel)
                gen_energy  = _calc_consumption(minfo.energy, _telemetry_energy)
                gen_battery = _calc_consumption(minfo.battery, _telemetry_battery)
                next(gen_fuel)   # prime to the first `yield`
                next(gen_energy)
                next(gen_battery)

            next(gen_fuel)

            has_ve = api.read.engine.virtual_energy() != 0
            if has_ve:
                next(gen_energy)
                minfo.hybrid.fuelEnergyRatio = fuel_to_energy_ratio(
                    minfo.fuel.amountUsedAvg, minfo.energy.amountUsedAvg)
            minfo.hybrid.batteryCharge = api.read.engine.battery_charge()

            # Hypercar-only hybrid readings — SoC via the same per-lap
            # consumption tracking as fuel/VE above; regen/deployment are
            # live-only (no per-lap tracking needed, so read directly).
            has_soc = api.read.engine.state_of_charge() > 0
            if has_soc:
                next(gen_battery)
                minfo.hybrid.regenKw    = api.read.engine.regen()
                minfo.hybrid.motorMap   = api.read.engine.motor_map()
                minfo.hybrid.motorMapMax = api.read.engine.motor_map_max()
