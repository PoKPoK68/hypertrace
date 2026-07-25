# Changelog

All notable changes to HyperTrace (formerly LMU App) are documented here.

---

## [1.0.1]

### Damage overlay
- **Reworked car silhouette** — the wheels are now tucked flush against the bodywork instead of standing well clear of it, with the flanks broken open at each wheel arch, and the suspension arms moved in to match. Purely visual; the zones and what they show are unchanged.

### Fuel & VE Calculators
- **New "Reset AVG 5" setting** — the rolling 5-lap average can now auto-reset **Never** (default, unchanged), **At session start**, or **On pit exit**.

### Fixes
- **Deleting the active preset now loads its replacement** — before, deleting the preset you were currently using switched the selection to another one but left every overlay in the deleted layout until you loaded it by hand.

---

## [1.0.0] — Renamed to HyperTrace

*(0.8.0 was never released publicly — its changes are folded in below, all counted against 0.7.2.)*

### Renamed: LMU App → HyperTrace
- The app is now called **HyperTrace**, with a new icon. Settings/logs moved from `~/.lmuapp/` to `~/.hypertrace/` — **nothing is carried over automatically**: you'll start with default overlay positions and **your presets need to be recreated**. Once you're set up, the old `~/.lmuapp` folder is no longer used and can be safely deleted.

### New: Damage overlay
- **New "Damage" widget** — top-down car silhouette , 17 zones total: 4 body edges + 4 corners, 4 wheels, 4 suspension wishbones, and the rear wing as its own zone. Each zone is coloured on a 4-level severity scale (grey/amber/orange/bright red for the most severe level).
- **Wheels** show detached/punctured state; **suspension** shows REST-only damage tiers; **body zones and the rear wing** are shared memory. No text or numeric readout — the silhouette is the whole display, matching the design spec.
- Suspension damage is REST-only — LMU has no shared-memory equivalent for it.

### Main window redesign
- **Sidebar layout** — the window is now a wider (560px) panel with a navigation rail on the left (Overlays / Presets / Stream / Broadcast, active page marked with an amber bar) instead of the old top tabs, in the style of typical sim-racing companion apps.
- **Header bar** — app name and version always visible at the top, on every page.
- **Status footer** — a permanent strip at the bottom shows at a glance whether the game is connected, REST enrichment is active, the stream is on, and broadcast is on.
- **Global controls grouped** — Lock/Free, Auto-hide and Merge Fuel & VE now live in a visually distinct "Global controls" card at the top of the Overlays page.
- **One single preset control** — a dropdown to switch, plus Save / Save As, at the bottom of the Overlays page; the active preset is also highlighted in the Presets page list.
- **Deleting a preset now asks for confirmation** — the trash button turns into a check on first click; clicking the check confirms the deletion, and it reverts to a trash on its own after a couple of seconds if you don't. No popup dialog.
- **Fixed Broadcast settings resetting on every launch** — the app was force-resetting that toggle to on at startup regardless of what was saved; it now stays exactly as you left it.
- **Tower is now off by default** on a fresh install, matching Battle/Driver Card/Sectors (it used to be the only one of the four turned on automatically).
- **Each preset is now its own file**, under a new `presets/` folder next to the config, instead of all being bundled together inside the main config file — easier to back up, share, or edit a single preset by hand.
- Internal: the window's small custom controls moved to their own module (`main_window_controls.py`), the hand-rolled segmented buttons and the triple-duplicated Battle/Driver Card/Sectors exclusivity were replaced by two small reusable components, and the toggle colors moved into the central theme.

### Fuel & VE Calculators
- **Fixed REFUEL showing absurd values** (a long race with a low-consumption class could show a refuel amount many times over 100%). REFUEL now shows what actually makes sense to add at your *next* stop, capped to what the tank can hold; the old "FINISH" column is now **"TO END"** and shows the *total* amount still needed for the rest of the race, uncapped — which is what could grow that large, just correctly labeled now.
- **New "TANKS" column** — number of full tanks/refills still needed to reach the end of the race, e.g. 400L needed with a 50L tank reads "8.0". Shown alongside "TO END".
- **REFUEL and TO END now also work in Practice and Qualifying**, not just Race.
- **More accurate numbers overall** — LAST and AVG 5 now read each lap's consumption from the same background engine that already ran everything else in the app, instead of a simpler estimate computed inside the widget itself. Laps remaining now accounts for exactly where you are on the current lap rather than rounding to the nearest whole lap.
- **Fixed the VE bar always showing green regardless of level** — it now turns orange under 25% and red under 10%, matching the VE column in Standings.

