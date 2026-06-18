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
    finish_status: int    = 0     # 0=none, 1=finished, 2=DNF, 3=DNQ, 4=DQ
    car_number: str   = ""
    team_name:  str   = ""
    time_behind_class_leader: float = 0.0
    laps_behind_class_leader: int   = 0


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
    ambient_temp: float      = 20.0
    track_temp: float        = 30.0
    raining: float           = 0.0  # 0-1
    avg_path_wetness: float  = 0.0  # 0-1
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
    session_active: bool     = False   # True only when a session is actually running
    viewed_slot_id: int      = -1      # slot_id of the currently focused/viewed driver
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

_REST_BASE = "http://localhost:6397"
_REST_FOCUS_INTERVAL = 0.2   # poll focus every 200 ms (5 Hz)


class LMUReader(BaseReader):
    """Lit la shared memory LMU via SimInfo de pyLMUSharedMemory."""

    def __init__(self, update_hz: int = 50):
        self._interval  = 1.0 / update_hz
        self._snapshot  = LMUSnapshot()
        self._lock      = threading.Lock()
        self._running   = False
        self._thread: threading.Thread | None = None
        self._rest_thread: threading.Thread | None = None
        self._sim: object | None = None
        self._connected = False
        self._rest_focus: int = -1   # slotID from REST API; -1 = unknown
        self._rest_data: dict[int, dict] = {}   # slot_id → REST standings entry

    def start(self):
        if self._running: return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, name="LMUReader", daemon=True)
        self._thread.start()
        self._rest_thread = threading.Thread(target=self._rest_loop, name="LMURestFocus", daemon=True)
        self._rest_thread.start()
        logger.info("LMUReader started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._sim:
            try: self._sim.close()
            except Exception: pass
        logger.info("LMUReader stopped")

    def _rest_loop(self):
        """Poll REST API: focus at 5 Hz, standings at 3 Hz."""
        import urllib.request as _ur
        import json as _json
        _last_st = 0.0
        while self._running:
            now = time.monotonic()
            try:
                with _ur.urlopen(f"{_REST_BASE}/rest/watch/focus", timeout=1) as r:
                    slot = int(r.read().decode().strip())
                    self._rest_focus = slot if slot >= 0 else -1
            except Exception:
                pass
            if now - _last_st >= 0.333:
                try:
                    with _ur.urlopen(f"{_REST_BASE}/rest/watch/standings", timeout=2) as r:
                        data = _json.loads(r.read())
                        self._rest_data = {int(item["slotID"]): item for item in data}
                        _last_st = now
                except Exception:
                    pass
            time.sleep(_REST_FOCUS_INTERVAL)

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
            s.avg_path_wetness        = sc_info.mAvgPathWetness
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
                    finish_status      = getattr(v, 'mFinishStatus', 0),
                ))

            # Merge REST standings data (car number, team, class gap)
            for entry in s.vehicles:
                rd = self._rest_data.get(entry.slot_id)
                if rd:
                    entry.car_number = str(rd.get("carNumber", ""))
                    entry.team_name  = rd.get("fullTeamName", "")
                    entry.time_behind_class_leader = float(rd.get("timeBehindClassLeader", 0.0))
                    entry.laps_behind_class_leader = int(rd.get("lapsBehindClassLeader", 0))

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

            # --- Session active + viewed vehicle ---
            player_sc = next((e for e in s.vehicles if e.is_player), None)
            snap.session_active = s.num_vehicles > 0 and s.current_et > 0
            if player_sc:
                snap.player_in_garage = player_sc.in_garage
                snap.viewed_slot_id   = player_sc.slot_id  # fallback: own car

            # REST API gives us the true focused slotID from /rest/watch/focus
            rest_slot = self._rest_focus
            if rest_slot > 0 and any(v.slot_id == rest_slot for v in s.vehicles):
                snap.viewed_slot_id = rest_slot

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

            if player_sc:
                v.lap_dist       = player_sc.lap_dist
                snap.is_on_track = snap.session_active

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


def lmu_rest_put(path: str, rest_base: str = _REST_BASE) -> bool:
    """Send a PUT to the LMU REST API. Returns True on success."""
    import urllib.request as _ur
    try:
        req = _ur.Request(f"{rest_base}{path}", method="PUT")
        _ur.urlopen(req, timeout=1)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# MockReader — données factices pour tester visuellement sans LMU
# ---------------------------------------------------------------------------

