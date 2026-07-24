# HyperTrace

Real-time telemetry overlay app for **Le Mans Ultimate**, built with Python and PySide6.

Draggable, configurable overlays sit directly on top of the game — no alt-tabbing, no browser window. A stream mode serves any overlay as a browser source for OBS, and a separate broadcast mode adds production-style graphics for streamers.

---

## Overlays

| Overlay | Description |
|---|---|
| **Speed & Gear** | Speed, gear and an RPM shift-light bar |
| **Pedals** | Throttle / brake / clutch bars with a trace history |
| **Standings** | Multi-class live standings — gaps, lap times, pit/out badges, tyre compound, manufacturer logo |
| **Relative** | On-track proximity list of the drivers immediately around you, with live gaps |
| **Delta** | Last lap / best lap / live delta-to-best with a gain-loss bar |
| **Tyres** | Per-tyre carcass temperature (colour-coded to each tyre's own optimal window) and wear |
| **Damage** | Top-down car silhouette showing body, wheel, suspension and rear-wing damage at a glance |
| **Fuel Calculator** | Fuel level, per-lap usage, laps remaining, refuel needed and full tanks to the end |
| **VE Calculator** | Same as Fuel Calculator, for cars that run on Virtual Energy (Hypercar, GT3) instead of fuel |
| **Weather** | Air/track temperature, rain, track wetness, and the session forecast |

Overlays appear automatically when you're on track and hide when you're not. Everything — position, size, opacity, visible columns/rows, colours — is configurable per overlay.

---

## How data is read

Telemetry comes primarily from the game's **shared memory**, read every tick. The game's local **REST API** (`localhost:6397`) is used only in a background thread to enrich a few things shared memory doesn't expose: the broadcast focus driver, standings details (car number, team name, class gap), the weather forecast, and suspension damage.

Two builds exist:
- **Standard** — shared memory + REST enrichment (all overlays fully populated).
- **without-rest-api** — shared memory only, for setups where the REST API is unavailable or undesirable. Identical except that REST-only signals (e.g. suspension damage) simply stay blank.

---

## Requirements

- **Le Mans Ultimate** (Windows)
- In-game: **Settings → Gameplay → Enable Plugins** must be **ON** — this is what publishes the shared memory the app reads. If you just enabled it, **restart the game**; it doesn't take effect on an already-running session.

---

## Download & run

1. Grab the latest `HyperTrace_x.x.x.zip` and extract it anywhere.
2. Run `HyperTrace.exe`. No Python install needed — everything is bundled.
3. Launch (or already be in) an LMU session. Overlays appear automatically once the game is on track.

Settings, positions and the enabled/disabled state of each overlay are saved to `%USERPROFILE%\.hypertrace\config.json` and persist between launches. Logs go to `%USERPROFILE%\.hypertrace\hypertrace.log` — check there first if something doesn't come up (e.g. the app started before LMU, or LMU is running elevated while the app isn't).

---

## The main window

A sidebar with four pages:

- **Overlays** — toggle each overlay on/off, open its settings (gear icon), and the **Global controls** card at the top:
  - **Lock / Free** — lock all overlays to prevent accidental dragging mid-race.
  - **Auto-hide** — hide every overlay unless you're actively driving on track (menus, replays, garage). Off by default.
  - **Merge Fuel & VE** — show a single calculator that automatically picks fuel or VE based on the car you're in.
- **Presets** — save and switch between full overlay layouts; one can be auto-loaded on startup.
- **Stream** — serve overlays to OBS (see below).
- **Broadcast** — production graphics for streamers (see below).

A status strip along the bottom always shows whether the game is connected and whether stream/broadcast are running.

### Positioning

**Drag** any overlay to move it — it snaps to screen edges and to other overlays when they line up. Arrow keys nudge a selected overlay pixel by pixel (hold Ctrl for larger steps).

---

## Stream mode

Each overlay can be served as a live PNG over HTTP for use as a **Browser Source** in OBS (or anything that can load a URL). Turn it on from the **Stream** page; each overlay gets its own URL at `http://localhost:<port>/<overlay>` (default port `8765`, configurable). Stream overlays are configured independently of the desktop ones, so you can size and lay them out for your scene without touching your on-screen setup.

## Broadcast mode

A separate set of production-style graphics — **Tower**, **Battle**, **Driver Card** and **Sectors** — plus a **Live Timing** panel with camera-focus control. Broadcast runs independently of Stream; turning on either one starts the local server on its own.

---

## Running from source

For development only — end users should use the packaged `.exe` above.

```bash
git clone <repo-url>
cd hypertrace

python -m venv .venv
.venv\Scripts\activate

pip install -e ".[dev]"

python -m hypertrace       # add --hz <n> to change the shared-memory poll rate (default 50)
                           # add --verbose for debug-level logging
```

To build the standalone executable:

```bash
pyinstaller HyperTrace.spec --noconfirm --clean
```

The result is written to `dist/HyperTrace/HyperTrace.exe`.

---

## Credits

HyperTrace's telemetry calculation engine and the overlay update/visibility engine are adapted from **TinyPedal** (GPLv3) — see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for details. All drawing, layout, the settings system, presets, stream mode and broadcast overlays are original to this app.