### New: Auto-hide (replaces "Hide in garage")
- New **Auto-hide** toggle in Global Controls (Overlays page) — when on, every overlay hides automatically unless you're actively driving on track, same as the game's own on-track detection. Off by default.
- **Replaces the old "Hide in garage" toggle**, which is now removed for desktop overlays — Auto-hide already covers the garage case and more (menus, replays, anywhere you're not actually driving). The Stream page keeps its own separate "Hide in garage" toggle, unaffected.

### Class badges
- **LMP2 and LMP3 now show their full names** instead of "P2"/"P3" wherever a class badge appears.

### Under the hood
- **One typeface across the whole app** — the Live Timing panel was still drawn in the system font, and its session clock in a third font again, while everything else used Montserrat; all of it now matches. The unused JetBrains Mono and Saira SemiCondensed files are no longer bundled either, which takes about a megabyte off the download.
- **REST enrichment no longer runs when there's nothing to enrich** — the background thread that queries LMU's local API (car numbers, team names, class gaps, weather forecast, suspension damage) used to send requests five times a second even with the game closed, on a loading screen or alt-tabbed. It now waits until a session is actually live.
- **Third-party attribution** — the app now ships a `THIRD_PARTY_NOTICES.md` crediting the GPLv3 project the calc engine and the overlay update loop are adapted from.

---

## [0.7.2]

### Widget settings
- **Per-session visibility** — every overlay's settings now have a "Visibility in session" section with Practice/Qualifying/Race toggles, so an overlay can be hidden during specific session types.
- **New "Apply to preset" button** — opens a checklist of every saved preset; tick any number of them and confirm once to write that overlay's current position and settings directly into all of them, without loading each one (and overwriting everything else in it) first.
- "Column order" entries (Standings) are now bold, matching the weight of the rest of the settings labels.

### Standings
- **VE/Fuel column is now shown by default.**
- **Fuel level for other cars now shows "-" instead of a value** — it isn't broadcast for other cars in online races, only the player's own is ever accurate. Virtual Energy is unaffected and still shown for everyone.

### Speed & Gear
- Fixed the speed digits shifting slightly as the value changes — same tabular-figures fix already used for lap times and gaps elsewhere.

### Main window
- "Hide overlays in garage" is now a pill toggle (matching the lock/free one) instead of a checkbox, labeled "Overlays visible/hidden in garage".
- Removed the description text above the preset list in the Presets tab.

### Broadcast
- **New master "Broadcast" on/off switch**, at the top of the Broadcast tab — lets you manually stop/restart REST (localhost:6397) without closing the app. REST still starts automatically on launch, unchanged.

---

## [0.7.1]

### Overlay visibility
- **Fixed overlays staying visible after being kicked back to the main menu** (e.g. a practice session with no qualifying/race after it), without hiding them early while still on track when a practice session's timer simply reaches zero. Visibility now checks whether the session clock is still actually advancing, instead of a session-phase flag that also flips the moment the timer runs out while still driving.

### Standings & Relative
- **Fixed remote opponents showing a PIT badge in multiplayer while clearly on track.** Per-car telemetry isn't reliably synced for remote vehicles over the network; the pit-lane detection for other cars now relies on a single, more reliable field instead of also factoring in telemetry data. The player's own pit-lane detection is unchanged.

---

## [0.7.0] — Data & rendering engine rewrite

### Engine
- **The telemetry/calculation engine has been rebuilt on a more robust, modular architecture.** Data reading, session detection, delta/fuel/VE calculations, standings/relative gaps, and the overlay update/visibility engine now run on proven patterns instead of this app's own earlier hand-rolled logic (see `THIRD_PARTY_NOTICES.md` for the open-source reference this was adapted from). The visual design, layout, colors, fonts and all settings of every overlay are unchanged — only what's underneath changed.
- Fixes several long-standing sources of fragility this way: session-reset detection (used to reset fuel/VE history, outlap/pit badges) is now based on a robust signal instead of a heuristic; the local player's telemetry is now matched by car ID instead of trusting a raw index, which is more reliable when the game reorders internal arrays; on-track detection now reflects actually driving (ignition/realtime state) rather than just "a session is running".
- Per-car sector times (used for gap columns) now come directly from shared memory instead of a slower REST poll — one less thing relying on the REST API to work.

This is a foundational change — please report anything that looks off, especially around session transitions (practice → qualify → race, or restarting a session).

### Presets
- **Presets are now created and saved from the Overlays tab.** A "Preset" row shows the currently loaded preset, with a **Save** button to overwrite it and a **Save As…** button that swaps the row for a name field to create a new one.
- **Removed the "Auto-load on session change" checkbox and the Practice/Qualifying/Race dropdown assignments.** Replaced with a **"Preset per class"** panel in the Presets tab — one dropdown per car class (Hypercar, LMP2, LMP3, GT3, GTE) to pick its dedicated preset, which then loads automatically as soon as you're driving a car of that class.

### Class colors
- **Removed the Colors tab.** Vehicle class colors (Hypercar, LMP2, LMP3, GT3, GTE) are no longer user-configurable and always use the app's defaults.

### Main window
- The control panel window can no longer be resized taller/shorter by dragging its edge — its height now follows each tab's own content instead.

### Widget settings dialogs
- **Fixed the Copy / Paste / Reset buttons clipping their text** on every overlay except Standings (whose settings dialog is wider due to its side panel). Shortened to "Copy" / "Paste" / "Reset".

### Delta
- The Last/Best lap time values and the live delta value are now smaller and closer in size to each other, instead of the delta being noticeably larger than the times.

### Speed & Gear
- **RPM bar shift light** — the bar now reads full at 92% of max RPM instead of 100%, and blinks blue every 100 ms from 95% onward as a shift cue.

### Weather
- The wetness row is now labeled "WETNESS" instead of the more ambiguous "WET".

---

## [0.6.13] — Performance & CPU usage

### Game freezing / CPU usage
- **Fixed the app causing the game to freeze while overlays were visible.** Each overlay is a separate always-on-top, per-pixel-alpha window; Windows has to recomposite all of them on every repaint, which competed with the game for the same CPU cores under load — consistent with the freezes only happening while overlays were shown, never while idle. The app's process priority is now set to Below Normal on startup, so Windows favors the game whenever both want the same core.
- **Fixed the Pedals overlay running two independent 60 fps repaint timers at once** instead of one — halves its timer overhead for the same smooth trace scrolling.
- Lowered the refresh rate of Weather, Standings, Fuel Calculator and VE Calculator to 1 fps — none of them show fast-changing values, so the higher rate was pure overhead.
- Lowered the Pedals overlay's own refresh rate from 60 fps to 30 fps.

### Fuel & VE calculators
- **Fixed the Fuel Calculator rendering a few pixels narrower than the VE Calculator.** Both size their table columns from a reference value string, and `%` (VE) renders wider than `L` (Fuel) at the same size; Fuel Calculator now sizes off the same reference so the two always match.

### Tyres
- **Hard tyre badge now uses the exact same red as the Hypercar class badge**, instead of a separate red that was close but not identical.

---

## [0.6.12] — Documentation

### README
- Fully rewritten — it still only described 6 of the 9 overlays and a source-only install. Now covers every current overlay, the packaged `.exe` as the primary way to run the app, stream mode, controls (snap, lock, presets, hide-in-garage), and where config/logs live.
- Corrected the in-game requirement: **Settings → Gameplay → Enable Plugins**.

---

## [0.6.11] — Montserrat font, layout fixes & coherence pass

### Overlay defaults
- **Fixed the VE Calculator being disabled by default on a fresh install** — every other overlay defaulted to enabled, this one alone was hard-coded off in the config defaults.

### Overlay sizing
- **Fixed overlays shrinking the instant any setting was first touched, and rendering oversized before that.** The code's own default scale (115%) disagreed with every widget's own settings-schema default (100%): a fresh install rendered at 115%, then the settings dialog would apply the schema's 100% the first time any control was touched. The code default is now 100%, matching every schema (Delta's own default scale also moved from 80% to 100%, per the same "always 100%" rule).
- **Recalibrated base sizes now that 100% is honest.** Tyres, Speed, Weather, and the Fuel/VE calculators used to be inflated by the 115% bug without anyone deciding it that way; their own pixel dimensions are increased so 100% still looks like what those widgets have always looked like. Delta — deliberately doubled earlier — is brought back down to exactly double its *original* size now that there's no extra 80%→100% scale change compounding on top of it.

