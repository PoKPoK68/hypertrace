"""lmu_app/main.py — Entry point."""
from __future__ import annotations
import argparse, logging, sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
from lmu_app.api.reader import DataReader
from lmu_app.config import AppConfig
from lmu_app.widgets.speed import SpeedWidget
from lmu_app.widgets.inputs import InputsWidget
from lmu_app.widgets.standings import StandingsWidget
from lmu_app.widgets.relative import RelativeWidget
from lmu_app.widgets.tyres import TyresWidget
from lmu_app.widgets.fuel_calc import FuelCalcWidget
from lmu_app.widgets.ve_calc import VECalcWidget
from lmu_app.ui.main_window import MainWindow


_FONTS = [
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Medium.ttf",
    "JetBrainsMono-Bold.ttf",
    "SairaSemiCondensed-SemiBold.ttf",
    "SairaSemiCondensed-Bold.ttf",
]

def _load_fonts() -> None:
    from pathlib import Path
    from PySide6.QtGui import QFontDatabase
    from lmu_app.utils import theme
    fonts_dir = Path(__file__).parent / "assets" / "fonts"
    _text_set = False
    _num_set  = False
    for name in _FONTS:
        path = fonts_dir / name
        fid = QFontDatabase.addApplicationFont(str(path))
        if fid < 0:
            logging.warning("Font failed to load: %s", path)
            continue
        families = QFontDatabase.applicationFontFamilies(fid)
        logging.info("Loaded font %s → fid=%d families=%s", name, fid, families)
        if not families:
            continue
        family = families[0]
        # Take the first file's registered name only — subsequent weights of the
        # same typeface may register under "Family Bold" / "Family Medium" as
        # separate families; we want the base family that covers all weights.
        if "JetBrains" in name and not _text_set:
            theme.T.F_TEXT = family
            _text_set = True
        elif "Saira" in name and not _num_set:
            theme.T.F_NUM = family
            _num_set = True
    logging.info("Active font tokens — F_TEXT=%r  F_NUM=%r", theme.T.F_TEXT, theme.T.F_NUM)


def _dark_palette() -> QPalette:
    """Fusion dark palette — makes spinbox/combobox arrows visible on dark backgrounds."""
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(45,  45,  45))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(220, 220, 220))
    pal.setColor(QPalette.ColorRole.Base,            QColor(30,  30,  30))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(50,  50,  50))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor(30,  30,  30))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor(220, 220, 220))
    pal.setColor(QPalette.ColorRole.Text,            QColor(220, 220, 220))
    pal.setColor(QPalette.ColorRole.Button,          QColor(55,  55,  55))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(220, 220, 220))
    pal.setColor(QPalette.ColorRole.BrightText,      Qt.GlobalColor.red)
    pal.setColor(QPalette.ColorRole.Link,            QColor(80,  160, 220))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(60,  130, 60))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(220, 220, 220))
    # Disabled state
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(120, 120, 120))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor(120, 120, 120))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(120, 120, 120))
    return pal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hz", type=int, default=50)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    app = QApplication(sys.argv)
    _load_fonts()
    app.setStyle("Fusion")        # consistent rendering
    app.setPalette(_dark_palette())  # makes arrows/indicators visible on dark bg
    app.setApplicationName("LMU App")
    app.setApplicationVersion("0.4.0")
    app.setQuitOnLastWindowClosed(False)

    config = AppConfig()
    reader = DataReader(update_hz=args.hz)
    reader.start()

    fuel_calc_w = FuelCalcWidget(reader, auto_hide=False)
    ve_calc_w   = VECalcWidget(reader,   auto_hide=False)

    widget_entries: list[tuple[str, object]] = [
        ("speed",      SpeedWidget(reader,     auto_hide=False)),
        ("inputs",     InputsWidget(reader,    auto_hide=False)),
        ("standings",  StandingsWidget(reader, auto_hide=False)),
        ("relative",   RelativeWidget(reader,  auto_hide=False)),
        ("tyres",      TyresWidget(reader,     auto_hide=False)),
        ("fuel_calc",  fuel_calc_w),
        ("ve_calc",    ve_calc_w),
    ]

    merge = config.merge_calc
    fuel_calc_w.set_merge(merge)
    ve_calc_w.set_merge(merge)

    locked = config.locked
    for key, widget in widget_entries:
        x, y = config.widget_pos(key)
        widget.move(x, y)
        widget.set_locked(locked)

        def _make_pos_cb(k: str):
            def _cb(wx: int, wy: int) -> None:
                config.set_widget_pos(k, wx, wy)
                config.save()
            return _cb

        widget._on_position_changed = _make_pos_cb(key)
        widget.set_hide_in_garage(config.hide_in_garage)

        saved_params = config.widget_params(key)
        if saved_params:
            widget.apply_params(saved_params)

        if config.widget_enabled(key):
            widget.start()

    main_win = MainWindow(config, widget_entries, reader=reader)
    main_win.show()

    def on_quit() -> None:
        for _, w in widget_entries:
            w.stop()
        reader.stop()

    app.aboutToQuit.connect(on_quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
