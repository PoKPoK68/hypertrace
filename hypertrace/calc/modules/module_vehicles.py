"""hypertrace/calc/modules/module_vehicles.py — Standings/relative dataset.

Not a full adaptation of the reference implementation's vehicles module —
that one computes gaps manually (needed for sims whose shared memory doesn't
provide them). LMU's
shared memory already publishes `mTimeBehindLeader`/`mTimeBehindNext` and
their lap-count equivalents directly, per car, so this module is mostly a
straight reorganization of the scoring+telemetry arrays into `minfo.vehicles`
— the same shape our old `reader.py:_scan_vehicles()` built, just sourced
through `calc/api.py` instead of raw struct field access sprinkled through
the widget-facing reader.

Runs the heavy full-field scan throttled to ~10 Hz (`active_interval`) —
standings/relative overlays sample at 5-10 Hz themselves, so finer-grained
scanning would be wasted work. Sector-time fields (cur/last/best S1/S2) come
straight from the scoring struct per car — no REST API involved. This build
has no REST integration at all (see CLAUDE.md); the handful of fields shared
memory genuinely doesn't expose (weather forecast) simply stay at default.
"""
from __future__ import annotations

from hypertrace.calc.api import api
from hypertrace.calc.module_info import VehicleData, minfo
from hypertrace.calc.modules._base import DataModule
from hypertrace.calc.realtime_state import realtime_state


def _update_session_info() -> None:
    """Coarse session/weather fields — cheap enough to refresh every tick
    alongside the vehicle scan rather than warrant its own module/thread."""
    s = minfo.session
    r = api.read.session
    s.trackName       = r.track_name()
    s.sessionType      = r.session_type_raw()
    s.gamePhase        = r.game_phase()
    s.maxLaps          = api.read.lap.maximum()
    s.trackLength       = api.read.lap.track_length()
    s.numVehicles       = r.num_vehicles()
    s.currentEt         = r.elapsed()
    s.timeRemaining     = r.remaining()
    s.ambientTemp        = r.ambient_temperature()
    s.trackTemp          = r.track_temperature()
    s.raining            = r.raininess()
    s.avgPathWetness      = r.wetness_average()
    s.playerName          = r.player_name()
    s.weatherSky          = r.cloud_coverage()

_COMPOUND_TYPES = {0: "Soft", 1: "Medium", 2: "Hard", 3: "Wet"}


def _decode(raw: bytes) -> str:
    return raw.decode(errors="replace").rstrip("\x00").strip()


def _scan() -> list[VehicleData]:
    scor_info = api.raw.lmuScorInfo
    n = min(scor_info.mNumVehicles, 104)

    vehicles: list[VehicleData] = []
    for i in range(n):
        v = api.raw.lmuScorVeh(i)
        try:
            vclass = _decode(v.mVehicleClass)
        except AttributeError:
            vclass = ""
        vehicles.append(VehicleData(
            slot_id             = v.mID,
            driver_name         = _decode(v.mDriverName),
            vehicle_name        = _decode(v.mVehicleName),
            vehicle_class       = vclass,
            place               = v.mPlace,
            total_laps          = v.mTotalLaps,
            lap_dist            = v.mLapDist,
            best_lap            = v.mBestLapTime,
            last_lap            = v.mLastLapTime,
            time_behind_leader  = v.mTimeBehindLeader,
            time_behind_next    = v.mTimeBehindNext,
            laps_behind_leader  = v.mLapsBehindLeader,
            laps_behind_next    = v.mLapsBehindNext,
            time_into_lap       = v.mTimeIntoLap,
            estimated_lap_time  = v.mEstimatedLapTime,
            is_player           = bool(v.mIsPlayer),
            in_pits             = bool(v.mInPits),
            pit_state           = int(getattr(v, "mPitState", 0)),
            in_garage           = bool(v.mInGarageStall),
            control             = v.mControl,
            finish_status       = getattr(v, "mFinishStatus", 0),
            cur_sector1         = v.mCurSector1,
            cur_sector2         = v.mCurSector2,
            last_sector1        = v.mLastSector1,
            last_sector2        = v.mLastSector2,
            best_sector1        = v.mBestSector1,
            best_sector2        = v.mBestSector2,
        ))

    # VE / fuel / compounds / pit-lane sign bit — telemetry array, matched by mID
    # (telemetry index isn't guaranteed to line up with the scoring index).
    ve_by_id: dict[int, float] = {}
    fuel_by_id: dict[int, float] = {}
    compound_by_id: dict[int, list[str]] = {}
    pitlane_by_id: dict[int, bool] = {}
    model_by_id: dict[int, str] = {}
    tele = api.raw.lmuTelemetry
    try:
        for i in range(min(tele.activeVehicles, 104)):
            t = tele.telemInfo[i]
            sid = t.mID
            ve_by_id[sid]   = float(t.mVirtualEnergy)
            fuel_by_id[sid] = float(t.mFuel)
            pitlane_by_id[sid] = int(t.mCurrentSector) < 0
            try:
                comps = [_COMPOUND_TYPES.get(int(t.mWheels[wi].mCompoundType), "") for wi in range(4)]
                if any(comps):
                    compound_by_id[sid] = comps
            except (AttributeError, IndexError, TypeError):
                pass
            try:
                m = _decode(t.mVehicleModel)
                if m:
                    model_by_id[sid] = m
            except AttributeError:
                pass
    except (AttributeError, IndexError):
        pass

    for entry in vehicles:
        entry.virtual_energy = ve_by_id.get(entry.slot_id, 0.0)
        entry.fuel            = fuel_by_id.get(entry.slot_id, 0.0)
        entry.pitlane          = pitlane_by_id.get(entry.slot_id, False)
        if entry.slot_id in compound_by_id:
            entry.compounds = compound_by_id[entry.slot_id]
        # mVehicleModel (brand + model, e.g. "Ferrari 499P") is what the logo
        # lookup matches on — mVehicleName from the scoring struct is a
        # different, more generic name that doesn't match the logo table.
        if entry.slot_id in model_by_id:
            entry.vehicle_name = model_by_id[entry.slot_id]

    return vehicles


class Realtime(DataModule):
    def __init__(self) -> None:
        super().__init__("vehicles", active_interval=0.1, idle_interval=0.5)

    def update_data(self) -> None:
        _event_wait = self._event.wait

        while not _event_wait(self.active_interval if realtime_state.active else self.idle_interval):
            if not realtime_state.live:
                continue

            data = _scan()
            minfo.vehicles.dataSet = data
            minfo.vehicles.totalVehicles = len(data)
            player = next((v for v in data if v.is_player), None)
            minfo.vehicles.playerSlotId = player.slot_id if player else -1
            minfo.vehicles.playerInGarage = player.in_garage if player else False
            _update_session_info()
