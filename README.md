# HyperTrace

Real-time telemetry overlay app for **Le Mans Ultimate**, built with Python and PySide6.

Draggable, configurable overlays sit directly on top of the game — no alt-tabbing, no browser window. An optional stream mode also serves any overlay as a browser source for OBS.

---

## Overlays

| Widget | Description |
|---|---|
| **Speed** | Speed, gear and an RPM shift-light bar |
| **Inputs** | Throttle / brake / clutch bars with a trace history |
| **Standings** | Multi-class live standings — gaps, lap times, pit/out badges, tyre compound, manufacturer logo |
| **Relative** | On-track proximity list of the drivers immediately around you, with live gaps |
| **Delta** | Last lap / best lap / live delta-to-best with a gain-loss bar |
| **Tyres** | Per-tyre carcass temperature (colour-coded to each tyre's own optimal temperature) and wear |
| **Fuel Calculator** | Fuel level, per-lap usage, laps remaining, refuel needed to the end of the session |
| **VE Calculator** | Same as Fuel Calculator, for cars that run on Virtual Energy (Hypercar, GT3) instead of fuel |
| **Weather** | Air/track temperature, rain, track wetness, and the session forecast |

All telemetry is read from the game's shared memory — overlays never call the game's REST API, which can be unstable mid-session.

Two additional pieces exist for broadcast-style production, currently on hold (stream-only, not shown as desktop overlays): a **Live Timing** panel and a set of **Broadcast** graphics (Tower / Battle / Driver Card / Sectors).

---

## Requirements

- **Le Mans Ultimate** (Windows)
- In-game: **Settings → Gameplay → Enable Plugins** must be **ON** (this is what publishes the shared memory the app reads). If you just enabled it, **restart the game** — it doesn't take effect on an already-running session.

---

## Download & run

1. Grab the latest `HyperTrace_x.x.x.zip` and extract it anywhere.
2. Run `HyperTrace.exe`. No Python install needed — everything is bundled.
3. Launch (or already be in) an LMU session. Overlays appear automatically once the game is on track.

Settings, positions and the enabled/disabled state of each overlay are saved to `%USERPROFILE%\.hypertrace\config.json` and persist between launches. Logs go to `%USERPROFILE%\.hypertrace\hypertrace.log` — check there first if something doesn't come up (e.g. the app started before LMU, or LMU is running elevated while the app isn't).

---

## Controls

- **Drag** any overlay to reposition it. Dragging near a screen edge or another overlay snaps it into alignment.
- **Lock** all overlays from the main window to prevent accidental dragging mid-race.
- **Per-overlay settings** — gear icon on each overlay's row in the main window: size, opacity, font size, visible columns/rows, decimals, colours, and more, depending on the widget.
- **Hide in garage** — optionally hide every overlay while you're in the garage, not just off-track.
- **Presets** — save/load a full overlay layout, with an option to auto-load one on startup.

---

## Stream mode

Each overlay can also be served as a PNG image over HTTP, for use as a Browser Source in OBS (or any tool that can load a URL). Enable it from the main window's **Stream** tab; each overlay gets its own URL at `http://localhost:<port>/<overlay>` (default port `8765`, configurable).

---

## Running from source

For development only — end users should use the packaged `.exe` above.

```bash
git clone <repo-url>
cd hypertrace

python -m venv .venv
.venv\Scripts\activate

pip install -e ".[dev]"

python -m hypertrace          # add --hz <n> to change the shared-memory poll rate (default 50)
                            # add --verbose for debug-level logging
```

To build the standalone executable:

```bash
pyinstaller HyperTrace.spec --noconfirm --clean
```

The result is written to `dist/HyperTrace/HyperTrace.exe`.
