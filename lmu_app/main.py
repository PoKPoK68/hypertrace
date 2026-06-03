"""lmu_app/main.py — Point d'entrée."""
from __future__ import annotations
import argparse, logging, sys
from PySide6.QtWidgets import QApplication
from lmu_app.api.reader import DataReader
from lmu_app.widgets.speed import SpeedWidget
from lmu_app.widgets.inputs import InputsWidget
from lmu_app.widgets.fuel import FuelWidget
from lmu_app.widgets.standings import StandingsWidget
from lmu_app.widgets.relative import RelativeWidget


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--hz", type=int, default=50)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    app = QApplication(sys.argv)
    app.setApplicationName("LMU App")
    app.setApplicationVersion("0.1.0")

    reader = DataReader(mock=args.mock, update_hz=args.hz)
    reader.start()

    widgets = [
    (SpeedWidget(reader,    auto_hide=False), 50,  50),
    (InputsWidget(reader,   auto_hide=False), 50, 190),
    (FuelWidget(reader,     auto_hide=False), 50, 370),
    (StandingsWidget(reader,auto_hide=False), 350, 50),
    (RelativeWidget(reader, auto_hide=False), 350, 310),
    ]
    for w, x, y in widgets:
        w.move(x, y); w.start()

    def on_quit():
        for w, *_ in widgets: w.stop()
        reader.stop()

    app.aboutToQuit.connect(on_quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
