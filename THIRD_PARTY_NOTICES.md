# Third-party notices

HyperTrace's telemetry calculation engine (`hypertrace/calc/`) and the base
overlay update/visibility engine (`hypertrace/widgets/base.py`) are adapted
from **TinyPedal** (https://github.com/s-victor/TinyPedal), licensed under
the **GNU General Public License v3.0** (full text:
https://www.gnu.org/licenses/gpl-3.0.html).

## What was adapted

- The per-module background-thread calculation engine and the shared
  `minfo` singleton pattern (`hypertrace/calc/module_info.py`,
  `hypertrace/calc/module_control.py`, `hypertrace/calc/modules/_base.py`).
- The shared-memory connector and semantic accessor layer for Le Mans
  Ultimate (`hypertrace/calc/lmu_connector.py`, `hypertrace/calc/api.py`).
- The active/idle/paused realtime-state detection
  (`hypertrace/calc/realtime_state.py`).
- Individual calculation modules — delta, fuel, stint/session-reset
  detection, wheel data, vehicle/standings gaps
  (`hypertrace/calc/modules/module_delta.py`,
  `hypertrace/calc/modules/module_fuel.py`,
  `hypertrace/calc/modules/module_stint.py`,
  `hypertrace/calc/modules/module_wheels.py`,
  `hypertrace/calc/modules/module_vehicles.py`) — each simplified to what
  this app needs for Le Mans Ultimate specifically (single-sim, no GPS
  position smoothing, no hybrid/electric-motor state).
- A handful of small calculation/validation helpers
  (`hypertrace/calc/_calc_util.py`).
- The overlay widget base class's timer/visibility engine
  (`hypertrace/widgets/base.py`).

## What was not adapted / is original to this app

Everything else: all drawing/layout code, colors, fonts, the settings
system, presets, the REST API integration (`hypertrace/calc/ext/rest_merge.py`),
stream mode, broadcast overlays, the Live Timing panel, and the main window.

## License

Per the GPLv3, the adapted portions listed above remain subject to its
terms. This file exists to keep that acknowledgment in one place instead of
repeated inline throughout the source and changelog.
