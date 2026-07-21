"""lmu_app/calc/module_info.py — Shared `minfo` singleton.

Ported from TinyPedal's `tinypedal/module_info.py` pattern: each calc module
(calc/modules/module_*.py) owns one of these dataclasses and writes onto its
fields every tick; widgets only ever read from `minfo`, never from shared
memory directly. Plain mutable objects, no locking — same tradeoff TinyPedal
makes (a widget reading a half-updated tick just repaints one frame stale,
never inconsistent enough to matter at these update rates).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VehicleData:
    """One row of the standings/relative dataset — one car."""
    slot_id: int              = 0
    driver_name: str          = ""
    vehicle_name: str         = ""
    vehicle_class: str        = ""
    place: int                = 0
    total_laps: int           = 0
    lap_dist: float           = 0.0
    best_lap: float           = -1.0
    last_lap: float           = -1.0
    time_behind_leader: float = 0.0
    time_behind_next: float   = 0.0
    laps_behind_leader: int   = 0
    laps_behind_next: int     = 0
    time_into_lap: float      = 0.0
    estimated_lap_time: float = 0.0
    is_player: bool           = False
    in_pits: bool             = False
    pit_state: int            = 0
    pitlane: bool             = False
    in_garage: bool           = False
    control: int              = 0
    finish_status: int        = 0
    fuel: float                = 0.0
    virtual_energy: float      = 0.0
    compounds: list[str] = field(default_factory=lambda: ["", "", "", ""])
    # REST-enriched (calc/ext/rest_merge.py) — absent from raw shared memory.
    car_number: str = ""
    team_name: str  = ""
    time_behind_class_leader: float = 0.0
    laps_behind_class_leader: int   = 0
    cur_sector1: float      = -1.0
    cur_sector2: float      = -1.0
    last_sector1: float     = -1.0
    last_sector2: float     = -1.0
    best_sector1: float     = -1.0
    best_sector2: float     = -1.0
    best_lap_sector2: float = -1.0

    @property
    def in_pit_lane(self) -> bool:
        """Combines all three signals — see calc/modules/module_vehicles.py."""
        return self.pitlane or self.pit_state >= 2 or self.in_pits


@dataclass
class VehiclesInfo:
    dataSet: list[VehicleData] = field(default_factory=list)
    totalVehicles: int  = 0
    playerSlotId: int   = -1
    viewedSlotId: int   = -1   # focused/watched driver (REST /rest/watch/focus)
    playerInGarage: bool = False   # computed once per scan — was re-scanned by every widget


@dataclass
class DeltaInfo:
    lapTimeCurrent: float = 0.0
    lapTimeLast: float    = 0.0
    lapTimeBest: float    = 0.0
    lapTimeEstimated: float = 0.0
    lapTimeSession: float = 0.0   # session-best
    deltaBest: float    = 0.0
    deltaLast: float    = 0.0
    deltaSession: float = 0.0
    deltaBestRaw: float = 0.0   # game's own mDeltaBest — the Delta widget displays this
    isValidLap: bool    = False


@dataclass
class FuelInfo:
    amountCurrent: float      = 0.0
    amountUsedLast: float     = 0.0
    amountUsedAvg: float      = 0.0    # rolling avg over last 5 laps
    estimatedLaps: float      = 0.0    # laps left on current avg consumption
    estimatedMinutes: float   = 0.0
    neededRelative: float     = 0.0    # additional amount needed to the end (0 if enough)
    amountEndStint: float     = 0.0    # amount left at the end of the current lap
    capacity: float           = 100.0


@dataclass
class EnergyInfo(FuelInfo):
    """Virtual Energy — same shape as fuel, tracked in percent (0-100) not liters."""


@dataclass
class PlayerTelemetryInfo:
    """Raw local-player telemetry — speed/gear/rpm/pedals. Refreshed by its
    own fast background module so widgets (Speed, Pedals) never touch shared
    memory from the GUI thread."""
    speedMs: float  = 0.0
    gear: int       = 0
    rpm: float      = 0.0
    rpmMax: float   = 9000.0
    throttle: float = 0.0
    brake: float    = 0.0
    clutch: float   = 0.0


@dataclass
class HybridInfo:
    batteryCharge: float      = 0.0   # fraction 0-1
    fuelEnergyRatio: float    = 0.0   # fuel used / VE used, for hybrid strategy calc


@dataclass
class WheelsInfo:
    wear: list[float]        = field(default_factory=lambda: [1.0] * 4)
    surfaceTemp: list[float] = field(default_factory=lambda: [0.0] * 4)
    innerTemp: list[float]   = field(default_factory=lambda: [0.0] * 4)
    carcassTemp: list[float] = field(default_factory=lambda: [0.0] * 4)
    optimalTemp: list[float] = field(default_factory=lambda: [0.0] * 4)
    pressure: list[float]    = field(default_factory=lambda: [0.0] * 4)
    brakeTemp: list[float]   = field(default_factory=lambda: [0.0] * 4)
    compounds: list[str]     = field(default_factory=lambda: ["", "", "", ""])


@dataclass
class StintInfo:
    """`resetCount` increments on every detected session reset/restart —
    widgets store the last value they saw and compare with `!=` each tick,
    which (unlike a one-tick pulse flag) can't be missed by polling at a
    different cadence than the stint module's own tick rate."""
    resetCount: int = 0


@dataclass
class SessionInfo:
    """Coarse session/weather fields every widget may need, refreshed each tick."""
    trackName: str        = ""
    sessionType: int      = 0     # 0-4 practice, 5-8 qualify, 9 warmup, 10-13 race
    gamePhase: int        = 0
    maxLaps: int           = 0
    trackLength: float     = 0.0
    numVehicles: int       = 0
    currentEt: float       = 0.0
    timeRemaining: float   = 0.0
    ambientTemp: float     = 20.0
    trackTemp: float       = 30.0
    raining: float         = 0.0
    avgPathWetness: float  = 0.0
    playerName: str        = ""
    weatherSky: int         = -1
    weatherForecast: list[int] = field(default_factory=list)


@dataclass
class ModuleInfo:
    vehicles: VehiclesInfo = field(default_factory=VehiclesInfo)
    delta: DeltaInfo       = field(default_factory=DeltaInfo)
    fuel: FuelInfo         = field(default_factory=FuelInfo)
    energy: EnergyInfo     = field(default_factory=EnergyInfo)
    hybrid: HybridInfo     = field(default_factory=HybridInfo)
    wheels: WheelsInfo     = field(default_factory=WheelsInfo)
    stint: StintInfo       = field(default_factory=StintInfo)
    session: SessionInfo   = field(default_factory=SessionInfo)
    player: PlayerTelemetryInfo = field(default_factory=PlayerTelemetryInfo)


minfo = ModuleInfo()
