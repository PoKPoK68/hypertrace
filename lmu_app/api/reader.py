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
import math
import threading
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

logger = logging.getLogger(__name__)

# Compound type → name (module constant; do not rebuild per vehicle per tick)
_COMPOUND_TYPES = {0: "Soft", 1: "Medium", 2: "Hard", 3: "Wet"}


@lru_cache(maxsize=1024)
def _decode(raw: bytes) -> str:
    """Decode a ctypes char buffer to str, memoized.

    Driver/team/class/model names are stable but were decoded for every car on
    every 50 Hz tick. Identical bytes → cache hit, so the decode+strip only runs
    once per distinct string instead of thousands of times per second.
    """
    return raw.decode(errors="replace").rstrip("\x00")


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
    optimal_temp: list[float]  = field(default_factory=lambda: [0.0]*4)   # °C (mOptimalTemp)


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
    pit_state: int        = 0     # 0=none, 1=request, 2=entering, 3=stopped, 4=exiting,
                                  # 5=undocumented (observed when leaving the garage box)
    pitlane: bool         = False # physically in the pit lane (mCurrentSector sign bit)
    control: int          = 0
    in_garage: bool       = False
    vehicle_class: str    = ""
    virtual_energy: float = 0.0   # 0-1 fraction; 0 if car has no VE
    fuel: float           = 0.0   # litres
    finish_status: int    = 0     # 0=none, 1=finished, 2=DNF, 3=DQ (per InternalsPlugin.hpp)
    car_number: str   = ""
    team_name:  str   = ""
    time_behind_class_leader: float = 0.0
    laps_behind_class_leader: int   = 0
    # Sector times from REST API
    cur_sector1: float     = -1.0   # currentSectorTime1 (in-progress lap, -1 if not yet crossed)
    cur_sector2: float     = -1.0   # currentSectorTime2 cumulative (-1 if not yet crossed)
    last_sector1: float    = -1.0   # lastSectorTime1 (last lap S1)
    last_sector2: float    = -1.0   # lastSectorTime2 cumulative (last lap S1+S2)
    best_sector1: float    = -1.0   # bestSectorTime1 (personal best S1)
    best_sector2: float    = -1.0   # bestSectorTime2 cumulative (personal best S1+S2)
    best_lap_sector2: float = -1.0  # bestLapSectorTime2 (S1+S2 from best lap, for S3 calc)
    compounds: list[str] = field(default_factory=lambda: ["", "", "", ""])  # [FL, FR, RL, RR] compound names

    @property
    def in_pit_lane(self) -> bool:
        """True while physically in the pit lane.

        Combines all three signals — none alone is sufficient, and they must be
        OR'ed (an early return on pit_state alone hid the pit lane when leaving
        the garage, where pit_state is the undocumented value 5):
          - `pitlane`   : mCurrentSector sign bit; observed 0x80000000 leaving
                          the garage and 0x80000002 entering from the track.
          - `pit_state` : >= 2 rather than a whitelist, so undocumented states
                          (5) still count. 1 = request is still on track.
          - `in_pits`   : "between pit entrance and pit exit"; the header warns
                          it is unreliable for remote vehicles.
        """
        return self.pitlane or self.pit_state >= 2 or self.in_pits


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
    weather_forecast: list[int] = field(default_factory=list)  # 5 sky types (0-10), [] if none
    weather_sky: int      = -1   # current sky type (mCloudCoverage, 0-10); -1 unknown
    session_id: int       = 0    # bumps on session change / restart (for per-session resets)


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
_SCORING_EVERY = 5           # full field scan every Nth tick (~10 Hz at 50 Hz base)
_WEATHER_URL = f"{_REST_BASE}/rest/sessions/weather"
_WEATHER_INTERVAL = 30.0     # weather forecast changes slowly — poll every 30 s
_WEATHER_NODES = ["START", "NODE_25", "NODE_50", "NODE_75", "FINISH"]


def _weather_outer_key(session_type: int) -> str:
    if session_type <= 4:
        return "PRACTICE"
    if session_type <= 8:
        return "QUALIFY"
    return "RACE"


