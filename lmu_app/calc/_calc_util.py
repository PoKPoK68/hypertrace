"""lmu_app/calc/_calc_util.py — Small numeric/session helpers shared by calc modules.

Ported from TinyPedal's `tinypedal/calculation.py` and `tinypedal/validator.py`
(s-victor/TinyPedal, GPLv3) — only the handful of functions our modules use.
"""
from __future__ import annotations

from typing import Sequence

MAX_SECONDS = 99999.0
DELTA_ZERO: tuple[float, float] = (0.0, 0.0)
DELTA_DEFAULT: tuple[tuple[float, float], ...] = (DELTA_ZERO,)


def linear_interp(x: float, x1: float, y1: float, x2: float, y2: float) -> float:
    x_diff = x2 - x1
    if x_diff:
        return y1 + (x - x1) * (y2 - y1) / x_diff
    return y1


def binary_search_higher_column(
    data: Sequence[Sequence], target: float, start: int, end: int, column: int = 0
) -> int:
    """Nearest-higher index from an ordered list, comparing on `column`."""
    while start < end:
        center = (start + end) // 2
        if target == data[center][column]:
            return center
        if target > data[center][column]:
            start = center + 1
        else:
            end = center
    return end


def delta_telemetry(
    dataset: Sequence[Sequence[float]], position: float, target: float,
    condition: bool = True, position_column: int = 0, target_column: int = 1,
) -> float:
    """target - reference value interpolated at `position` from `dataset`."""
    if not condition:
        return 0.0
    index_higher = binary_search_higher_column(dataset, position, 0, len(dataset) - 1, position_column)
    if index_higher > 0:
        index_lower = index_higher - 1
        return target - linear_interp(
            position,
            dataset[index_lower][position_column], dataset[index_lower][target_column],
            dataset[index_higher][position_column], dataset[index_higher][target_column],
        )
    return 0.0


def exp_mov_avg(factor: float, ema_last: float, source: float) -> float:
    return ema_last + factor * (source - ema_last)


def ema_factor(samples: int, min_samples: int = 1) -> float:
    return 2 / (max(samples, min_samples) + 1)


def is_same_session(
    session_id: tuple[int, int, int], last_session_id: tuple[int, int, int],
) -> bool:
    """True if `session_id` is a continuation of `last_session_id` (not a reset).

    session_id = (session_stamp, session_etime, session_tlaps) from
    api.read.session.identifier(). session_stamp bakes in session length +
    type, so a monotonicity break on elapsed-time or completed-laps (or a
    changed stamp) means the session was reset/restarted/changed.
    """
    return (
        last_session_id[0] == session_id[0] and
        last_session_id[1] <= session_id[1] and
        last_session_id[2] <= session_id[2]
    )


def valid_delta_raw(dataset: list[tuple[float, float]], final: float, column: int) -> bool:
    """Drop trailing rows whose value exceeds `final`; False if nothing usable is left."""
    try:
        if len(dataset) <= 1:
            return False
        while dataset[-1][column] > final:
            dataset.pop()
            if not dataset:
                return False
        return True
    except (AttributeError, TypeError, IndexError):
        return False


def min_nonzero(data: Sequence[float]) -> float:
    return min((v for v in data if v > 0), default=0.0)


# --- Fuel/energy consumption formulas (ported from calculation.py) --------

def end_lap_consumption(consumption: float, consumption_delta: float, condition: bool) -> float:
    return consumption + consumption_delta if condition else consumption


def lap_type_full_laps_remain(laps_total: int, laps_finished: int) -> int:
    return laps_total - laps_finished


def lap_type_laps_remain(full_laps_remain: int, lap_into: float) -> float:
    return full_laps_remain - lap_into


def end_timer_laps_remain(lap_into: float, laptime_last: float, seconds_remain: float) -> float:
    if laptime_last:
        if seconds_remain <= 0:
            return lap_into
        return seconds_remain / laptime_last + lap_into
    return 0.0


def time_type_laps_remain(full_laps_remain: int, lap_into: float) -> float:
    return max(full_laps_remain - lap_into, 0)


def end_stint_fuel(fuel_in_tank: float, consumption_into_lap: float, consumption: float) -> float:
    if consumption:
        fuel_at_lap_start = fuel_in_tank + consumption_into_lap
        return fuel_at_lap_start / consumption % 1 * consumption
    return 0.0


def end_stint_laps(fuel_in_tank: float, consumption: float) -> float:
    if consumption:
        return fuel_in_tank / consumption
    return 0.0


def end_stint_minutes(laps_runnable: float, laptime_last: float) -> float:
    return laps_runnable * laptime_last / 60


def end_lap_empty_capacity(capacity_total: float, fuel_in_tank: float, consumption: float) -> float:
    return capacity_total - fuel_in_tank + consumption


def end_stint_pit_counts(fuel_needed: float, capacity_total: float) -> float:
    if capacity_total:
        return fuel_needed / capacity_total
    return 0.0


def fuel_to_energy_ratio(fuel: float, energy: float) -> float:
    if fuel and energy:
        return fuel / energy
    return 0.0
