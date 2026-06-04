"""lmu_app/ui/main_window.py — Tabbed main control panel."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from lmu_app.utils.class_colors import CLASS_ENTRIES

if TYPE_CHECKING:
    from lmu_app.config import AppConfig
    from lmu_app.widgets.base import BaseWidget

_BTN_LOCK   = "background:#3a3a1a; color:#ffdd44; border-color:#666622;"
_BTN_UNLOCK = "background:#1a3a1a; color:#88ff88; border-color:#226622;"
_BTN_QUIT   = "background:#3a1a1a; color:#ff8888; border-color:#662222;"


class MainWindow(QWidget):
    """Tabbed control panel."""

    def __init__(
        self,
        config: AppConfig,
        widget_entries: list[tuple[str, BaseWidget]],
    ) -> None:
        super().__init__()
        self._config  = config
        self._entries = widget_entries

        self.setWindowTitle("LMU App")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(290)

        self._setup_ui()
        self._apply_lock_state()
        self._broadcast_class_colors()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(8, 8, 8, 8)

        title = QLabel("LMU App")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffd700; padding: 2px 0;")
        root.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._make_overlays_tab(), "Overlays")
        tabs.addTab(self._make_class_colors_tab(), "Class Colors")
        root.addWidget(tabs)

    # ------------------------------------------------------------------ Tab 1

    def _make_overlays_tab(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setSpacing(4)
        vl.setContentsMargins(6, 8, 6, 8)

        self._checkboxes: dict[str, QCheckBox] = {}
        for key, widget in self._entries:
            vl.addWidget(self._make_row(key, widget))

        vl.addWidget(_sep())

        self._garage_cb = QCheckBox("Hide overlays in garage")
        self._garage_cb.setChecked(self._config.hide_in_garage)
        self._garage_cb.toggled.connect(self._toggle_garage_hide)
        vl.addWidget(self._garage_cb)

        vl.addWidget(_sep())

        self._lock_btn = QPushButton()
        self._lock_btn.clicked.connect(self._toggle_lock)
        vl.addWidget(self._lock_btn)

        quit_btn = QPushButton("Quit")
        quit_btn.setStyleSheet(_BTN_QUIT)
        quit_btn.clicked.connect(QApplication.instance().quit)
        vl.addWidget(quit_btn)

        vl.addStretch()
        return w

    def _make_row(self, key: str, widget: BaseWidget) -> QWidget:
        row = QWidget()
        hl  = QHBoxLayout(row)
        hl.setContentsMargins(0, 1, 0, 1)
        hl.setSpacing(6)

        cb = QCheckBox(widget.WIDGET_NAME)
        cb.setChecked(self._config.widget_enabled(key))
        cb.toggled.connect(lambda checked, k=key, w=widget: self._on_toggle(k, w, checked))
        self._checkboxes[key] = cb
        hl.addWidget(cb, 1)

        if widget.CONFIG_SCHEMA:
            cfg_btn = QPushButton("⚙")
            cfg_btn.setFixedSize(22, 22)
            cfg_btn.setToolTip(f"Configure {widget.WIDGET_NAME}")
            cfg_btn.clicked.connect(lambda _, k=key, w=widget: self._open_config(k, w))
            hl.addWidget(cfg_btn)

        return row

    # ------------------------------------------------------------------ Tab 2

    def _make_class_colors_tab(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setSpacing(6)
        vl.setContentsMargins(6, 8, 6, 8)

        info = QLabel("Background color per car class.\nApplied automatically from class name.")
        info.setStyleSheet("color: #888; font-size: 11px;")
        info.setWordWrap(True)
        vl.addWidget(info)

        self._class_btns: dict[str, _ClassColorBtn] = {}
        saved = self._config.class_colors()

        for entry in CLASS_ENTRIES:
            row = QWidget()
            hl  = QHBoxLayout(row)
            hl.setContentsMargins(0, 2, 0, 2)
            hl.setSpacing(8)

            lbl = QLabel(entry["label"])
            lbl.setMinimumWidth(120)
            btn = _ClassColorBtn(saved.get(entry["key"], entry["default"]))
            btn.color_changed.connect(
                lambda _, k=entry["key"]: self._on_class_color_change(k)
            )
            self._class_btns[entry["key"]] = btn
            hl.addWidget(lbl, 1)
            hl.addWidget(btn)
            vl.addWidget(row)

        vl.addWidget(_sep())

        reset_btn = QPushButton("Reset to defaults")
        reset_btn.clicked.connect(self._reset_class_colors)
        vl.addWidget(reset_btn)
        vl.addStretch()
        return w

    # ------------------------------------------------------------------ Handlers

    def _on_toggle(self, key: str, widget: BaseWidget, enabled: bool) -> None:
        self._config.set_widget_enabled(key, enabled)
        self._config.save()
        widget.start() if enabled else widget.stop()

    def _open_config(self, key: str, widget: BaseWidget) -> None:
        from lmu_app.ui.widget_config_dialog import WidgetConfigDialog
        WidgetConfigDialog(self._config, key, widget, parent=self).exec()

    def _toggle_lock(self) -> None:
        self._config.locked = not self._config.locked
        self._config.save()
        self._apply_lock_state()

    def _toggle_garage_hide(self, checked: bool) -> None:
        self._config.hide_in_garage = checked
        self._config.save()
        for _, widget in self._entries:
            widget.set_hide_in_garage(checked)

    def _apply_lock_state(self) -> None:
        locked = self._config.locked
        for _, widget in self._entries:
            widget.set_locked(locked)
        if locked:
            self._lock_btn.setText("Unlock widgets")
            self._lock_btn.setStyleSheet(_BTN_UNLOCK)
        else:
            self._lock_btn.setText("Lock widgets")
            self._lock_btn.setStyleSheet(_BTN_LOCK)

    def _on_class_color_change(self, key: str) -> None:
        colors = self._config.class_colors()
        colors[key] = self._class_btns[key].color_str()
        self._config.set_class_colors(colors)
        self._config.save()
        self._broadcast_class_colors()

    def _reset_class_colors(self) -> None:
        self._config.set_class_colors({})
        self._config.save()
        for entry in CLASS_ENTRIES:
            self._class_btns[entry["key"]].set_color(entry["default"])
        self._broadcast_class_colors()

    def _broadcast_class_colors(self) -> None:
        colors = self._config.class_colors()
        for _, widget in self._entries:
            try:
                widget.apply_class_colors(colors)
            except AttributeError:
                pass


# ---------------------------------------------------------------------------

from PySide6.QtCore import Signal  # noqa: E402


class _ClassColorBtn(QPushButton):
    color_changed = Signal()

    def __init__(self, hex_color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        c = QColor(hex_color)
        self._color = c if c.isValid() else QColor("#404040")
        self.setFixedHeight(24)
        self._refresh()
        self.clicked.connect(self._pick)

    def _refresh(self) -> None:
        h = self._color.name()
        lum = (self._color.red()*299 + self._color.green()*587 + self._color.blue()*114) // 1000
        txt = "#000" if lum > 128 else "#fff"
        self.setStyleSheet(
            f"QPushButton {{ background:{h}; color:{txt}; border:1px solid #666; "
            f"padding:2px 8px; border-radius:3px; }}"
        )
        self.setText(h.upper())

    def _pick(self) -> None:
        c = QColorDialog.getColor(self._color, self)
        if c.isValid():
            self._color = c
            self._refresh()
            self.color_changed.emit()

    def set_color(self, hex_color: str) -> None:
        c = QColor(hex_color)
        if c.isValid():
            self._color = c
            self._refresh()

    def color_str(self) -> str:
        return self._color.name()


def _sep() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Plain)
    return line
