"""hypertrace/calc/modules/module_stint.py — Canonical session-reset signal.

Not a full adaptation of the reference implementation's stint module (that
one builds a lap-by-lap stint history log nothing in this app's widgets
displays) — this is the piece of it that matters here: a single, reliable
"did the session just reset" flag, replacing the old hand-rolled heuristic
in reader.py (`session_type changed OR current_et jumped back by >2s`),
which every per-session-state widget (fuel/VE history, relative outlap/pit
badges, standings pit-badge memory) used to duplicate slightly differently.

Two signals, matching what the reference implementation uses in different places:
  - `api.read.session.identifier()` monotonicity check, done once per
    idle→active transition (catches session-type changes, restarts).
  - a cheap live per-tick check — session elapsed time going backwards —
    for a restart that happens without an idle/active transition in between
    (e.g. clicking "Restart Session" while still on track).
"""
from __future__ import annotations

from hypertrace.calc._calc_util import is_same_session
from hypertrace.calc.api import api
from hypertrace.calc.module_info import minfo
from hypertrace.calc.modules._base import DataModule
from hypertrace.calc.realtime_state import realtime_state


class Realtime(DataModule):
    def __init__(self) -> None:
        super().__init__("stint", active_interval=0.2, idle_interval=0.5)

    def update_data(self) -> None:
        _event_wait = self._event.wait
        reset = False
        interval = self.idle_interval

        last_session_id = (0, -1, -1)
        last_elapsed = 0.0

        while not _event_wait(interval):
            if not realtime_state.live:
                if reset:
                    reset = False
                    interval = self.idle_interval
                continue

            # Gate computation on `live` (connected, not just "on track right
            # now"), so this and every other module keep publishing fresh
            # data while sitting in the garage, not just while driving — see
            # RealtimeState.live. `active` still governs the poll rate.
            interval = self.active_interval if realtime_state.active else self.idle_interval

            session_id = api.read.session.identifier()
            elapsed = session_id[1]

            if not reset:
                reset = True
                if not is_same_session(session_id, last_session_id):
                    minfo.stint.resetCount += 1
            elif elapsed < last_elapsed:
                minfo.stint.resetCount += 1

            last_elapsed = elapsed
            last_session_id = session_id
