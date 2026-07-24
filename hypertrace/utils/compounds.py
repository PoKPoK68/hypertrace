"""Shared tire compound badge utilities (shared memory only — no REST API)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter

# mCompoundType values from lmu_enum.LMUCompoundType
COMP_TYPE_TO_NAME: dict[int, str] = {0: "Soft", 1: "Medium", 2: "Hard", 3: "Wet"}

_COMP_COLORS: dict[str, tuple[str, str]] = {
    "S": ("#FFFFFF", "#111111"),   # Soft   → blanc
    "M": ("#F5C518", "#111111"),   # Medium → jaune
    "H": ("#CC0000", "#FFFFFF"),   # Hard   → rouge
    "W": ("#4488CC", "#FFFFFF"),   # Wet    → bleu
}


def comp_letter(name: str) -> str:
    n = name.strip().upper()
    if "SOFT"  in n:              return "S"
    if "MED"   in n:              return "M"
    if "HARD"  in n:              return "H"
    if "WET"   in n or "INTER" in n: return "W"
    return n[:1] if n else ""


def draw_compound_badge(p: QPainter, cx: float, cy: float,
                        comps: list[str], r: int = 11) -> None:
    """Dessine un badge composé centré en (cx, cy).
    4 pneus identiques → grand cercle avec lettre.
    Pneus différents → grille 2×2 de petits disques colorés.
    """
    letters = [comp_letter(c) for c in comps]
    valid   = [l for l in letters if l]
    if not valid:
        return
    all_same = len(set(valid)) == 1

    p.setPen(Qt.PenStyle.NoPen)
    if all_same:
        # Colour alone identifies the compound — the letter was unreadable at
        # this size anyway (white / yellow / red / blue = S / M / H / W).
        bg, _fg = _COMP_COLORS.get(valid[0], ("#777777", "#FFFFFF"))
        p.setBrush(QColor(bg))
        p.drawEllipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
    else:
        dot = max(5, r - 2)
        gap = 2
        ox  = cx - dot - gap / 2
        oy  = cy - dot - gap / 2
        positions = [
            (ox,             oy),
            (ox + dot + gap, oy),
            (ox,             oy + dot + gap),
            (ox + dot + gap, oy + dot + gap),
        ]
        for i, (px_, py_) in enumerate(positions):
            L = letters[i] if i < len(letters) else ""
            bg, _ = _COMP_COLORS.get(L, ("#AAAAAA", "#FFFFFF"))
            p.setBrush(QColor(bg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(px_, py_, dot, dot))
