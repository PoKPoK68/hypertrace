"""
hypertrace/utils/theme.py

Design tokens for the "Broadcast" overlay redesign (Direction A).
Drop this in and import from the widgets so every overlay shares one source of
truth. All values map 1:1 to the HTML/CSS reference in the handoff bundle.

Usage:
    from hypertrace.utils.theme import T, qcolor, panel_brush

    p.setBrush(panel_brush(0, 0, h, alpha=self._bg_alpha()))
    p.setPen(border_pen(self._opacity))
    p.drawRoundedRect(0, 0, w, h, T.RADIUS, T.RADIUS)
"""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPen


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

    # calculator bar fills
    FUEL_LO = "#1E64D2"
    FUEL_HI = "#4A90E8"
    VE_LO   = "#1C9A4A"
    VE_HI   = "#3FD06A"

    # gaps (relative)
    GAP_AHEAD = "#5AB6FF"
    GAP_BEHIND = "#FF8A55"

    # badges
    PIT_BG, PIT_FG = "#3270C8", "#FFFFFF"
    OUT_BG, OUT_FG = "#BE8200", "#14140A"
    GAR_BG, GAR_FG = "#4A4A4A", "#C8C8C8"
    LAP_BG, LAP_FG = "#FFD700", "#111111"   # pit lap badge: yellow / black

    # main window — ON/OFF pills, lock toggle, danger actions (centralized out
    # of hypertrace/ui/main_window_controls.py, same values as before — no visual
    # change, just one place to look them up)
    TOGGLE_ON        = "#00A040"
    TOGGLE_ON_HOVER  = "#00B848"
    TOGGLE_OFF       = "#CC0000"
    TOGGLE_OFF_HOVER = "#E00000"
    LOCK_TRACK_OFF    = (38, 38, 38)        # _LockToggle rail color at the "FREE" end
    LOCK_TRACK_BORDER = (255, 255, 255, 30)
    CARD_BG_ALPHA     = 10                  # ~0.04 alpha white — grouped-section cards
    DANGER            = "#FF7070"           # delete buttons + armed confirm state

    # vehicle classes (mirror utils/class_colors.py defaults)
    CLASS = {
        "HYPERCAR": "#CC0000", "LMP2": "#1050C8", "LMP3": "#7020C0",
        "GT3": "#00A040", "GTE": "#E06010",
    }

    # ---- type -----------------------------------------------------------
    # The app's single typeface, for every window and every overlay. Both
    # tokens are rewritten at startup by main.py's _load_fonts() with the name
    # Qt actually registered for the bundled file; these values are what they
    # name if that ever fails, so they must stay Montserrat too.
    F_TEXT = "Montserrat"              # names, labels, titles, headers
    F_NUM  = "Montserrat"              # speed, gear, gaps, lap times, %, °
    # No letter tracking: it visibly spaced out short codes (GT3, GAR) and
    # pushed centred single glyphs off-centre.

    # ---- RPM / shift-light bar -----------------------------------------
    RPM_SEGMENTS = 18
    RPM_ZONE_LO = 0.62               # below -> GOOD, below 0.85 -> WARN, else CRIT
    RPM_ZONE_HI = 0.85
    RPM_SHIFT = "#2E8FFF"            # shift-point blink color


def border_pen(opacity_pct: int) -> QPen:
    a = round(T.BORDER_ALPHA * opacity_pct / 100)
    if a <= 0:
        return QPen(Qt.PenStyle.NoPen)
    return QPen(QColor(*T.BORDER, a), 1)


def panel_brush(_x: float, _y: float, _h: float, alpha: int) -> QBrush:
    return QBrush(QColor(*T.PANEL_TOP, alpha))


def accent_hairline(w: float, opacity_pct: int = 100) -> QLinearGradient:
    alpha = round(255 * opacity_pct / 100)
    g = QLinearGradient(9, 0, w * 0.8, 0)
    g.setColorAt(0.0, QColor(0xEC, 0xAA, 0x43, alpha))
    g.setColorAt(1.0, QColor(0xEC, 0xAA, 0x43, 0))
    return g


