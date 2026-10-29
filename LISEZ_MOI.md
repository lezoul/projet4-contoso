# Projet 4 · Mise à jour du 6 octobre 2026 : passage aux ventes complètes

Ce dossier contient uniquement les fichiers **modifiés ou ajoutés**. Il se dépose par-dessus le dossier du projet, en gardant la même arborescence.

## Contenu

```
Projet4_mise_a_jour_2026-10-06/
├── LISEZ_MOI.md                      ce fichier
├── Connexion.py                      MODIFIÉ : extrait aussi les ventes complètes (étape 6)
├── Exploration_promotions.py         MODIFIÉ : dates SQL au format AAAAMMJJ
├── src/
│   ├── config.py                     MODIFIÉ : deux sources de ventes, variable SOURCE_VENTES
│   └── etl.py                        MODIFIÉ : lecture de l'une ou l'autre source
├── notebooks/1_preparation/
│   ├── 00_inventaire.ipynb           MODIFIÉ : nouvelle section 9 (périmètre et justification)
│   ├── 01_etl.ipynb                  inchangé, réexécuté sur les ventes complètes
│   ├── 02_flocon.ipynb               deux commentaires mis à jour, réexécuté
│   ├── 03_diagnostic.ipynb           MODIFIÉ : règle R5 analysée, sections 9 et 11 mises à jour
│   ├── 04_nettoyage.ipynb            MODIFIÉ : nouvelle règle N6
│   └── 05_variables.ipynb            MODIFIÉ : textes mis à jour, réexécuté
├── data/raw/contoso/Sales_complet/   NOUVEAU : 8 fichiers, un par trimestre (376 234 lignes)
│   ├── Sales 2020 T1.csv ... Sales 2020 T4.csv
│   └── Sales 2021 T1.csv ... Sales 2021 T4.csv
└── reports/livrables/L1_L2_phases_backlog/
    └── L2_backlog_taches_v2.xlsx     NOUVEAU : backlog mis à jour (la version remise le 5 octobre n'est pas touchée)
```

## Backlog mis à jour (`L2_backlog_taches_v2.xlsx`)

| Élément | Avant | Après |
|---|---|---|
| User stories | 33 (175 points) | 37 (198 points) |
| Tâches | 166 (282,5 h) | 185 (315,5 h) |
| Priorités | 31 Must, 2 Should | 29 Must, 4 Should, 4 Could |

- **US34 (Must, Sprint 1)** : passage aux ventes complètes, tâches T167 à T174 (7 terminées, 1 à faire : le report dans Jira).
- **US35 (Should, Sprint 4)** : rentabilité nette par boutique avec les charges du plan stratégique, tâches T175 à T179.
- **US36 (Should, Sprint 4)** : dépenses de publicité face aux promotions, tâches T180 à T182.
- **US37 (Could, Sprint 4)** : détail des ventes en ligne pour comprendre les remises, tâches T183 à T185.
- **US28, US30, US32** : passées de Must à Could. Ce sont les seules qui peuvent ne pas être faites sans manquer à une consigne de l'énoncé (voir l'onglet Changements). Proposition à confirmer en équipe.
- Nouvel onglet **Changements** : la liste datée de tout ce qui a bougé, avec une colonne « Statut dans Jira ».

**Jira n'est pas encore à jour** : un membre de l'équipe doit y reporter ces changements (tâche T174) en suivant l'onglet Changements.

## Installation

1. Copier le contenu de ce dossier dans le dossier du projet, en acceptant de remplacer les fichiers.
2. Ne rien supprimer dans `data/raw/contoso/Sales` : les six fichiers du professeur et le fichier `FactSales_cles_canal_devise.csv` y restent. Ils servent à la comparaison de `00_inventaire` et au canal de vente.
3. Il n'est pas nécessaire d'avoir la base Contoso ni de lancer `Connexion.py` : les ventes complètes sont déjà dans `Sales_complet`.
4. Exécuter les notebooks dans l'ordre, avec « Run All » : `00_inventaire`, `01_etl`, `02_flocon`, `03_diagnostic`, `04_nettoyage`, `05_variables`.

## Ce qu'il faut obtenir après exécution

| Contrôle | Valeur attendue |
|---|---|
| Lignes de vente | 376 234 |
| Chiffre d'affaires brut de la source | 1 466 593 660 $ |
| Boutiques / produits / promotions | 56 / 2 508 / 14 |
| Validation de `04_nettoyage` | 24 contrôles réussis sur 24 |
| Lignes corrigées par la règle N6 | 386 |
| Chiffre d'affaires brut après nettoyage | 1 466 593 660 $ (inchangé : N6 ne modifie que la quantité remisée) |
| Colonnes de `fait_ventes_variables.parquet` | 66 |

## Revenir au périmètre du professeur

Dans `src/config.py`, mettre `SOURCE_VENTES = "professeur"`, puis relancer les notebooks.

## Remarque sur les sorties déjà affichées

Les notebooks sont livrés exécutés. Les chemins affichés dans les sorties sont ceux de la machine d'exécution : ils seront remplacés par les vôtres au premier « Run All ».
