"""Shared vehicle class color + abbreviation logic."""
from __future__ import annotations
from PySide6.QtGui import QColor

# Each entry: config key, keywords, dialog label, short display code, default hex color
CLASS_ENTRIES: list[dict] = [
    {"key": "HYPERCAR", "keywords": ("HYPERCAR", "LMH", "GTP", "HYPER"),
     "label": "Hypercar", "abbrev": "HY",  "default": "#8a1414"},
    {"key": "LMP2",     "keywords": ("LMP2", "P2"),
     "label": "LMP2",    "abbrev": "P2",  "default": "#1040a0"},
    {"key": "LMP3",     "keywords": ("LMP3", "P3"),
     "label": "LMP3",    "abbrev": "P3",  "default": "#501490"},
    {"key": "GT3",      "keywords": ("LMGT3", "GT3", "GTD"),
     "label": "GT3",     "abbrev": "GT3", "default": "#106020"},
    {"key": "GTE",      "keywords": ("GTE", "GT2"),
     "label": "GTE",     "abbrev": "GTE", "default": "#904010"},
    {"key": "UNKNOWN",  "keywords": (),           # catch-all, matched last
     "label": "Unknown class", "abbrev": "",  "default": "#404040"},
]

_ALPHA = 155


def class_color(vclass: str, overrides: dict[str, str] | None = None) -> QColor | None:
    """Return semi-transparent background QColor for a vehicle class string."""
    if not vclass:
        return None
    vc = vclass.strip().upper()

    for entry in CLASS_ENTRIES:
        if not entry["keywords"]:
            continue  # skip catch-all here
        if any(k in vc for k in entry["keywords"]):
            hex_col = (overrides or {}).get(entry["key"], entry["default"])
            c = QColor(hex_col)
            if not c.isValid():
                c = QColor(entry["default"])
            c.setAlpha(_ALPHA)
            return c

    # Unknown class — use override or default grey
    hex_col = (overrides or {}).get("UNKNOWN", CLASS_ENTRIES[-1]["default"])
    c = QColor(hex_col)
    if not c.isValid():
        c = QColor(CLASS_ENTRIES[-1]["default"])
    c.setAlpha(_ALPHA)
    return c


def class_abbrev(vclass: str) -> str:
    """Short code to display in the class column cell."""
    if not vclass:
        return ""
    vc = vclass.strip().upper()
    for entry in CLASS_ENTRIES:
        if not entry["keywords"]:
            continue
        if any(k in vc for k in entry["keywords"]):
            return entry["abbrev"]
    # Unknown: first 3 chars
    return vc[:3]
