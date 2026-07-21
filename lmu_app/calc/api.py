"""lmu_app/calc/api.py — Semantic shared-memory accessor.

Ported from TinyPedal's `tinypedal/adapter/lmu_reader.py` (s-victor/TinyPedal,
GPLv3), trimmed to the domains this app's widgets/modules actually read
(state, lap, session, timing, tyre, vehicle, engine fuel/energy, pedal
inputs). Anything LMU-specific not used here (brakes, electric-motor detail,
switches/assists, suspension, damage, car setup) was intentionally left out —
see the plan for the full rationale.

`index=None` means "the local player", resolved by `LMUInfo` via mID-matched
sync rather than trusting a raw index — see calc/lmu_connector.py.
"""
from __future__ import annotations

from functools import lru_cache
from math import isfinite

from pyLMUSharedMemory import lmu_enum

from lmu_app.calc.lmu_connector import LMUInfo

LMU_COMPOUND_TYPE = lmu_enum.enum_map(lmu_enum.LMUCompoundType)


def rmnan(value: float) -> float:
    """Convert inf/nan telemetry glitches to zero."""
    return value if isfinite(value) else 0.0


@lru_cache(maxsize=1024)
def _decode(raw: bytes) -> str:
    """Decode a ctypes char buffer to str, memoized (same names repeat every tick)."""
    return raw.decode(errors="replace").rstrip("\x00").strip()


class _Adapter:
    __slots__ = ("shmm",)

    def __init__(self, shmm: LMUInfo) -> None:
        self.shmm = shmm


class State(_Adapter):
    __slots__ = ()

    def active(self) -> bool:
        """Actually driving/on-track right now."""
        return self.shmm.isActive

    def paused(self) -> bool:
        """Game stopped producing new data (alt-tab, replay, loading)."""
        return self.shmm.isPaused

    def game_running(self) -> bool:
        return bool(self.shmm.lmuGeneric.gameVersion)


class Lap(_Adapter):
    __slots__ = ()

    def number(self, index: int | None = None) -> int:
        return self.shmm.lmuTeleVeh(index).mLapNumber

    def completed_laps(self, index: int | None = None) -> int:
        return self.shmm.lmuScorVeh(index).mTotalLaps

    def track_length(self) -> float:
        return rmnan(self.shmm.lmuScorInfo.mLapDist)

    def distance(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mLapDist)

    def progress(self, index: int | None = None) -> float:
        """Fraction (0-1) into the current lap, by distance."""
        length = rmnan(self.shmm.lmuScorInfo.mLapDist)
        if length < 1:
            return 0.0
        value = rmnan(self.shmm.lmuScorVeh(index).mLapDist) / length
        return max(0.0, min(1.0, value))

    def maximum(self) -> int:
        return self.shmm.lmuScorInfo.mMaxLaps

    def sector_index(self, index: int | None = None) -> int:
        """0 = S1, 1 = S2, 2 = S3 (LMU's raw mSector is 0=S3,1=S1,2=S2)."""
        sector = self.shmm.lmuScorVeh(index).mSector
        if sector == 0:
            return 2
        if sector == 1:
            return 0
        return 1

    def in_pit_lane(self, index: int | None = None) -> bool:
        """Physically in the pit lane — mCurrentSector's sign bit."""
        return int(self.shmm.lmuTeleVeh(index).mCurrentSector) < 0

    def behind_leader(self, index: int | None = None) -> int:
        return self.shmm.lmuScorVeh(index).mLapsBehindLeader

    def behind_next(self, index: int | None = None) -> int:
        return self.shmm.lmuScorVeh(index).mLapsBehindNext


class Session(_Adapter):
    __slots__ = ()

    def track_name(self) -> str:
        return _decode(self.shmm.lmuScorInfo.mTrackName)

    def identifier(self) -> tuple[int, int, int]:
        """(session_stamp, session_etime, session_tlaps) — canonical new-session signal."""
        scor = self.shmm.lmuScorInfo
        session_stamp = int(rmnan(scor.mEndET) * 100 + scor.mSession)
        session_etime = int(rmnan(scor.mCurrentET))
        session_tlaps = self.shmm.lmuScorVeh().mTotalLaps
        return session_stamp, session_etime, session_tlaps

    def elapsed(self) -> float:
        return rmnan(self.shmm.lmuScorInfo.mCurrentET)

    def remaining(self) -> float:
        scor = self.shmm.lmuScorInfo
        return max(0.0, rmnan(scor.mEndET - scor.mCurrentET))

    def session_type_raw(self) -> int:
        """Raw mSession (0-4 practice, 5-8 qualify, 9 warmup, 10-13 race)."""
        return self.shmm.lmuScorInfo.mSession

    def game_phase(self) -> int:
        return self.shmm.lmuScorInfo.mGamePhase

    def finish_type(self) -> int:
        """0 = time only, 1 = laps only, 2 = laps & time."""
        scor = self.shmm.lmuScorInfo
        if scor.mMaxLaps > 999999:
            return 0
        if scor.mEndET < 1:
            return 1
        return 2

    def in_race(self) -> bool:
        return self.shmm.lmuScorInfo.mSession > 9

    def pre_race(self) -> bool:
        return self.shmm.lmuScorInfo.mGamePhase <= 4

    def num_vehicles(self) -> int:
        return self.shmm.lmuScorInfo.mNumVehicles

    def track_temperature(self) -> float:
        return rmnan(self.shmm.lmuScorInfo.mTrackTemp)

    def ambient_temperature(self) -> float:
        return rmnan(self.shmm.lmuScorInfo.mAmbientTemp)

    def raininess(self) -> float:
        return rmnan(self.shmm.lmuScorInfo.mRaining)

    def wetness_average(self) -> float:
        return rmnan(self.shmm.lmuScorInfo.mAvgPathWetness)

    def cloud_coverage(self) -> int:
        return int(self.shmm.lmuScorInfo.mCloudCoverage)

    def player_name(self) -> str:
        return _decode(self.shmm.lmuScorInfo.mPlayerName)


