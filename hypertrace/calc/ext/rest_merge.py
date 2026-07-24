"""hypertrace/calc/ext/rest_merge.py — LMU REST API enrichment.

This is specific to LMU's own REST API (localhost:6397) and entirely
original to this app. Kept exactly as it worked in the old reader.py, just
relocated and re-targeted to write into `minfo` instead of the old
`LMUSnapshot`.

Per this app's standing security rule: REST is only ever touched here, in a
background thread — never from a widget. Reader.py used to also merge
per-car sector times from REST; that's now redundant, shared memory already
publishes them directly (see module_vehicles.py) and more reliably (REST
polls at 3 Hz; shared memory is read every tick).

Four independent things, each on its own cadence:
  - focus (watched driver)   — 5 Hz
  - standings enrichment     — 3 Hz  (car number, team name, class gap)
  - weather forecast         — every 30s, fast-retry (2s) until first success
  - suspension damage        — 2 Hz  (player only — REST doesn't broadcast
                                 this for other cars; LMU has no shared-memory
                                 equivalent, this is REST-only by nature, see
                                 project memory. Deliberately not ported to
                                 the without-rest-api build: that build simply
                                 never populates minfo.damage.suspensionDamage,
                                 which the Damage widget already treats as
                                 "no data" via the -1.0 default.)
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.request as _ur

from hypertrace.calc.module_info import minfo
from hypertrace.calc.realtime_state import realtime_state

logger = logging.getLogger(__name__)

_REST_BASE = "http://localhost:6397"
_FOCUS_INTERVAL = 0.2
_STANDINGS_INTERVAL = 0.333
_WEATHER_INTERVAL = 30.0
_WEATHER_RETRY_INTERVAL = 2.0
_WEATHER_URL = f"{_REST_BASE}/rest/sessions/weather"
_WEATHER_NODES = ["START", "NODE_25", "NODE_50", "NODE_75", "FINISH"]
_DAMAGE_INTERVAL = 0.5
_DAMAGE_URL = f"{_REST_BASE}/rest/garage/UIScreen/RepairAndRefuel"


def _weather_outer_key(session_type: int) -> str:
    if session_type <= 4:
        return "PRACTICE"
    if session_type <= 8:
        return "QUALIFY"
    return "RACE"


def _fetch_weather_forecast(session_type: int) -> list[int]:
    try:
        req = _ur.Request(_WEATHER_URL, headers={"Accept": "application/json"})
        with _ur.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
        outer = _weather_outer_key(session_type)
        sub = (data.get(outer) or data.get("PRACTICE") or data.get("QUALIFY")
               or data.get("RACE") or data)
        return [int(sub.get(n, {}).get("WNV_SKY", {}).get("currentValue", -1))
                for n in _WEATHER_NODES]
    except Exception:
        return []


class RestMerge:
    def __init__(self) -> None:
        self._running = False
        self._thread: threading.Thread | None = None
        self._pinned = False

    @property
    def running(self) -> bool:
        """Whether the REST polling thread is currently active."""
        return self._running

    def pin(self) -> None:
        """Full build only: keep REST running for the whole session.

        The Broadcast master switch (ui/main_window.py) calls stop() on its
        way off. That is correct on the without-rest-api build, where REST
        exists *only* to serve Broadcast — but wrong here: on this build REST
        starts with the calc modules and feeds the desktop overlays too (car
        number, team name, class gap, weather forecast, suspension damage),
        none of which have anything to do with Broadcast. Turning Broadcast
        off would silently blank all of them for the rest of the session.

        Pinning makes stop() a no-op so the shared UI code stays correct on
        both branches — the difference lives in calc/module_control.py, which
        is one of the two files allowed to diverge. Shutdown still stops the
        thread, via stop(force=True) from module_control.
        """
        self._pinned = True

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="LMURestMerge", daemon=True)
        self._thread.start()

    def stop(self, force: bool = False) -> None:
        if self._pinned and not force:
            return
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _loop(self) -> None:
        last_standings = 0.0
        last_weather = 0.0
        last_damage = 0.0
        wx_last_session: int | None = None

        while self._running:
            now = time.monotonic()

            try:
                with _ur.urlopen(f"{_REST_BASE}/rest/watch/focus", timeout=1) as r:
                    slot = int(r.read().decode().strip())
                    minfo.vehicles.viewedSlotId = slot if slot >= 0 else minfo.vehicles.playerSlotId
            except Exception:
                pass

            if now - last_standings >= _STANDINGS_INTERVAL:
                try:
                    with _ur.urlopen(f"{_REST_BASE}/rest/watch/standings", timeout=2) as r:
                        rest_data = {int(item["slotID"]): item for item in json.loads(r.read())}
                    for entry in minfo.vehicles.dataSet:
                        rd = rest_data.get(entry.slot_id)
                        if rd:
                            entry.car_number = str(rd.get("carNumber", ""))
                            entry.team_name  = rd.get("fullTeamName", "")
                            entry.time_behind_class_leader = float(rd.get("timeBehindClassLeader", 0.0))
                            entry.laps_behind_class_leader = int(rd.get("lapsBehindClassLeader", 0))
                    last_standings = now
                except Exception:
                    pass

            if now - last_damage >= _DAMAGE_INTERVAL:
                try:
                    with _ur.urlopen(_DAMAGE_URL, timeout=1) as r:
                        wearables = json.loads(r.read()).get("wearables") or {}
                    susp = wearables.get("suspension")
                    if isinstance(susp, list) and len(susp) == 4:
                        minfo.damage.suspensionDamage = [float(v) for v in susp]
                    last_damage = now
                except Exception:
                    pass

            session_type = minfo.session.sessionType
            session_changed = session_type != wx_last_session
            has_forecast = bool(minfo.session.weatherForecast)
            wx_interval = _WEATHER_RETRY_INTERVAL if (not has_forecast or session_changed) else _WEATHER_INTERVAL
            if now - last_weather >= wx_interval:
                fc = _fetch_weather_forecast(session_type)
                if fc:
                    minfo.session.weatherForecast = fc
                    wx_last_session = session_type
                last_weather = now

            time.sleep(_FOCUS_INTERVAL)


rest_merge = RestMerge()
