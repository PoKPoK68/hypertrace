# Handoff — LMU App : refonte des overlays (Direction A « Broadcast »)

## Vue d'ensemble
Refonte visuelle des 6 overlays de télémétrie de **LMU App** (Le Mans Ultimate)
et de la fenêtre de contrôle. La direction retenue est **A — « Broadcast »** :
look graphique TV endurance, fond sombre translucide, accent **ambre**, texte en
**mono** et chiffres en **condensé tabulaire**. Le but : remplacer le rendu actuel
(fond `(10,10,10)`, mono partout, barres plates, hiérarchie faible) par un système
cohérent et lisible.

## À propos des fichiers de design
Les fichiers de ce bundle sont des **références de design réalisées en HTML/CSS**
(`LMU Redesign.html`, `overlays.css`, `widgets.js`). **Ce ne sont pas des fichiers
à copier tels quels.** L'app cible est en **Python / PySide6**, rendue en
**QPainter** dans des sous-classes de `BaseWidget`. La tâche est donc de **porter la
direction A dans les widgets QPainter existants** (`lmu_app/widgets/*.py`,
`lmu_app/ui/main_window.py`), en réutilisant les patterns du dépôt.

Tout le design a été pensé pour être **fidèlement reproductible en QPainter** :
uniquement des rectangles arrondis, dégradés linéaires, traits, texte et formes
géométriques simples — rien qui demande du CSS impossible à porter.

Ouvre `LMU Redesign.html` dans un navigateur, va sur la section **« Direction
BROADCAST »** : c'est la cible pixel-perfect. (Les sections B/C/D sont des
alternatives écartées — ignore-les.)

## Fidélité
**Haute fidélité.** Couleurs, typographies, tailles, rayons et espacements sont
définitifs. Reproduis-les au pixel près avec QPainter.

---

## Design tokens (Direction A)

