"""hypertrace/ui/main_window.py — Tabbed main control panel — Direction A "Broadcast"."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hypertrace.calc.realtime_state import realtime_state
from hypertrace.ui.main_window_controls import (
    _SS_BTN,
    _SS_BTN_DANGER,
    _SS_BTN_DANGER_ARMED,
    _CogBtn,
    _LockToggle,
    _OnOffBtn,
    _StreamConfigProxy,
    _sep,
)
from hypertrace.utils.class_colors import CLASS_ENTRIES, class_key
from hypertrace.utils.theme import T, border_pen, label_font, panel_brush

if TYPE_CHECKING:
    from hypertrace.config import AppConfig
    from hypertrace.stream.server import StreamManager
    from hypertrace.widgets.base import BaseWidget


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

_check_svg      = (Path(__file__).parent.parent / "assets" / "check.svg").as_posix()
_edit_svg       = (Path(__file__).parent.parent / "assets" / "edit.svg").as_posix()
_trash_svg      = (Path(__file__).parent.parent / "assets" / "trash.svg").as_posix()
_chevron_svg    = (Path(__file__).parent.parent / "assets" / "chevron-down.svg").as_posix()
_chevron_up_svg = (Path(__file__).parent.parent / "assets" / "chevron-up.svg").as_posix()
_wordmark_svg   = Path(__file__).parent.parent / "assets" / "hypertrace_wordmark.svg"


def _render_svg(path: Path, height: int, dpr: float = 1.0) -> QPixmap | None:
    """Rasterise an SVG at the requested *logical* height, preserving aspect
    ratio. Renders at `height * dpr` physical pixels and tags the pixmap with
    that device pixel ratio, so it stays crisp on HiDPI displays instead of
    being upscaled and blurred by Qt after the fact — drawing straight to the
    target resolution keeps it sharp, unlike rasterising at source size and
    scaling down."""
    try:
        from PySide6.QtSvg import QSvgRenderer
    except ImportError:
        return None
    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        return None
    box = renderer.viewBoxF()
    vw, vh = box.width(), box.height()
    if vw <= 0 or vh <= 0:
        return None
    phys_h = max(1, round(height * dpr))
    phys_w = max(1, round(vw * phys_h / vh))
    px = QPixmap(phys_w, phys_h)
    px.setDevicePixelRatio(dpr)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, phys_w / dpr, phys_h / dpr))
    painter.end()
    return px

_WINDOW_SS = f"""
QWidget {{
    color: {T.TEXT};
    font-family: '{T.F_TEXT}';
    font-size: 12px;
    font-weight: bold;
}}
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: transparent;
    color: {T.DIM};
    font-family: '{T.F_TEXT}';
    font-size: 11px;
    padding: 6px 9px;
    border: none;
    border-bottom: 2px solid transparent;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QTabBar::tab:selected {{
    color: {T.TEXT};
    border-bottom: 2px solid {T.ACCENT};
}}
QTabBar::tab:hover {{ color: {T.TEXT}; }}
QScrollBar:vertical {{ background: transparent; width: 6px; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.15); border-radius: 3px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QCheckBox {{ spacing: 6px; color: {T.DIM}; }}
QCheckBox::indicator {{
    width: 14px; height: 14px; border-radius: 3px;
    border: 1px solid rgba(255,255,255,0.20);
    background: rgba(255,255,255,0.05);
}}
QCheckBox::indicator:checked {{ background: {T.ACCENT}; border-color: {T.ACCENT}; image: url({_check_svg}); }}
QComboBox {{
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 4px; padding: 2px 6px;
    color: {T.TEXT}; min-height: 22px;
}}
QComboBox:hover {{ border-color: rgba(255,255,255,0.25); }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{ image: url({_chevron_svg}); width: 10px; height: 6px; }}
QComboBox QAbstractItemView {{
    background: #2A2C30;
    border: 1px solid rgba(255,255,255,0.15);
    selection-background-color: rgba(236,170,67,0.2);
    color: {T.TEXT}; outline: none; padding: 2px;
}}
QSpinBox {{
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 4px;
    padding: 2px 4px;
    color: {T.TEXT};
    min-height: 22px;
}}
QSpinBox:hover {{ border-color: rgba(255,255,255,0.25); }}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px;
    border: none;
    background: rgba(255,255,255,0.06);
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background: rgba(255,255,255,0.14);
}}
QSpinBox::up-arrow   {{ image: url({_chevron_up_svg});   width: 8px; height: 5px; }}
QSpinBox::down-arrow {{ image: url({_chevron_svg}); width: 8px; height: 5px; }}
"""

# Sidebar navigation buttons — checked page gets a solid accent bar on the
# left edge (SimHub/RaceLab-style rail), unchecked stays dim.
_SS_NAV = (
    f"QPushButton {{ text-align: left; padding: 8px 10px 8px 12px; "
    f"color: {T.DIM}; background: transparent; border: none; "
    f"border-left: 3px solid transparent; font-size: 11px; font-weight: bold; "
    f"letter-spacing: 1px; text-transform: uppercase; }}"
    f"QPushButton:hover {{ color: {T.TEXT}; background: rgba(255,255,255,0.04); }}"
    f"QPushButton:checked {{ color: {T.TEXT}; border-left: 3px solid {T.ACCENT}; "
    f"background: rgba(255,255,255,0.05); }}"
)


class MainWindow(QWidget):
    """Tabbed control panel — Direction A Broadcast."""

    def __init__(
        self,
        config: AppConfig,
        widget_entries: list[tuple[str, BaseWidget]],
        reader=None,
        stream_manager: StreamManager | None = None,
        stream_entries: list[tuple[str, object]] | None = None,
    ) -> None:
        super().__init__()
        self._config          = config
        self._entries         = widget_entries
        self._stream_manager  = stream_manager
        self._stream_entries  = stream_entries or []
        self._get_snapshot    = reader.get if reader is not None else None
        self._last_player_class: str | None = None

        self.setWindowTitle("HyperTrace")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(560)
        self.setStyleSheet(_WINDOW_SS)

        self._toggles: dict[str, _OnOffBtn] = {}
        self._stack: QStackedWidget | None = None
        self._nav_btns: list[QPushButton] = []
        self._status_lbl: QLabel | None = None
        self._lock_toggle: _LockToggle | None = None
        self._lock_label: QLabel | None = None
        self._auto_hide_toggle: _LockToggle | None = None
        self._auto_hide_label: QLabel | None = None
        self._merge_btn: _OnOffBtn | None = None
        self._preset_switcher_combo: QComboBox | None = None
        self._preset_list_layout: QVBoxLayout | None = None
        self._preset_row_labels: dict[str, QLabel] = {}
        self._preset_row_w: QWidget | None = None
        self._saveas_row_w: QWidget | None = None
        self._saveas_name_edit: QLineEdit | None = None
        self._class_panel_w: QWidget | None = None
        self._class_combos: dict[str, QComboBox] = {}
        self._stream_main_toggle: _OnOffBtn | None = None
        self._stream_toggles: dict[str, _OnOffBtn] = {}
        self._params_clipboard: dict | None = None   # (params dict, copied from key)
        self._stream_url_lbl: QLabel | None = None
        self._stream_rows_w: QWidget | None = None
        self._stream_port_spin: QSpinBox | None = None

        self._setup_ui()
        self._apply_lock_state()

        if not self._config.preset_names():
            self._config.upsert_preset("Default", self._capture_state())
            self._config.save()
            self._rebuild_preset_ui()
        if not self._config.current_preset:
            names = self._config.preset_names()
            self._config.current_preset = names[0] if names else ""
            self._config.save()
        self._refresh_preset_chrome()
        self._resize_to_current_tab()

        if self._get_snapshot is not None:
            self._session_timer = QTimer(self)
            self._session_timer.setInterval(1000)
            self._session_timer.timeout.connect(self._on_class_watch)
            self._session_timer.start()

        # Status footer refresh — independent of the reader-driven class
        # watcher above so the footer works even without a reader.
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(1000)
        self._status_timer.timeout.connect(self._refresh_status_footer)
        self._status_timer.start()
        self._refresh_status_footer()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setBrush(panel_brush(0, 0, h, 248))
        p.setPen(border_pen(100))
        p.drawRoundedRect(1, 1, w - 2, h - 2, 9, 9)
        p.end()

    def _resize_to_current_tab(self) -> None:
        """Fix the window height to exactly what the current page needs, so
        it can't be dragged taller/shorter (width is already fixed via
        setFixedWidth()) while still adapting per page instead of settling
        on one height tall enough for the biggest page and leaving a gap on
        the others. Re-run whenever the current page's own content height
        changes (e.g. the Save As row swapping in, a collapsible group
        toggling).

        QStackedLayout's sizeHint is always the max over *every* page it
        holds, regardless of each page's QSizePolicy (unlike a plain
        QBoxLayout item, which does respect Ignored) — there's no public
        flag to change that. So instead of fighting the stack's own hint,
        this pins the stack itself to exactly the current page's height for
        the moment adjustSize() measures the window, then releases it back
        to flexible so it keeps filling the now-correctly-sized window."""
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        if self._stack is not None and self._stack.currentWidget() is not None:
            page_h = self._stack.currentWidget().sizeHint().height()
            self._stack.setMinimumHeight(page_h)
            self._stack.setMaximumHeight(page_h)
            # The stack's own updateGeometry() only marks *its* cache dirty —
            # the intermediate "body" row (rail + stack, in a QHBoxLayout)
            # caches its own sizeHint too and doesn't get told to recompute
            # just because its child changed size, so it kept reporting
            # whatever height was current the first time it was laid out.
            body_layout = self._stack.parentWidget().layout()
            if body_layout is not None:
                body_layout.invalidate()
                body_layout.activate()
            self.adjustSize()
            self.setFixedHeight(self.sizeHint().height())
            self._stack.setMinimumHeight(0)
            self._stack.setMaximumHeight(16777215)
        else:
            self.adjustSize()
            self.setFixedHeight(self.sizeHint().height())

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(10, 10, 10, 10)

        root.addWidget(self._make_header())
        root.addWidget(_sep())

        # Body: nav rail on the left, stacked pages on the right — replaces
        # the old QTabWidget. The pages themselves are the same 3 builders.
        body = QWidget()
        body_hl = QHBoxLayout(body)
        body_hl.setContentsMargins(0, 0, 0, 0)
        body_hl.setSpacing(8)

        rail = QWidget()
        # Kept at 116 (unchanged from when a wider "BROADCAST" label also
        # lived in this rail) rather than re-tuned for the 3 remaining
        # labels, to avoid re-verifying pixel-perfect nav-button padding
        # without a visual pass.
        rail.setFixedWidth(116)
        rail_vl = QVBoxLayout(rail)
        rail_vl.setContentsMargins(0, 4, 0, 0)
        rail_vl.setSpacing(2)
        for i, name in enumerate(("Overlays", "Presets", "Stream")):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet(_SS_NAV)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._on_nav(idx))
            rail_vl.addWidget(btn)
            self._nav_btns.append(btn)
        rail_vl.addStretch()
        body_hl.addWidget(rail)

        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setStyleSheet("color: rgba(255,255,255,0.08);")
        body_hl.addWidget(vline)

        stack = QStackedWidget()
        stack.addWidget(self._make_overlays_tab())
        stack.addWidget(self._make_presets_tab())
        stack.addWidget(self._make_stream_tab())
        body_hl.addWidget(stack, 1)
        self._stack = stack

        root.addWidget(body)

        root.addWidget(_sep())
        root.addWidget(self._make_footer())

        self._nav_btns[0].setChecked(True)

    def _make_header(self) -> QWidget:
        hdr = QWidget()
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(2, 0, 2, 2)
        hl.setSpacing(8)

        _HEADER_ROW_H = 24  # both labels below get this exact box height, so
        # neither the layout nor either QLabel's own alignment has to guess
        # at how to position a shorter item next to a taller one — there is
        # no taller one, they're identical, and each just centers its own
        # content (text or pixmap) within the same box.
        _LOGO_H = 16  # the logo itself is rendered smaller than the row and
        # centered within it, rather than filling the row — filling it made
        # the wordmark look oversized next to the version text.

        title = QLabel()
        title.setFixedHeight(_HEADER_ROW_H)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        _screen = QApplication.primaryScreen()
        logo = _render_svg(_wordmark_svg, _LOGO_H, _screen.devicePixelRatio() if _screen else 1.0)
        if logo is not None:
            title.setPixmap(logo)
        else:
            title.setText("HYPERTRACE")
            title.setFont(label_font(14))
            title.setStyleSheet(f"color: {T.ACCENT};")
        hl.addWidget(title)

        from hypertrace.main import APP_VERSION
        ver = QLabel(f"v{APP_VERSION}")
        ver.setFixedHeight(_HEADER_ROW_H)
        ver.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        ver.setStyleSheet(f"color: {T.DIM}; font-size: 10px;")
        hl.addWidget(ver)

        hl.addStretch()
        # Preset switching lives at the bottom of the Overlays page only —
        # having it here too was a duplicate control for the same thing.
        return hdr

    def _make_footer(self) -> QWidget:
        lbl = QLabel()
        lbl.setStyleSheet(f"color: {T.DIM}; font-size: 10px; padding: 0 2px;")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        self._status_lbl = lbl
        return lbl

    def _refresh_status_footer(self) -> None:
        if self._status_lbl is None:
            return
        def dot(on: bool, good: str = T.GOOD) -> str:
            return f"<span style='color:{good if on else T.DIM};'>●</span>"
        game = realtime_state.game_running and realtime_state.connected
        parts = [
            f"{dot(game)} Game {'connected' if game else 'not running'}",
            f"{dot(self._config.stream_active)} Stream {'on' if self._config.stream_active else 'off'}",
        ]
        self._status_lbl.setText("&nbsp;&nbsp;&nbsp;".join(parts))

    def _on_nav(self, idx: int) -> None:
        if self._stack is None:
            return
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)
        self._stack.setCurrentIndex(idx)
        # Deferred: right after setCurrentIndex(), the stack/pages haven't
        # finished their own layout pass yet, so measuring sizeHint()
        # synchronously here could still see the *previous* page's cached
        # size — which read as "have to click twice" (the second click's
        # resize call would pick up what the first one should have). Running
        # after the pending events flush makes one click reliable.
        QTimer.singleShot(0, self._resize_to_current_tab)

    def _on_preset_switcher_changed(self, name: str) -> None:
        if not name or name == self._config.current_preset:
            return
        self._load_preset(name)

    def _update_preset_switcher(self) -> None:
        combo = self._preset_switcher_combo
        if combo is None:
            return
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(self._config.preset_names())
        idx = combo.findText(self._config.current_preset)
        combo.setCurrentIndex(max(0, idx))
        combo.blockSignals(False)

    # ------------------------------------------------------------------ Tab 1 — Overlays

    def _make_global_controls_group(self) -> QWidget:
        group = QWidget()
        group.setObjectName("globalControls")
        group.setStyleSheet(
            f"#globalControls {{ background: rgba(255,255,255,{T.CARD_BG_ALPHA}); "
            f"border-radius: 6px; }}"
        )
        vl = QVBoxLayout(group)
        vl.setContentsMargins(8, 6, 8, 8)
        vl.setSpacing(6)

        hdr = QLabel("GLOBAL CONTROLS")
        hdr.setStyleSheet(
            f"color: {T.DIM}; font-size: 10px; font-weight: bold; letter-spacing: 1px;"
        )
        vl.addWidget(hdr)

        fc = self._find_widget("fuel_calc")
        vc = self._find_widget("ve_calc")
        if fc and vc:
            merge_row = QWidget()
            hl = QHBoxLayout(merge_row)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(6)
            lbl = QLabel("Merge Fuel & VE calc")
            lbl.setStyleSheet(f"color: {T.DIM}; font-size: 11px;")
            hl.addWidget(lbl, 1)
            self._merge_btn = _OnOffBtn(self._config.merge_calc)
            self._merge_btn.toggled.connect(self._on_merge_toggled)
            hl.addWidget(self._merge_btn)
            vl.addWidget(merge_row)

        auto_hide_row = QWidget()
        auto_hide_hl  = QHBoxLayout(auto_hide_row)
        auto_hide_hl.setContentsMargins(0, 0, 0, 0)
        auto_hide_hl.setSpacing(8)
        self._auto_hide_toggle = _LockToggle(
            self._config.auto_hide,
            tooltip="Hide overlays unless you're actively driving on track",
        )
        self._auto_hide_toggle.toggled.connect(self._toggle_auto_hide)
        auto_hide_hl.addWidget(self._auto_hide_toggle)
        self._auto_hide_label = QLabel(self._auto_hide_text(self._config.auto_hide))
        self._auto_hide_label.setStyleSheet(f"color: {T.DIM}; font-size: 11px;")
        auto_hide_hl.addWidget(self._auto_hide_label, 1)
        vl.addWidget(auto_hide_row)

        lock_row = QWidget()
        lock_hl  = QHBoxLayout(lock_row)
        lock_hl.setContentsMargins(0, 0, 0, 0)
        lock_hl.setSpacing(8)
        self._lock_toggle = _LockToggle(self._config.locked)
        self._lock_toggle.toggled.connect(self._on_lock_toggled)
        lock_hl.addWidget(self._lock_toggle)
        self._lock_label = QLabel(self._lock_text(self._config.locked))
        self._lock_label.setStyleSheet(f"color: {T.DIM}; font-size: 11px;")
        lock_hl.addWidget(self._lock_label, 1)
        vl.addWidget(lock_row)

        return group

    def _make_overlays_tab(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setSpacing(4)
        vl.setContentsMargins(6, 8, 6, 8)

        vl.addWidget(self._make_global_controls_group())
        vl.addWidget(_sep())

        for key, widget in self._entries:
            vl.addWidget(self._make_row(key, widget))

        vl.addWidget(_sep())
        vl.addWidget(self._make_preset_row())
        vl.addWidget(self._make_saveas_row())

        vl.addStretch()
        return w

    def _make_preset_row(self) -> QWidget:
        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)

        title = QLabel("Preset:")
        title.setStyleSheet(f"color: {T.DIM}; font-size: 11px;")
        hl.addWidget(title)

        combo = QComboBox()
        combo.currentTextChanged.connect(self._on_preset_switcher_changed)
        self._preset_switcher_combo = combo
        hl.addWidget(combo, 1)

        save_btn = QPushButton("Save")
        save_btn.setFixedSize(48, 22)
        save_btn.setStyleSheet(_SS_BTN)
        save_btn.clicked.connect(self._save_current_preset)
        hl.addWidget(save_btn)

        saveas_btn = QPushButton("Save As")
        saveas_btn.setFixedSize(72, 22)
        saveas_btn.setStyleSheet(_SS_BTN)
        saveas_btn.clicked.connect(self._toggle_saveas_row)
        hl.addWidget(saveas_btn)

        self._preset_row_w = row
        return row

    def _make_saveas_row(self) -> QWidget:
        row = QWidget()
        row.setObjectName("saveAsRow")
        row.setStyleSheet(
            f"#saveAsRow {{ background: rgba(236,170,67,0.10); border-radius: 4px; "
            f"border: 1px solid rgba(236,170,67,0.30); }}"
        )
        hl = QHBoxLayout(row)
        hl.setContentsMargins(6, 4, 4, 4)
        hl.setSpacing(4)

        edit = QLineEdit("New Preset")
        edit.setFixedHeight(20)
        edit.setStyleSheet(
            f"QLineEdit {{ background: rgba(255,255,255,0.08); "
            f"border: 1px solid {T.ACCENT}; border-radius: 3px; "
            f"color: {T.TEXT}; font-size: 11px; padding: 0 4px; }}"
        )
        self._saveas_name_edit = edit
        hl.addWidget(edit, 1)

        cancel_btn = QPushButton("✕")
        cancel_btn.setFixedSize(26, 22)
        cancel_btn.setStyleSheet(_SS_BTN)
        cancel_btn.setToolTip("Cancel")
        cancel_btn.clicked.connect(self._hide_saveas_row)
        hl.addWidget(cancel_btn)

        confirm_btn = QPushButton()
        confirm_btn.setIcon(QIcon(_check_svg))
        confirm_btn.setIconSize(QSize(13, 13))
        confirm_btn.setFixedSize(26, 22)
        confirm_btn.setStyleSheet(
            f"QPushButton {{ background: {T.ACCENT}; border: 1px solid {T.ACCENT}; "
            f"border-radius: 4px; padding: 0px; }}"
            f"QPushButton:hover {{ background: #F0B54A; }}"
        )
        confirm_btn.setToolTip("Create preset")
        confirm_btn.clicked.connect(self._confirm_saveas)
        hl.addWidget(confirm_btn)

        edit.returnPressed.connect(self._confirm_saveas)
        orig_kp = edit.keyPressEvent
        def _nkp(event, orig=orig_kp):
            if event.key() == Qt.Key.Key_Escape:
                self._hide_saveas_row()
            elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._confirm_saveas()
            else:
                orig(event)
        edit.keyPressEvent = _nkp

        row.setVisible(False)
        self._saveas_row_w = row
        return row

    def _make_row(self, key: str, widget: BaseWidget) -> QWidget:
        row = QWidget()
        hl  = QHBoxLayout(row)
        hl.setContentsMargins(0, 2, 0, 2)
        hl.setSpacing(6)

        lbl = QLabel(widget.WIDGET_NAME)
        lbl.setStyleSheet(f"color: {T.TEXT}; font-size: 12px;")
        hl.addWidget(lbl, 1)

        if widget.CONFIG_SCHEMA:
            cog = _CogBtn()
            cog.setToolTip(f"Configure {widget.WIDGET_NAME}")
            cog.clicked.connect(lambda _, k=key, w=widget: self._open_config(k, w))
            hl.addWidget(cog)

        btn = _OnOffBtn(self._config.widget_enabled(key))
        btn.toggled.connect(lambda checked, k=key, w=widget: self._on_toggle(k, w, checked))
        self._toggles[key] = btn
        hl.addWidget(btn)

        return row

    def _paste_params(self, key: str, widget) -> None:
        if not self._params_clipboard:
            return
        self._config.set_stream_widget_params(key, dict(self._params_clipboard))
        self._config.save()
        widget.apply_params(self._params_clipboard)
        # find the stream widget instance in stream_manager and update it
        if self._stream_manager:
            sw = self._stream_manager._widgets.get(key)
            if sw is not None:
                sw.apply_params(self._params_clipboard)

    def _refresh_preset_chrome(self) -> None:
        """Single point of truth for "what's the current preset" across the
        UI: the switcher combo at the bottom of the Overlays page, and the
        highlighted row in the Presets page list."""
        current = self._config.current_preset
        if self._preset_switcher_combo is not None:
            self._preset_switcher_combo.blockSignals(True)
            idx = self._preset_switcher_combo.findText(current)
            if idx >= 0:
                self._preset_switcher_combo.setCurrentIndex(idx)
            self._preset_switcher_combo.blockSignals(False)
        self._update_active_preset_highlight()

    def _save_current_preset(self) -> None:
        name = self._config.current_preset
        if not name:
            self._toggle_saveas_row()
            return
        self._config.upsert_preset(name, self._capture_state())
        self._config.save()
        self._rebuild_preset_ui()

    def _toggle_saveas_row(self) -> None:
        if self._saveas_row_w is None:
            return
        visible = not self._saveas_row_w.isVisible()
        self._saveas_row_w.setVisible(visible)
        if self._preset_row_w is not None:
            self._preset_row_w.setVisible(not visible)
        if visible and self._saveas_name_edit is not None:
            self._saveas_name_edit.setText("New Preset")
            QTimer.singleShot(0, self._saveas_name_edit.setFocus)
            QTimer.singleShot(0, self._saveas_name_edit.selectAll)
        self._resize_to_current_tab()

    def _hide_saveas_row(self) -> None:
        if self._saveas_row_w is not None:
            self._saveas_row_w.setVisible(False)
        if self._preset_row_w is not None:
            self._preset_row_w.setVisible(True)
        self._resize_to_current_tab()

    def _confirm_saveas(self) -> None:
        if self._saveas_name_edit is None:
            return
        name = self._saveas_name_edit.text().strip()
        if not name:
            return
        self._config.upsert_preset(name, self._capture_state())
        self._config.current_preset = name
        self._config.save()
        self._hide_saveas_row()
        self._refresh_preset_chrome()
        self._rebuild_preset_ui()

    # ------------------------------------------------------------------ Tab 2 — Presets

    def _make_presets_tab(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setSpacing(6)
        vl.setContentsMargins(6, 8, 6, 8)

        # Scrollable preset list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        list_container = QWidget()
        list_container.setStyleSheet("background: transparent;")
        self._preset_list_layout = QVBoxLayout(list_container)
        self._preset_list_layout.setSpacing(3)
        self._preset_list_layout.setContentsMargins(0, 0, 0, 0)
        self._preset_list_layout.addStretch()
        scroll.setWidget(list_container)
        scroll.setFixedHeight(200)
        vl.addWidget(scroll)

        vl.addWidget(_sep())

        class_hdr = QLabel("Preset per class")
        class_hdr.setStyleSheet(f"color: {T.DIM}; font-size: 11px; font-weight: bold;")
        vl.addWidget(class_hdr)
        vl.addWidget(self._make_class_panel())

        vl.addStretch()
        self._rebuild_preset_ui()
        return w

    def _make_class_panel(self) -> QWidget:
        panel = QWidget()
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(0, 4, 0, 0)
        pl.setSpacing(4)

        for entry in CLASS_ENTRIES:
            if entry["key"] == "UNKNOWN":
                continue
            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 1, 0, 1)
            hl.setSpacing(8)
            lbl = QLabel(entry["label"])
            lbl.setStyleSheet(f"color: {T.DIM}; font-size: 11px;")
            lbl.setFixedWidth(72)
            combo = QComboBox()
            combo.currentIndexChanged.connect(
                lambda _, k=entry["key"]: self._on_class_combo_changed(k)
            )
            self._class_combos[entry["key"]] = combo
            hl.addWidget(lbl)
            hl.addWidget(combo, 1)
            pl.addWidget(row)

        self._class_panel_w = panel
        return panel

    def _update_class_combos(self) -> None:
        names = self._config.preset_names()
        cp    = self._config.class_presets
        for cls_key, combo in self._class_combos.items():
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("— None —", "")
            for n in names:
                combo.addItem(n, n)
            current = cp.get(cls_key, "")
            idx = combo.findData(current)
            combo.setCurrentIndex(max(0, idx))
            combo.blockSignals(False)

    def _on_class_combo_changed(self, cls_key: str) -> None:
        combo = self._class_combos.get(cls_key)
        if combo is None:
            return
        cp = dict(self._config.class_presets)
        value = combo.currentData()
        if value:
            cp[cls_key] = value
        else:
            cp.pop(cls_key, None)
        self._config.class_presets = cp
        self._config.save()
        self._rebuild_preset_ui()
        self._maybe_apply_class_preset(cls_key, value)

    def _maybe_apply_class_preset(self, cls_key: str, preset_name: str) -> None:
        """If the player is currently driving that class, apply the newly
        dedicated preset right away instead of waiting for the next class
        change (which may never come again this session)."""
        if not preset_name or self._get_snapshot is None:
            return
        snap = self._get_snapshot()
        if not snap or not snap.game_running:
            return
        player = next((v for v in snap.session.vehicles if v.is_player), None)
        if player is None or class_key(player.vehicle_class) != cls_key:
            return
        preset = self._config.preset_by_name(preset_name)
        if preset:
            self._apply_preset_data(preset)
            self._config.current_preset = preset_name
            self._config.save()
            self._refresh_preset_chrome()

    def _wire_delete_button(self, btn: QPushButton, name: str) -> None:
        """Two-step delete, no modal QMessageBox. First click arms the button:
        the trash icon becomes a check (✓) that says "confirm" instead of the
        same trash asking to be clicked again — the swap makes the second click
        read as a deliberate confirmation, not a repeat. Stays armed 2.5s, then
        reverts to the trash on its own. Same micro-feedback family as the
        "✓ Copied" buttons, inverted to arm a destructive action."""
        state = {"armed": False}

        def _revert() -> None:
            if not state["armed"]:
                return
            state["armed"] = False
            try:
                btn.setIcon(QIcon(_trash_svg))
                btn.setStyleSheet(_SS_BTN_DANGER)
                btn.setToolTip("Delete")
            except RuntimeError:
                pass   # button already destroyed by a full preset-list rebuild

        def _click() -> None:
            if not state["armed"]:
                state["armed"] = True
                btn.setIcon(QIcon(_check_svg))
                btn.setStyleSheet(_SS_BTN_DANGER_ARMED)
                btn.setToolTip("Click the check to delete permanently")
                QTimer.singleShot(2500, _revert)
            else:
                self._delete_preset(name)

        btn.clicked.connect(_click)

    def _rebuild_preset_ui(self) -> None:
        if self._preset_list_layout is None:
            return

        # Clear existing rows (keep stretch at end)
        while self._preset_list_layout.count() > 1:
            item = self._preset_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._preset_row_labels.clear()

        insert_at = 0

        for name in self._config.preset_names():
            row = QWidget()
            row.setStyleSheet(
                "QWidget { background: rgba(255,255,255,0.04); border-radius: 4px; }"
            )
            hl = QHBoxLayout(row)
            hl.setContentsMargins(8, 4, 4, 4)
            hl.setSpacing(4)

            lbl = QLabel(name)
            lbl.setStyleSheet(f"color: {T.TEXT}; font-size: 11px; background: transparent;")
            hl.addWidget(lbl, 1)
            self._preset_row_labels[name] = lbl

            inline_edit = QLineEdit(name)
            inline_edit.setFixedHeight(20)
            inline_edit.setStyleSheet(
                f"QLineEdit {{ background: rgba(255,255,255,0.08); "
                f"border: 1px solid {T.ACCENT}; border-radius: 3px; "
                f"color: {T.TEXT}; font-size: 11px; padding: 0 4px; }}"
            )
            inline_edit.hide()
            hl.addWidget(inline_edit, 1)

            load_btn = QPushButton("Load")
            load_btn.setFixedSize(54, 22)   # 44 clipped in Montserrat (padding+border eat 18px)
            load_btn.setStyleSheet(_SS_BTN)
            load_btn.clicked.connect(lambda _, n=name: self._load_preset(n))
            hl.addWidget(load_btn)

            rename_btn = QPushButton()
            rename_btn.setIcon(QIcon(_edit_svg))
            rename_btn.setIconSize(QSize(15, 15))
            rename_btn.setFixedSize(28, 24)
            rename_btn.setStyleSheet(_SS_BTN)
            rename_btn.setToolTip("Rename")
            hl.addWidget(rename_btn)

            del_btn = QPushButton()
            del_btn.setIcon(QIcon(_trash_svg))
            del_btn.setIconSize(QSize(15, 15))
            del_btn.setFixedSize(28, 24)
            del_btn.setStyleSheet(_SS_BTN_DANGER)
            del_btn.setToolTip("Delete")
            self._wire_delete_button(del_btn, name)
            hl.addWidget(del_btn)

            # ---- inline rename wiring ----
            def _commit(n=name, l=lbl, e=inline_edit):
                new = e.text().strip()
                e.blockSignals(True); e.hide(); e.blockSignals(False)
                if new and new != n:
                    self._config.rename_preset(n, new)
                    if self._config.current_preset == n:
                        self._config.current_preset = new
                    self._config.save()
                    self._refresh_preset_chrome()
                    self._rebuild_preset_ui()
                else:
                    l.show()

            def _cancel(l=lbl, e=inline_edit):
                e.blockSignals(True); e.hide(); e.blockSignals(False)
                l.show()

            def _start(l=lbl, e=inline_edit):
                l.hide(); e.show(); e.setFocus(); e.selectAll()

            orig_kp = inline_edit.keyPressEvent
            def _kp(event, commit=_commit, cancel=_cancel, orig=orig_kp):
                if event.key() == Qt.Key.Key_Escape:
                    cancel()
                elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    commit()
                else:
                    orig(event)
            inline_edit.keyPressEvent = _kp

            orig_foe = inline_edit.focusOutEvent
            def _foe(event, commit=_commit, orig=orig_foe, e=inline_edit):
                orig(event)
                if e.isVisible():
                    commit()
            inline_edit.focusOutEvent = _foe

            rename_btn.clicked.connect(lambda _, start=_start: start())

            self._preset_list_layout.insertWidget(insert_at, row)
            insert_at += 1

        self._update_class_combos()
        self._update_preset_switcher()
        self._update_active_preset_highlight()

    def _update_active_preset_highlight(self) -> None:
        current = self._config.current_preset
        for name, lbl in self._preset_row_labels.items():
            try:
                if name == current:
                    lbl.setStyleSheet(
                        f"color: {T.ACCENT}; font-size: 11px; font-weight: bold; "
                        f"background: transparent;"
                    )
                else:
                    lbl.setStyleSheet(
                        f"color: {T.TEXT}; font-size: 11px; background: transparent;"
                    )
            except RuntimeError:
                pass   # stale entry from a row deleted since this dict was populated

    def _load_preset(self, name: str) -> None:
        preset = self._config.preset_by_name(name)
        if preset:
            self._apply_preset_data(preset)
            self._config.current_preset = name
            self._config.save()
            self._refresh_preset_chrome()

    def _delete_preset(self, name: str) -> None:
        was_active = self._config.current_preset == name
        self._config.delete_preset(name)
        if was_active:
            names = self._config.preset_names()
            if names:
                # Deleting the *active* preset — actually load whichever one
                # takes its place, not just repoint current_preset at it.
                # Without the load the dropdown switched but every overlay kept
                # the deleted layout until the next manual load.
                self._load_preset(names[0])
            else:
                self._config.current_preset = ""
                self._config.save()
        else:
            self._config.save()
        self._refresh_preset_chrome()
        self._rebuild_preset_ui()

    def _capture_state(self) -> dict:
        data: dict = {
            "locked":        self._config.locked,
            "merge_calc":    self._config.merge_calc,
            "auto_hide":     self._config.auto_hide,
            "widgets":       {},
        }
        for key, widget in self._entries:
            data["widgets"][key] = {
                "enabled": self._config.widget_enabled(key),
                "x":       widget.x(),
                "y":       widget.y(),
                "params":  dict(self._config.widget_params(key)),
            }
        return data

    def _apply_preset_data(self, data: dict) -> None:
        locked = data.get("locked", self._config.locked)
        self._config.locked = locked
        for _, w in self._entries:
            w.set_locked(locked)
        if self._lock_toggle:
            self._lock_toggle.set_locked(locked)
        if self._lock_label:
            self._lock_label.setText(self._lock_text(locked))

        auto_hide = data.get("auto_hide", self._config.auto_hide)
        self._config.auto_hide = auto_hide
        for _, w in self._entries:
            w.set_auto_hide(auto_hide)
        if self._auto_hide_toggle is not None:
            self._auto_hide_toggle.set_locked(auto_hide)
        if self._auto_hide_label is not None:
            self._auto_hide_label.setText(self._auto_hide_text(auto_hide))

        merge = data.get("merge_calc", self._config.merge_calc)
        self._config.merge_calc = merge
        fc = self._find_widget("fuel_calc")
        vc = self._find_widget("ve_calc")
        if fc:
            fc.set_merge(merge)
        if vc:
            vc.set_merge(merge)
        if self._merge_btn:
            self._merge_btn.setChecked(merge)

        for key, widget in self._entries:
            wdata = data.get("widgets", {}).get(key)
            if not wdata:
                continue
            x, y = wdata.get("x"), wdata.get("y")
            if x is not None and y is not None:
                widget.move(int(x), int(y))
                self._config.set_widget_pos(key, int(x), int(y))
            params = wdata.get("params")
            if params:
                widget.apply_params(params)
                self._config.set_widget_params(key, params)
            enabled = wdata.get("enabled")
            if enabled is not None:
                self._config.set_widget_enabled(key, bool(enabled))
                if bool(enabled):
                    if not widget._timer.isActive():
                        widget.start()
                else:
                    if widget._timer.isActive():
                        widget.stop()
                if key in self._toggles:
                    self._toggles[key].setChecked(bool(enabled))

        self._config.save()

    def _on_class_watch(self) -> None:
        if self._get_snapshot is None:
            return
        snap = self._get_snapshot()
        if not snap.game_running:
            self._last_player_class = None
            return
        player = next((v for v in snap.session.vehicles if v.is_player), None)
        if player is None:
            return
        cls = class_key(player.vehicle_class)
        if cls == self._last_player_class:
            return
        self._last_player_class = cls
        preset_name = self._config.class_presets.get(cls, "")
        if not preset_name:
            return
        preset = self._config.preset_by_name(preset_name)
        if preset:
            self._apply_preset_data(preset)
            self._config.current_preset = preset_name
            self._config.save()
            self._refresh_preset_chrome()

    # ------------------------------------------------------------------ Tab 3 — Streaming

    def _make_stream_tab(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setSpacing(6)
        vl.setContentsMargins(6, 8, 6, 8)

        # ── master stream row ──────────────────────────────────────────
        ctrl = QWidget()
        hl = QHBoxLayout(ctrl)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)

        lbl = QLabel("Stream")
        lbl.setStyleSheet(f"color: {T.TEXT}; font-size: 12px; font-weight: bold;")
        hl.addWidget(lbl)

        stream_toggle = _OnOffBtn(self._config.stream_active)
        stream_toggle.toggled.connect(self._on_stream_toggle)
        self._stream_main_toggle = stream_toggle
        hl.addWidget(stream_toggle)

        hl.addStretch()

        port_lbl = QLabel("Port:")
        port_lbl.setStyleSheet(f"color: {T.DIM}; font-size: 11px;")
        hl.addWidget(port_lbl)

        spin = QSpinBox()
        spin.setRange(1024, 65535)
        spin.setValue(self._config.stream_port)
        spin.setFixedWidth(68)
        spin.valueChanged.connect(self._on_stream_port_changed)
        self._stream_port_spin = spin
        hl.addWidget(spin)
        vl.addWidget(ctrl)

        url_lbl = QLabel()
        url_lbl.setStyleSheet(f"color: {T.ACCENT}; font-size: 10px;")
        url_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._stream_url_lbl = url_lbl
        vl.addWidget(url_lbl)

        vl.addWidget(_sep())

        # ── per-overlay rows ─────────────────────────────────────────────
        rows_w = QWidget()
        rows_vl = QVBoxLayout(rows_w)
        rows_vl.setSpacing(4)
        rows_vl.setContentsMargins(0, 0, 0, 0)
        self._stream_rows_w = rows_w
        for key, widget in self._stream_entries:
            rows_vl.addWidget(self._make_stream_row(key, widget))
        vl.addWidget(rows_w)

        vl.addWidget(_sep())

        _cb_ss = f"""