class MockReader(BaseReader):
    """Fake reader for visual testing — no LMU required.

    Hamilton (slot 4) cycles through badge states every few seconds:
      Phase 0: normal on track
      Phase 1: enters pits  → PIT badge
      Phase 2: exits pits   → OUT badge (widget detects transition)
      Phase 3: lap complete → L5 badge (OUT cleared)
    then wraps back to 0.
    """

    _CYCLE_S = 6.0
    _LAP     = 90.0

    def __init__(self):
        self._phase   = 0
        self._running = False
        self._lock    = threading.Lock()
        self._snapshot = self._build(0)
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="MockReader", daemon=True)
        self._thread.start()
        logger.info("MockReader started — cycling HAMILTON every %.0fs", self._CYCLE_S)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("MockReader stopped")

    @property
    def is_connected(self) -> bool:
        return True

    def get(self) -> LMUSnapshot:
        with self._lock:
            return self._snapshot

    def _loop(self):
        _names = ["normal", "PIT (enters pits)", "OUT (outlap)", "L5 (lap done)"]
        while self._running:
            time.sleep(self._CYCLE_S)
            self._phase = (self._phase + 1) % 4
            snap = self._build(self._phase)
            logger.info("MockReader → phase %d: %s", self._phase, _names[self._phase])
            with self._lock:
                self._snapshot = snap

    def _build(self, phase: int) -> LMUSnapshot:
        LAP = self._LAP
        ham_in_pits = (phase == 1)
        ham_laps    = 7 if phase <= 2 else 8   # 8 on phase 3 → clears OUT → L7 badge

        P = 45.0  # player time_into_lap
        # (slot, place, name, cls, til, is_player, in_pits, in_garage, laps, best_lap, gap)
        _drivers = [
            (0,  1,  "Max VERSTAPPEN",  "HYPERCAR", P+9.1,  False, False,       False, 7, LAP+0.00, 0.000),
            (1,  2,  "Charles LECLERC", "HYPERCAR", P+5.8,  False, False,       False, 7, LAP+0.21, 1.823),
            (2,  3,  "Lando NORRIS",    "HYPERCAR", P,      True,  False,       False, 7, LAP+0.45, 3.451),
            (3,  4,  "Carlos SAINZ",    "HYPERCAR", P+3.2,  False, False,       False, 7, LAP+0.81, 5.102),
            (4,  5,  "Lewis HAMILTON",  "HYPERCAR", P-1.8,  False, ham_in_pits, False, ham_laps,   LAP+1.05, 123.456),
            (5,  6,  "George RUSSELL",  "HYPERCAR", P+1.5,  False, False,       False, 6, LAP+1.40, 8.234),
            (6,  7,  "Fernando ALONSO", "HYPERCAR", P-4.3,  False, False,       False, 6, LAP+1.72, 10.560),  # -1L
            (7,  8,  "Oscar PIASTRI",   "HYPERCAR", P-8.0,  False, False,       False, 6, LAP+2.10, 12.100),  # -1L
            (8,  9,  "Sergio PEREZ",    "HYPERCAR", P-12.5, False, False,       False, 5, LAP+2.50, 14.220),  # -2L
            (9,  10, "Zhou GUANYU",     "HYPERCAR", 0.0,    False, False,       True,  5, LAP+3.10, 18.400),  # garage
        ]

        vehicles = [
            VehicleScoringEntry(
                slot_id=slot, driver_name=name, place=place, total_laps=laps,
                lap_dist=til * 13626.0 / LAP if til > 0 else 0.0,
                best_lap=best, last_lap=best + 0.12,
                time_behind_leader=gap, time_behind_next=1.8 if place > 1 else 0.0,
                time_into_lap=til, estimated_lap_time=LAP,
                is_player=is_p, in_pits=in_pits, in_garage=in_gar,
                vehicle_class=cls, fuel=50.0 - gap * 0.5, virtual_energy=0.0,
            )
            for slot, place, name, cls, til, is_p, in_pits, in_gar, laps, best, gap in _drivers
        ]

        session = SessionData(
            track_name="Le Mans", session_type=10, game_phase=5,
            max_laps=0, track_length=13626.0, num_vehicles=len(vehicles),
            current_et=3600.0 + phase * self._CYCLE_S,
            session_time_remaining=10800.0 - phase * self._CYCLE_S,
            ambient_temp=24.0, track_temp=38.0,
            vehicles=vehicles,
        )

        player = next((v for v in vehicles if v.is_player), None)
        return LMUSnapshot(
            vehicle=VehicleData(
                speed_kmh=285.0, rpm=9200.0, rpm_max=10500.0,
                gear=7, throttle=0.95, fuel=50.0,
            ),
            session=session,
            is_on_track=True, game_running=True, session_active=True,
            viewed_slot_id=player.slot_id if player else -1,
            timestamp=time.time(),
        )


# ---------------------------------------------------------------------------
# DataReader — façade publique
# ---------------------------------------------------------------------------

class DataReader:
    def __init__(self, update_hz: int = 50, mock: bool = False):
        if mock:
            self._reader: BaseReader = MockReader()
            logger.info("DataReader: Mock")
        else:
            self._reader = LMUReader(update_hz)
            logger.info("DataReader: LMU")

    def start(self):  self._reader.start()
    def stop(self):   self._reader.stop()
    def get(self) -> LMUSnapshot: return self._reader.get()

    @property
    def is_connected(self) -> bool: return self._reader.is_connected
