# LMU App

Real-time telemetry overlay for **Le Mans Ultimate**, built with Python and PySide6.

Displays live race data directly on top of the game — no alt-tabbing required.

---

## Overlays

| Widget      | Description                                                              |
|-------------|--------------------------------------------------------------------------|
| **Speed**   | Current speed, gear and RPM bar                                          |
| **Inputs**  | Throttle, brake and clutch bars with a rotating steering wheel           |
| **Fuel**    | Fuel level and virtual energy with lap estimates                         |
| **Standings** | Multi-class live standings with gaps, lap times, pit status and fuel   |
| **Relative**  | On-track proximity list showing class position and time gaps           |
| **Tyres**   | Carcass temperature (colour-coded) and wear bar for all 4 tyres          |

---

## Requirements

- Python 3.11+
- Le Mans Ultimate (Windows)
- In-game: **Settings → Gameplay → Enable Plugins** must be **ON**

---

## Installation

```bash
git clone https://github.com/you/lmu-app.git
cd lmu-app

python -m venv .venv
.venv\Scripts\activate

pip install -e ".[dev]"
```

---

## Usage

```bash
# With LMU running
python -m lmu_app

# Offline mode — simulated data, no game needed
python -m lmu_app --mock

# Extra options
python -m lmu_app --mock --hz 60 --verbose
```

Each overlay can be dragged to any position on screen, locked in place, and configured independently via the main control window.

---

## Controls

- **Drag** any overlay to reposition it
- **Lock** overlays from the main window to prevent accidental movement
- **Configure** each overlay with its own settings panel (font size, columns, thresholds…)
