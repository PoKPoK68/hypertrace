"""hypertrace/main.py — Entry point."""
from __future__ import annotations
import argparse, gc, logging, sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
from hypertrace.api.reader import DataReader
from hypertrace.calc.ext.rest_merge import rest_merge
from hypertrace.config import AppConfig
from hypertrace.widgets.speed import SpeedWidget
from hypertrace.widgets.inputs import InputsWidget
from hypertrace.widgets.standings import StandingsWidget
from hypertrace.widgets.relative import RelativeWidget
from hypertrace.widgets.tyres import TyresWidget
from hypertrace.widgets.damage import DamageWidget
from hypertrace.widgets.fuel_calc import FuelCalcWidget
from hypertrace.widgets.ve_calc import VECalcWidget
from hypertrace.widgets.weather import WeatherWidget
from hypertrace.widgets.delta import DeltaWidget
from hypertrace.stream.server import StreamManager
from hypertrace.ui.main_window import MainWindow
from hypertrace.widgets.broadcast import BroadcastBattle, BroadcastDriverCard, BroadcastSectors, BroadcastState, BroadcastTower


_FONTS = [
    "Montserrat-Bold.ttf",
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Medium.ttf",
    "JetBrainsMono-Bold.ttf",
    "SairaSemiCondensed-SemiBold.ttf",
    "SairaSemiCondensed-Bold.ttf",
]

APP_VERSION = "1.0.0"
_LOGO = "hypertrace_icon.ico"
LOG_PATH = None   # set by _log_handlers()


def _log_handlers(verbose: bool) -> list:
    """Console + rotating file log.

    The packaged app is built with console=False, so stderr goes nowhere — a
    file log is the only way to diagnose anything on a machine without Python.
    Lives next to the config, in ~/.hypertrace/.
    """
    global LOG_PATH
    handlers: list = [logging.StreamHandler()]
    try:
        from pathlib import Path
        from logging.handlers import RotatingFileHandler
        log_dir = Path.home() / ".hypertrace"
        log_dir.mkdir(parents=True, exist_ok=True)
        LOG_PATH = log_dir / "hypertrace.log"
        fh = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=2,
                                 encoding="utf-8")
        fh.setLevel(logging.DEBUG if verbose else logging.INFO)
        handlers.append(fh)
    except Exception:
        pass      # never let logging setup prevent the app from starting
    return handlers


def _set_app_user_model_id() -> None:
    """Windows: give the process its own taskbar identity.

    Without this, a dev run is grouped under python.exe and shows the Python
    icon in the taskbar regardless of the window icon. Must run before any
    window is created. No-op on other platforms.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HyperTrace.Overlay")
    except Exception as exc:
        logging.debug("Could not set AppUserModelID: %s", exc)


def _lower_process_priority() -> None:
    """Windows: run the whole process at BELOW_NORMAL priority.

    Each visible overlay is a separate always-on-top, per-pixel-alpha window;
    Windows/DWM has to recomposite all of them on every repaint, which runs on
    this process's main thread. Under CPU contention that competed with the
    game for the same cores and could freeze it — confirmed by the fact it
    only happened while overlays were shown (never while hidden, i.e. never
    while idle), and that restricting the app's scheduling with Process Lasso
    made the freezes disappear. Lowering the whole process's priority class
    tells the Windows scheduler to prefer the game whenever both want the
    same core, without having to guess which cores the game itself is using.
    Must run before QApplication is created. No-op on other platforms.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes
        BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetCurrentProcess.restype  = wintypes.HANDLE
        k32.SetPriorityClass.restype   = wintypes.BOOL
        k32.SetPriorityClass.argtypes  = [wintypes.HANDLE, wintypes.DWORD]
        handle = k32.GetCurrentProcess()
        if not k32.SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS):
            logging.debug("SetPriorityClass failed: %s", ctypes.get_last_error())
    except Exception as exc:
        logging.debug("Could not lower process priority: %s", exc)


