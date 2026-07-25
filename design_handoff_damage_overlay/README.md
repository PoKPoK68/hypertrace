# Handoff: Damage Overlay (LMU App — Broadcast)

## Overview
Overlay temps réel affichant l'état des dégâts de la voiture dans Le Mans Ultimate,
sous forme d'une **vue de dessus** de la voiture. La silhouette est découpée en
**17 zones** (carrosserie, coins, roues, suspensions, + aileron arrière) ; chaque zone change de couleur selon la gravité des dégâts. Il s'intègre
à la suite d'overlays LMU existante (Speed, Inputs, Fuel, Tyres, Standings, Relative)
et suit la direction visuelle **Broadcast** (ambre WEC/TV, rayon 2–7px, liseré ambre en haut).

## About the Design Files
Les fichiers de ce bundle sont des **références de design en HTML/CSS/JS** — un prototype
montrant l'apparence et le comportement voulus, **pas** du code à copier tel quel.
L'app cible est en **Python / PySide6 (QPainter)** : la tâche est de **recréer ce design
comme un widget overlay PySide6** (ex. `widgets/damage.py`), sur le même modèle que les
autres overlays du projet, en réutilisant les tokens de `utils/theme.py`.
Tout le dessin est volontairement fait de primitives transposables en QPainter :
rectangles arrondis, lignes/arcs stroke, remplissages pleins, texte.

## Fidelity
**Hi-fi.** Couleurs, proportions, épaisseurs de trait et géométrie sont finales.
Reproduire fidèlement la vue de dessus et le code couleur des zones.

## Screen / View — « Damage »

> **17 zones au total** : les 16 zones de dégât d'origine + l'aileron arrière (`wing-rear`),
> ajouté comme élément distinct.

### Purpose
Le pilote voit d'un coup d'œil quelles parties de la voiture sont endommagées et à
quel point (carrosserie, coins, roues, suspensions).

### Layout
- Panneau overlay unique `.ov` (tokens Broadcast), padding **12px**.
- Contient uniquement la voiture (SVG), centrée. Aucun texte, légende ou score.
- Le SVG a un **viewBox `0 0 230 300`** (portrait), rendu à **150px de large** (hauteur auto).
- La voiture pointe vers le **haut** (avant = haut, arrière = bas).

### Silhouette (fond, non-interactif)
Rectangle arrondi à **rayon constant 28**, remplissage `rgba(255,255,255,.025)`, sans trait.
Path :
`M86,34 L144,34 A28,28 0 0 1 172,62 L172,238 A28,28 0 0 1 144,266 L86,266 A28,28 0 0 1 58,238 L58,62 A28,28 0 0 1 86,34 Z`

### Les 16 zones (interactives, colorées par gravité)
Chaque zone a un `data-zone`, un niveau `0..3`, et une géométrie fixe (coords viewBox 230×300).

**Carrosserie (4)** — trait `stroke-width:7`, `stroke-linecap:round`, `fill:none` :
| id | label | path |
|---|---|---|
| `body-front` | Carrosserie AV | `M91,34 L139,34` |
| `body-rear`  | Carrosserie AR | `M91,266 L139,266` |
| `body-left`  | Flanc gauche   | `M58,117 L58,183` |
| `body-right` | Flanc droit    | `M172,117 L172,183` |

Le flanc n'est **plus une ligne continue** : il est interrompu (deux extrémités séparées,
aucun tracé) à l'endroit de chaque passage de roue avant/arrière — pas une encoche qui
contourne la roue, un vrai trou dans la carrosserie, avec ~4 unités de dégagement de
chaque côté de la roue pour ne pas la toucher.

**Coins (4)** — mêmes réglages de trait, arcs de rayon 28 :
| id | label | path |
|---|---|---|
| `corner-fl` | Coin AV-G | `M58.4,57.1 A28,28 0 0 1 81.1,34.4` |
| `corner-fr` | Coin AV-D | `M148.9,34.4 A28,28 0 0 1 171.6,57.1` |
| `corner-rl` | Coin AR-G | `M81.1,265.6 A28,28 0 0 1 58.4,242.9` |
| `corner-rr` | Coin AR-D | `M171.6,242.9 A28,28 0 0 1 148.9,265.6` |

Les segments carrosserie/coins laissent un **gap constant (~10 unités viewBox)** entre eux :
ils ne se touchent jamais.

**Roues (4)** — `<rect>` **pleins** (remplissage opaque), `rx:5`, `width:22 height:42`, `stroke-width:2.5` :
| id | label | x | y |
|---|---|---|---|
| `wheel-fl` | Roue AV-G | 52 | 66 |
| `wheel-fr` | Roue AV-D | 156 | 66 |
| `wheel-rl` | Roue AR-G | 52 | 192 |
| `wheel-rr` | Roue AR-D | 156 | 192 |

