"""hypertrace/calc/modules/module_delta.py — Best/last/session delta.

Simplified port of TinyPedal's `tinypedal/module/module_delta.py`
(s-victor/TinyPedal, GPLv3). Two deliberate simplifications from the original:
  - Position along the lap comes straight from `api.read.lap.distance()`
    (mLapDist) instead of TinyPedal's GPS-position-sync smoothing generator —
    our tick rate is high enough that raw distance doesn't need it.
  - "All-time best" delta lives in memory for this run only, not persisted to
    disk per track/class combo — this app never had that feature before, so
    it's not a regression, just not carrying it over.

Fixes, by construction, a bug the old hand-rolled code had: comparing
`last_lap < best_lap` for "did I just set a new best" could (almost) never be
true, since best_lap is defined as the minimum including the lap that just
finished. Here, delta math naturally handles the equal-case correctly.
"""
from __future__ import annotations

from functools import partial

from hypertrace.calc._calc_util import (
    DELTA_DEFAULT, DELTA_ZERO, MAX_SECONDS,
    delta_telemetry, ema_factor, exp_mov_avg, is_same_session, valid_delta_raw,
)
from hypertrace.calc.api import api
from hypertrace.calc.module_info import minfo
from hypertrace.calc.modules._base import DataModule
from hypertrace.calc.realtime_state import realtime_state

_EMA_SAMPLES = 15   # smoothing window; no per-user setting for this, unlike TinyPedal


class Realtime(DataModule):
    def __init__(self) -> None:
        super().__init__("delta", active_interval=0.05, idle_interval=0.5)

    def update_data(self) -> None:
        _event_wait = self._event.wait
        reset = False
        interval = self.idle_interval
        output = minfo.delta

        last_session_id = (0, -1, -1)
        delta_array_best = DELTA_DEFAULT      # this run's best lap trace
        delta_array_session = DELTA_DEFAULT
        laptime_best = MAX_SECONDS
        laptime_session_best = MAX_SECONDS

        calc_ema = partial(exp_mov_avg, ema_factor(_EMA_SAMPLES))

        delta_array_raw: list[tuple[float, float]] = [DELTA_ZERO]
        delta_array_last = DELTA_DEFAULT
        delta_ema_best = delta_ema_last = delta_ema_session = 0.0
        laptime_curr = laptime_last = 0.0
        last_lap_stime = float("inf")
        pos_last = pos_recorded = 0.0
        recording = False
        validating = 0.0

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
                recording = False
                validating = 0.0
                delta_array_raw = [DELTA_ZERO]
                delta_array_last = DELTA_DEFAULT
                delta_ema_best = delta_ema_last = delta_ema_session = 0.0
                laptime_curr = laptime_last = 0.0
                last_lap_stime = float("inf")
                pos_last = pos_recorded = 0.0

                session_id = api.read.session.identifier()
                if not is_same_session(session_id, last_session_id):
                    delta_array_best = DELTA_DEFAULT
                    delta_array_session = DELTA_DEFAULT
                    laptime_best = MAX_SECONDS
                    laptime_session_best = MAX_SECONDS
                last_session_id = session_id

            lap_stime = api.read.timing.start()
            laptime_curr = max(api.read.timing.current_laptime(), 0.0)
            laptime_valid = api.read.timing.last_laptime()
            pos_curr = api.read.lap.distance()

            # Lap start/finish detection: mLapStartET changing means a new lap began.
            if lap_stime > last_lap_stime:
                laptime_last = lap_stime - last_lap_stime
                if valid_delta_raw(delta_array_raw, laptime_last, 1):
                    delta_array_raw.append((round(pos_last + 10, 6), round(laptime_last, 6)))
                    delta_array_last = tuple(delta_array_raw)
                    validating = api.read.timing.elapsed()
                delta_array_raw = [DELTA_ZERO]
                pos_last = pos_recorded = pos_curr
                recording = laptime_curr < 1
            last_lap_stime = lap_stime

            # Guard against a garage/pit teleport being read as a huge lap-start jump.
            if 0 < laptime_curr < 1 and pos_curr > 300:
                pos_last = pos_recorded = pos_curr = 0.0

            if 0 <= pos_curr != pos_last:
                if recording and pos_curr - pos_recorded >= 5:   # min sample spacing, meters
                    delta_array_raw.append((round(pos_curr, 6), round(laptime_curr, 6)))
                    pos_recorded = pos_curr
                pos_last = pos_curr

            # ~1s after crossing the line, confirm the just-finished lap and file it.
            if validating:
                timer = api.read.timing.elapsed() - validating
                if timer > 10:
                    validating = 0.0
                elif timer > 1 and laptime_valid > 0 and abs(laptime_valid - laptime_last) < 0.001:
                    if laptime_best > laptime_last:
                        laptime_best = laptime_last
                        delta_array_best = delta_array_last
                    if laptime_session_best > laptime_last:
                        laptime_session_best = laptime_last
                        delta_array_session = delta_array_last
                    validating = 0.0

            delay_update = laptime_curr > 0.3
            delta_ema_best = calc_ema(delta_ema_best, delta_telemetry(
                delta_array_best, pos_curr, laptime_curr, delay_update))
            delta_ema_last = calc_ema(delta_ema_last, delta_telemetry(
                delta_array_last, pos_curr, laptime_curr, delay_update))
            delta_ema_session = calc_ema(delta_ema_session, delta_telemetry(
                delta_array_session, pos_curr, laptime_curr, delay_update))

            output.deltaBest    = delta_ema_best
            output.deltaLast    = delta_ema_last
            output.deltaSession = delta_ema_session
            output.isValidLap   = laptime_valid > 0
            output.lapTimeCurrent   = laptime_curr
            output.lapTimeLast      = laptime_last
            output.lapTimeBest      = laptime_best if laptime_best < MAX_SECONDS else 0.0
            output.lapTimeSession   = laptime_session_best if laptime_session_best < MAX_SECONDS else 0.0
            output.lapTimeEstimated = api.read.timing.estimated_laptime()
            output.deltaBestRaw     = api.read.engine.delta_best()
