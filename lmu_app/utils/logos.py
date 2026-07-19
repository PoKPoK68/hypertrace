"""lmu_app/utils/logos.py — Shared manufacturer logo loader."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap

_LOGOS_DIR = Path(__file__).resolve().parent.parent / "assets" / "manufacturers"

_index_cache:  dict[str, Path] | None       = None   # brand (lower) → svg path
_scaled_cache: dict[tuple, QPixmap | None]  = {}     # (name, max_w, max_h) → pixmap


def _index() -> dict[str, Path]:
    """Build brand → file map once. Filenames follow 'Brand=<Name>.<ext>'.

    Vector is preferred, but PNG is supported too: some 'SVG' logos are really a
    raster image wrapped in an SVG (pattern + embedded base64), which Qt's
    SVG 1.2 Tiny renderer cannot draw — those are shipped as plain PNG instead.
    """
    global _index_cache
    if _index_cache is None:
        idx: dict[str, Path] = {}
        if _LOGOS_DIR.is_dir():
            for pattern in ("*.png", "*.svg"):      # svg last → wins if both exist
                for path in _LOGOS_DIR.glob(pattern):
                    brand = path.stem.split("=", 1)[-1].strip().lower()
                    if brand:
                        idx[brand] = path
        _index_cache = idx
    return _index_cache


def _match(vehicle_name: str) -> Path | None:
    """Longest brand name contained in the vehicle name wins (e.g. so
    'Mercedes-AMG' is preferred over a hypothetical 'Mercedes')."""
    vn = vehicle_name.lower()
    best: Path | None = None
    best_len = 0
    for brand, path in _index().items():
        if brand in vn and len(brand) > best_len:
            best, best_len = path, len(brand)
    return best


def _render(path: Path, max_w: int, max_h: int) -> QPixmap | None:
    """Rasterise the SVG *at* the requested size, preserving aspect ratio.

    Drawing from vector straight to the target resolution keeps logos sharp at
    any size. The previous loader rasterised at the source size and then scaled
    down, which is what made them look blurry.
    """
    if path.suffix.lower() != ".svg":
        # Raster source: only ever scale DOWN, upscaling would just blur it.
        raw = QPixmap(str(path))
        if raw.isNull():
            return None
        if raw.width() <= max_w and raw.height() <= max_h:
            return raw
        return raw.scaled(max_w, max_h,
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)

    try:
        from PySide6.QtSvg import QSvgRenderer
    except ImportError:
        return None

    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        return None

    box = renderer.viewBoxF()
    vw, vh = box.width(), box.height()
    if vw <= 0 or vh <= 0:                      # no viewBox → fall back
        size = renderer.defaultSize()
        vw, vh = size.width(), size.height()
    if vw <= 0 or vh <= 0:
        return None

    scale = min(max_w / vw, max_h / vh)
    w = max(1, round(vw * scale))
    h = max(1, round(vh * scale))

    px = QPixmap(w, h)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, w, h))
    painter.end()
    return px


def get_logo(vehicle_name: str, max_w: int = 24, max_h: int = 20) -> QPixmap | None:
    """Return a manufacturer logo pixmap fitting within max_w × max_h, or None."""
    if not vehicle_name:
        return None
    key = (vehicle_name, max_w, max_h)
    if key in _scaled_cache:
        return _scaled_cache[key]
    path = _match(vehicle_name)
    px = _render(path, max_w, max_h) if path is not None else None
    _scaled_cache[key] = px
    return px
