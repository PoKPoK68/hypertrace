"""lmu_app/utils/logos.py — Shared manufacturer logo loader."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

_LOGOS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "brandlogo"
_raw_cache:    dict[str, QPixmap | None]   = {}   # vehicle_name → raw full-res pixmap
_scaled_cache: dict[tuple, QPixmap | None] = {}   # (name, max_w, max_h) → scaled pixmap


def _load_raw(vehicle_name: str) -> QPixmap | None:
    """Load and cache the full-resolution source PNG for a vehicle."""
    if vehicle_name in _raw_cache:
        return _raw_cache[vehicle_name]
    vn_lower  = vehicle_name.lower()
    best_path = None
    best_len  = 0
    for path in _LOGOS_DIR.glob("*.png"):
        brand = path.stem.lower()
        if brand in vn_lower and len(brand) > best_len:
            best_path = path
            best_len  = len(brand)
    raw = QPixmap(best_path.as_posix()) if best_path else None
    if raw is not None and raw.isNull():
        raw = None
    _raw_cache[vehicle_name] = raw
    return raw


def get_logo(vehicle_name: str, max_w: int = 24, max_h: int = 20) -> QPixmap | None:
    """Return a manufacturer logo pixmap that fits within max_w × max_h.

    Only scales DOWN from the source resolution — never upscales, which would
    introduce blur. The caller is responsible for enabling SmoothPixmapTransform
    on the QPainter when drawing the returned pixmap at a different size.
    """
    if not vehicle_name:
        return None
    key = (vehicle_name, max_w, max_h)
    if key in _scaled_cache:
        return _scaled_cache[key]
    raw = _load_raw(vehicle_name)
    if raw is None:
        _scaled_cache[key] = None
        return None
    # If the source already fits within the target box, use it as-is (no upscale).
    if raw.width() <= max_w and raw.height() <= max_h:
        px = raw
    else:
        px = raw.scaled(max_w, max_h,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
    _scaled_cache[key] = px
    return px
