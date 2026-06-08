# Correctifs — points relevés après 1ʳᵉ implémentation

Trois soucis + un oubli de cadrage (les **calculateurs** n'étaient pas dans le lot
initial). Donne chaque bloc à Claude Code séparément.

---

## A. Liseré ambre manquant sur les calculateurs Fuel & VE
**Cause :** `widgets/fuel_calc.py` et `widgets/ve_calc.py` n'étaient pas dans la
checklist — ils dessinent encore leur panneau « à l'ancienne »
(`p.drawRoundedRect(0, 0, w, h, 8, 8)` sur fond `(10,10,10)`), donc pas de liseré.

**Correctif :** migrer les deux vers le helper de panneau, comme les autres widgets.

1. Dans **`fuel_calc.py`** et **`ve_calc.py`**, remplacer dans `paintEvent` :
   ```python
   p.setBrush(QColor(10, 10, 10, self._bg_alpha()))
   p.setPen(self._border_pen())
   p.drawRoundedRect(0, 0, self._w, self._layout_h, 8, 8)
   ```
   par :
   ```python
   from lmu_app.utils import theme
   theme.draw_panel(p, self._w, self._layout_h, self._opacity, self._bg_alpha())
   ```
2. Migrer les **helpers partagés** de `fuel_calc.py` (utilisés aussi par `ve_calc.py`)
   vers les tokens `theme.T` :
   - `_draw_bar` / `_draw_level` : piste `theme.T.TRACK`, couleurs fuel/VE depuis
     `theme.T` (`FUEL_OK`→bleu `#1E64D2`/`#4A90E8`, VE vert `#1C9A4A`/`#3FD06A`),
     **label** en `theme.label_font(...)` (JetBrains Mono maj), **valeur** en
     `theme.num_font(...)` (Saira Semi Condensed).
   - en-têtes de colonnes (`USAGE/LAPS/REFUEL/FINISH`) et labels de ligne
     (`LAST/AVG 5/FUEL RATIO`) : `theme.label_font` dim.
   - valeurs du tableau : `theme.num_font`, couleur `theme.T.TEXT` (et `GOOD` pour `OK`).
   - séparateur : `theme.T.FAINT` au lieu de `_C_SEP`.
3. Cible visuelle : artboards **« Fuel Calculator »** et **« VE Calculator »** de la
   section « Direction BROADCAST » dans `LMU Redesign.html` (markup de référence dans
   `widgets.js` → `renderFuelCalc` / `renderVeCalc`, styles `.ov-calc*` dans
   `overlays.css`).

> Astuce : les hauteurs de barres passent de 8 px de rayon à **5 px**, et le rayon de
> panneau de 8 → **7** (déjà géré par `theme.draw_panel`).

---

## B. La case à cocher n'a pas de « coche »
**Où :** `ui/main_window.py`, le `QCheckBox` « Hide overlays in garage ».

**Correctif (idiomatique Qt) :** bundler `lmu_app/assets/check.svg` (fourni ci-dessous)
puis styler l'indicateur :
```python
self._garage_cb.setStyleSheet("""
QCheckBox { color: #F4F1EA; font-family: 'JetBrains Mono'; font-size: 12px; spacing: 9px; }
QCheckBox::indicator {
    width: 15px; height: 15px; border-radius: 3px;
    border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.03);
}
QCheckBox::indicator:checked {
    background: #ECAA43; border-color: #ECAA43;
    image: url(lmu_app/assets/check.svg);
}
""")
```
`assets/check.svg` (coche couleur « accent-ink » `#1A1407`, lisible sur l'ambre) :
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">
  <path d="M3.5 8.5l3 3 6-7" fill="none" stroke="#1A1407"
        stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```
> Si le chemin relatif pose souci au runtime, charge le SVG via une ressource Qt
> (`.qrc`) ou un chemin absolu `Path(__file__).parent.parent / "assets" / "check.svg"`.

---

## C. Le bouton de verrouillage n'est pas le bon
**Où :** `ui/main_window.py`, classe `_LockToggle` (l'ancien pictogramme cadenas
vert→or sur le bouton).

**Cible :** un pill propre aux tokens Direction A — piste **neutre** en FREE, **ambre**
en LOCK, pastille coulissante claire→ambre-ink. Remplace `_LockToggle.paintEvent` par :
```python
def paintEvent(self, _):
    p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    W, H, t = self._W, self._H, self._t
    pad = 3; knob_d = H - pad * 2; travel = W - pad * 2 - knob_d

    # piste : FREE = neutre translucide -> LOCK = ambre plein
    def lerp(a, b): return round(a + (b - a) * t)
    track = QColor(lerp(38, 0xEC), lerp(38, 0xAA), lerp(38, 0x43), lerp(40, 255))
    p.setBrush(track); p.setPen(QPen(QColor(255, 255, 255, 30), 1))
    p.drawRoundedRect(0, 0, W, H, H // 2, H // 2)

    # pastille : claire en FREE, ambre-ink en LOCK
    knob_x = pad + int(travel * t)
    p.setBrush(QColor(0x1A, 0x14, 0x07) if t > 0.5 else QColor(0xF4, 0xF1, 0xEA))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(knob_x, pad, knob_d, knob_d)
    p.end()
```
Et la légende à côté (`_LockToggle` est suivi d'un `QLabel` dans `main_window`) doit
dire `FREE — overlays draggable` / `LOCK — overlays fixed` selon l'état, en JetBrains
Mono dim 11 px. (Garde la logique d'animation `_step`/`_timer` existante.)

> Tu peux conserver un mini-cadenas si tu y tiens, mais la maquette mise une lecture
> par **couleur + position** plutôt qu'un pictogramme.

---

## Prompts à coller (un par bloc)
1. > Migre `lmu_app/widgets/fuel_calc.py` et `ve_calc.py` vers `lmu_app/utils/theme.py`
   > + `theme.draw_panel`, en suivant le bloc A de `FIXES.md`. Reproduis les artboards
   > « Fuel Calculator » / « VE Calculator » de la section BROADCAST de `LMU Redesign.html`.
   > Ne touche qu'à ces deux fichiers (+ helpers partagés qu'ils contiennent).
2. > Applique le bloc B de `FIXES.md` à la checkbox « Hide overlays in garage » dans
   > `ui/main_window.py` (ajoute `assets/check.svg`).
3. > Applique le bloc C de `FIXES.md` : restyle `_LockToggle.paintEvent` et sa légende
   > dans `ui/main_window.py`.
