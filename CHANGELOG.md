# Changelog

Toutes les modifications notables sont documentées ici.  
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/)

---

## [0.1.0]

### Ajouté

#### Widget Tyres (`widgets/tyres.py`)
- Grille 2×2 affichant les 4 pneus (FL, FR, RL, RR) sans label de position
- Température carcasse colorée dynamiquement : bleu (froid) → vert (optimal) → rouge (chaud)
- Barre d'usure avec pourcentage optionnel (`show_wear_pct`)
- Affichage de la pression en kPa (désactivé par défaut)
- Seuils de température entièrement configurables (Cold / Optimal from-to / Hot)
- Hauteur du widget adaptée automatiquement aux rangées activées
- Enregistré dans `main.py` sous la clé `tyres`

#### Standings (`widgets/standings.py`)
- **Classement multi-classe** : classes plus rapides (Hypercar > LMP2 > LMP3 > GTE > GT3) affichées au-dessus du joueur, classes plus lentes en dessous
- Pilotes en garage affichés avec badge **GAR** ; section masquée uniquement si *tous* les pilotes de la classe sont en garage
- Section **Laps** dans les paramètres : nombre de décimales configurable séparément pour Best lap et Last lap
- **Font size** (7–14) : hauteur de ligne, largeur des colonnes et largeur du badge s'adaptent dynamiquement
- Colonne Fuel affichée pour tous les pilotes (pas uniquement ceux avec énergie virtuelle)
- `_class_rank()` pour ordonner les sections de classe
- Fonctions `_char_px()`, `_badge_px()`, `_row_h()`, `_col_w()`, `_total_w()` paramétrées par `font_size`
- `_fmt_lap()` avec 0 décimales retourne `"1:23"`, avec N décimales retourne `"1:23.456"`

#### Relative (`widgets/relative.py`)
- Numéro affiché = **position dans la classe** (non le classement général)
- Largeur des colonnes nom et badge adaptées au `font_size` via `_char_px()` et `_badge_px()`
- Hauteur de ligne dynamique via `_row_h(font_size)`

#### Inputs (`widgets/inputs.py`)
- Taille de base réduite : `BASE_W=128, BASE_H=88`
- Barres T/B/C et rayon du volant recalibrés proportionnellement
- Marges gauche/droite rééquilibrées (8 px de chaque côté)

#### Config dialog (`ui/widget_config_dialog.py`)
- Bouton **✕** (effacer l'image de volant) : règle CSS `#icon_btn` avec `padding: 0px` pour rendre le caractère visible + tooltip explicatif ajouté
- Widget de réordonnancement (`ordered_multiselect`) vertical sans cases à cocher : n'affiche que les colonnes activées
- Cases enable/disable des colonnes déplacées dans leur section de paramètre respective (Gaps, Display…) via `show_keys`
- En-tête de section renommé "Column order" ; label redondant supprimé
- Filtre des valeurs obsolètes dans `_OrderedMultiSelectWidget.__init__` (supprime les colonnes inconnues chargées depuis un ancien config)

#### API (`api/reader.py`)
- Champ `fuel: float` ajouté sur `VehicleScoringEntry` (litres, tous pilotes)
- `TyreData` : champs `temp_carcass`, `wear`, `pressure`, `brake_temp` exposés et alimentés par `LMUReader` et `MockReader`

#### Performance (`widgets/base.py`)
- Vérification du timestamp du snapshot dans `BaseWidget._update()` : `on_data` n'est appelé que si les données ont réellement changé depuis le dernier tick, supprimant tous les repaints inutiles en pause ou pendant le chargement

#### Fondations
- Architecture de base : `BaseWidget`, `DataReader`, `LMUReader`, `MockReader`
- Widgets initiaux : Speed, Inputs, Fuel, Standings, Relative
- Fenêtre de contrôle principale (`MainWindow`) avec activation/désactivation par widget
- `AppConfig` : persistance des positions et paramètres en JSON
- `WidgetConfigDialog` : dialogue de configuration générique piloté par `CONFIG_SCHEMA`
- Sections collapsibles dans le dialogue de configuration
- Mode `--mock` pour tester sans Le Mans Ultimate lancé
- Support drag & drop et verrouillage des overlays
- Badge PIT / OUT / GAR dans Standings et Relative
- Outlap tracking dans Relative
