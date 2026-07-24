"""hypertrace/calc/lmu_connector.py — Shared-memory sync layer.

Adapted from an established reference implementation (see
THIRD_PARTY_NOTICES.md), trimmed to what this app needs: no player-index override (LMU always
tells us who the local player is via mIsPlayer) and no results-stream parsing
(incident/track-cut history, unused by any of our widgets).

Runs its own background thread that keeps a synced copy of the local player's
scoring/telemetry structs (matched by mID rather than trusting the raw
playerVehicleIdx, since the scoring and telemetry arrays are not guaranteed to
use the same ordering) and detects two distinct states:
  - `paused`: the game stopped updating mCurrentET for >2s (alt-tab, replay,
    loading screen) — not "not driving", but "not producing new data at all".
  - `active` (see LMUInfo.isActive): actually driving/on-track right now.
"""
from __future__ import annotations

import ctypes
import logging
import threading
from time import monotonic

from pyLMUSharedMemory import lmu_data
from pyLMUSharedMemory.lmu_mmap import INVALID_INDEX, MAX_VEHICLES, LMUConstants, MMapControl

logger = logging.getLogger(__name__)


def copy_struct(struct_data):
    """Copy a ctypes struct (works with __slots__-based structs)."""
    return type(struct_data).from_buffer_copy(
        ctypes.string_at(ctypes.byref(struct_data), ctypes.sizeof(struct_data))
    )


def local_scoring_index(scor_veh) -> int:
    """Find the local player's scoring-array index via mIsPlayer."""
    for scor_idx, veh_info in enumerate(scor_veh):
        if veh_info.mIsPlayer:
            return scor_idx
    return INVALID_INDEX


class MMapDataSet:
    """Owns the mmap connection to the game's shared memory."""

    __slots__ = ("shmm",)

    def __init__(self) -> None:
        self.shmm = MMapControl(LMUConstants.LMU_SHARED_MEMORY_FILE, lmu_data.LMUObjectOut)

    def create_mmap(self, access_mode: int) -> None:
        self.shmm.create(access_mode)

    def close_mmap(self) -> None:
        self.shmm.close()

    def update_mmap(self) -> None:
        self.shmm.update()


class SyncData:
    """Background thread: keeps player scoring/telemetry structs in sync,
    and derives `paused` from whether mCurrentET is still advancing."""

    __slots__ = (
        "_updating",
        "_update_thread",
        "_event",
        "_tele_indexes",
        "paused",
        "synced",
        "player_scor_index",
        "player_scor",
        "player_tele",
        "dataset",
    )

    def __init__(self) -> None:
        self._updating = False
        self._update_thread: threading.Thread | None = None
        self._event = threading.Event()
        self._tele_indexes: dict[int, int] = {i: i for i in range(MAX_VEHICLES)}

        self.paused = False
        self.synced = False
        self.player_scor_index = INVALID_INDEX
        self.player_scor = None
        self.player_tele = None
        self.dataset = MMapDataSet()

    def __sync_player_scor(self, scor_index: int = INVALID_INDEX) -> None:
        self.player_scor = self.dataset.shmm.data.scoring.vehScoringInfo[scor_index]

    def __sync_player_tele(self, tele_index: int = INVALID_INDEX) -> None:
        self.player_tele = self.dataset.shmm.data.telemetry.telemInfo[tele_index]

    def __sync_player_data(self) -> bool:
        scor_idx = local_scoring_index(self.dataset.shmm.data.scoring.vehScoringInfo)
        if scor_idx == INVALID_INDEX:
            return False
        self.player_scor_index = scor_idx
        self.__sync_player_scor(scor_idx)
        self.__sync_player_tele(self.sync_tele_index(scor_idx))
        return True

    @staticmethod
    def __update_tele_indexes(veh_total: int, tele_data, tele_indexes: dict) -> None:
        """Telemetry index can differ from scoring index — match by mID."""
        for tele_idx, veh_info in zip(range(veh_total), tele_data.telemInfo):
            tele_indexes[veh_info.mID] = tele_idx

    def sync_tele_index(self, scor_idx: int) -> int:
        return self._tele_indexes.get(
            self.dataset.shmm.data.scoring.vehScoringInfo[scor_idx].mID, INVALID_INDEX)

    def start(self, access_mode: int = 0) -> None:
        if self._updating:
            logger.warning("calc: SyncData already started")
            return
        self._updating = True
        self.dataset.create_mmap(access_mode)
        self.__update_tele_indexes(
            self.dataset.shmm.data.scoring.scoringInfo.mNumVehicles,
            self.dataset.shmm.data.telemetry,
            self._tele_indexes,
        )
        if not self.__sync_player_data():
            self.__sync_player_scor()
            self.__sync_player_tele()
        self._event.clear()
        self._update_thread = threading.Thread(target=self.__update, name="LMUSyncData", daemon=True)
        self._update_thread.start()
        logger.info("calc: SyncData thread started")

    def stop(self) -> None:
        if not self._updating:
            return
        self._event.set()
        self._updating = False
        if self._update_thread:
            self._update_thread.join(timeout=2.0)
        # Final copy before close — mmap won't close cleanly under direct access otherwise.
        if self.player_scor is not None:
            self.player_scor = copy_struct(self.player_scor)
        if self.player_tele is not None:
            self.player_tele = copy_struct(self.player_tele)
        self.dataset.close_mmap()
        logger.info("calc: SyncData thread stopped")

    def __update(self) -> None:
        self.paused = False
        self.synced = False

        _event_wait = self._event.wait
        freezed_version = 0
        last_version_update = 0
        last_update_time = 0.0
        data_freezed = True
        reset_counter = 0
        update_delay = 0.5

        while not _event_wait(update_delay):
            self.dataset.update_mmap()
            self.__update_tele_indexes(
                self.dataset.shmm.data.scoring.scoringInfo.mNumVehicles,
                self.dataset.shmm.data.telemetry,
                self._tele_indexes,
            )
            version_update = self.dataset.shmm.data.scoring.scoringInfo.mCurrentET

            if not data_freezed:
                data_synced = self.__sync_player_data()
                if data_synced:
                    reset_counter = 0
                    self.synced = True
                elif reset_counter < 6:
                    reset_counter += 1
                    if reset_counter == 5:
                        self.player_scor_index = INVALID_INDEX
                        self.__sync_player_scor()
                        self.__sync_player_tele()
                        self.synced = False

            if last_version_update != version_update:
                last_version_update = version_update
                last_update_time = monotonic()

            if data_freezed:
                if freezed_version != last_version_update:
                    # The reference implementation uses 0.01 (100 Hz) here. Every iteration
                    # does two full scans over every car on track — a linear
                    # search for the player's index (local_scoring_index) and
                    # a full mID->index dict rebuild (__update_tele_indexes) —
                    # neither of which changes tick to tick. At 100 Hz with a
                    # full endurance-race grid that's real, continuous CPU
                    # work no widget here needs (nothing polls faster than
                    # 20 Hz). 20 Hz keeps player-data sync well ahead of every
                    # widget's own rate at a fraction of the cost.
                    update_delay = 0.05
                    self.paused = data_freezed = False
                    logger.info("calc: data resumed (version %s)", last_version_update)
            elif monotonic() - last_update_time > 2:
                update_delay = 0.5
                self.paused = data_freezed = True
                self.synced = False
                freezed_version = last_version_update
                logger.info("calc: data paused (version %s)", freezed_version)

        logger.info("calc: SyncData thread stopped (loop exit)")