def _set_app_icon(app) -> None:
    """Window icon (title bar) + taskbar icon for every window of the app."""
    from pathlib import Path
    from PySide6.QtGui import QIcon
    path = Path(__file__).parent / "assets" / _LOGO
    if not path.exists():
        logging.warning("App logo not found: %s", path)
        return
    icon = QIcon(str(path))
    if icon.isNull():
        logging.warning("App logo could not be loaded: %s", path)
        return
    app.setWindowIcon(icon)


def _load_fonts() -> None:
    from pathlib import Path
    from PySide6.QtGui import QFontDatabase
    from hypertrace.utils import theme
    fonts_dir = Path(__file__).parent / "assets" / "fonts"
    _num_set = False
    _text_set = False
    for name in _FONTS:
        path = fonts_dir / name
        fid = QFontDatabase.addApplicationFont(str(path))
        if fid < 0:
            logging.warning("Font failed to load: %s", path)
            continue
        families = QFontDatabase.applicationFontFamilies(fid)
        logging.debug("Loaded font %s → fid=%d families=%s", name, fid, families)
        if not families:
            continue
        family = families[0]
        # Take the first file's registered name only — subsequent weights of the
        # same typeface may register under "Family Bold" / "Family Medium" as
        # separate families; we want the base family that covers all weights.
        # Montserrat everywhere. It is proportional, but num_font() enables the
        # OpenType "tnum" feature so digits keep a fixed advance and columns
        # stay aligned. JetBrains Mono is only a fallback if it fails to load.
        if "Montserrat" in name and not _text_set:
            theme.T.F_TEXT = family
            theme.T.F_NUM  = family
            _text_set = _num_set = True
        elif "JetBrains" in name and not _num_set:
            theme.T.F_TEXT = family
            theme.T.F_NUM  = family
            _num_set = True
    logging.debug("Active font tokens — F_TEXT=%r  F_NUM=%r", theme.T.F_TEXT, theme.T.F_NUM)


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
        handlers=_log_handlers(args.verbose),
    )
    logging.info("HyperTrace %s starting (hz=%d) — log file: %s",
                 APP_VERSION, args.hz, LOG_PATH)

    _set_app_user_model_id()
    _lower_process_priority()
    app = QApplication(sys.argv)
    _load_fonts()
    app.setStyle("Fusion")        # consistent rendering
    app.setPalette(_dark_palette())  # makes arrows/indicators visible on dark bg
    app.setApplicationName("HyperTrace")
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(False)
    _set_app_icon(app)

    config = AppConfig()
    reader = DataReader(update_hz=args.hz)
    reader.start()

    # REST (localhost:6397) starts unconditionally as part of reader.start()
    # (see calc/module_control.py) regardless of the Broadcast toggle — stop
    # it again immediately if the user had it off last session, so the
    # toggle's saved state actually persists instead of forcing it back on
    # every launch (which is what used to happen here).
    if not config.broadcast_active:
        rest_merge.stop()

    fuel_calc_w = FuelCalcWidget(auto_hide=False)
    ve_calc_w   = VECalcWidget(auto_hide=False)

    widget_entries: list[tuple[str, object]] = [
        ("damage",     DamageWidget(auto_hide=False)),
        ("delta",      DeltaWidget(auto_hide=False)),
        ("fuel_calc",  fuel_calc_w),
        ("inputs",     InputsWidget(auto_hide=False)),
        ("relative",   RelativeWidget(auto_hide=False)),
        ("speed",      SpeedWidget(auto_hide=False)),
        ("standings",  StandingsWidget(auto_hide=False)),
        ("tyres",      TyresWidget(auto_hide=False)),
        ("ve_calc",    ve_calc_w),
        ("weather",    WeatherWidget(auto_hide=False)),
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
        widget.set_auto_hide(config.auto_hide)

        saved_params = config.widget_params(key)
        if saved_params:
            widget.apply_params(saved_params)

        if config.widget_enabled(key):
            widget.start()

    # ── Stream mode ────────────────────────────────────────────────────
    stream_manager = StreamManager(reader)

    _stream_classes = [
        ("damage",    DamageWidget),
        ("delta",     DeltaWidget),
        ("fuel_calc", FuelCalcWidget),
        ("inputs",    InputsWidget),
        ("relative",  RelativeWidget),
        ("speed",     SpeedWidget),
        ("standings", StandingsWidget),
        ("tyres",     TyresWidget),
        ("ve_calc",   VECalcWidget),
        ("weather",   WeatherWidget),
    ]
    stream_entries: list[tuple[str, object]] = []
    for key, cls in _stream_classes:
        sw = cls(auto_hide=False)
        stream_entries.append((key, sw))
        stream_manager.add_widget(key, sw)
        p = config.stream_widget_params(key)
        if p:
            sw.apply_params(p)
        stream_manager.set_widget_enabled(key, config.stream_widget_enabled(key))

    stream_manager.set_hide_in_garage(config.stream_hide_in_garage)

    # ── Broadcast mode ─────────────────────────────────────────────────
    bc_state  = BroadcastState()
    bc_state.tower_mode             = config.bc_tower_mode
    bc_state.tower_count_overall    = config.bc_tower_count_overall
    bc_state.tower_count_multiclass = config.bc_tower_count_multiclass
    bc_state.tower_count_ourclass   = config.bc_tower_count_ourclass
    bc_state.tower_filter_class     = config.bc_tower_filter_class
    bc_state.show_team              = config.bc_tower_show_team

    bc_tower   = BroadcastTower(bc_state)
    bc_battle  = BroadcastBattle(bc_state)
    bc_driver  = BroadcastDriverCard(bc_state)
    bc_sectors = BroadcastSectors(bc_state)

    stream_manager.add_widget("bc_tower",   bc_tower)
    stream_manager.add_widget("bc_battle",  bc_battle)
    stream_manager.add_widget("bc_driver",  bc_driver)
    stream_manager.add_widget("bc_sectors", bc_sectors)
    stream_manager.set_widget_enabled("bc_tower",   config.bc_tower_enabled)
    stream_manager.set_widget_enabled("bc_battle",  config.bc_battle_enabled)
    stream_manager.set_widget_enabled("bc_driver",  config.bc_driver_enabled)
    stream_manager.set_widget_enabled("bc_sectors", config.bc_sectors_enabled)

    # The OBS server is shared infrastructure between Stream and Broadcast
    # (see MainWindow._sync_stream_server) — resume it on launch if either
    # was left on. Deliberately NOT keyed on config.broadcast_active: that
    # flag is forced True a few lines above regardless of what was saved
    # (see comment there), so using it here would start this server on every
    # launch even for someone who never streams.
    broadcast_graphics_enabled = (
        config.bc_tower_enabled or config.bc_battle_enabled
        or config.bc_driver_enabled or config.bc_sectors_enabled
    )
    if config.stream_active or broadcast_graphics_enabled:
        stream_manager.start(config.stream_port)

    main_win = MainWindow(config, widget_entries, reader=reader,
                          stream_manager=stream_manager,
                          stream_entries=stream_entries)
    main_win.set_broadcast_state(bc_state)
    main_win.show()

    from hypertrace.widgets.live_timing import LiveTimingPanel
    live_timing_win = LiveTimingPanel(reader, bc_state)
    main_win.open_live_timing.connect(lambda: (live_timing_win.show(), live_timing_win.raise_()))

    def on_quit() -> None:
        live_timing_win.close()
        stream_manager.stop()
        for _, w in widget_entries:
            w.stop()
        reader.stop()

    app.aboutToQuit.connect(on_quit)

    # Everything constructed above (widgets, config, fonts, Qt's own object
    # graph) is long-lived — freeze() moves it out of the generations the
    # cyclic collector rescans on every pass, so a collection triggered later
    # by this session's steady per-tick allocations only has to look at
    # actual new garbage, not re-walk the whole app's permanent object graph
    # each time. This is a real technique for long-running GUI apps with
    # allocation churn, original to this app — untested against the actual
    # freeze, since that needs the game running to reproduce.
    gc.collect()
    gc.freeze()
    gc.disable()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