def _fetch_weather_forecast(session_type: int) -> list[int]:
    """GET the weather forecast → 5 sky_type ints (0-10). [] on failure.

    Lives in the reader (not the widget) so overlays never touch the REST API.
    """
    import urllib.request as _ur
    import json as _json
    try:
        req = _ur.Request(_WEATHER_URL, headers={"Accept": "application/json"})
        with _ur.urlopen(req, timeout=2) as resp:
            data = _json.loads(resp.read())
        # Response is wrapped by session type: {"PRACTICE": {nodes...}, "QUALIFY": ...}
        outer = _weather_outer_key(session_type)
        sub = (data.get(outer) or data.get("PRACTICE") or data.get("QUALIFY")
               or data.get("RACE") or data)
        return [int(sub.get(n, {}).get("WNV_SKY", {}).get("currentValue", -1))
                for n in _WEATHER_NODES]
    except Exception:
        return []


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
        self._rest_lock  = threading.Lock()
        self._rest_focus: int = -1   # slotID from REST API; -1 = unknown
        self._rest_data: dict[int, dict] = {}   # slot_id → REST standings entry
        self._rest_weather: list[int] = []      # 5 sky types from REST weather endpoint
        # Two-tier cadence: the heavy full-field scan runs at ~10 Hz, its result
        # is cached and reused on the fast (50 Hz) ticks that only refresh the
        # light player telemetry. Touched only by the reader thread.
        self._veh_cache: list[VehicleScoringEntry] = []
        self._scoring_counter: int = 0
        self._scan_session: int = -1   # mSession value at last full scan
        # Session identity: bumped on session type change or clock reset (restart)
        self._session_id: int = 0
        self._prev_session_type: int | None = None
        self._prev_current_et: float = 0.0

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
        if self._rest_thread:
            self._rest_thread.join(timeout=1.0)
        if self._sim:
            try: self._sim.close()
            except Exception: pass
        logger.info("LMUReader stopped")

    def _rest_loop(self):
        """Poll REST API: focus at 5 Hz, standings at 3 Hz, weather every 30 s."""
        import urllib.request as _ur
        import json as _json
        _last_st = 0.0
        _last_weather = 0.0
        _wx_last_session: int | None = None   # session_type of last weather fetch
        while self._running:
            now = time.monotonic()
            try:
                with _ur.urlopen(f"{_REST_BASE}/rest/watch/focus", timeout=1) as r:
                    slot = int(r.read().decode().strip())
                    with self._rest_lock:
                        self._rest_focus = slot if slot >= 0 else -1
            except Exception:
                pass
            if now - _last_st >= 0.333:
                try:
                    with _ur.urlopen(f"{_REST_BASE}/rest/watch/standings", timeout=2) as r:
                        data = _json.loads(r.read())
                        new_data = {int(item["slotID"]): item for item in data}
                    with self._rest_lock:
                        self._rest_data = new_data
                        _last_st = now
                except Exception:
                    pass
            # Weather: fetch immediately at launch and on every session change
            # (the forecast is per-session). Retry fast until we have data for
            # the current session (REST may not be ready yet), then poll slowly.
            with self._lock:
                st = self._snapshot.session.session_type
            session_changed = (st != _wx_last_session)
            wx_interval = 2.0 if (not self._rest_weather or session_changed) else _WEATHER_INTERVAL
            if now - _last_weather >= wx_interval:
                fc = _fetch_weather_forecast(st)
                if fc:
                    with self._rest_lock:
                        self._rest_weather = fc
                    _wx_last_session = st
                _last_weather = now
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

    def _scan_vehicles(self, data, sc_info, telem) -> list[VehicleScoringEntry]:
        """Heavy full-field scan: scoring entries + REST merge + telemInfo
        (VE / fuel / compounds / model). Throttled to ~10 Hz by the caller —
        standings/relative overlays sample at 5-10 Hz so this is imperceptible.
        Always returns a fresh list (never mutates a previously published one)."""
        vehicles: list[VehicleScoringEntry] = []
        for i in range(min(sc_info.mNumVehicles, 104)):
            v = data.scoring.vehScoringInfo[i]
            try:
                vclass = _decode(v.mVehicleClass)
            except AttributeError:
                vclass = ""
            vehicles.append(VehicleScoringEntry(
                slot_id            = v.mID,
                driver_name        = _decode(v.mDriverName),
                vehicle_name       = _decode(v.mVehicleName),
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
                pit_state          = int(getattr(v, 'mPitState', 0)),
                in_garage          = bool(v.mInGarageStall),
                control            = v.mControl,
                vehicle_class      = vclass,
                finish_status      = getattr(v, 'mFinishStatus', 0),
            ))

        # Merge REST standings data (car number, team, class gap)
        with self._rest_lock:
            rest_snapshot = dict(self._rest_data)
        for entry in vehicles:
            rd = rest_snapshot.get(entry.slot_id)
            if rd:
                entry.car_number = str(rd.get("carNumber", ""))
                entry.team_name  = rd.get("fullTeamName", "")
                entry.time_behind_class_leader = float(rd.get("timeBehindClassLeader", 0.0))
                entry.laps_behind_class_leader = int(rd.get("lapsBehindClassLeader", 0))
                entry.cur_sector1      = float(rd.get("currentSectorTime1", -1.0))
                entry.cur_sector2      = float(rd.get("currentSectorTime2", -1.0))
                entry.last_sector1     = float(rd.get("lastSectorTime1", -1.0))
                entry.last_sector2     = float(rd.get("lastSectorTime2", -1.0))
                entry.best_sector1     = float(rd.get("bestSectorTime1", -1.0))
                entry.best_sector2     = float(rd.get("bestSectorTime2", -1.0))
                entry.best_lap_sector2 = float(rd.get("bestLapSectorTime2", -1.0))

        # --- VE, fuel et compounds pour tous les véhicules depuis telemInfo ---
        ve_by_id:       dict[int, float]      = {}
        fuel_by_id:     dict[int, float]      = {}
        model_by_id:    dict[int, str]        = {}
        compound_by_id: dict[int, list[str]]  = {}
        pitlane_by_id:  dict[int, bool]       = {}
        try:
            for i in range(min(telem.activeVehicles, 104)):
                t = telem.telemInfo[i]
                sid = t.mID
                ve_by_id[sid]   = float(t.mVirtualEnergy)
                fuel_by_id[sid] = float(t.mFuel)
                # Pit lane is encoded in mCurrentSector's sign bit (e.g. 0x80000002)
                pitlane_by_id[sid] = int(t.mCurrentSector) < 0
                try:
                    # mCompoundType: 0=Soft 1=Medium 2=Hard 3=Wet, per wheel, all vehicles
                    comps = [_COMPOUND_TYPES.get(int(t.mWheels[wi].mCompoundType), "")
                             for wi in range(4)]
                    if any(comps):
                        compound_by_id[t.mID] = comps
                except (AttributeError, IndexError, TypeError):
                    pass
                try:
                    m = _decode(t.mVehicleModel)
                    if m:
                        model_by_id[t.mID] = m
                except AttributeError:
                    pass
        except (AttributeError, IndexError):
            pass
        for entry in vehicles:
            entry.virtual_energy = ve_by_id.get(entry.slot_id, 0.0)
            entry.fuel           = fuel_by_id.get(entry.slot_id, 0.0)
            entry.pitlane        = pitlane_by_id.get(entry.slot_id, False)
            if entry.slot_id in compound_by_id:
                entry.compounds = compound_by_id[entry.slot_id]
            if entry.slot_id in model_by_id:
                entry.vehicle_name = model_by_id[entry.slot_id]

        return vehicles

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
            s.track_name              = _decode(sc_info.mTrackName)
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
            s.player_name             = _decode(sc_info.mPlayerName)
            s.weather_sky             = int(sc_info.mCloudCoverage)   # current sky (0-10), from SM
            with self._rest_lock:
                s.weather_forecast    = list(self._rest_weather)

            # Session identity: bump on session-type change or a clock reset
            # (session restart drops mCurrentET back to ~0). Widgets compare
            # snap.session.session_id to reset per-session state reliably.
            if (self._prev_session_type is not None
                    and (sc_info.mSession != self._prev_session_type
                         or s.current_et + 2.0 < self._prev_current_et)):
                self._session_id += 1
            self._prev_session_type = sc_info.mSession
            self._prev_current_et   = s.current_et
            s.session_id = self._session_id

            # --- Véhicules scoring (scan complet lourd throttlé à ~10 Hz) ---
            # Sur les ticks rapides on réutilise la liste mise en cache : elle
            # n'est jamais mutée en place (chaque scan crée une liste neuve),
            # donc les snapshots déjà publiés restent cohérents.
            if (not self._veh_cache
                    or self._scoring_counter % _SCORING_EVERY == 0
                    or sc_info.mNumVehicles != len(self._veh_cache)
                    or sc_info.mSession != self._scan_session):
                self._veh_cache = self._scan_vehicles(data, sc_info, telem)
                self._scan_session = sc_info.mSession
            self._scoring_counter += 1
            s.vehicles = self._veh_cache

            # --- Session active + viewed vehicle ---
            player_sc = next((e for e in s.vehicles if e.is_player), None)
            snap.session_active = s.num_vehicles > 0 and s.current_et > 0
            if player_sc:
                snap.player_in_garage = player_sc.in_garage
                snap.viewed_slot_id   = player_sc.slot_id  # fallback: own car

            # REST API gives us the true focused slotID from /rest/watch/focus
            with self._rest_lock:
                rest_slot = self._rest_focus
            if rest_slot > 0 and any(v.slot_id == rest_slot for v in s.vehicles):
                snap.viewed_slot_id = rest_slot

            # --- Télémétrie joueur ---
            if not telem.playerHasVehicle:
                with self._lock:
                    self._snapshot = snap
                return

            idx  = telem.playerVehicleIdx
            if not (0 <= idx < 104):
                with self._lock:
                    self._snapshot = snap
                return
            tel  = telem.telemInfo[idx]

            # Vitesse locale (norme du vecteur mLocalVel)
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
                # mOptimalTemp is documented as Celsius; guard in case a build
                # reports Kelvin so the tyre colours never break.
                _ot = float(w.mOptimalTemp)
                t.optimal_temp[i]  = _ot - 273.15 if _ot > 200.0 else _ot

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