QCheckBox {{ color: {T.TEXT}; font-family: '{T.F_TEXT}'; font-size: 12px; spacing: 9px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border-radius: 3px;
    border: 1px solid rgba(255,255,255,0.12);
    background: rgba(255,255,255,0.03);
}}
QCheckBox::indicator:checked {{
    background: {T.ACCENT}; border-color: {T.ACCENT};
    image: url({_check_svg});
}}
"""
        hig = QCheckBox("Hide in garage")
        hig.setStyleSheet(_cb_ss)
        hig.setChecked(self._config.stream_hide_in_garage)
        hig.toggled.connect(self._on_stream_hide_garage)
        vl.addWidget(hig)

        vl.addStretch()

        self._refresh_stream_ui()
        return w

    def _make_stream_row(self, key: str, widget) -> QWidget:
        row = QWidget()
        hl  = QHBoxLayout(row)
        hl.setContentsMargins(0, 2, 0, 2)
        hl.setSpacing(4)

        lbl = QLabel(widget.WIDGET_NAME)
        lbl.setStyleSheet(f"color: {T.TEXT}; font-size: 12px;")
        hl.addWidget(lbl, 1)

        if widget.CONFIG_SCHEMA:
            cog = _CogBtn()
            cog.setToolTip(f"Stream settings for {widget.WIDGET_NAME}")
            cog.clicked.connect(lambda _, k=key, ww=widget: self._open_stream_config(k, ww))
            hl.addWidget(cog)

        copy_btn = QPushButton("URL")
        copy_btn.setFixedSize(46, 22)
        copy_btn.setStyleSheet(_SS_BTN)
        copy_btn.setToolTip("Copy OBS browser source URL")
        copy_btn.clicked.connect(lambda _, k=key: self._copy_stream_url(k))
        hl.addWidget(copy_btn)

        tog = _OnOffBtn(self._config.stream_widget_enabled(key))
        tog.toggled.connect(lambda checked, k=key: self._on_stream_widget_toggle(k, checked))
        self._stream_toggles[key] = tog
        hl.addWidget(tog)

        return row

    def _sync_stream_server(self) -> None:
        """Starts/stops the localhost OBS server to match the Stream toggle.
        Called after every toggle that could change that state."""
        if self._stream_manager is None:
            return
        should_run = self._config.stream_active
        running = self._stream_manager.is_running
        if should_run and not running:
            ok = self._stream_manager.start(self._config.stream_port)
            if ok:
                if self._stream_url_lbl is not None:
                    self._stream_url_lbl.setVisible(False)
                return
            # Port conflict — Stream was the only thing that could have just
            # turned on (should_run was false a moment ago), so reverting it
            # is exactly reverting what just changed, nothing else.
            setattr(self._config, "stream_active", False)
            if self._stream_main_toggle is not None:
                self._stream_main_toggle.blockSignals(True)
                self._stream_main_toggle.setChecked(False)
                self._stream_main_toggle.blockSignals(False)
            self._config.save()
            if self._stream_url_lbl is not None:
                self._stream_url_lbl.setText("Port already in use — choose another port")
                self._stream_url_lbl.setVisible(True)
            self._refresh_stream_ui()
        elif not should_run and running:
            self._stream_manager.stop()
            if self._stream_url_lbl is not None:
                self._stream_url_lbl.setVisible(False)

    def _refresh_stream_ui(self) -> None:
        """No success URL shown here on purpose — each overlay row already
        has its own "URL" copy button, so a top-level link is redundant.
        `_stream_url_lbl` still exists purely for the port-conflict error
        message (`_sync_stream_server`), which sets/shows it directly."""
        stream_active  = self._config.stream_active
        server_running = self._stream_manager.is_running if self._stream_manager else False
        if self._stream_port_spin:
            self._stream_port_spin.setEnabled(not server_running)
        if self._stream_rows_w:
            self._stream_rows_w.setEnabled(stream_active)

    def _on_stream_toggle(self, checked: bool) -> None:
        self._config.stream_active = checked
        self._config.save()
        self._sync_stream_server()
        self._refresh_stream_ui()

    def _on_stream_port_changed(self, value: int) -> None:
        self._config.stream_port = value
        self._config.save()

    def _on_stream_hide_garage(self, checked: bool) -> None:
        self._config.stream_hide_in_garage = checked
        self._config.save()
        if self._stream_manager:
            self._stream_manager.set_hide_in_garage(checked)

    def _on_stream_widget_toggle(self, key: str, checked: bool) -> None:
        self._config.set_stream_widget_enabled(key, checked)
        self._config.save()
        if self._stream_manager:
            self._stream_manager.set_widget_enabled(key, checked)

    def _copy_stream_url(self, key: str) -> None:
        url = f"http://localhost:{self._config.stream_port}/{key}"
        QApplication.clipboard().setText(url)
        # Brief visual feedback on the button
        btn = self.sender()
        if isinstance(btn, QPushButton):
            btn.setText("✓")
            QTimer.singleShot(1200, lambda b=btn: b.setText("URL"))

    def _open_stream_config(self, key: str, widget) -> None:
        from hypertrace.ui.widget_config_dialog import WidgetConfigDialog
        proxy = _StreamConfigProxy(self._config, key)
        WidgetConfigDialog(
            proxy, key, widget, parent=self,
            on_copy=lambda p: setattr(self, "_params_clipboard", p),
            on_paste=lambda: self._paste_params(key, widget),
        ).exec()

    # ------------------------------------------------------------------ Handlers

    def _on_toggle(self, key: str, widget: BaseWidget, enabled: bool) -> None:
        self._config.set_widget_enabled(key, enabled)
        self._config.save()
        widget.start() if enabled else widget.stop()

    def closeEvent(self, event) -> None:
        QApplication.instance().quit()
        event.accept()

    def _open_config(self, key: str, widget: BaseWidget) -> None:
        from hypertrace.ui.widget_config_dialog import WidgetConfigDialog
        WidgetConfigDialog(
            self._config, key, widget, parent=self,
            on_copy=lambda p: setattr(self, "_params_clipboard", p),
            on_paste=lambda: self._paste_params_to_normal(key, widget),
        ).exec()

    def _paste_params_to_normal(self, key: str, widget) -> None:
        if not self._params_clipboard:
            return
        self._config.set_widget_params(key, dict(self._params_clipboard))
        self._config.save()
        widget.apply_params(self._params_clipboard)

    @staticmethod
    def _lock_text(locked: bool) -> str:
        return "LOCK — overlays fixed" if locked else "FREE — overlays draggable"

    @staticmethod
    def _auto_hide_text(enabled: bool) -> str:
        return "Auto-hide ON — only shown while driving" if enabled else "Auto-hide OFF — always shown"

    def _on_lock_toggled(self, locked: bool) -> None:
        self._config.locked = locked
        self._config.save()
        if self._lock_label is not None:
            self._lock_label.setText(self._lock_text(locked))
        for _, widget in self._entries:
            widget.set_locked(locked)

    def _toggle_auto_hide(self, checked: bool) -> None:
        self._config.auto_hide = checked
        self._config.save()
        if self._auto_hide_label is not None:
            self._auto_hide_label.setText(self._auto_hide_text(checked))
        for _, widget in self._entries:
            widget.set_auto_hide(checked)

    def _apply_lock_state(self) -> None:
        locked = self._config.locked
        for _, widget in self._entries:
            widget.set_locked(locked)
        if self._lock_toggle is not None:
            self._lock_toggle.set_locked(locked)

    def _find_widget(self, key: str):
        return next((w for k, w in self._entries if k == key), None)

    def _on_merge_toggled(self, enabled: bool) -> None:
        self._config.merge_calc = enabled
        self._config.save()
        fc = self._find_widget("fuel_calc")
        vc = self._find_widget("ve_calc")
        if fc:
            fc.set_merge(enabled)
        if vc:
            vc.set_merge(enabled)