### Overlay positioning
- **Fixed magnetic snap triggering across the whole screen.** X and Y snapping were evaluated independently, so a peer overlay whose edge happened to line up would snap even hundreds of pixels away on the other axis. Snapping to a peer's edge on one axis now requires that peer to actually be nearby on the other axis; ordinary stacking/side-by-side snapping with a normal gap is unaffected.

### Lap time colors
- **Fixed the last-lap color (purple/green) never showing on a new personal or session best**, in Standings, Delta and Live Timing. `best_lap` is the minimum lap time *including* the last one, so the instant a lap sets a new best, `last_lap` and `best_lap` become equal — the strict `<` comparison could (almost) never be true at exactly the moment it should fire. Changed to `<=` for this specific "did my last lap equal my best" check (unrelated to the other strict comparisons, which compare a live time against a separate, unmoving reference).

### Standings
- Column header labels (`GAP`/`INT`/`BEST`/`LAST`) reduced by two sizes — they matched the driver-name size, which read as too large (a one-size reduction wasn't a big enough step to notice).

### Relative
- Added a small gap between the position chip and the driver name.
- Added a small gap between the name/badge zone and the relative-time value, so a wide value like `+123.4` no longer touches a `PIT`/`OUT`/`GAR`/`L`*n* badge — the column width reference was based on a 2-digit gap (`+12.x`), too narrow for the 3-digit gaps a long track like Le Mans can produce; it now matches Standings' `+999` reference.

### Speed & Gear
- **Fixed the still-oversized gap between `KM/H` and the gear.** The widget's width was computed from a content-area height formula that didn't match the one `paintEvent` actually used (40 px assumed vs 26 px real), sizing the layout for text far larger than what gets drawn and leaving a large unexplained gap. Both now share one formula.
- **Fixed the gear digit being clipped on the left.** The gear column was sized to fit `"8"`, but `"N"` (neutral — shown any time you're stopped) and `"R"` are both wider; Qt clips `drawText` to its bounding rect by default, so the left edge of those glyphs was silently cut off. The reference now covers every character the gear display can show.

### Fonts / bold text
- **Class badge (standings) and status badges (`GAR`/`PIT`/`OUT`/`L`*n*, standings and relative) now render with the same synthetic-bold weight as the rest of the text.** Requesting a heavier `QFont.Weight` has no effect since only one Montserrat weight is bundled; at these small sizes the single embedded weight reads as visibly thinner than larger text.

### Delta
- The "no lap yet" placeholder is a `-` (hyphen) instead of an em-dash, which rendered as a disproportionately large solid bar (35 px wide vs 10 px) next to the lap-time digits.

### Fuel & VE calculators
- The `VE`/`FUEL` bar and level labels were noticeably smaller than the value next to them; bumped from an 8 px to an 11 px render size.

### Shared memory
- **Fixed the app never receiving data when started before LMU.** `mmap` with a tag name *creates* the mapping when it is missing, so the app attached to its own empty mapping, reported a successful connection and read zeros forever. The mapping's existence is now probed first, and a mapping that only ever reads zeros is dropped and reconnected. Launch order no longer matters.
- Failures now report the Windows error code, distinguishing "LMU is not publishing" from "access denied" (elevation mismatch).
- Added a rotating log file in `~/.lmuapp/lmuapp.log`: the packaged app has no console, so nothing was diagnosable on a machine without Python. Each overlay also logs why it is shown or hidden.

### Standings
- **Status badges (PIT / GAR / OUT / L*n*) now have their own column** instead of being drawn over the end of the name column, where they truncated long names. It can be reordered like any other column.
- Badge width is derived from the actual text metrics, so labels keep an even margin at every font size instead of touching both edges.
- **Manufacturer logos are sharp again** — they were rasterised at 3× and shrunk by the painter, whose bilinear filtering softens a >2× downscale. Vector logos are now rasterised directly at their on-screen size.

### Text rendering
- **Letter tracking removed everywhere.** The 14% tracking applied to labels visibly spaced out short codes (`GT3`, `GAR`) and pushed centred single glyphs off-centre.
- The synthetic-bold workaround introduced in 0.6.9 is now limited to text containing digits. Applying it to driver names and labels made them look blurry, since it works by drawing the text twice with a sub-pixel offset.

### Relative
- The header shows only the **remaining** session time; the previous "elapsed / total" form was twice as wide and got clipped with a narrow name column.

### Typography
- **Montserrat Bold is now the app font**, for text and numbers alike. The OpenType `tnum` feature is enabled on numeric text so every digit keeps the same advance — lap times, gaps and the live delta stay aligned instead of shifting on each update. JetBrains Mono remains as a fallback.
- **Font sizes are now expressed in pixels** rather than points. A point size is converted using the screen DPI and then rounded, so consecutive settings steps could render identically; pixel sizes always differ. Overlays also render identically on machines with different DPI or Windows scaling.
- Fixed the smallest font sizes rendering identically: a floor in the derived sizes made steps 7 and 8 produce exactly the same text.

### Standings & Relative
- Default font size raised to **11**; default name width lowered to **150 px**.
- **Header height now follows the font size** — it was a hard-coded constant, so it never adapted.
- **Column header labels are now the same size as driver names** (same perceived weight), instead of a smaller derived size.
- The name column is configured in **pixels** with a slider instead of a character count, which no longer maps to a width with a proportional font. Names are elided to the real column width instead of being cut at N characters.
- **Standings**: fixed pit/out-lap badges never resetting on a session change or restart — the same fix applied to Relative in 0.6.9 had been missed here, so a stale `OUT` / `PIT` / `L*n*` badge could survive into the next session.
- **Relative**: the gap/interval column width is now measured from real font metrics instead of a per-character estimate, which could run 2 px too narrow at large font sizes and clip the value.
- Fixed a stale fallback color (`#ffc800`) used only when a saved config predates the `player_color` setting; it no longer disagrees with the setting's own default (`#ECAA43`).
- A `-` dash is always white (`T.TEXT`), never dim (`T.DIM`) — fixed one remaining case in the Standings VE/Fuel column, and unified it from `---` to a single `-` like every other empty value.

### Tyres
- Removed the compound-badge letter (S/M/H/W) — unreadable at this size; the badge colour alone already identifies the compound.

### Delta
- Widget doubled in size (200×… instead of 100×…), fonts scaled to match.

### Speed & Gear
- Fixed **`KM/H` overlapping the gear** — the widget width was a hard-coded constant that assumed the previous monospaced font; Montserrat's wider digits made the speed block alone exceed it. Width is now computed from the fonts actually in use.

### Pedals
- Fixed the trailing `0` being clipped on `100`: the value box was 1 px narrower than the text it had to hold.

### Removed
- `DEFAULT_COLUMNS` (Standings): a stale, unused module constant listing an outdated set of default columns.

---

## [0.6.10] — App icon & display fixes

### App icon
- The application logo is now used for the **window title bar** and the **taskbar**.
- Windows: an explicit AppUserModelID is set so the app no longer inherits the Python icon and gets its own taskbar entry when run from source.
- A `.ico` is generated from the logo and embedded in the executable, giving `LMUApp.exe` its own icon in Explorer and when pinned.

### Fuel & VE calculators
- Units are no longer separated from the value: `58.0%` and `58.0L` instead of `58.0 %` / `58.0 L`.
- Since columns are sized to their content, the widget is **19 px narrower** as a result (233 → 214 px).

### Weather
- Fixed the **flattened `0`** on temperatures, RAIN/WET percentages and the forecast node labels — same hinting artefact already fixed elsewhere in 0.6.9.

### Settings
- **Column order (Standings)**: fixed rows painting on top of each other when toggling a column or reordering. Rows removed from the layout stayed children of the container and kept being drawn until the next event-loop pass.

---

## [0.6.9] — Performance, text rendering & pit detection

### Performance
- **Stream mode no longer stutters the on-screen overlays** — PNG encoding moved off the Qt GUI thread onto a dedicated encoder thread with a latest-wins queue. The GUI thread now only rasterises the widget; the zlib compression runs on another core.
- **Reader split into two cadences** — the heavy full-field scan (all vehicles, REST merge, telemetry loop) is throttled to ~10 Hz while player telemetry stays at full rate, cutting allocations and GC churn by ~5×. Standings/relative already sampled at 5-10 Hz, so there is no visible difference.
- Full-field rescan forced immediately on session change or when the car count changes, so the field is never stale.
- Reader micro-optimisations: memoized string decoding (driver/team/class/model names were decoded for every car on every tick), compound-type map hoisted to a module constant, `import math` moved out of the hot path.
- **Pedals overlay** — dedicated 60 fps render timer and wall-clock trace scrolling, decoupled from the 50 Hz data feed (removes the 60/50 Hz beat stutter).

### Text rendering
- Fixed the **flattened `0`** and the **asymmetric capital `M`** at small sizes: font hinting snapped round glyphs to the pixel grid. Hinting is now disabled on the affected text, with synthetic bold (`draw_bold`) restoring the weight that hinting used to provide.
- Applied to session headers (relative, standings), tyre temperatures and wear %, the compound badge letter, the `KM/H` unit and driver names in standings, relative and broadcast.
- Compound badge letter is now correctly centred — the label letter-spacing added a trailing gap that pushed a lone glyph off-centre.

### Pit detection
- **PIT badge now appears after leaving the garage.** No single field covers every case: `mPitState` only tracks a pit *stop* sequence, and `mInPits` stays false when driving out of the box. `in_pit_lane` now combines `mCurrentSector`'s pit-lane sign bit, `mPitState >= 2` and `mInPits`.
- Handles the undocumented `mPitState = 5` observed when leaving the garage (the header only documents 0-4).
- Pit state is centralised in the reader instead of being re-derived in each widget, and is used by standings, relative, broadcast and live timing.
- **Relative**: `GAR` badge added for the player — other drivers in the garage are filtered out of the list, so the case was never handled and showed `PIT` instead.

### Session handling
- New `session_id`, bumped on session change **or restart**, giving widgets a reliable per-session reset signal. Fuel calculator, VE calculator and relative badges now use it instead of the fragile "lap counter went backwards" heuristic.

### Tyres
- Tyre colours are now derived from each tyre's **own optimal temperature** (`mOptimalTemp`, read per wheel) instead of fixed thresholds, so they adapt per car and per compound.
- The four temperature-range settings (Cold below / Optimal from / Optimal to / Hot above) have been removed — they no longer have any meaning.

### Weather
- The forecast is now fetched by the reader; **the weather widget no longer performs any REST call**.
- Current sky type is read from shared memory (`mCloudCoverage`) and shown immediately while the forecast loads, instead of "NO DATA".
- Forecast fetched at launch and refreshed on every session change.

### Manufacturer logos
- **Logos were never displayed** — the loader pointed at a non-existent folder, searched for `.png` while the files are `.svg`, and used a matching rule that could never succeed.
- SVGs are now rendered at the target size via `QSvgRenderer` (sharp at any scale) rather than rasterised at source size and downscaled.
- PNG sources are supported too: the Porsche "SVG" was a raster image wrapped in an SVG (`pattern` + embedded base64), which Qt's SVG 1.2 Tiny renderer cannot draw.

### Fuel & VE calculators
- Table columns are now sized to their content instead of being split equally — `REFUEL` was truncated (`+99.9 %` needs 52 px but only had 35).
- Values keep one decimal up to 99.9 and drop it at 100 (`100 %` / `100 L`, never `100.0 %`).
- Missing values display a single `-`.

### Removed
- Offline/mock mode fully removed: `MockReader`, the `mock` parameter of `DataReader`, the `tests/` directory and the pytest configuration.

---

## [0.6.8] — Broadcast polish & lap time color fixes

### Broadcast Tower
- **P1 row** now shows best lap time (practice/quali) or "LEADER" (race) in the GAP and Interval columns
- Column header labels now align correctly with the data column (was offset by the logo column width)
- POS +/- column is now per-class in Overall mode (was overall position delta)
- Column headers renamed: "Interval" (was "INT"), "Pos +/-" (was "POS")

### Broadcast Battle
- Gap display is now refreshed every 2 s to avoid visual noise
- Rival filter now tolerates ±1 lap difference (prevents card disappearing when crossing the finish line)

### Broadcast Driver Card
- Last lap time is now colored purple/green when improved, white otherwise (was always white)

### Broadcast Sectors
- Sector bars thickened to 26 px; sector time displayed inside the bar
- After crossing the finish line, sector data stays visible for 10 s then goes blank

### Lap time color convention — all overlays
- **Strict `<` comparison everywhere** — equal times are no longer considered an improvement (no more `+0.001` / `+0.002` tolerance)
- Rule: `last < personal_best` → green; if also `personal_best ≤ class_session_best` → purple
- Same logic applied to sectors: `t < personal_sector_best` → green; `t < class_sector_best` → purple
- Applied across `broadcast.py`, `live_timing.py`, `standings.py`, `delta.py`
- No improvement → yellow in broadcast overlays and live timing; white in standings and delta

### Refresh rate
- All broadcast overlays reduced to 20 Hz (was higher)

---

## [0.6.7] — Compound badges & sector color fixes

### Broadcast overlays — compound badges
- **Driver Card, Battle, Sectors**: tire compound badge added to each widget
  - 4 identical compounds → large circle with letter (S / M / H / W) on colored background (red / yellow / grey / blue)
  - Mixed compounds → 4 small colored dots (no letter), same footprint as the circle
- Compound data sourced from `mWheels[i].mCompoundIndex` (shared memory, all vehicles) cross-referenced with the TireManagement REST endpoint polled every 30 s for the authoritative index→name mapping
- **Driver Card, Battle, Sectors are mutually exclusive** — enabling one automatically disables the other two

### Sector color convention (Broadcast Sectors)
- **Purple**: session best in class (≤ leader's reference time)
- **Green**: personal improvement (≤ own personal best)
- **Yellow**: worse than personal best
- Previously, green was shown when faster than the previous lap (not vs personal best) and all three bars turned yellow on lap completion

### Live-timing standings
- Sector color fix also applied to the "last lap" column: purple = session best, green = personal best, white otherwise

---

## [0.6.6] — Overlay UX & settings polish

### Overlay positioning
- **Snap to screen edges** — overlays magnetically snap to screen edges when dragged within 5 px
- **Snap to other overlays** — overlays also snap to each other's edges and sides for easy alignment
- **Keyboard nudge** — hold left mouse button on an overlay then use arrow keys to nudge 1 px at a time; Ctrl+arrow moves 10 px

### Settings dialog
- **Reset to defaults** button — restores all settings for a widget to their default values in one click
- **Standings**: reorganised sections — font size moved to Appearance; cleaner labels; "Player row" and "Badges" sections; columns listed in logical order with decimals immediately below their toggle
- **Relative**: restructured — Appearance (opacity/scale/font size), Rows (drivers + gap decimals), Names, Player row, Header (content hidden when header is off), Badges
- **Fixed**: horizontal scrollbar no longer appears in the Standings config dialog
- **Fixed**: dialogs without a side panel are now constrained to 400 px width; scrollbar no longer collides with content

### Fonts
- **JetBrains Mono zero** — the zero digit is now a plain oval (no slash, no dot), eliminating confusion with 8

---

## [0.6.5] — Manufacturer logos in broadcast overlays

### Broadcast Tower
- **Manufacturer logo column** — a logo column between position and car number displays the manufacturer brand logo, sourced from `assets/brandlogo/`; matched from the vehicle model name (`mVehicleModel` from telemetry data)

### Broadcast Driver Card
- **Manufacturer logo** — logo displayed between position number and car number on the main row

### Broadcast Battle
- **Manufacturer logo** — small logo shown below the car number in each driver's position column

---

## [0.6.4] — Delta overlay & bug fixes

### New: Delta overlay
- **Last Lap / Best Lap / Delta** — compact overlay showing last lap (color-coded: purple = class best, green = personal best, white = no improvement), personal best lap in purple, and live delta vs best lap
- **Delta bar** — centered bar visualising the gap (green left = gaining, red right = losing); range configurable in settings
- Available in stream mode

### Bug fixes
- **Parade crash** — broadcast tower no longer crashes when all drivers DNF or enter garage while parade mode is active
- **QBuffer leak** — stream PNG buffers are now explicitly closed after each render (was leaking at 30 Hz)
- **REST race condition** — `_rest_focus` and `_rest_data` now protected by a dedicated lock; reads take a snapshot to minimise lock hold time
- **REST thread not joined** — `LMUReader.stop()` now joins the REST thread before returning
- **Bounds check on `playerVehicleIdx`** — guards against out-of-range telemetry index (0–103)
- **Session reset** — fuel/VE history and pit/outlap badges now clear correctly when a new session starts

---

## [0.6.3] — Live Timing & Pedals

### Live Timing
- **Sector times** — S1 / S2 / S3 columns added; shows current in-progress sectors when available, falls back to last lap; color-coded per class (purple = class best, green = personal best, yellow = no improvement)
- **Session label** — displays full name (PRACTICE / QUALIFYING / RACE) instead of abbreviated code
- **Header order** — session name first, then remaining time, then track name

### Pedals (stream)
- **Per-pedal toggles** — throttle, brake and clutch can each be enabled or disabled independently; widget resizes automatically
- **Per-channel trace toggles** — each trace curve (T / B / C) can be shown or hidden independently
- **Stream refresh rate** — configurable per widget via `stream_hz`; tick loop runs at 60 fps with per-widget throttling

---

## [0.6.2] — Visual polish

### All overlays
- **JetBrains Mono everywhere** — F_TEXT and F_NUM unified, Bold by default, TypeWriter style hint to ensure correct font resolution
- **Dashes "-"** are always white in all columns (best, last, gap, interval)

### Standings
- **Per-class best lap** — purple only for the best time within a driver's own class (multiclass fix: HYP and GT3 each have their own reference)
- **VE/Fuel color coding** — green ≥ 20% / 20 L, orange < 20, red < 10
- **Position column** widened to fit 2-digit numbers
- **Header font** separated from class badge font — column labels at 7.5 pt, badges unchanged

### Tyres
- **Uniform spacing** — outer margins and inter-tyre gaps are identical (`_G = 4 px`)

### Relative
- **Interval column** — width adjusts dynamically based on the configured decimal count

### UI
- Live Timing no longer opens automatically on startup

---

## [0.6.1] — Overlay size & camera polish

### All overlays
- **Default size +15 %** — all overlays are 15 % larger out of the box; configurable via a single `DEFAULT_SCALE` constant in `base.py`

### Live Timing
- Camera switching to WS / CP is now significantly faster — advances the Onboard ring in one calculated step instead of polling in a loop
- CP camera fixed: corrects off-by-one errors with a single verification pass after switching

---

## [0.6.0] — Broadcast mode & Live Timing

### New: Broadcast tab
- New **Broadcast** tab in the main window, dedicated to director / broadcast tooling
- **Tower** overlay — live standings rendered as a broadcast tower; three modes: *Overall* (top N), *Multiclass* (top N per class), *Class* (top N of one class)
- **Battle** overlay — highlights the two drivers currently fighting for position
- **Driver Card** overlay — shows the currently viewed driver's name, position and gap
- Toggle between **Driver Name** and **Team Name** display across all broadcast overlays (full name shown, never truncated)
- Tower, Battle and Driver Card can each be enabled or disabled independently
- A single **/broadcast** browser-source URL combines all three overlays into one OBS source — copy it directly from the tab

### New: Live Timing Panel
- Standalone window opened from the Broadcast tab via **Open Live Timing Panel**
- Full live timing table: position, class color chip, car number, driver / team name, class, best lap, last lap, gap to leader and status
- **TV / WS / CP camera buttons** on every driver row — click to focus that driver *and* switch camera simultaneously:
  - **TV** — TracksideCycle (broadcast trackside cameras)
  - **WS** — Windshield onboard
  - **CP** — Cockpit onboard

### Stream
- **Hide in garage** checkbox — overlays go transparent while the player is in the garage; re-appear automatically on track

---

## [0.5.1] — Stream improvements

### Stream
- **OBS clears on exit** — a transparent frame is pushed to all overlays before the server stops, so OBS shows nothing instead of a frozen image
- **Hide in garage** — new checkbox in the Stream tab; when checked, stream overlays go transparent while the player is in the garage
- Stream tab moved after Presets in the tab bar

---

## [0.5.0] — Stream mode & Weather overlay

### New: Stream mode
- **Stream tab** — new tab in the main window to configure OBS integration
- Local HTTP server (configurable port) serves each overlay as a browser source URL
- Each overlay can be enabled/disabled independently for stream, with its own settings (opacity, scale, etc.)
- **Copy URL** button per overlay to paste directly into OBS Browser Source

### New: Weather overlay
- Air temperature, track temperature, rain %, path wetness
- Session forecast with sky condition icons (clear → storm) polled from LMU's REST API

### Settings dialogs
- **Copy / Paste Settings** — copy settings from any overlay's config dialog and paste into another (e.g. normal → stream or vice versa)

### Standings & Relative
- Air / track temperature display is now left-aligned in the session bar

### Relative
- "Nothing" header option now fully hides the session bar instead of leaving it empty

---

## [0.4.2] — Visual fixes

### All overlays
- **Opacity now affects the accent hairline** — the yellow gradient at the top of each overlay fades with the opacity setting
- **Settings `show_if`** — dependent rows are now hidden entirely instead of grayed out

---

## [0.4.1] — Standings & Relative polish

### Standings
- **Lapped cars** — gap column shows `+1L`, `+2L`, etc. instead of a gap in seconds; uses `time_into_lap` to avoid false positives when the leader just crossed the finish line
- **Pit lap badge** — `L{n}` badge now has a yellow background and black text, fully opaque
- **Dynamic column widths** — GAP/INT columns sized for `+999.X`, BEST/LAST for `9:99.XXX`, computed from actual font metrics at the configured decimal precision
- **Uniform column spacing** — constant `_CP = 3 px` padding on each side of every column for consistent visual gaps
- **Header info** — single dropdown replaces three separate booleans; shows session letter + elapsed/total time side by side (e.g. `R  1:00:12 / 4:00:00`)

### Relative
- **Header info** — same dropdown as Standings; shows full session name + time (e.g. `RACE  1:00:12 / 4:00:00`)

---

## [0.4.0] — UI polish

### Main window
- **Presets** — save the current position and settings of all overlays as a named preset, load or overwrite it at any time
- Main window no longer stays on top of other apps

### Settings dialogs
- Visual style now matches the main window
- Standings settings use a two-column layout (less scrolling)

### Standings & Relative
- New name casing option: ALL CAPS / Name LASTNAME / Name Lastname

---

## [0.3.2] — Polish & bug fixes

### Speed
- Overlay is more compact
- RPM bar now spans the full width of the overlay
- The "KM/H" label repositions automatically depending on how many digits the speed has (e.g. "9" vs "300")

### Inputs
- Overlay is more compact
- Spacing between pedals, steering wheel and edges is now equal on both sides
- Throttle / brake / clutch bars are drawn as solid colors (lighter to render)

### Tyres
- Tyre name (FL / FR / RL / RR) is now centered inside its rectangle
- Temperature is displayed at the top center, above the tyre name

### Standings
- Position number is centered in its column
- PIT / GAR / OUT badge is now correctly aligned to the right edge of the name column
- Player's class header (e.g. "HYP HYPERCAR") stays visible even when "Show other classes" is turned off
- Long driver names (e.g. PIER GUIDI) no longer overflow onto the badge

### Relative
- Gap intervals are displayed in plain white — no more color distinction between drivers ahead and behind
- Player name is displayed in white like all other drivers (no more yellow highlight)

### Fuel Calculator / VE Calculator — Merge mode
- Rule is now clearly: **Hypercar or GT3 → VE Calc**; all other classes → Fuel Calc
- All `---` dashes are displayed in white (some were previously shown in grey)

### Main window
- ON / OFF buttons now have a solid, fully opaque background: bright green for ON, bright red for OFF
- Checkboxes now display a white tick when checked

### Fixed
- Fuel / VE overlay flickering when toggling Merge mode — fixed
- Fuel / VE overlay flickering in the garage while Merge mode was active — fixed
- VE Calculator not showing in Hypercar in some cases — fixed
- General rendering performance improvements (fewer calculations per frame)

---

## [0.3.1]

### Fixed
- **Fuel & VE Calculator** — The FINISH column now shows a value only when current fuel / VE is sufficient to finish the race; displays `---` if a pit stop is required

---

## [0.3.0] — Broadcast visual redesign

### New
- All overlays adopt a new broadcast style: dark translucent panel, thin amber accent bar at the top, custom fonts
- Custom fonts loaded at startup: JetBrains Mono for labels, Saira Semi Condensed for numbers
- Centralized color system: all overlays share the same design tokens

### Changes per overlay
- **Speed** — 18-segment RPM bar (green → amber → red), large speed number, gear in amber
- **Inputs** — vertical T/B/C bars, 3-spoke steering wheel with angle label
- **Tyres** — bars colored by temperature, FL/FR/RL/RR corner labels
- **Standings** — P1/P2/P3 in gold/silver/bronze, best lap in purple, player row highlighted in amber
- **Relative** — class color chip on position, colored gap (blue = ahead, orange = behind)
- **Fuel / VE Calculator** — blue fuel bar, green VE bar, unified table style
- **Main window** — dark panel, amber tab underline, custom drawn gear icon

### Fixed
- Crash at startup when a tyre temperature was 0
- Lock toggle colors were misaligned with the theme

---

## [0.2.0] — Fuel & VE Calculators

### New
- **Fuel Calculator** — fuel bar + table (last lap, 5-lap average, consumption, refuel needed, finish estimate), configurable safety margin
- **VE Calculator** — same as Fuel Calculator but for virtual energy (Hypercar), with fuel ratio display
- **Merge mode** — single toggle: automatically shows the right calculator based on car class (Hypercar / GT3 → VE Calc, others → Fuel Calc)
- Refuel detection: fuel spikes above 2 L are excluded from the consumption history
- Each element of the overlay can be hidden independently (bar, level text, rows, columns)
- Overlay width adjusts automatically to the visible columns

### Removed
- Old basic Fuel overlay replaced by the Fuel Calculator

---

## [0.1.2] — Standings & Relative

### New
- Player row highlight color and opacity are now configurable in Standings and Relative

---

## [0.1.1] — Quality of life improvements

### New
- Opacity control (0–100 %) on all overlays
- **Tyres** — 4 vertical bars (FL/FR/RL/RR): height = remaining wear, color = temperature
- **Fuel** — VE row auto-hides if no virtual energy is detected
- Animated lock toggle: green = free to move, gold = locked in place
- ON / OFF buttons per overlay in the main window

### Changed
- **Standings** — class headers shown as colored badges (HYP / P2 / P3 / GTE / GT3)
- Class colors inspired by WEC: Hypercar red, LMP2 blue, LMP3 purple, GT3 green, GTE orange
- Reduced default overlay sizes to take up less screen space

### Fixed
- Hypercars named "LMH" or "GTP" in-game were appearing below GT3 in the standings
- Overlay border remained visible at 0% opacity

---

## [0.1.0] — Initial release

### New
- Core architecture: live LMU data reading, resizable and draggable overlays
- Overlays: **Speed**, **Inputs**, **Fuel**, **Standings**, **Relative**, **Tyres**
- Main control window with per-overlay enable / disable
- Automatic config saving (positions and parameters)
- Per-overlay settings dialog
- Drag & drop and position lock
- PIT / OUT / GAR badges in Standings and Relative
- Outlap tracking in Relative
