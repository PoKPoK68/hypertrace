# Third-party notices

## Bundled dependencies

### SVappsLAB.iRacingTelemetrySDK

Copyright (C) 2024-2026 Scott Velez.
Source: https://github.com/SVappsLAB/iRacingTelemetrySDK

Licensed under the **Apache License, Version 2.0** (full text:
https://www.apache.org/licenses/LICENSE-2.0). Distributed with HyperTrace
as an unmodified NuGet package; no changes have been made to it.

HyperTrace reads iRacing's live telemetry through this SDK — the shared
memory mapping, the variable table, the session-info block, and the
connect/disconnect lifecycle. Everything on HyperTrace's own side of that
boundary (`hypertrace/overlay/src/IRacing/`) is HyperTrace's: mapping the
SDK's types onto this app's `GameState`, and the per-lap fuel bookkeeping
the SDK does not provide.

Apache 2.0 is permissive and imposes no licensing obligation on
HyperTrace's own code or on the binary it distributes — unlike the GPLv3
situation described below, which is why that distinction is spelled out
here rather than left implicit.

### SkiaSharp

Copyright (c) Microsoft Corporation and contributors.
Licensed under the **MIT License**. Used for all overlay rendering.

## Historical acknowledgment

HyperTrace's original Python implementation (retired to `legacy/hypertrace/`
— see its own git history on the `legacy-python` branch) adapted portions
of its telemetry calculation engine and its overlay visibility engine from
**TinyPedal** (https://github.com/s-victor/TinyPedal), licensed under the
**GNU General Public License v3.0** (full text:
https://www.gnu.org/licenses/gpl-3.0.html).

The current C++/C# app does not contain that adapted code. The
functionally equivalent logic — fuel/energy/battery consumption tracking,
reference-lap-time and session-finish-type derivation, shared-memory field
extraction, and the auto-hide visibility gate — was independently
reimplemented for the rewrite: same observable behavior, different
internal design (see `hypertrace/bridge/src/consumption_tracker.hpp`,
`hypertrace/bridge/src/bridge_core.cpp`, `hypertrace/bridge/src/lmu_bridge.cpp`,
and `hypertrace/overlay/src/SessionActivity.cs`). No GPLv3 obligation
applies to the binary this app distributes.

TinyPedal is credited here as a courtesy, for the historical record of
where the original Python prototype's approach came from — not because
the current app incorporates any of its code.

## CrewChiefV4 (MIT)

`hypertrace/overlay/src/AssettoCorsa/AcTyreFloors.cs` carries the figure
each of Assetto Corsa's tyre compounds stops wearing at, taken from
[CrewChiefV4](https://github.com/mrbelowski/CrewChiefV4) (MIT), which
measured them. The game publishes a wear figure but nothing that says how
far it can fall, and the answer differs from compound to compound — 70 for
a road tyre, 98 for a vintage GP one — so a wear reading means nothing
without them.

What is used is that table of measurements, keyed by the compound name the
game itself publishes; no CrewChiefV4 code is used or adapted. MIT asks
only that the notice travel with the work, which is what this section is
for.

## License

This file exists to keep that historical acknowledgment in one place
instead of scattered through old commit messages and the changelog.