Les roues sont positionnées **à fleur de la carrosserie** : leur bord extérieur affleure
le flanc (avec un léger débord vers l'extérieur, ~6 unités), et elles sont centrées
verticalement sur le trou découpé dans le flanc (voir ci-dessus), pas sur l'ancien repère
de la ligne de carrosserie.

**Suspensions (4)** — wishbone à deux branches, `stroke-width:4`, `fill:none`, `stroke-linecap:round`.
Elles **frôlent** la carrosserie et la roue sans les chevaucher :
| id | label | path |
|---|---|---|
| `susp-fl` | Susp. AV-G | `M89,79 L77,87 M89,97 L77,87` |
| `susp-fr` | Susp. AV-D | `M141,79 L153,87 M141,97 L153,87` |
| `susp-rl` | Susp. AR-G | `M89,205 L77,213 M89,223 L77,213` |
| `susp-rr` | Susp. AR-D | `M141,205 L153,213 M141,223 L153,213` |

Chaque suspension est un chevron à deux branches dont la **pointe reste accrochée à la
roue** (convergent vers un point côté roue) et dont l'écartement est ancré côté châssis ;
translatée en bloc avec sa roue, la forme/le sens ne changent jamais, seule la position glisse.

**Aileron arrière (1)** — élément **en plus** du pare-chocs arrière (ne le remplace pas).
Forme **pleine** (classe `dz-wing`, `stroke:none`, couleur appliquée au `fill`), arrondi
**asymétrique** : coins hauts très ronds (r=5.5), coins bas quasi droits (r=2) :
| id | label | path |
|---|---|---|
| `wing-rear` | Aileron AR | `M65,277 L165,277 A7,7 0 0 1 172,284 L172,288.5 A2.5,2.5 0 0 1 169.5,291 L60.5,291 A2.5,2.5 0 0 1 58,288.5 L58,284 A7,7 0 0 1 65,277 Z` |

### Code couleur (par niveau de gravité)
`COLORS = ['#3f434a', '#e0a52a', '#e8701c', '#e0433d']`
- **0 — sain** : `#3f434a` (gris neutre)
- **1 — léger** : `#e0a52a` (ambre)
- **2 — moyen** : `#e8701c` (orange)
- **3 — grave** : `#e0433d` (rouge)

Application par zone :
- Carrosserie / coins / suspensions : la couleur s'applique au **trait** (`stroke`).
- Roues **et aileron arrière** : la couleur s'applique au **remplissage plein** (`fill`).
- Roues : la couleur s'applique au **remplissage plein** (`fill`), y compris au niveau 0
  (roue toujours pleine, gris neutre sans dégât).
- **Niveau 3 uniquement** : ajouter un halo `drop-shadow(0 0 4px <couleur>)` sur la zone.

## Interactions & Behavior
- **Runtime (app réelle)** : chaque zone est pilotée par la télémétrie ; mettre à jour
  `state[zone] = 0..3` et redessiner. Pas d'interaction utilisateur nécessaire.
- **Dans le prototype (démo seulement)** : cliquer une zone fait défiler sa gravité
  `0→1→2→3→0`. À supprimer côté app — c'est juste pour visualiser.
- Transition douce `stroke/fill/filter 120ms` (optionnel en QPainter).

## State Management
- Modèle : `state` = dict `{ zoneId: level(0..3) }` pour les 16 zones (voir `ORDER` dans le HTML).
- Alimenté par les données de dégâts du jeu (par zone).
- Redessin à chaque tick télémétrie.

## Design Tokens (Broadcast, depuis `utils/theme.py` / `overlays.css`)
- Accent ambre : `#ecaa43`
- Fond panneau : `rgba(13,14,16,.90)` + dégradé `--bg-grad`
- Bordure : `rgba(255,255,255,.10)`, rayon panneau **7px**, liseré ambre haut (2px)
- Texte : `#f4f1ea`, dim : `#908d86`
- Polices : texte `JetBrains Mono`, chiffres `Saira SemiCondensed`
- Couleurs gravité : voir `COLORS` ci-dessus
- Silhouette : fill `rgba(255,255,255,.025)`, rayon **28**
- Traits : carrosserie/coins 7 · suspensions 4 · roues 2.5 · aileron 11

## Assets
Aucun asset externe. Toute la voiture est dessinée en primitives SVG (transposables QPainter).
Polices Google : `JetBrains Mono`, `Saira Semi Condensed`.

## Files
- `Damage Overlay.html` — prototype complet (silhouette + 16 zones + démo de clic).
  La géométrie et les couleurs exactes sont dans le `<script>` (`ZONES`, `WHEELS`, `ORDER`, `COLORS`, `LABELS`).
- `overlays.css` — design system des overlays (tokens des 4 directions ; utiliser `.dir-broadcast`).