class LMUInfo:
    """Public shared-memory data handle — one instance for the whole app."""

    __slots__ = ("_sync", "_shmm")

    def __init__(self) -> None:
        self._sync = SyncData()
        self._shmm = self._sync.dataset.shmm

    def start(self) -> None:
        # Direct access: the mmap is read in place, no periodic copy. Matches
        # the old reader's SimInfo exactly, which always used direct access.
        # Copy access (the reference implementation's own default) re-copies
        # the ENTIRE ~325 KB struct on every sync-loop iteration — up to
        # ~100 Hz once the game is actively updating (update_delay drops to
        # 0.01s), i.e. up to ~32 MB/s of continuous memcpy that never existed
        # before this port.
        # That's a new, substantial, sustained cost — and unlike a CPU-time
        # cost, restricting the app to specific cores (which is what fixed
        # freezes before) doesn't isolate memory-bandwidth/cache contention,
        # which is consistent with the freeze coming back even with the same
        # CPU affinity restriction that used to fix it. Direct access trades
        # away copy-based tear protection, but the old app ran this way for
        # the whole app's life without needing it.
        self._sync.start(access_mode=1)

    def stop(self) -> None:
        self._sync.stop()

    @property
    def lmuScorInfo(self):
        return self._shmm.data.scoring.scoringInfo

    def lmuScorVeh(self, index: int | None = None):
        """Scoring struct. `index=None` → local player (synced by mID)."""
        if index is None:
            return self._sync.player_scor
        return self._shmm.data.scoring.vehScoringInfo[index]

    def lmuTeleVeh(self, index: int | None = None):
        """Telemetry struct. `index=None` → local player (synced by mID)."""
        if index is None:
            return self._sync.player_tele
        return self._shmm.data.telemetry.telemInfo[self._sync.sync_tele_index(index)]

    @property
    def lmuGeneric(self):
        return self._shmm.data.generic

    @property
    def lmuTelemetry(self):
        """Raw telemetry container (`.telemInfo[i]`, `.activeVehicles`) —
        used only by module_vehicles.py's per-car scan, which needs the whole
        array rather than one synced index at a time."""
        return self._shmm.data.telemetry

    @property
    def playerIndex(self) -> int:
        return self._sync.player_scor_index

    @property
    def isPaused(self) -> bool:
        """Game stopped producing new data (alt-tab, replay, loading)."""
        return self._sync.paused

    @property
    def isActive(self) -> bool:
        """Actually driving/on-track right now (not just "game running")."""
        return self._sync.synced and self._sync.player_scor_index >= 0 and (
            self.lmuScorInfo.mInRealtime
            or self.lmuTeleVeh().mIgnitionStarter > 0
        )
