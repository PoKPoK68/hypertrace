# Changelog

All notable changes to LMU App are documented here.

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