# Sizes passed to the font helpers below stay expressed in the historical point
# scale, but are applied as *pixels*. Two reasons:
#   - a point size is converted to pixels using the screen DPI and then rounded,
#     so consecutive sizes could rasterise identically (a settings step did
#     nothing) — pixel sizes always differ by at least one pixel;
#   - it makes overlays render identically on machines with different DPI or
#     Windows scaling, instead of silently changing size between them.
# The 4/3 factor is the 96 DPI point→pixel ratio, so on-screen sizes are
# unchanged compared to the previous point-based rendering.
_PX_PER_PT = 4 / 3


def _px(size: float) -> int:
    return max(1, round(size * _PX_PER_PT))


@lru_cache(maxsize=256)
def _label_font_cached(size: float, weight: QFont.Weight, hint: bool) -> QFont:
    f = QFont(T.F_TEXT, -1, weight)
    f.setPixelSize(_px(size))
    if not hint:
        f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    f.setCapitalization(QFont.Capitalization.AllUppercase)
    return f


def label_font(size: float, weight: QFont.Weight = QFont.Weight.Bold,
               hint: bool = True) -> QFont:
    # Every paintEvent used to build a brand new QFont per call — family
    # lookup, feature/hinting setup — dozens of times per repaint across 9
    # overlays. Returning a copy of a cached template keeps that one-time
    # cost to a single construction per distinct size, while still handing
    # each caller its own QFont instance (some call sites mutate the
    # returned font, e.g. standings.py's session-bar capitalization override
    # — mutating the cached template itself would corrupt it for everyone).
    return QFont(_label_font_cached(size, weight, hint))


@lru_cache(maxsize=256)
def _num_font_cached(size: float, weight: QFont.Weight, hint: bool) -> QFont:
    f = QFont(T.F_NUM, -1, weight)
    f.setPixelSize(_px(size))
    f.setStyleHint(QFont.StyleHint.TypeWriter)
    # Tabular figures: every digit gets the same advance, so lap times, gaps and
    # the live delta keep their columns aligned instead of shifting on each
    # update. Proportional fonts (Montserrat) make "1" about half of "0".
    try:
        f.setFeature(QFont.Tag("tnum"), 1)
    except (AttributeError, TypeError, ValueError):
        pass          # older Qt without font-feature support — falls back
    if not hint:
        f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def num_font(size: float, weight: QFont.Weight = QFont.Weight.Bold,
             hint: bool = True) -> QFont:
    return QFont(_num_font_cached(size, weight, hint))


@lru_cache(maxsize=256)
def _text_font_cached(size: float, weight: QFont.Weight, hint: bool) -> QFont:
    f = QFont(T.F_TEXT, -1, weight)
    f.setPixelSize(_px(size))
    f.setStyleHint(QFont.StyleHint.TypeWriter)
    if not hint:
        f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def text_font(size: float, weight: QFont.Weight = QFont.Weight.Bold,
              hint: bool = True) -> QFont:
    return QFont(_text_font_cached(size, weight, hint))


def draw_bold(p, draw, offset: float = 0.5) -> None:
    """Synthetic bold for hint-disabled fonts.

    Disabling hinting keeps round glyphs (the `0`) undistorted at small sizes,
    but it also removes the stem-darkening that made hinted text look bold.
    Re-draw the same text with a sub-pixel horizontal offset so vertical stems
    accumulate coverage — restoring the perceived weight without re-flattening
    the `0`. `draw` is a zero-arg callable that performs the actual p.drawText.
    """
    draw()
    p.save()
    p.translate(offset, 0.0)
    draw()
    p.restore()


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
        p.fillRect(QRectF(9, 0, w - 18, 2), accent_hairline(w, opacity_pct))
