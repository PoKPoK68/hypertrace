"""
lmu_app/api/reader.py — Lecture shared memory LMU + mode mock.

Structure LMU (d'après lmu_data.py) :
  LMUObjectOut
    .generic.gameVersion        → int (0 si LMU pas lancé)
    .scoring.scoringInfo        → LMUScoringInfo
    .scoring.vehScoringInfo[i]  → LMUVehicleScoring
    .telemetry.playerVehicleIdx → index joueur
    .telemetry.playerHasVehicle → bool
    .telemetry.activeVehicles   → nombre de véhicules actifs
    .telemetry.telemInfo[i]     → LMUVehicleTelemetry
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

@dataclass
class VehicleData:
    speed_ms: float     = 0.0
    speed_kmh: float    = 0.0
    rpm: float          = 0.0
    rpm_max: float      = 9000.0
    gear: int           = 0          # -1=R, 0=N, 1+
    throttle: float     = 0.0        # 0-1
    brake: float        = 0.0        # 0-1
    clutch: float       = 0.0        # 0-1
    steering: float     = 0.0        # -1..1
    fuel: float         = 0.0        # litres
    fuel_capacity: float = 100.0
    virtual_energy: float = 0.0      # fraction 0-1  (mVirtualEnergy)
    state_of_charge: float = 0.0     # fraction 0-1  (mBatteryChargeFraction)
    delta_best: float   = 0.0        # s (mDeltaBest)
    lap_dist: float     = 0.0        # metres depuis start/finish
    in_pits: bool       = False


@dataclass
class TyreData:
    # indices : 0=FL, 1=FR, 2=RL, 3=RR
    temp_surface: list[float]  = field(default_factory=lambda: [0.0]*4)   # °C centre
    temp_inner: list[float]    = field(default_factory=lambda: [0.0]*4)   # °C intérieur
    temp_carcass: list[float]  = field(default_factory=lambda: [0.0]*4)   # °C carcasse
    wear: list[float]          = field(default_factory=lambda: [1.0]*4)   # 0-1 (1=neuf)
    pressure: list[float]      = field(default_factory=lambda: [0.0]*4)   # kPa
    brake_temp: list[float]    = field(default_factory=lambda: [0.0]*4)   # °C


@dataclass
class VehicleScoringEntry:
    """Un véhicule dans le classement."""
    slot_id: int          = 0
    driver_name: str      = ""
    vehicle_name: str     = ""
    place: int            = 0
    total_laps: int       = 0
    lap_dist: float       = 0.0
    best_lap: float       = -1.0
    last_lap: float       = -1.0
    time_behind_leader: float = 0.0
    time_behind_next: float   = 0.0
    time_into_lap: float      = 0.0   # estimated time into lap (s)
    estimated_lap_time: float = 0.0   # estimated lap time used for relative gap
    is_player: bool       = False
    in_pits: bool         = False
    control: int          = 0
    in_garage: bool       = False
    vehicle_class: str    = ""
    virtual_energy: float = 0.0   # 0-1 fraction; 0 if car has no VE
    fuel: float           = 0.0   # litres


@dataclass
class SessionData:
    track_name: str       = ""
    session_type: int     = 0    # 0-4=practice, 5-8=qual, 9=warmup, 10-13=race
    game_phase: int       = 0    # 5=green, 6=FCY, 7=stopped, 8=over
    max_laps: int         = 0
    track_length: float   = 0.0  # metres
    num_vehicles: int     = 0
    current_et: float     = 0.0  # elapsed time session (s)
    session_time_remaining: float = 0.0
    ambient_temp: float   = 20.0
    track_temp: float     = 30.0
    raining: float        = 0.0  # 0-1
    player_name: str      = ""
    vehicles: list[VehicleScoringEntry] = field(default_factory=list)


@dataclass
class LMUSnapshot:
    vehicle: VehicleData     = field(default_factory=VehicleData)
    tyres: TyreData          = field(default_factory=TyreData)
    session: SessionData     = field(default_factory=SessionData)
    is_on_track: bool        = False
    player_in_garage: bool   = False
    game_running: bool       = False
    timestamp: float         = 0.0


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseReader:
    def start(self): raise NotImplementedError
    def stop(self):  raise NotImplementedError
    def get(self) -> LMUSnapshot: raise NotImplementedError
    @property
    def is_connected(self) -> bool: raise NotImplementedError


# ---------------------------------------------------------------------------
# LMU Reader — shared memory native via SimInfo (lmu_data.py)
# ---------------------------------------------------------------------------

class LMUReader(BaseReader):
    """Lit la shared memory LMU via SimInfo de pyLMUSharedMemory."""

    def __init__(self, update_hz: int = 50):
        self._interval  = 1.0 / update_hz
        self._snapshot  = LMUSnapshot()
        self._lock      = threading.Lock()
        self._running   = False
        self._thread: threading.Thread | None = None
        self._sim: object | None = None
        self._connected = False

    def start(self):
        if self._running: return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, name="LMUReader", daemon=True)
        self._thread.start()
        logger.info("LMUReader started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._sim:
            try: self._sim.close()
            except Exception: pass
        logger.info("LMUReader stopped")

    def get(self) -> LMUSnapshot:
        with self._lock:
            return self._snapshot

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _loop(self):
        self._connect()
        while self._running:
            t0 = time.perf_counter()
            if self._sim:
                self._tick()
            else:
                # Réessayer la connexion toutes les 2s
                time.sleep(2.0)
                self._connect()
                continue
            elapsed = time.perf_counter() - t0
            s = self._interval - elapsed
            if s > 0:
                time.sleep(s)

    def _connect(self):
        try:
            from pyLMUSharedMemory.lmu_data import SimInfo  # type: ignore
            self._sim = SimInfo()
            self._connected = True
            logger.info("LMU shared memory connected")
        except Exception as e:
            logger.warning("Cannot open LMU shared memory: %s — LMU running?", e)
            self._connected = False
            self._sim = None

    def _tick(self):
        try:
            data = self._sim.LMUData

            # LMU pas lancé → gameVersion == 0
            if not data.generic.gameVersion:
                with self._lock:
                    self._snapshot = LMUSnapshot(game_running=False)
                return

            sc_info = data.scoring.scoringInfo
            telem   = data.telemetry

            snap = LMUSnapshot()
            snap.game_running = True
            snap.timestamp    = time.time()

            # --- Session ---
            s = snap.session
            s.track_name              = sc_info.mTrackName.decode(errors="replace").rstrip("\x00")
            s.session_type            = sc_info.mSession
            s.game_phase              = sc_info.mGamePhase
            s.max_laps                = sc_info.mMaxLaps
            s.track_length            = sc_info.mLapDist
            s.num_vehicles            = sc_info.mNumVehicles
            s.current_et              = sc_info.mCurrentET
            s.session_time_remaining  = sc_info.mSessionTimeRemaining
            s.ambient_temp            = sc_info.mAmbientTemp
            s.track_temp              = sc_info.mTrackTemp
            s.raining                 = sc_info.mRaining
            s.player_name             = sc_info.mPlayerName.decode(errors="replace").rstrip("\x00")

            # --- Véhicules scoring ---
            s.vehicles = []
            for i in range(min(sc_info.mNumVehicles, 104)):
                v = data.scoring.vehScoringInfo[i]
                try:
                    vclass = v.mVehicleClass.decode(errors="replace").rstrip("\x00")
                except AttributeError:
                    vclass = ""
                s.vehicles.append(VehicleScoringEntry(
                    slot_id            = v.mID,
                    driver_name        = v.mDriverName.decode(errors="replace").rstrip("\x00"),
                    vehicle_name       = v.mVehicleName.decode(errors="replace").rstrip("\x00"),
                    place              = v.mPlace,
                    total_laps         = v.mTotalLaps,
                    lap_dist           = v.mLapDist,
                    best_lap           = v.mBestLapTime,
                    last_lap           = v.mLastLapTime,
                    time_behind_leader = v.mTimeBehindLeader,
                    time_behind_next   = v.mTimeBehindNext,
                    time_into_lap      = v.mTimeIntoLap,
                    estimated_lap_time = v.mEstimatedLapTime,
                    is_player          = bool(v.mIsPlayer),
                    in_pits            = bool(v.mInPits),
                    in_garage          = bool(v.mInGarageStall),
                    control            = v.mControl,
                    vehicle_class      = vclass,
                ))

            # --- VE et fuel pour tous les véhicules depuis telemInfo ---
            ve_by_id:   dict[int, float] = {}
            fuel_by_id: dict[int, float] = {}
            try:
                for i in range(min(telem.activeVehicles, 104)):
                    t = telem.telemInfo[i]
                    ve_by_id[t.mID]   = float(t.mVirtualEnergy)
                    fuel_by_id[t.mID] = float(t.mFuel)
            except (AttributeError, IndexError):
                pass
            for entry in s.vehicles:
                entry.virtual_energy = ve_by_id.get(entry.slot_id, 0.0)
                entry.fuel           = fuel_by_id.get(entry.slot_id, 0.0)

            # --- Télémétrie joueur ---
            if not telem.playerHasVehicle:
                with self._lock:
                    self._snapshot = snap
                return

            idx  = telem.playerVehicleIdx
            tel  = telem.telemInfo[idx]

            # Vitesse locale (norme du vecteur mLocalVel)
            import math
            lv = tel.mLocalVel
            speed_ms  = math.sqrt(lv.x**2 + lv.y**2 + lv.z**2)

            v = snap.vehicle
            v.speed_ms       = speed_ms
            v.speed_kmh      = speed_ms * 3.6
            v.rpm            = tel.mEngineRPM
            v.rpm_max        = tel.mEngineMaxRPM
            v.gear           = tel.mGear
            v.throttle       = tel.mUnfilteredThrottle
            v.brake          = tel.mUnfilteredBrake
            v.clutch         = tel.mUnfilteredClutch
            v.steering       = tel.mUnfilteredSteering
            v.fuel           = tel.mFuel
            v.fuel_capacity  = tel.mFuelCapacity
            v.virtual_energy = tel.mVirtualEnergy
            v.state_of_charge= tel.mBatteryChargeFraction
            v.delta_best     = tel.mDeltaBest
            v.in_pits        = bool(tel.mSpeedLimiter)

            # Trouver le scoring joueur pour lap_dist et on_track
            player_sc = next((e for e in s.vehicles if e.is_player), None)
            if player_sc:
                v.lap_dist           = player_sc.lap_dist
                snap.is_on_track     = not player_sc.in_pits and sc_info.mInRealtime
                snap.player_in_garage = player_sc.in_garage

            # --- Pneus (0=FL,1=FR,2=RL,3=RR) ---
            t = snap.tyres
            for i in range(4):
                w = tel.mWheels[i]
                t.temp_surface[i]  = w.mTemperature[1] - 273.15   # Kelvin → °C (centre)
                t.temp_inner[i]    = w.mTemperature[0] - 273.15
                t.temp_carcass[i]  = w.mTireCarcassTemperature - 273.15
                t.wear[i]          = max(0., min(1., w.mWear))
                t.pressure[i]      = w.mPressure
                t.brake_temp[i]    = w.mBrakeTemp

            with self._lock:
                self._snapshot = snap

        except Exception as e:
            logger.error("LMUReader tick error: %s", e)


# ---------------------------------------------------------------------------
# DataReader — façade publique
# ---------------------------------------------------------------------------

class DataReader:
    def __init__(self, update_hz: int = 50):
        self._reader: BaseReader = LMUReader(update_hz)
        logger.info("DataReader: LMU")

    def start(self):  self._reader.start()
    def stop(self):   self._reader.stop()
    def get(self) -> LMUSnapshot: return self._reader.get()

    @property
    def is_connected(self) -> bool: return self._reader.is_connected
