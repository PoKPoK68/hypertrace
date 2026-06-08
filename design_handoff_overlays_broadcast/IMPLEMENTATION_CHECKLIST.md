# Checklist d'implémentation — Direction A (Broadcast)

> Donne **un seul item à la fois** à Claude Code (prompts prêts à coller plus bas).
> Ne lui demande PAS « fais tous les overlays » d'un coup — il s'arrête en cours de
> route. Un fichier = un prompt = un commit. Coche au fur et à mesure.

## Ordre d'implémentation

- [ ] **0. Socle** — `lmu_app/utils/theme.py` (déposer le module fourni) +
      `lmu_app/assets/fonts/` (bundler JetBrains Mono + Saira Semi Condensed, les
      charger via `QFontDatabase.addApplicationFont` au démarrage dans `main.py`).
- [ ] **1. `widgets/base.py`** — ajouter le helper `_draw_panel(p, w, h, accent=True)`
      (fond dégradé + bordure + liseré ambre). Ne pas casser opacity/scale/drag.
- [ ] **2. `widgets/speed.py`** — panneau via helper ; barre RPM **18 segments** ;
      vitesse Saira SC ~52 px ; `KM/H` JetBrains Mono dim maj ; rapport ambre ~50 px.
- [ ] **3. `widgets/inputs.py`** — 3 barres T/B/C (dégradé, couleurs throttle/brake/
      clutch) ; volant à **3 branches (90/180/270°, ouvert en haut)** + moyeu, tourné
      de `steering*270°` ; angle dessous.
- [ ] **4. `widgets/fuel.py`** — 2 barres horizontales ; Fuel coloré par niveau
      (crit/warn/ok) ; VE vert ; label JetBrains Mono maj, valeur Saira SC.
- [ ] **5. `widgets/tyres.py`** — grille 2×2 ; remplissage=usure, couleur=temp
      (garder `_temp_color`) ; ajouter code coin `FL/FR/RL/RR`.
- [ ] **5b. `widgets/fuel_calc.py`** — voir `FIXES.md` bloc A (panneau + liseré + theme).
- [ ] **5c. `widgets/ve_calc.py`** — idem (réutilise les helpers de `fuel_calc.py`).
- [ ] **6. `widgets/standings.py`** — noms JetBrains Mono, chiffres Saira SC tabulaire ;
      P1/P2/P3 colorés ; BEST global violet, best joueur vert ; ligne joueur fond
      `accent@16%` ; pastilles de classe ; badges PIT/OUT/GAR. Garder colonnes config.
- [ ] **7. `widgets/relative.py`** — chip position couleur de classe ; écart
      devant bleu / derrière orange / joueur ambre ; ligne joueur surlignée ; badges.
- [ ] **8. `ui/main_window.py`** — fond panneau + bordure ; titre `LMU APP` mono maj ;
      onglets (actif souligné ambre) ; lignes overlay = nom + **engrenage cog** +
      pastille ON/OFF ; restyle toggle FREE/LOCK + case garage. **L'icône doit être un
      vrai cog à dents, pas un cercle à rayons.**

## Critère « terminé » pour chaque widget
1. Le panneau utilise `theme.draw_panel` (rayon 7, liseré ambre).
2. Texte = JetBrains Mono, chiffres = Saira Semi Condensed (tabulaire).
3. Couleurs prises depuis `theme.T` — aucune valeur hex en dur dans le widget.
4. Comportement existant intact (opacity, scale, drag, auto-hide, config dialog).
5. Rendu comparé visuellement à la section « Direction BROADCAST » de
   `LMU Redesign.html` (ouvrir côte à côte).

---

## Prompts prêts à coller (un par étape)

**Étape 0**
> Lis `design_handoff_overlays_broadcast/README.md` et `theme.py`. Copie `theme.py`
> dans `lmu_app/utils/`. Bundle JetBrains Mono et Saira Semi Condensed dans
> `lmu_app/assets/fonts/` et charge-les au démarrage. Ne touche pas encore aux widgets.

**Étape 1**
> Ajoute dans `lmu_app/widgets/base.py` un helper `_draw_panel(self, p, w, h,
> accent=True)` conforme au README (dégradé vertical, bordure modulée par opacity,
> liseré ambre 2px en haut, rayon 7). N'modifie aucun autre widget.

**Étapes 2 à 8** (remplace `<fichier>` / `<section>`)
> Applique la Direction A au widget `<fichier>` en suivant la section
> « <section> » du README et en utilisant `lmu_app/utils/theme.py` + le helper
> `_draw_panel`. Reproduis le rendu de la section « Direction BROADCAST » de
> `LMU Redesign.html`. Ne change rien au comportement (opacity, scale, drag,
> auto-hide, dialogue de config). Ne touche qu'à ce fichier.

Exemple étape 2 :
> Applique la Direction A au widget `lmu_app/widgets/speed.py` en suivant la section
> « 1. Speed & Gear » du README … (etc.)

## Vérification finale
> Lance `python -m lmu_app --mock` et vérifie que les 6 overlays + la fenêtre de
> contrôle s'affichent sans erreur, façon section « Direction BROADCAST ». Liste les
> widgets restés sur l'ancien style, le cas échéant.