class Timing(_Adapter):
    __slots__ = ()

    def start(self, index: int | None = None) -> float:
        """Current lap start time (seconds) — mLapStartET."""
        return rmnan(self.shmm.lmuTeleVeh(index).mLapStartET)

    def current_laptime(self, index: int | None = None) -> float:
        tele_veh = self.shmm.lmuTeleVeh(index)
        return rmnan(tele_veh.mElapsedTime - tele_veh.mLapStartET)

    def last_laptime(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mLastLapTime)

    def best_laptime(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mBestLapTime)

    def estimated_laptime(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mEstimatedLapTime)

    def estimated_time_into(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mTimeIntoLap)

    def behind_leader(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mTimeBehindLeader)

    def behind_next(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mTimeBehindNext)

    def current_sector1(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mCurSector1)

    def current_sector2(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mCurSector2)

    def last_sector1(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mLastSector1)

    def last_sector2(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mLastSector2)

    def best_sector1(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mBestSector1)

    def best_sector2(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuScorVeh(index).mBestSector2)

    def elapsed(self, index: int | None = None) -> float:
        """Current lap elapsed time (seconds) — for delta-vs-distance interpolation."""
        return rmnan(self.shmm.lmuTeleVeh(index).mElapsedTime)


class Tyre(_Adapter):
    __slots__ = ()

    def compound_name(self, index: int | None = None) -> tuple[str, str, str, str]:
        wheel_data = self.shmm.lmuTeleVeh(index).mWheels
        return (
            LMU_COMPOUND_TYPE(wheel_data[0].mCompoundType),
            LMU_COMPOUND_TYPE(wheel_data[1].mCompoundType),
            LMU_COMPOUND_TYPE(wheel_data[2].mCompoundType),
            LMU_COMPOUND_TYPE(wheel_data[3].mCompoundType),
        )

    def surface_temperature(self, index: int | None = None) -> tuple[float, float, float, float]:
        """Center surface temperature (Celsius) — mTemperature[1]."""
        wheel_data = self.shmm.lmuTeleVeh(index).mWheels
        return tuple(rmnan(w.mTemperature[1]) - 273.15 for w in wheel_data)

    def inner_temperature(self, index: int | None = None) -> tuple[float, float, float, float]:
        wheel_data = self.shmm.lmuTeleVeh(index).mWheels
        return tuple(rmnan(w.mTemperature[0]) - 273.15 for w in wheel_data)

    def carcass_temperature(self, index: int | None = None) -> tuple[float, float, float, float]:
        wheel_data = self.shmm.lmuTeleVeh(index).mWheels
        return tuple(rmnan(w.mTireCarcassTemperature) - 273.15 for w in wheel_data)

    def optimal_temperature(self, index: int | None = None) -> tuple[float, float, float, float]:
        """Documented as Celsius; guard in case a build reports Kelvin."""
        wheel_data = self.shmm.lmuTeleVeh(index).mWheels
        out = []
        for w in wheel_data:
            t = rmnan(float(w.mOptimalTemp))
            out.append(t - 273.15 if t > 200.0 else t)
        return tuple(out)

    def pressure(self, index: int | None = None) -> tuple[float, float, float, float]:
        wheel_data = self.shmm.lmuTeleVeh(index).mWheels
        return tuple(rmnan(w.mPressure) for w in wheel_data)

    def wear(self, index: int | None = None) -> tuple[float, float, float, float]:
        """Tyre wear (fraction, 1.0 = new)."""
        wheel_data = self.shmm.lmuTeleVeh(index).mWheels
        return tuple(max(0.0, min(1.0, rmnan(w.mWear))) for w in wheel_data)

    def brake_temperature(self, index: int | None = None) -> tuple[float, float, float, float]:
        wheel_data = self.shmm.lmuTeleVeh(index).mWheels
        return tuple(rmnan(w.mBrakeTemp) for w in wheel_data)


