"""lmu_app/ui/class_colors_dialog.py — Class color configuration panel."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from lmu_app.utils.class_colors import CLASS_ENTRIES

if TYPE_CHECKING:
    from lmu_app.config import AppConfig


class ClassColorsDialog(QDialog):
    """
    Lets users customise the background colour per vehicle class.
    Changes apply immediately to all widgets passed in `widgets`.
    """

    def __init__(
        self,
        config: AppConfig,
        widgets: list,          # list of BaseWidget-like objects
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config  = config
        self._widgets = widgets
        self._buttons: dict[str, _ColorButton] = {}

        self.setWindowTitle("Class Colors")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(300)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(14, 14, 14, 14)

        title = QLabel("Vehicle Class Colors")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffd700;")
        root.addWidget(title)

        sub = QLabel("Colors are applied automatically based on car class name.")
        sub.setStyleSheet("color: #888; font-size: 11px;")
        root.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(8)
        saved = self._config.class_colors()

        for entry in CLASS_ENTRIES:
            key     = entry["key"]
            current = saved.get(key, entry["default"])
            btn     = _ColorButton(current)
            btn.color_changed.connect(lambda _, k=key: self._on_color_change(k))
            self._buttons[key] = btn
            lbl = QLabel(entry["label"])
            lbl.setStyleSheet("color: #ddd;")
            form.addRow(lbl, btn)

        root.addLayout(form)

        # Bottom buttons
        hl = QHBoxLayout()
        reset_btn = QPushButton("Reset to defaults")
        reset_btn.clicked.connect(self._reset)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        hl.addWidget(reset_btn)
        hl.addStretch()
        hl.addWidget(close_btn)
        root.addLayout(hl)

    def _on_color_change(self, key: str) -> None:
        colors = self._config.class_colors()
        colors[key] = self._buttons[key].color_str()
        self._config.set_class_colors(colors)
        self._config.save()
        self._broadcast()

    def _reset(self) -> None:
        self._config.set_class_colors({})
        self._config.save()
        for entry in CLASS_ENTRIES:
            self._buttons[entry["key"]].set_color(entry["default"])
        self._broadcast()

    def _broadcast(self) -> None:
        colors = self._config.class_colors()
        for w in self._widgets:
            try:
                w.apply_class_colors(colors)
            except AttributeError:
                pass


# ---------------------------------------------------------------------------

from PySide6.QtCore import Signal   # noqa: E402  (after class to avoid circular at top)


class _ColorButton(QPushButton):
    color_changed = Signal()

    def __init__(self, hex_color: str = "#333333", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor(hex_color) if QColor(hex_color).isValid() else QColor("#333333")
        self._refresh()
        self.clicked.connect(self._pick)

    def _refresh(self) -> None:
        h = self._color.name()
        lum = (self._color.red()*299 + self._color.green()*587 + self._color.blue()*114) // 1000
        txt = "#000" if lum > 128 else "#fff"
        self.setStyleSheet(
            f"QPushButton {{ background:{h}; color:{txt}; border:1px solid #666; "
            f"padding:3px 10px; border-radius:3px; min-width:80px; }}"
        )
        self.setText(h.upper())

    def _pick(self) -> None:
        c = QColorDialog.getColor(self._color, self, "Pick class color")
        if c.isValid():
            self._color = c
            self._refresh()
            self.color_changed.emit()

    def set_color(self, hex_color: str) -> None:
        self._color = QColor(hex_color) if QColor(hex_color).isValid() else self._color
        self._refresh()

    def color_str(self) -> str:
        return self._color.name()
