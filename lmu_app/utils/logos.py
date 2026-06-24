"""lmu_app/utils/logos.py — Shared manufacturer logo loader."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

_LOGOS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "brandlogo"
_logo_cache: dict[tuple, QPixmap | None] = {}


def get_logo(vehicle_name: str, max_w: int = 24, max_h: int = 20) -> QPixmap | None:
    """Return a scaled manufacturer logo pixmap for the given vehicle model name, or None."""
    if not vehicle_name:
        return None
    key = (vehicle_name, max_w, max_h)
    if key in _logo_cache:
        return _logo_cache[key]
    vn_lower  = vehicle_name.lower()
    best_path = None
    best_len  = 0
    for p in _LOGOS_DIR.glob("*.png"):
        brand = p.stem.lower()
        if brand in vn_lower and len(brand) > best_len:
            best_path = p
            best_len  = len(brand)
    if best_path:
        raw = QPixmap(best_path.as_posix())
        px  = raw.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation) if not raw.isNull() else None
    else:
        px = None
    _logo_cache[key] = px
    return px
