"""hypertrace/api/reader.py — Compatibility snapshot adapter.

The 9 primary overlays (standings, relative, delta, fuel/VE calculators,
tyres, weather, speed, pedals) no longer use this module — they read
`hypertrace.calc.module_info.minfo` and `hypertrace.calc.api.api` directly.

This stays as a thin adapter for what hasn't been migrated: the stream-only
broadcast graphics (`widgets/broadcast.py`) and the live-timing panel
(`widgets/live_timing.py`) — both already documented as on-hold/paused
features, not part of the calc-engine migration — plus
`stream/server.py`'s own per-tick game-state checks. `DataReader.get()`
builds a fresh `LMUSnapshot` from the calc engine's shared singletons on
every call. There is only one live shared-memory connection in the app,
owned by `calc/module_control.py`; nothing here opens its own.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from hypertrace.calc.api import api
from hypertrace.calc.module_control import mctrl
from hypertrace.calc.module_info import VehicleData, minfo
from hypertrace.calc.realtime_state import realtime_state

# Same shape as before (driver_name, best_lap, in_pit_lane, compounds, sector
# times, REST-enriched fields, ...) — kept as an alias so old type hints and
# imports keep resolving; VehicleData was designed to match it field-for-field.
VehicleScoringEntry = VehicleData


@dataclass
class SessionData:
    track_name: str       = ""
    session_type: int     = 0
    game_phase: int       = 0
    max_laps: int         = 0
    track_length: float   = 0.0
    num_vehicles: int     = 0
    current_et: float     = 0.0
    session_time_remaining: float = 0.0
    ambient_temp: float      = 20.0
    track_temp: float        = 30.0
    raining: float           = 0.0
    avg_path_wetness: float  = 0.0
    player_name: str      = ""
    vehicles: list[VehicleData] = field(default_factory=list)
    weather_forecast: list[int] = field(default_factory=list)
    weather_sky: int      = -1
    session_id: int       = 0


@dataclass
class LMUSnapshot:
    session: SessionData     = field(default_factory=SessionData)
    is_on_track: bool        = False
    player_in_garage: bool   = False
    game_running: bool       = False
    session_active: bool     = False
    viewed_slot_id: int      = -1
    timestamp: float         = 0.0


def _build_snapshot() -> LMUSnapshot:
    s = SessionData(
        track_name             = minfo.session.trackName,
        session_type           = minfo.session.sessionType,
        game_phase              = minfo.session.gamePhase,
        max_laps                = minfo.session.maxLaps,
        track_length             = minfo.session.trackLength,
        num_vehicles             = minfo.session.numVehicles,
        current_et                = minfo.session.currentEt,
        session_time_remaining     = minfo.session.timeRemaining,
        ambient_temp                = minfo.session.ambientTemp,
        track_temp                   = minfo.session.trackTemp,
        raining                       = minfo.session.raining,
        avg_path_wetness               = minfo.session.avgPathWetness,
        player_name                     = minfo.session.playerName,
        vehicles                         = minfo.vehicles.dataSet,
        weather_forecast                  = minfo.session.weatherForecast,
        weather_sky                        = minfo.session.weatherSky,
        session_id                          = minfo.stint.resetCount,
    )
    player = next((v for v in s.vehicles if v.is_player), None)
    session_active = s.num_vehicles > 0 and s.current_et > 0
    return LMUSnapshot(
        session          = s,
        is_on_track       = realtime_state.active,
        player_in_garage   = player.in_garage if player else False,
        game_running         = realtime_state.game_running,
        session_active         = session_active,
        viewed_slot_id           = minfo.vehicles.viewedSlotId,
        timestamp                 = time.time(),
    )


class DataReader:
    """Starts/stops the calc engine; `.get()` returns a fresh compat snapshot."""

    def __init__(self, update_hz: int = 50) -> None:
        pass   # update_hz is a no-op here — each calc module sets its own rate

    def start(self) -> None:
        mctrl.start()

    def stop(self) -> None:
        mctrl.stop()

    def get(self) -> LMUSnapshot:
        return _build_snapshot()

    @property
    def is_connected(self) -> bool:
        return realtime_state.connected


def lmu_rest_put(path: str, rest_base: str = "http://localhost:6397") -> bool:
    """Send a PUT to the LMU REST API. Returns True on success."""
    import urllib.request as _ur
    try:
        req = _ur.Request(f"{rest_base}{path}", method="PUT")
        _ur.urlopen(req, timeout=1)
        return True
    except Exception:
        return False
