# Polices — où utiliser quoi (Direction A « Broadcast »)

Le système n'utilise que **DEUX polices**. La règle est simple :

| Famille | Sert à | Style |
|---|---|---|
| **JetBrains Mono** | Tout le **TEXTE** : noms, labels, titres, en-têtes de colonnes, onglets | 400 / 500 / 700. Labels & titres en **MAJUSCULES**, interlettrage ≈ 0.14em |
| **Saira Semi Condensed** | Tous les **NOMBRES** : vitesse, rapport, écarts, chronos, %, °C, litres, badges | 600 / 700, **chiffres tabulaires** (`tabular-nums`) |

> Règle mnémotechnique : **lettres = JetBrains Mono, chiffres = Saira Semi Condensed.**
> Un même widget mélange les deux (ex. un nom de pilote en mono + son chrono en Saira).

## Installation
Bundler les TTF dans `lmu_app/assets/fonts/` et les charger au démarrage (`main.py`)
AVANT de créer la fenêtre :
```python
from PySide6.QtGui import QFontDatabase
from pathlib import Path

FONTS = Path(__file__).parent / "assets" / "fonts"
for f in ["JetBrainsMono-Regular.ttf", "JetBrainsMono-Medium.ttf", "JetBrainsMono-Bold.ttf",
          "SairaSemiCondensed-SemiBold.ttf", "SairaSemiCondensed-Bold.ttf"]:
    QFontDatabase.addApplicationFont(str(FONTS / f))
```
- JetBrains Mono → https://www.jetbrains.com/lp/mono/
- Saira Semi Condensed → Google Fonts (https://fonts.google.com/specimen/Saira+Semi+Condensed)

Dans le code, utilise les helpers de `theme.py` plutôt que `QFont(...)` en dur :
- `theme.label_font(size)` → JetBrains Mono, MAJ, tracking (labels/titres/en-têtes)
- `theme.text_font(size)` → JetBrains Mono casse normale (noms de pilotes)
- `theme.num_font(size)` → Saira Semi Condensed tabulaire (tous les chiffres)

---

## Détail par widget

### Speed & Gear
- Vitesse `248` → **Saira SC** ~52 px bold
- `KM/H` → **JetBrains Mono** 11 px (label dim, MAJ)
- Rapport `4` → **Saira SC** ~50 px bold (ambre)

### Inputs
- Valeurs `86 / 0 / 0` (T/B/C) → **Saira SC**
- Lettres `T / B / C` et angle `-76°` : angle → **Saira SC** (chiffre) ; lettres → JetBrains Mono

### Fuel & VE (barres simples)
- `FUEL`, `VIRTUAL ENERGY` → **JetBrains Mono** (label MAJ)
- `58.4 L`, `61 %` → **Saira SC**

### Fuel Calculator / VE Calculator
- En-têtes `USAGE / LAPS / REFUEL / FINISH`, labels `LAST / AVG 5 / FUEL RATIO`,
  `FUEL` / `VE` → **JetBrains Mono** (MAJ, dim)
- Toutes les valeurs du tableau (`3.2L`, `18.3`, `+14L`, `0.59`, `58.4 L`, `61 %`…)
  → **Saira SC** tabulaire

### Tyres
- Codes coin `FL / FR / RL / RR` → **JetBrains Mono** 8 px
- Température `88°` et usure `93%` → **Saira SC**

### Standings
- En-têtes `DRIVER / GAP / INT / BEST / LAST` → **JetBrains Mono** (MAJ dim)
- Noms de pilotes (`B. HARTLEY`…) → **JetBrains Mono** ~13 px
- Position, écarts, chronos (`+1.2`, `3:24.123`…) → **Saira SC** tabulaire
- Pastille de classe (`HYP`) et nom de classe → **JetBrains Mono**
- Badges `PIT / OUT / GAR` → **Saira SC**

### Relative
- Noms → **JetBrains Mono**
- Chip position (`5`) et écarts (`-1.6`, `+2.3`) → **Saira SC**

### Fenêtre de contrôle (main_window)
- Titre `LMU APP`, onglets, noms d'overlays, libellés (`Hide overlays in garage`,
  `FREE / LOCK`) → **JetBrains Mono**
- Pastilles `ON / OFF` → **JetBrains Mono** (ce sont des mots, pas des nombres)

---

## À éviter
- ❌ Ne pas mettre les chiffres en JetBrains Mono « parce que c'est mono » — l'aligne-
  ment vient de `tabular-nums` sur **Saira SC**, c'est voulu.
- ❌ Ne pas laisser la police système (`Consolas`/`Courier`) si les TTF ne se chargent
  pas : vérifier que `addApplicationFont` retourne un id ≥ 0 au démarrage.
- ❌ Pas d'autre famille. Deux polices, point.