class Vehicle(_Adapter):
    __slots__ = ()

    def player_index(self) -> int:
        return self.shmm.playerIndex

    def is_player(self, index: int | None = None) -> bool:
        return bool(self.shmm.lmuScorVeh(index).mIsPlayer)

    def slot_id(self, index: int | None = None) -> int:
        return self.shmm.lmuScorVeh(index).mID

    def driver_name(self, index: int | None = None) -> str:
        return _decode(self.shmm.lmuScorVeh(index).mDriverName)

    def vehicle_name(self, index: int | None = None) -> str:
        return _decode(self.shmm.lmuScorVeh(index).mVehicleName)

    def vehicle_model(self, index: int | None = None) -> str:
        return _decode(self.shmm.lmuTeleVeh(index).mVehicleModel)

    def class_name(self, index: int | None = None) -> str:
        return _decode(self.shmm.lmuScorVeh(index).mVehicleClass)

    def total_vehicles(self) -> int:
        return self.shmm.lmuScorInfo.mNumVehicles

    def place(self, index: int | None = None) -> int:
        return self.shmm.lmuScorVeh(index).mPlace

    def total_laps(self, index: int | None = None) -> int:
        return self.shmm.lmuScorVeh(index).mTotalLaps

    def in_pits(self, index: int | None = None) -> bool:
        return bool(self.shmm.lmuScorVeh(index).mInPits)

    def in_garage(self, index: int | None = None) -> bool:
        return bool(self.shmm.lmuScorVeh(index).mInGarageStall)

    def pit_state(self, index: int | None = None) -> int:
        """0=none, 1=request, 2=entering, 3=stopped, 4=exiting, 5=undocumented."""
        return int(getattr(self.shmm.lmuScorVeh(index), "mPitState", 0))

    def control(self, index: int | None = None) -> int:
        return self.shmm.lmuScorVeh(index).mControl

    def finish_state(self, index: int | None = None) -> int:
        """0=none, 1=finished, 2=DNF, 3=DQ."""
        return int(getattr(self.shmm.lmuScorVeh(index), "mFinishStatus", 0))

    def speed(self, index: int | None = None) -> float:
        """Speed (m/s) — magnitude of the local velocity vector."""
        v = self.shmm.lmuTeleVeh(index).mLocalVel
        return rmnan((v.x ** 2 + v.y ** 2 + v.z ** 2) ** 0.5)


class Engine(_Adapter):
    __slots__ = ()

    def rpm(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuTeleVeh(index).mEngineRPM)

    def rpm_max(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuTeleVeh(index).mEngineMaxRPM)

    def gear(self, index: int | None = None) -> int:
        return self.shmm.lmuTeleVeh(index).mGear

    def fuel(self, index: int | None = None) -> float:
        """Remaining fuel (liters)."""
        return rmnan(self.shmm.lmuTeleVeh(index).mFuel)

    def tank_capacity(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuTeleVeh(index).mFuelCapacity)

    def virtual_energy(self, index: int | None = None) -> float:
        """Remaining virtual energy (fraction 0-1); 0 if the car has none."""
        return rmnan(self.shmm.lmuTeleVeh(index).mVirtualEnergy)

    def battery_charge(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuTeleVeh(index).mBatteryChargeFraction)

    def delta_best(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuTeleVeh(index).mDeltaBest)

    def speed_limiter_active(self, index: int | None = None) -> bool:
        """Pit lane speed limiter engaged — used as an additional in_pits signal."""
        return bool(self.shmm.lmuTeleVeh(index).mSpeedLimiter)


class Inputs(_Adapter):
    __slots__ = ()

    def throttle(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuTeleVeh(index).mUnfilteredThrottle)

    def brake(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuTeleVeh(index).mUnfilteredBrake)

    def clutch(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuTeleVeh(index).mUnfilteredClutch)

    def steering(self, index: int | None = None) -> float:
        return rmnan(self.shmm.lmuTeleVeh(index).mUnfilteredSteering)

    def local_velocity(self, index: int | None = None) -> tuple[float, float, float]:
        v = self.shmm.lmuTeleVeh(index).mLocalVel
        return rmnan(v.x), rmnan(v.y), rmnan(v.z)


class SimAPI:
    """Top-level accessor — `api.read.<domain>.<method>()`."""

    __slots__ = ("_info", "read", "raw")

    class _Read:
        __slots__ = ("state", "lap", "session", "timing", "tyre", "vehicle", "engine", "inputs")

        def __init__(self, shmm: LMUInfo) -> None:
            self.state   = State(shmm)
            self.lap     = Lap(shmm)
            self.session = Session(shmm)
            self.timing  = Timing(shmm)
            self.tyre    = Tyre(shmm)
            self.vehicle = Vehicle(shmm)
            self.engine  = Engine(shmm)
            self.inputs  = Inputs(shmm)

    def __init__(self) -> None:
        self._info = LMUInfo()
        self.read = self._Read(self._info)
        self.raw = self._info   # direct struct access — see module_vehicles.py's per-car scan

    def start(self) -> None:
        self._info.start()

    def stop(self) -> None:
        self._info.stop()


api = SimAPI()
