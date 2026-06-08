"""
lmu_app/utils/theme.py

Design tokens for the "Broadcast" overlay redesign (Direction A).
Drop this in and import from the widgets so every overlay shares one source of
truth. All values map 1:1 to the HTML/CSS reference in the handoff bundle.

Usage:
    from lmu_app.utils.theme import T, qcolor, panel_brush

    p.setBrush(panel_brush(0, 0, h, alpha=self._bg_alpha()))
    p.setPen(border_pen(self._opacity))
    p.drawRoundedRect(0, 0, w, h, T.RADIUS, T.RADIUS)
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPen


def qcolor(hex_or_rgba: str, alpha: int | None = None) -> QColor:
    c = QColor(hex_or_rgba)
    if alpha is not None:
        c.setAlpha(alpha)
    return c


class T:
    # ---- panel ----------------------------------------------------------
    RADIUS = 7
    PANEL_TOP = (28, 30, 34)      # rgba top of vertical gradient (alpha = opacity)
    PANEL_BOT = (13, 14, 16)      # rgba bottom
    BORDER = (255, 255, 255)      # @ ~0.10 alpha, modulated by opacity
    BORDER_ALPHA = 26             # 255 * 0.10
    FAINT = QColor(255, 255, 255, 15)   # separators ~0.06
    TRACK = QColor(255, 255, 255, 26)   # bar tracks ~0.10

    # ---- color ----------------------------------------------------------
    ACCENT = "#ECAA43"
    ACCENT_INK = "#1A1407"
    TEXT = "#F4F1EA"
    DIM = "#908D86"

    # semantic
    GOOD = "#46C86E"
    WARN = "#E0A52A"
    CRIT = "#E0433D"
    COLD = "#4E90FF"
    PURPLE = "#B664FF"          # best lap
    THROTTLE = "#38D06A"
    BRAKE = "#E0433D"
    CLUTCH = "#4A8CE0"

    # positions
    P1 = "#FFD24A"
    P2 = "#CFD3D8"
    P3 = "#D98A44"

    # gaps (relative)
    GAP_AHEAD = "#5AB6FF"
    GAP_BEHIND = "#FF8A55"

    # badges
    PIT_BG, PIT_FG = "#3270C8", "#FFFFFF"
    OUT_BG, OUT_FG = "#BE8200", "#14140A"
    GAR_BG, GAR_FG = "#4A4A4A", "#C8C8C8"

    # vehicle classes (mirror utils/class_colors.py defaults)
    CLASS = {
        "HYPERCAR": "#CC0000", "LMP2": "#1050C8", "LMP3": "#7020C0",
        "GT3": "#00A040", "GTE": "#E06010",
    }

    # ---- type -----------------------------------------------------------
    F_TEXT = "JetBrains Mono"        # names, labels, titles, headers
    F_NUM = "Saira Semi Condensed"   # speed, gear, gaps, lap times, %, °
    LABEL_TRACKING = 114             # PercentageSpacing for uppercase labels (~0.14em)

    # ---- RPM / shift-light bar -----------------------------------------
    RPM_SEGMENTS = 18
    RPM_ZONE_LO = 0.62               # below -> GOOD, below 0.85 -> WARN, else CRIT
    RPM_ZONE_HI = 0.85


def border_pen(opacity_pct: int) -> QPen:
    a = round(T.BORDER_ALPHA * opacity_pct / 100)
    if a <= 0:
        return QPen(Qt.PenStyle.NoPen)
    return QPen(QColor(*T.BORDER, a), 1)


def panel_brush(x: float, y: float, h: float, alpha: int) -> QLinearGradient:
    """Vertical panel gradient; `alpha` from BaseWidget._bg_alpha()."""
    g = QLinearGradient(x, y, x, y + h)
    g.setColorAt(0.0, QColor(*T.PANEL_TOP, alpha))
    g.setColorAt(1.0, QColor(*T.PANEL_BOT, alpha))
    return g


def accent_hairline(w: float) -> QLinearGradient:
    """Top accent line gradient (the Broadcast signature)."""
    g = QLinearGradient(9, 0, w * 0.8, 0)
    g.setColorAt(0.0, QColor(T.ACCENT))
    g.setColorAt(1.0, QColor(0xEC, 0xAA, 0x43, 0))
    return g


def label_font(size: int, weight: QFont.Weight = QFont.Weight.Bold) -> QFont:
    f = QFont(T.F_TEXT, size, weight)
    f.setCapitalization(QFont.Capitalization.AllUppercase)
    f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, T.LABEL_TRACKING)
    return f


def num_font(size: int, weight: QFont.Weight = QFont.Weight.Bold) -> QFont:
    f = QFont(T.F_NUM, size, weight)
    # tabular figures for aligned columns
    f.setStyleHint(QFont.StyleHint.TypeWriter)
    return f


def text_font(size: int, weight: QFont.Weight = QFont.Weight.Medium) -> QFont:
    return QFont(T.F_TEXT, size, weight)


def rpm_seg_color(frac: float) -> QColor:
    """Color of a lit RPM segment at normalized position `frac` (0..1)."""
    if frac < T.RPM_ZONE_LO:
        return QColor(T.GOOD)
    if frac < T.RPM_ZONE_HI:
        return QColor(T.WARN)
    return QColor(T.CRIT)


def draw_panel(p, w: float, h: float, opacity_pct: int, bg_alpha: int,
               accent: bool = True) -> None:
    """Shared panel: gradient fill + border + top accent hairline.
    Call at the top of every widget's paintEvent."""
    p.setBrush(panel_brush(0, 0, h, bg_alpha))
    p.setPen(border_pen(opacity_pct))
    p.drawRoundedRect(0, 0, w, h, T.RADIUS, T.RADIUS)
    if accent:
        p.fillRect(QRectF(9, 0, w - 18, 2), accent_hairline(w))
