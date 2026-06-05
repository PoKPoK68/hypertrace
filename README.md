# LMU App

Overlay de télémétrie moderne pour **Le Mans Ultimate**.

Inspiré de TinyPedal, avec une UI repensée de zéro.

## Prérequis

- Python 3.11+
- Le Mans Ultimate (Windows ou Linux)
- Dans LMU : **Settings → Gameplay → Enable Plugins** = ON

## Installation

```bash
# 1. Cloner le projet
git clone https://github.com/vous/lmu-overlay.git
cd lmu-overlay

# 2. Récupérer la lib shared memory LMU
git submodule add https://github.com/TinyPedal/pyLMUSharedMemory.git pyLMUSharedMemory
# (ou copier les fichiers manuellement depuis le repo pyLMUSharedMemory)

# 3. Créer un virtualenv et installer les dépendances
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\activate.bat      # Windows

pip install -e ".[dev]"
```

## Lancement

```bash
# Avec LMU lancé :
python -m lmu_app

# Mode offline (données simulées, sans LMU) :
python -m lmu_app --mock

# Options :
python -m lmu_app --mock --hz 60 --verbose
```

## Tests

```bash
pytest
```

## Structure du projet

```
lmu_app/
├── api/
│   └── reader.py        # DataReader, LMUReader, MockReader, LMUSnapshot
├── modules/             # Modules de calcul (fuel, delta, sector...)
├── widgets/
│   ├── base.py          # BaseWidget (overlay Qt)
│   └── speed.py         # Widget vitesse/gear/RPM
├── ui/                  # Fenêtre de configuration principale
└── utils/               # Helpers divers
pyLMUSharedMemory/       # Submodule — lib shared memory LMU
tests/
pyproject.toml
```

## Widgets disponibles

| Clé         | Description                                          |
|-------------|------------------------------------------------------|
| `speed`     | Vitesse, rapport, RPM                                |
| `inputs`    | Throttle / Brake / Clutch + volant rotatif           |
| `fuel`      | Carburant & énergie virtuelle                        |
| `standings` | Classement multi-classe en temps réel                |
| `relative`  | Proximité des pilotes sur la piste                   |
| `tyres`     | Température carcasse & usure des 4 pneus             |

---

## Changelog

### 2026-06-05

#### Nouveau widget — Tyres (`widgets/tyres.py`)
- Grille 2×2 (FL, FR, RL, RR) sans labels de position
- Température carcasse colorée : bleu (froid) → vert (optimal) → rouge (chaud)
- Barre d'usure avec % optionnel (`show_wear_pct`)
- Pression optionnelle en kPa (`show_pressure`)
- Seuils de température configurables (Cold / Optimal from-to / Hot)
- Hauteur automatique selon les rangées actives

#### Standings (`widgets/standings.py`)
- Classement multi-classe : classes plus rapides affichées **au-dessus** du joueur (Hypercar > LMP2 > LMP3 > GTE > GT3), classes plus lentes en dessous
- Drivers en garage affichés avec badge **GAR** ; section de classe masquée seulement si **tous** ses pilotes sont en garage
- Section **Laps** dans les paramètres : décimales configurables séparément pour Best lap et Last lap
- Font size (7–14) : hauteur de ligne, largeur des colonnes et largeur du badge s'adaptent dynamiquement
- Fuel affiché pour tous les pilotes (pas uniquement le joueur VE)

#### Relative (`widgets/relative.py`)
- Numéro affiché = **position dans la classe**, non le classement général
- Largeur des colonnes et du badge adaptées au `font_size`
- Font size (7–14) avec hauteur de ligne dynamique

#### Inputs (`widgets/inputs.py`)
- Taille de base réduite (`BASE_W=128, BASE_H=88`)
- Marges gauche/droite rééquilibrées (8 px de chaque côté)

#### Config dialog (`ui/widget_config_dialog.py`)
- Bouton **✕** (effacer le chemin de l'image de volant) : padding CSS corrigé + tooltip ajouté
- Widget de réordonnancement vertical sans cases à cocher ; n'affiche que les colonnes activées
- Les cases enable/disable des colonnes sont dans leur section de paramètre respective

#### Performance (`widgets/base.py`)
- Vérification du timestamp du snapshot : `on_data` n'est appelé que si les données ont changé depuis le dernier tick, supprimant les repaints inutiles en pause/chargement

#### API (`api/reader.py`)
- Champ `fuel` ajouté sur `VehicleScoringEntry` (litres, tous pilotes)
- `TyreData` : champs `temp_carcass`, `wear`, `pressure`, `brake_temp` exposés

---

## Roadmap

Voir la roadmap complète dans `docs/roadmap.md`.