Centralise-les dans un nouveau module `lmu_app/utils/theme.py` (un starter prêt à
l'emploi est fourni dans ce bundle : `theme.py`). Toutes les valeurs ci-dessous en
sont extraites.

### Panneau (fond commun à tous les overlays)
| Token | Valeur |
|---|---|
| Fond (dégradé vertical) | haut `rgba(28,30,34,0.92)` → bas `rgba(13,14,16,0.92)` |
| Bordure | `rgba(255,255,255,0.10)`, 1 px |
| Rayon des coins | **7 px** |
| Liseré d'accent (signature) | trait **2 px** en haut, encart 9 px G/D, dégradé `#ECAA43` → transparent (≈80 %) |

> L'**opacité** existante (slider 0–100 %) doit continuer à moduler le fond ET la
> bordure, comme aujourd'hui dans `BaseWidget._bg_alpha()` / `_border_pen()`.

### Couleurs
| Rôle | Hex |
|---|---|
| Accent (ambre) | `#ECAA43` |
| Accent ink (texte sur ambre) | `#1A1407` |
| Texte | `#F4F1EA` |
| Texte atténué (dim) | `#908D86` |
| Séparateur (faint) | `rgba(255,255,255,0.06)` |
| Piste de barre (track) | `rgba(255,255,255,0.10)` |

#### Sémantique (états — partagés)
| Rôle | Hex |
|---|---|
| OK / vert | `#46C86E` |
| Warn / ambre | `#E0A52A` |
| Critique / rouge | `#E0433D` |
| Froid / bleu | `#4E90FF` |
| Meilleur tour (violet) | `#B664FF` |
| Throttle | `#38D06A` |
| Brake | `#E0433D` |
| Clutch | `#4A8CE0` |

#### Couleurs de classe (inchangées vs `utils/class_colors.py`)
HYP `#CC0000` · LMP2 `#1050C8` · LMP3 `#7020C0` · GT3 `#00A040` · GTE `#E06010`

### Typographie
**Deux familles, à bundler en TTF** (`lmu_app/assets/fonts/`, chargées via
`QFontDatabase.addApplicationFont` au démarrage) :

| Usage | Police | Détails |
|---|---|---|
| **Texte** (noms, labels, titres, en-têtes de colonnes, onglets) | **JetBrains Mono** | poids 400/500/700 |
| **Chiffres** (vitesse, rapport, écarts, chronos, %, °C, badges) | **Saira Semi Condensed** | poids 600/700, **chiffres tabulaires** (`font-variant-numeric: tabular-nums`) |

Labels/titres : **MAJUSCULES**, interlettrage ≈ **0.14 em** (en QPainter : utiliser
`QFont.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 114)` ou un
`setCapitalization(QFont.AllUppercase)`).

Téléchargement : JetBrains Mono → https://www.jetbrains.com/lp/mono/ ·
Saira Semi Condensed → Google Fonts.

---

## Mapping CSS → QPainter

### Helper panneau (à factoriser dans `BaseWidget`)
Ajoute une méthode partagée qui dessine le fond + bordure + liseré d'accent, pour
arrêter de répéter le `drawRoundedRect` dans chaque widget :

```python
# dans BaseWidget
def _draw_panel(self, p: QPainter, w: int, h: int, accent: bool = True) -> None:
    # fond : dégradé vertical
    g = QLinearGradient(0, 0, 0, h)
    a = self._bg_alpha()
    g.setColorAt(0.0, QColor(28, 30, 34, a))
    g.setColorAt(1.0, QColor(13, 14, 16, a))
    p.setBrush(g)
    p.setPen(self._border_pen())          # rgba(255,255,255,0.10) modulé par opacity
    p.drawRoundedRect(0, 0, w, h, 7, 7)   # rayon 7
    # liseré d'accent en haut (signature Broadcast)
    if accent:
        ag = QLinearGradient(9, 0, w * 0.8, 0)
        ag.setColorAt(0.0, QColor(0xEC, 0xAA, 0x43))
        ag.setColorAt(1.0, QColor(0xEC, 0xAA, 0x43, 0))
        p.fillRect(QRectF(9, 0, w - 18, 2), ag)
```
> Remplace dans chaque widget l'appel `p.drawRoundedRect(0,0,w,h,8,8)` actuel par
> `self._draw_panel(p, w, h)`. Note le passage du rayon **8 → 7**.

### Barre RPM / shift-lights segmentée (`speed.py`)
Au lieu de la barre pleine actuelle, dessiner **18 segments** :
- nb allumés = `round(ratio * 18)`
- couleur par zone selon la position `f = i / 17` : `f < 0.62` → vert `#46C86E`,
  `f < 0.85` → ambre `#E0A52A`, sinon rouge `#E0433D`
- segment éteint = `track` `rgba(255,255,255,0.10)`
- Broadcast : hauteur ≈ 7 px, gap 1 px, 1er/dernier segment arrondis (3 px)

```python
n, lit = 18, round(ratio * 18)
seg_w = (bar_w - (n - 1) * gap) / n
for i in range(n):
    f = i / (n - 1)
    if i < lit:
        col = QColor("#46C86E") if f < 0.62 else QColor("#E0A52A") if f < 0.85 else QColor("#E0433D")
    else:
        col = QColor(255, 255, 255, 26)   # track
    p.setBrush(col); p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(bar_x + i * (seg_w + gap), bar_y, seg_w, bar_h), 1, 1)
```

### Barres remplies (inputs / fuel / tyres)
Dégradé léger (couleur pleine → +30 % de luminosité côté extrémité), coins arrondis
suivant le sens de remplissage, sur une piste `track`. Les valeurs (%, L, °C, %usure)
sont en **Saira Semi Condensed** par-dessus.

---

## Écrans / widgets (specs détaillées)

> Tailles données à l'échelle de référence du mockup ; en jeu elles sont multipliées
> par le slider `scale` existant. Conserve les ratios.

### 1. Speed & Gear — `widgets/speed.py`
- Panneau ~232×80. Padding 10/12.
- En haut : **barre RPM segmentée** (voir ci-dessus).
- Bas-gauche : **vitesse** en Saira Semi Condensed **bold ~52 px**, `#F4F1EA`,
  suivie de `KM/H` en JetBrains Mono 11 px `#908D86` (majuscule, tracking 0.14em).
- Bas-droite : **rapport** en Saira Semi Condensed bold ~50 px, **accent `#ECAA43`**
  (`N` au neutre, `R` en marche arrière).

### 2. Inputs — `widgets/inputs.py`
- Panneau ~212×88. À gauche : 3 barres verticales **T/B/C** (track + remplissage
  dégradé) ; valeur 0–100 au-dessus (couleur de l'entrée), lettre en dessous (dim).
  Throttle `#38D06A`, Brake `#E0433D`, Clutch `#4A8CE0`.
- À droite : **volant** = anneau (stroke ~6) + **3 branches** à **90°, 180°, 270°**
  (droite, bas, gauche — ouvert en haut) + moyeu central, le tout tourné de
  `steering * 270°`. Angle affiché dessous (ex. `-76°`).
  Rim `#D8D2C4` pour Broadcast.

### 3. Fuel & Virtual Energy — `widgets/fuel.py`
- 2 barres horizontales (h ~26, rayon 5). Label à gauche (JetBrains Mono 10 px maj,
  blanc, ombre portée), valeur à droite (Saira SC bold 14 px).
- Fuel : couleur selon niveau — `<10 %` rouge `#E0433D`, `<25 %` ambre `#E0A52A`,
  sinon bleu (dégradé `#1E64D2`→`#4A90E8`).
- VE : vert (dégradé `#1C9A4A`→`#3FD06A`).
- Le masquage auto de la ligne VE (absence de système VE) reste comme aujourd'hui.

### 4. Tyres — `widgets/tyres.py`
- Grille 2×2, cellules ~33×52 (rayon 4), gap ~7. Remplissage = usure (monte du bas),
  **couleur = température** (logique `_temp_color` conservée : froid bleu → opt vert
  → chaud orange/rouge). Temp en haut, % usure en bas (Saira SC, ombre portée).
- **Ajout** : petit code coin `FL/FR/RL/RR` en haut-gauche, JetBrains Mono 8 px,
  `rgba(255,255,255,0.55)`.

### 5. Standings (multi-classe) — `widgets/standings.py`
- Colonnes : `POS | DRIVER | GAP | INT | BEST | LAST` (ordre/visibilité configurables
  comme aujourd'hui). En-têtes en JetBrains Mono 9 px maj, dim, tracking 0.14em.
- Noms pilotes en **JetBrains Mono** ~13 px ; chiffres (écarts, chronos) en **Saira
  SC** tabulaire. Hauteur de ligne ≈ `font_size + 11`.
- Position : P1 `#FFD24A`, P2 `#CFD3D8`, P3 `#D98A44`, sinon dim.
- Meilleur tour global : **BEST** en violet `#B664FF`. Best du joueur : vert `#46C86E`.
- **Ligne joueur** : fond `accent @ 16 %` (`rgba(236,170,67,0.16)`), rayon 3.
- En-tête de classe : pastille couleur de classe (texte blanc, `HYP`…) + nom de
  classe en dim. Séparateur = trait `faint`.
- Badges (dans la colonne nom) : `PIT` fond `#3270C8`/texte blanc · `OUT` fond
  `#BE8200`/texte `#14140A` · `GAR` gris. Saira SC 8 px, rayon 2.

### 6. Relative — `widgets/relative.py`
- Colonnes : `chip position (couleur de classe) | nom | écart`.
- Écart **devant** bleu `#5AB6FF`, **derrière** orange `#FF8A55`, **joueur** accent.
- Ligne joueur surlignée comme dans Standings ; nom du joueur en accent.
- Mêmes badges PIT/OUT que Standings.

### 7. Fenêtre de contrôle — `ui/main_window.py`
- Même fond panneau (dégradé) + bordure, rayon ~9.
- Barre de titre : point accent + `LMU APP` (JetBrains Mono, maj, tracking 0.14em).
- Onglets `Overlays` / `Class Colors` : actif souligné en accent ambre.
- Chaque ligne overlay : nom (JetBrains Mono 13 px) + **bouton engrenage** (vrai
  **cog** à dents — PAS un soleil/rayons) + pastille **ON/OFF** (ON = vert
  `#46C86E @ ~22 %` fond + bord + texte clair ; OFF = rouge équivalent).
- Toggle **FREE/LOCK** et case « Hide overlays in garage » : conserver le
  comportement, restyler aux mêmes tokens.

> ⚠️ **Icône engrenage** : l'icône actuelle (cercle + rayons) ressemble à un soleil.
> La remplacer par un véritable cog à dents avec trou central (voir `gearSvg()` dans
> `widgets.js`, ou un `QPainterPath` de roue dentée).

---

## Interactions & comportement
Aucune nouvelle interaction. On conserve l'existant : drag pour repositionner, lock,
auto-hide hors piste / au garage, polling `QTimer`, dialogues de config par widget,
sliders opacity/scale, sélecteur de couleurs de classe. **Refonte purement visuelle.**

## Fichiers de ce bundle
- `LMU Redesign.html` — référence interactive (ouvre la section « Direction BROADCAST »).
- `overlays.css` — toutes les valeurs exactes (tokens `.dir-broadcast`, composants `.ov-*`).
- `widgets.js` — markup de chaque overlay + scénario de données + `gearSvg()` (le cog).
- `theme.py` — module de tokens Python prêt à déposer dans `lmu_app/utils/`.

## Fichiers à modifier dans le dépôt
`lmu_app/widgets/base.py` (helper panneau), `speed.py`, `inputs.py`, `fuel.py`,
`tyres.py`, `standings.py`, `relative.py`, `ui/main_window.py`, et nouveau
`lmu_app/utils/theme.py`.
