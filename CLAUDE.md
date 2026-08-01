# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

HyperTrace is a real-time telemetry **overlay** app for the sim racing game **Le Mans Ultimate** (Windows-only), built with Python + PySide6. Frameless, always-on-top overlays sit on top of the game; a stream mode serves them as PNGs for OBS, and a broadcast mode adds production graphics.

## Commands

```bash
# Dev install (into the repo's .venv)
pip install -e ".[dev]"

# Run from source
python -m hypertrace            # --hz <n> shared-memory poll rate (default 50); --verbose for DEBUG

# Lint (ruff; line-length 100, target py311)
ruff check .

# Build the standalone exe
# The .venv/Scripts/pyinstaller.exe shim is broken (crashes silently, exit 1,
# even on --version) — a past folder rename left it pointing at a stale path.
# Invoke PyInstaller as a module instead:
.venv/Scripts/python.exe -m PyInstaller HyperTrace.spec --noconfirm --clean
# → dist/HyperTrace/HyperTrace.exe ; zip as dist/.../HyperTrace_<version>.zip
```

`pytest`/`pytest-qt` are declared as dev deps but there is currently **no test suite** in the repo.

Logs and config live in `%USERPROFILE%\.hypertrace\` (`config.json`, `hypertrace.log`, `presets/`). When something won't start, read `hypertrace.log` first. Running the app needs LMU with **Settings → Gameplay → Enable Plugins = ON** (publishes the shared memory); the app also runs without the game (it just logs "shared memory unavailable" and shows nothing).

## Architecture (the data pipeline)

Data flows one direction through clearly separated layers. **The golden rule: only background calc threads touch the game; the GUI never does.**

1. **`pyLMUSharedMemory/`** — vendored fork that memory-maps LMU's raw shared-memory structs. Do **not** rename or edit; it's game-data, not app code.
2. **`hypertrace/calc/lmu_connector.py` + `api.py`** — `lmu_connector` wraps the raw structs; `api.py` exposes semantic accessors as a singleton `api` (`api.read.state.active()`, `api.read.lap.distance()`, …). Adapters only; no threads.
3. **`hypertrace/calc/modules/*` + `module_control.py`** — each `module_*.py` is a `Realtime(DataModule)` running on its **own background thread**, polling `api` and writing computed results into the shared `minfo` singleton. `module_control.py` (singleton `mctrl`) owns the fixed list of modules and starts/stops them together.
4. **`hypertrace/calc/module_info.py`** — the `minfo` singleton: plain mutable dataclasses (`minfo.fuel`, `minfo.vehicles`, `minfo.delta`, …). Unlocked by design — a widget reading mid-update just repaints one frame stale, never wrong long enough to matter.
5. **`hypertrace/calc/realtime_state.py`** — the `realtime_state` singleton + `StateControl` thread: owns the connect/reconnect lifecycle and the coarse flags every widget/module reads (`game_running`, `connected`, `active`, `paused`). Note `realtime_state.live` (compute-gating) vs `active` (literally driving).
6. **`hypertrace/widgets/base.py` (`BaseWidget`)** — every overlay subclasses this. Frameless, always-on-top, drag+snap, per-widget `CONFIG_SCHEMA`. It runs a `QBasicTimer`, and on each tick reads `minfo`/`realtime_state` and repaints. Visibility (auto-hide, session-type filtering) is decided here from `realtime_state`, not by each widget.

**`hypertrace/api/reader.py` (`DataReader`)** is a thin snapshot layer (`LMUSnapshot`) still consumed by the broadcast/live-timing widgets; it reads `minfo`/`api`, it does not open its own connection.

### REST enrichment (isolated)

`hypertrace/calc/ext/rest_merge.py` is the **only** place that calls LMU's local REST API (`localhost:6397`), on its own background thread, writing into `minfo`. It enriches what shared memory can't give: broadcast focus driver, standings car number/team/class-gap, weather forecast, and player suspension damage. Never call REST from anywhere else.

### WebSocket enrichment (isolated, `main` only for now)

LMU also exposes a local **WebSocket** next to the REST port — `ws://localhost:<REST port + 1>/websocket/ui` (`6398` by default), subscribed with `{"messageType":"SUB","topic":"LiveStandings"}` — pushing richer per-car data than REST or shared memory ever expose, discovered by decompiling the companion app *LMU Broadcast Control*. `hypertrace/calc/ext/ws_merge.py` is the **only** place that opens it, same isolation rule and same shape as `rest_merge.py` (own background thread, writes into `minfo`, never touched elsewhere). Currently used for one thing: penalty *type* (drive-through/stop-go/time-in-seconds) for Standings' penalty tag — shared memory's `mNumPenalties` is only ever a bare count. Written onto `minfo.vehicles.penaltyTypes` (a `slot_id -> (DT, SG, TIME)` dict on `VehiclesInfo`, **not** per-`VehicleData`) deliberately: `module_vehicles.py` rebuilds the whole `dataSet` list from scratch roughly every 100ms, and per-car fields written there raced against that rebuild and flickered. `VehiclesInfo` itself isn't rebuilt, so the dict survives untouched between `ws_merge` updates. No `websockets` package dependency — a small raw-socket client, matching how `rest_merge.py`/`widgets/live_timing.py` already talk HTTP by hand. Marked `REMOVE ME` in its own docstring: delete the file, its `module_control.py` wiring, and `penaltyTypes` the day shared memory exposes penalty type directly.

### Two builds / two branches

- **`main`** — full build: REST starts unconditionally with the calc modules and stays on the whole session. `module_control` also calls `rest_merge.pin()`, which makes `stop()` a no-op — the Broadcast toggle in `main_window.py` calls `stop()` on its way off, and without the pin that would blank every REST-only signal in the *desktop* overlays too. Shutdown uses `stop(force=True)` to override the pin. `module_control` also starts `ws_merge` unconditionally, no pin needed (nothing ever toggles it off).
- **`without-rest-api`** — shared-memory-first build: as of this writing, Broadcast and REST were removed from this build entirely (see its own commit "Drop Broadcast and REST API integration from this build" — check that branch's own CLAUDE.md for the current, branch-specific architecture, since it now differs from `main` more than the two-file rule below implies). Work on this branch is currently paused; whether `ws_merge.py` belongs there (it's a local, no-server-needed API, unlike REST-for-Broadcast — but the branch's whole premise is avoiding LMU's local API surface beyond shared memory) is an open question for whenever it resumes.

On `main`, shared files between the two branches are **identical except for the REST/WebSocket wiring in exactly two files**: `hypertrace/main.py` and `hypertrace/calc/module_control.py` — plus, currently, `ws_merge.py` existing only on `main` (see above). When porting features between them, touch everything freely but preserve each branch's version of those two files. Always check `git branch --show-current` before editing.

### UI, stream, broadcast

- **`hypertrace/ui/main_window.py`** — sidebar window (pages: Overlays / Presets / Stream / Broadcast) plus a "Global controls" card (Lock/Free, Auto-hide, Merge Fuel & VE). Small custom controls (pill toggles, on/off buttons) live in `main_window_controls.py`.
- **`hypertrace/stream/server.py`** — renders each overlay `QWidget` to a `QImage`→PNG and serves it over HTTP for OBS Browser Sources. Stream overlays are configured independently of the desktop ones.
- **Broadcast** overlays (`widgets/broadcast.py`) + the `Live Timing` panel (`widgets/live_timing.py`) are stream-only production graphics.

## Conventions worth knowing

- **Naming — game vs app.** Identifiers containing `lmu`/`LMU` that refer to *Le Mans Ultimate the game* (`pyLMUSharedMemory`, `lmu_connector`, `LMUInfo`, `lmuScorVeh`, `lmu_enum`, `LMU_COMPOUND_TYPE`, `LMUSnapshot`) are game vocabulary and must **not** be renamed to `hypertrace`. The app package/branding is `hypertrace`/HyperTrace; the game is Le Mans Ultimate.
- **Theme & fonts.** All design tokens live in `hypertrace/utils/theme.py` (`T`), with cached `label_font()`/`num_font()`/`text_font()` helpers. Font sizes are expressed in the historical point scale but applied as **pixels** (`_PX_PER_PT`) so overlays render identically across DPI/scaling — keep that intact when touching sizes. A `-` dash is always drawn `T.TEXT` (white), never `T.DIM`.
- **Name mangling pitfall.** Inside classes, a leading `__name` triggers Python name-mangling and silently breaks cross-reference; use a single underscore `_name`.
- **Versioning.** "Bump to X.Y.Z" means updating all three together: `pyproject.toml` `version`, `hypertrace/main.py` `APP_VERSION`, and a new `## [X.Y.Z]` section in `CHANGELOG.md` (written in **English**). The changelog documents only the net diff versus the last *publicly released* zip — never mention bugs introduced and fixed within an unreleased cycle. Each release zip also gets a cumulative `dist/.../HyperTrace_<version>_CHANGELOG.md` covering everything since the previous zip.
- **Attribution.** The calc engine (`calc/`) and `widgets/base.py`'s update/visibility engine are adapted from **TinyPedal** (GPLv3) — see `THIRD_PARTY_NOTICES.md`. Everything else (drawing, layout, settings, presets, stream, broadcast) is original.
