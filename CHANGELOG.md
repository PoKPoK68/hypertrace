# Changelog

All notable changes are documented here.  
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [0.2.0] — Fuel & VE Calculators

### Added
- **Fuel Calculator** — fuel bar + table (LAST/AVG 5 rows, USAGE/LAPS/REFUEL/FINISH columns), configurable safety margin (default 1.0 lap)
- **VE Calculator** — VE and fuel bars, VE table, FUEL RATIO (last lap only, rounded up to 2 decimal places, no unit)
- **Merge mode** — single toggle: LMH/GTP/LMGT3 → VE calc, all others → Fuel calc; class-based, flicker-free
- Refuel detection: spike > 2 L excluded from consumption history
- Show/hide toggle for each element independently:
  - Fuel bar / fuel level text
  - VE bar / VE level text (VE calc only)
  - LAST row / AVG 5 row
  - USAGE / LAPS / REFUEL / FINISH columns
  - FUEL RATIO row (VE calc only)
- Dynamic width: widget shrinks with hidden columns (240 → 193 → 150 px min)

### Removed
- Old **Fuel** overlay replaced by Fuel Calculator

---

## [0.1.2] — Standings / Relative

### Added
- **Standings & Relative** — configurable player row highlight color and opacity
- Player name always displayed in white; bold text throughout

---

## [0.1.1] — QoL pass

### Added
- Opacity control (0–100 %) on all overlays
- **Tyres** — 4 vertical bars (FL/FR/RL/RR): height = remaining wear, color = temperature
- **Fuel** — auto-hide VE row when no virtual energy detected (10 zero ticks)
- Lock overlay: animated sliding toggle (green = free, gold = locked)
- Overlays tab: ON / OFF buttons per overlay

### Changed
- **Standings** — class header shown as colored badge (HYP/P2/P3/GTE/GT3)
- Class colors (WEC-inspired): Hypercar `#CC0000`, LMP2 `#1050C8`, LMP3 `#7020C0`, GT3 `#00A040`, GTE `#E06010`
- Reduced default sizes: Speed 75 %, Inputs 80 %, Fuel 85 %

### Fixed
- Hypercar appearing below GT3 when class name is "LMH" or "GTP"
- Overlay border visible at 0 % opacity

---

## [0.1.0] — Initial release

### Added
- Core overlay architecture: `BaseWidget`, `DataReader`, `LMUReader`
- Widgets: **Speed**, **Inputs**, **Fuel**, **Standings**, **Relative**, **Tyres**
- Main control window with per-overlay enable/disable
- Config persistence (JSON), configurable positions and parameters
- Generic `WidgetConfigDialog` driven by `CONFIG_SCHEMA`
- Drag & drop and overlay lock
- PIT / OUT / GAR badges in Standings and Relative
- Outlap tracking in Relative
