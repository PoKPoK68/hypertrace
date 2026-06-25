# Changelog

All notable changes to LMU App are documented here.

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
